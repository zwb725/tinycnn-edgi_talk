from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import torch
from executorch.devtools.backend_debug import get_delegation_info
from torchao.quantization.pt2e.quantize_pt2e import convert_pt2e, prepare_pt2e

from executorch.backends.arm.ethosu import EthosUCompileSpec, EthosUPartitioner
from executorch.backends.arm.quantizer import (
    EthosUQuantizer,
    get_symmetric_quantization_config,
)
from executorch.exir import (
    EdgeCompileConfig,
    ExecutorchBackendConfig,
    to_edge_transform_and_lower,
)
from executorch.extension.export_util.utils import save_pte_program

from tinycnn.export_ethosu import (
    CALIBRATION_SAMPLES,
    ensure_quantized_ops_loaded,
    qdq_nodes,
    tensor_data,
)
from tinycnn.model import create_model


PROJECT_DIR = Path(__file__).resolve().parent
VARIANT_ROOT = PROJECT_DIR / "build" / "variants"
DEFAULT_TARGET = "ethos-u55-128"
DEFAULT_SYSTEM_CONFIG = "Ethos_U55_High_End_Embedded"
DEFAULT_MEMORY_MODE = "Shared_Sram"
DEFAULT_SEED = 20260716

PTE_FILENAMES = {
    "default": "tinycnn_default.pte",
    "size": "tinycnn_size.pte",
    "input_64": "tinycnn_input_64.pte",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export custom TinyCNN ExecuTorch/Ethos-U variants."
    )
    parser.add_argument("--variant", required=True, help="Variant name.")
    parser.add_argument("--input-size", type=int, default=96, help="Square H/W size.")
    parser.add_argument(
        "--optimise",
        choices=("Default", "Size", "Performance"),
        default="Default",
        help="Vela optimisation strategy. Default leaves Vela default behaviour unchanged.",
    )
    parser.add_argument("--target", default=DEFAULT_TARGET)
    parser.add_argument("--system-config", default=DEFAULT_SYSTEM_CONFIG)
    parser.add_argument("--memory-mode", default=DEFAULT_MEMORY_MODE)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=VARIANT_ROOT,
        help="Root directory for variant build outputs.",
    )
    return parser.parse_args()


def input_shape(input_size: int) -> tuple[int, int, int, int]:
    if input_size <= 0:
        raise ValueError(f"input-size must be positive, got {input_size}")
    return (1, 3, input_size, input_size)


def create_example_input(shape: tuple[int, int, int, int]) -> torch.Tensor:
    generator = torch.Generator()
    generator.manual_seed(DEFAULT_SEED)
    return torch.rand(shape, generator=generator, dtype=torch.float32)


def parameter_count(model: torch.nn.Module) -> int:
    return sum(param.numel() for param in model.parameters())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def calibrate(prepared_model: torch.fx.GraphModule, shape: tuple[int, int, int, int]) -> None:
    generator = torch.Generator()
    generator.manual_seed(DEFAULT_SEED)
    with torch.no_grad():
        for index in range(CALIBRATION_SAMPLES):
            sample = torch.rand(shape, generator=generator, dtype=torch.float32)
            prepared_model(sample)
            if (index + 1) % 8 == 0:
                print(f"Calibration: {index + 1}/{CALIBRATION_SAMPLES}")


def vela_extra_flags(optimise: str) -> list[str]:
    if optimise == "Default":
        return []
    return [f"--optimise={optimise}"]


def parse_delegation_summary(summary: str) -> dict[str, int]:
    result = {
        "delegated_subgraphs": 0,
        "delegated_nodes": 0,
        "non_delegated_nodes": 0,
    }
    patterns = {
        "delegated_subgraphs": r"Total delegated subgraphs:\s*(\d+)",
        "delegated_nodes": r"Number of delegated nodes:\s*(\d+)",
        "non_delegated_nodes": r"Number of non-delegated nodes:\s*(\d+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, summary)
        if match:
            result[key] = int(match.group(1))
    return result


def dataframe_rows(delegation_info: Any) -> list[dict[str, Any]]:
    df = delegation_info.get_operator_delegation_dataframe()
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        rows.append(
            {
                "op_type": str(row["op_type"]),
                "delegated": int(row["occurrences_in_delegated_graphs"]),
                "non_delegated": int(row["occurrences_in_non_delegated_graphs"]),
            }
        )
    return rows


def write_delegated_subgraphs(edge_graph_module: torch.fx.GraphModule, path: Path) -> None:
    chunks: list[str] = []
    for node in edge_graph_module.graph.nodes:
        if node.op != "get_attr" or not node.name.startswith("lowered_module_"):
            continue
        lowered_module = getattr(edge_graph_module, node.name)
        chunks.append(f"## {node.name}\n")
        chunks.append(str(lowered_module.original_module.graph))
        chunks.append("\n")
    if not chunks:
        chunks.append("No lowered_module_* subgraphs were found.\n")
    path.write_text("\n".join(chunks), encoding="utf-8")


def parse_vela_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return {}
    row = rows[0]
    parsed: dict[str, Any] = {}
    for key, value in row.items():
        if value is None or value == "":
            parsed[key] = value
            continue
        try:
            number = float(value)
            if number.is_integer():
                parsed[key] = int(number)
            else:
                parsed[key] = number
        except ValueError:
            parsed[key] = value
    return parsed


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "None."
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    lines.extend("| " + " | ".join(str(item) for item in row) + " |" for row in rows)
    return "\n".join(lines)


def write_variant_reports(
    *,
    variant_dir: Path,
    metadata: dict[str, Any],
    quant_nodes: list[str],
    operator_rows: list[dict[str, Any]],
) -> None:
    report_dir = variant_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    quant_report = "\n".join(
        [
            f"# TinyCNN Variant Quantization Report: {metadata['variant']}",
            "",
            f"- Input shape: `{tuple(metadata['input_shape'])}`",
            f"- Calibration samples: `{metadata['calibration_samples']}` fixed random tensors",
            f"- Quantized ops library: `{metadata['quantized_ops_library']}`",
            f"- FP32 output: `{metadata['fp32_output']}`",
            f"- PT2E INT8 output: `{metadata['quantized_output']}`",
            f"- FP32 Top-1: `{metadata['fp32_top1']}`",
            f"- INT8 Top-1: `{metadata['quantized_top1']}`",
            f"- Max absolute error: `{metadata['max_abs_error']}`",
            "",
            "## Quantize / Dequantize Nodes",
            "",
            "\n".join(f"- `{node}`" for node in quant_nodes) if quant_nodes else "None found.",
            "",
        ]
    )
    (report_dir / "quantization_report.md").write_text(quant_report, encoding="utf-8")

    delegation_report = "\n".join(
        [
            f"# TinyCNN Variant Delegation Report: {metadata['variant']}",
            "",
            metadata["delegation_summary"].strip(),
            "",
            "## Operator Delegation",
            "",
            markdown_table(
                ["op_type", "delegated", "non_delegated"],
                [[row["op_type"], row["delegated"], row["non_delegated"]] for row in operator_rows],
            ),
            "",
            "## TOSA / Vela Artifacts",
            "",
            "\n".join(f"- `{item}`" for item in metadata["artifacts"]),
            "",
        ]
    )
    (report_dir / "delegation_report.md").write_text(delegation_report, encoding="utf-8")


def main() -> None:
    args = parse_args()
    shape = input_shape(args.input_size)
    variant_dir = args.output_root / args.variant
    intermediate_dir = variant_dir / "intermediates"
    report_dir = variant_dir / "reports"
    pte_path = variant_dir / PTE_FILENAMES.get(args.variant, f"tinycnn_{args.variant}.pte")
    quantized_graph_path = report_dir / "quantized_graph.txt"
    edge_graph_path = report_dir / "edge_lowered_graph.txt"
    delegated_subgraphs_path = report_dir / "delegated_subgraphs.txt"
    metadata_path = variant_dir / "metadata.json"

    variant_dir.mkdir(parents=True, exist_ok=True)
    intermediate_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    quantized_ops_library = ensure_quantized_ops_loaded()
    if quantized_ops_library is not None:
        print("Loaded quantized ops library:", quantized_ops_library)

    model = create_model()
    example_input = create_example_input(shape)
    example_inputs = (example_input,)

    with torch.no_grad():
        fp32_output = model(example_input)

    print("=" * 64)
    print(f"Variant      : {args.variant}")
    print(f"Input shape  : {tuple(example_input.shape)}")
    print(f"Output shape : {tuple(fp32_output.shape)}")
    print(f"Optimise     : {args.optimise}")
    print("FP32 output  :", fp32_output)
    print("FP32 Top-1   :", int(fp32_output.argmax(dim=1).item()))
    print("=" * 64)

    exported_program = torch.export.export(model, example_inputs)
    graph_module = exported_program.module(check_guards=False)
    print("torch.export completed")

    compile_spec = EthosUCompileSpec(
        target=args.target,
        system_config=args.system_config,
        memory_mode=args.memory_mode,
        extra_flags=vela_extra_flags(args.optimise),
    )
    compile_spec.dump_intermediate_artifacts_to(str(intermediate_dir))
    print("Ethos-U compile spec created")
    print("Compiler flags:", compile_spec.compiler_flags)

    quantizer = EthosUQuantizer(compile_spec)
    quantizer.set_global(get_symmetric_quantization_config())
    prepared_model = prepare_pt2e(graph_module, quantizer)
    print("PT2E prepare completed")

    calibrate(prepared_model, shape)
    quantized_model = convert_pt2e(prepared_model)
    print("PT2E convert completed")

    with torch.no_grad():
        quantized_output = quantized_model(example_input)

    max_abs_error = (fp32_output - quantized_output).abs().max().item()
    fp32_top1 = int(fp32_output.argmax(dim=1).item())
    quantized_top1 = int(quantized_output.argmax(dim=1).item())
    print("=" * 64)
    print("Quantized output:", quantized_output)
    print("FP32 Top-1       :", fp32_top1)
    print("INT8 Top-1       :", quantized_top1)
    print("Max abs error    :", max_abs_error)
    print("=" * 64)

    quantized_graph_path.write_text(str(quantized_model.graph), encoding="utf-8")
    quant_nodes = qdq_nodes(quantized_model)

    quantized_exported_program = torch.export.export(quantized_model, example_inputs)
    print("Quantized graph exported")

    partitioner = EthosUPartitioner(compile_spec)
    edge_program_manager = to_edge_transform_and_lower(
        quantized_exported_program,
        partitioner=[partitioner],
        compile_config=EdgeCompileConfig(_check_ir_validity=False),
    )
    edge_graph_module = edge_program_manager.exported_program().graph_module
    edge_graph_path.write_text(str(edge_graph_module.graph), encoding="utf-8")
    write_delegated_subgraphs(edge_graph_module, delegated_subgraphs_path)
    delegation_info = get_delegation_info(edge_graph_module)
    delegation_summary = delegation_info.get_summary().strip()
    delegate_counts = parse_delegation_summary(delegation_summary)
    operator_rows = dataframe_rows(delegation_info)
    print("Ethos-U partition and Vela lowering completed")
    print(delegation_summary)

    executorch_program_manager = edge_program_manager.to_executorch(
        config=ExecutorchBackendConfig(extract_delegate_segments=False)
    )
    print("ExecuTorch program generated")

    save_pte_program(executorch_program_manager, str(pte_path), output_dir=str(variant_dir))
    if not pte_path.exists():
        raise RuntimeError(f"PTE was not generated: {pte_path}")
    if pte_path.stat().st_size == 0:
        raise RuntimeError(f"PTE file is empty: {pte_path}")

    vela_summary_path = intermediate_dir / "output" / f"out_summary_{args.system_config}.csv"
    artifacts = [str(path) for path in sorted(intermediate_dir.rglob("*")) if path.is_file()]
    vela_summary = parse_vela_summary(vela_summary_path)

    metadata: dict[str, Any] = {
        "variant": args.variant,
        "input_shape": list(shape),
        "parameter_count": parameter_count(model),
        "target": args.target,
        "system_config": args.system_config,
        "memory_mode": args.memory_mode,
        "optimise": args.optimise,
        "vela_extra_flags": vela_extra_flags(args.optimise),
        "compiler_flags": list(compile_spec.compiler_flags),
        "calibration_samples": CALIBRATION_SAMPLES,
        "seed": DEFAULT_SEED,
        "quantized_ops_library": str(quantized_ops_library) if quantized_ops_library else "already registered",
        "fp32_output": tensor_data(fp32_output),
        "quantized_output": tensor_data(quantized_output),
        "output_shape": list(quantized_output.shape),
        "fp32_top1": fp32_top1,
        "quantized_top1": quantized_top1,
        "max_abs_error": max_abs_error,
        "pte_path": str(pte_path),
        "pte_size_bytes": pte_path.stat().st_size,
        "pte_sha256": sha256_file(pte_path),
        "intermediate_dir": str(intermediate_dir),
        "vela_summary_path": str(vela_summary_path),
        "vela_summary": vela_summary,
        "delegation_summary": delegation_summary,
        "operator_delegation_rows": operator_rows,
        "artifacts": artifacts,
        **delegate_counts,
    }

    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    (variant_dir / "export_result.txt").write_text(
        "\n".join(
            [
                f"variant={args.variant}",
                f"input_shape={tuple(shape)}",
                f"optimise={args.optimise}",
                f"fp32_top1={fp32_top1}",
                f"quantized_top1={quantized_top1}",
                f"max_abs_error={max_abs_error}",
                f"pte_path={pte_path}",
                f"pte_size_bytes={pte_path.stat().st_size}",
                f"metadata={metadata_path}",
            ]
        ) + "\n",
        encoding="utf-8",
    )
    write_variant_reports(
        variant_dir=variant_dir,
        metadata=metadata,
        quant_nodes=quant_nodes,
        operator_rows=operator_rows,
    )

    print()
    print("=" * 64)
    print("Variant export success")
    print("PTE path     :", pte_path)
    print("PTE size     :", pte_path.stat().st_size, "bytes")
    print("Metadata     :", metadata_path)
    print("Intermediates:", intermediate_dir)
    print("Vela summary :", vela_summary_path)
    print("=" * 64)


if __name__ == "__main__":
    main()
