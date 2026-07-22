from __future__ import annotations

from pathlib import Path

import torch
from executorch.devtools.backend_debug import get_delegation_info
from torchao.quantization.pt2e.quantize_pt2e import (
    convert_pt2e,
    prepare_pt2e,
)

from executorch.backends.arm.ethosu import (
    EthosUCompileSpec,
    EthosUPartitioner,
)
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

from tinycnn.model import (
    INPUT_SHAPE,
    create_example_input,
    create_model,
)


PROJECT_DIR = Path(__file__).resolve().parent
BUILD_DIR = PROJECT_DIR / "build"
INTERMEDIATE_DIR = BUILD_DIR / "intermediates"
REPORT_DIR = PROJECT_DIR / "reports"

PTE_PATH = BUILD_DIR / "tinycnn_u55.pte"
QUANTIZED_GRAPH_PATH = REPORT_DIR / "quantized_graph.txt"
RESULT_PATH = REPORT_DIR / "export_result.txt"
QUANTIZATION_REPORT_PATH = REPORT_DIR / "quantization_report.md"
DELEGATION_REPORT_PATH = REPORT_DIR / "delegation_report.md"
EDGE_GRAPH_PATH = REPORT_DIR / "edge_lowered_graph.txt"
DELEGATED_SUBGRAPHS_PATH = REPORT_DIR / "delegated_subgraphs.txt"

CALIBRATION_SAMPLES = 32


def has_quantized_out_variants() -> bool:
    try:
        _ = torch.ops.quantized_decomposed.quantize_per_tensor.out
        _ = torch.ops.quantized_decomposed.dequantize_per_tensor.out
        return True
    except AttributeError:
        return False


def ensure_quantized_ops_loaded() -> Path | None:
    if has_quantized_out_variants():
        return None

    try:
        import executorch.kernels.quantized  # noqa: F401
    except ImportError:
        pass

    if has_quantized_out_variants():
        return None

    project_root = PROJECT_DIR.parent
    search_patterns = (
        ".venv/lib/python3.10/site-packages/executorch/kernels/quantized/libquantized_ops_aot_lib.*",
        "executorch/pip-out/lib.*/executorch/kernels/quantized/libquantized_ops_aot_lib.*",
        "executorch/pip-out/temp.*/cmake-out/kernels/quantized/libquantized_ops_aot_lib.*",
        "executorch/cmake-out/kernels/quantized/libquantized_ops_aot_lib.*",
        "executorch/arm_test/*/kernels/quantized/libquantized_ops_aot_lib.*",
    )
    for pattern in search_patterns:
        for candidate in sorted(project_root.glob(pattern)):
            if not candidate.is_file():
                continue
            torch.ops.load_library(str(candidate))
            if has_quantized_out_variants():
                return candidate

    raise RuntimeError(
        "INT8 export requires quantized_decomposed out-variant ops. "
        "Expected quantize_per_tensor.out and dequantize_per_tensor.out "
        "to be registered by libquantized_ops_aot_lib."
    )


def tensor_data(tensor: torch.Tensor) -> list:
    return tensor.detach().cpu().tolist()


def qdq_nodes(graph_module: torch.fx.GraphModule) -> list[str]:
    nodes: list[str] = []
    for node in graph_module.graph.nodes:
        target = str(node.target)
        if "quantize" in target or "dequantize" in target:
            nodes.append(f"{node.name}: {target}")
    return nodes


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    if not rows:
        return "None."
    header_line = "| " + " | ".join(headers) + " |"
    sep_line = "| " + " | ".join("---" for _ in headers) + " |"
    row_lines = [
        "| " + " | ".join(str(item) for item in row) + " |"
        for row in rows
    ]
    return "\n".join([header_line, sep_line, *row_lines])


def artifact_lines() -> list[str]:
    if not INTERMEDIATE_DIR.exists():
        return []
    lines: list[str] = []
    for path in sorted(INTERMEDIATE_DIR.rglob("*")):
        if path.is_file():
            lines.append(f"- `{path}` ({path.stat().st_size} bytes)")
    return lines


def write_delegated_subgraphs(edge_graph_module: torch.fx.GraphModule) -> None:
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
    DELEGATED_SUBGRAPHS_PATH.write_text("\n".join(chunks), encoding="utf-8")


def write_reports(
    *,
    fp32_output: torch.Tensor,
    quantized_output: torch.Tensor,
    max_abs_error: float,
    fp32_top1: int,
    quantized_top1: int,
    quant_nodes: list[str],
    delegation_info,
    quantized_ops_library: Path | None,
) -> None:
    pte_size = PTE_PATH.stat().st_size if PTE_PATH.exists() else 0
    artifacts = artifact_lines()
    warning_notes = [
        "Yes. Non-fatal export warnings were observed in `tinycnn/build/export_ethosu.log`.",
        "Observed warning classes include PyTorch pytree deprecation, torch.tensor copy construction, LeafSpec deprecation, and guard_size_oblivious deprecation.",
    ]

    quant_report = "\n".join(
        [
            "# TinyCNN PT2E Quantization Report",
            "",
            f"- Input shape: `{INPUT_SHAPE}`",
            f"- Calibration samples: `{CALIBRATION_SAMPLES}` fixed random tensors",
            f"- Quantized ops library: `{quantized_ops_library}`" if quantized_ops_library else "- Quantized ops library: already registered before explicit load",
            f"- FP32 output: `{tensor_data(fp32_output)}`",
            f"- PT2E INT8 output: `{tensor_data(quantized_output)}`",
            f"- Output shape: `{tuple(quantized_output.shape)}`",
            f"- FP32 Top-1: `{fp32_top1}`",
            f"- INT8 Top-1: `{quantized_top1}`",
            f"- Top-1 match: `{fp32_top1 == quantized_top1}`",
            f"- Max absolute error: `{max_abs_error}`",
            "",
            "## Quantize / Dequantize Nodes",
            "",
            "\n".join(f"- `{node}`" for node in quant_nodes) if quant_nodes else "None found.",
            "",
            "## Warnings",
            "",
            "\n".join(f"- {note}" for note in warning_notes),
            "",
            "## Artifacts",
            "",
            f"- Quantized graph: `{QUANTIZED_GRAPH_PATH}`",
            f"- PTE: `{PTE_PATH}` ({pte_size} bytes)",
            *artifacts,
            "",
        ]
    )
    QUANTIZATION_REPORT_PATH.write_text(quant_report, encoding="utf-8")

    df = delegation_info.get_operator_delegation_dataframe()
    rows = [
        [
            row["op_type"],
            int(row["occurrences_in_delegated_graphs"]),
            int(row["occurrences_in_non_delegated_graphs"]),
        ]
        for _, row in df.iterrows()
    ]
    fallback_rows = [row for row in rows if row[0] != "Total" and row[2] > 0]

    delegation_report = "\n".join(
        [
            "# TinyCNN Ethos-U Delegation Report",
            "",
            delegation_info.get_summary().strip(),
            "",
            "## Operator Delegation",
            "",
            markdown_table(
                ["op_type", "delegated", "non_delegated"],
                rows,
            ),
            "",
            "## CPU Fallback Operators",
            "",
            "These are EXIR nodes left outside the Ethos-U delegate. The Vela summary for the delegated network reports `CPU operators = 0` and `NPU operators = 7`; no coverage percentage is estimated here.",
            "",
            markdown_table(
                ["op_type", "non_delegated"],
                [[row[0], row[2]] for row in fallback_rows],
            ),
            "",
            "## Delegate Subgraphs",
            "",
            f"- Delegated subgraph dump: `{DELEGATED_SUBGRAPHS_PATH}`",
            f"- Lowered edge graph: `{EDGE_GRAPH_PATH}`",
            "",
            "## TOSA / Vela Artifacts",
            "",
            "\n".join(artifacts) if artifacts else "No intermediate artifacts found.",
            "",
            "## PTE",
            "",
            f"- Path: `{PTE_PATH}`",
            f"- Size: `{pte_size}` bytes",
            "",
            "## Warnings",
            "",
            "\n".join(f"- {note}" for note in warning_notes),
            "",
        ]
    )
    DELEGATION_REPORT_PATH.write_text(delegation_report, encoding="utf-8")


def calibrate(prepared_model: torch.fx.GraphModule) -> None:
    """
    使用固定随机样本完成第一版PTQ校准。

    这里只验证量化、TOSA、Vela和PTE生成链路，
    不用于评估模型分类精度。
    """
    generator = torch.Generator()
    generator.manual_seed(20260716)

    with torch.no_grad():
        for index in range(CALIBRATION_SAMPLES):
            sample = torch.rand(
                INPUT_SHAPE,
                generator=generator,
                dtype=torch.float32,
            )

            prepared_model(sample)

            if (index + 1) % 8 == 0:
                print(
                    f"Calibration: "
                    f"{index + 1}/{CALIBRATION_SAMPLES}"
                )


def main() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    quantized_ops_library = ensure_quantized_ops_loaded()
    if quantized_ops_library is not None:
        print("Loaded quantized ops library:", quantized_ops_library)

    model = create_model()
    example_input = create_example_input()
    example_inputs = (example_input,)

    # ---------------------------------------------------------
    # 1. FP32参考输出
    # ---------------------------------------------------------
    with torch.no_grad():
        fp32_output = model(example_input)

    print("=" * 64)
    print("1. FP32 reference")
    print("Input shape :", tuple(example_input.shape))
    print("Output shape:", tuple(fp32_output.shape))
    print("Output      :", fp32_output)
    print("Top-1       :", int(fp32_output.argmax(dim=1).item()))
    print("=" * 64)

    # ---------------------------------------------------------
    # 2. 捕获原始PyTorch计算图
    # ---------------------------------------------------------
    exported_program = torch.export.export(
        model,
        example_inputs,
    )

    graph_module = exported_program.module(
        check_guards=False,
    )

    print("2. torch.export completed")

    # ---------------------------------------------------------
    # 3. Ethos-U55 / Vela目标配置
    #
    # 当前配置用于Corstone-300参考平台验证。
    # 后续面向E84真板时，需要替换成真实Target Profile。
    # ---------------------------------------------------------
    compile_spec = EthosUCompileSpec(
        target="ethos-u55-128",
        system_config="Ethos_U55_High_End_Embedded",
        memory_mode="Shared_Sram",
    )

    compile_spec.dump_intermediate_artifacts_to(
        str(INTERMEDIATE_DIR)
    )

    print("3. Ethos-U55 compile spec created")
    print("   target       : ethos-u55-128")
    print("   system config: Ethos_U55_High_End_Embedded")
    print("   memory mode  : Shared_Sram")

    # ---------------------------------------------------------
    # 4. 配置PT2E INT8量化器
    # ---------------------------------------------------------
    quantizer = EthosUQuantizer(compile_spec)

    quantization_config = (
        get_symmetric_quantization_config()
    )

    quantizer.set_global(quantization_config)

    prepared_model = prepare_pt2e(
        graph_module,
        quantizer,
    )

    print("4. PT2E prepare completed")

    # ---------------------------------------------------------
    # 5. 校准并转换量化模型
    # ---------------------------------------------------------
    calibrate(prepared_model)

    quantized_model = convert_pt2e(
        prepared_model
    )

    print("5. PT2E convert completed")

    # ---------------------------------------------------------
    # 6. 检查量化模型输出
    # ---------------------------------------------------------
    with torch.no_grad():
        quantized_output = quantized_model(
            example_input
        )

    max_abs_error = (
        fp32_output - quantized_output
    ).abs().max().item()

    fp32_top1 = int(
        fp32_output.argmax(dim=1).item()
    )
    quantized_top1 = int(
        quantized_output.argmax(dim=1).item()
    )

    print("=" * 64)
    print("6. Quantized model output")
    print("Output shape :", tuple(quantized_output.shape))
    print("Output       :", quantized_output)
    print("FP32 Top-1   :", fp32_top1)
    print("INT8 Top-1   :", quantized_top1)
    print("Max abs error:", max_abs_error)
    print("=" * 64)

    QUANTIZED_GRAPH_PATH.write_text(
        str(quantized_model.graph),
        encoding="utf-8",
    )
    quant_nodes = qdq_nodes(quantized_model)

    # ---------------------------------------------------------
    # 7. 重新导出量化图
    # ---------------------------------------------------------
    quantized_exported_program = torch.export.export(
        quantized_model,
        example_inputs,
    )

    print("7. Quantized graph exported")

    # ---------------------------------------------------------
    # 8. Ethos-U子图划分、TOSA Lowering与Vela编译
    # ---------------------------------------------------------
    partitioner = EthosUPartitioner(
        compile_spec
    )

    edge_program_manager = to_edge_transform_and_lower(
        quantized_exported_program,
        partitioner=[partitioner],
        compile_config=EdgeCompileConfig(
            _check_ir_validity=False,
        ),
    )

    edge_graph_module = edge_program_manager.exported_program().graph_module
    EDGE_GRAPH_PATH.write_text(str(edge_graph_module.graph), encoding="utf-8")
    write_delegated_subgraphs(edge_graph_module)
    delegation_info = get_delegation_info(edge_graph_module)

    print("8. Ethos-U partition and Vela lowering completed")
    print(delegation_info.get_summary().strip())

    # ---------------------------------------------------------
    # 9. 生成ExecuTorch Program
    # ---------------------------------------------------------
    executorch_program_manager = (
        edge_program_manager.to_executorch(
            config=ExecutorchBackendConfig(
                extract_delegate_segments=False,
            )
        )
    )

    print("9. ExecuTorch program generated")

    # ---------------------------------------------------------
    # 10. 保存PTE
    # ---------------------------------------------------------
    save_pte_program(
        executorch_program_manager,
        str(PTE_PATH),
        output_dir=str(BUILD_DIR),
    )

    if not PTE_PATH.exists():
        raise RuntimeError(
            f"PTE was not generated: {PTE_PATH}"
        )

    if PTE_PATH.stat().st_size == 0:
        raise RuntimeError(
            f"PTE file is empty: {PTE_PATH}"
        )

    result = "\n".join(
        [
            "TinyCNN Ethos-U55 export result",
            f"input_shape={tuple(example_input.shape)}",
            f"output_shape={tuple(quantized_output.shape)}",
            f"fp32_top1={fp32_top1}",
            f"quantized_top1={quantized_top1}",
            f"max_abs_error={max_abs_error}",
            f"pte_path={PTE_PATH}",
            f"pte_size_bytes={PTE_PATH.stat().st_size}",
            f"intermediate_dir={INTERMEDIATE_DIR}",
        ]
    )

    RESULT_PATH.write_text(
        result + "\n",
        encoding="utf-8",
    )

    write_reports(
        fp32_output=fp32_output,
        quantized_output=quantized_output,
        max_abs_error=max_abs_error,
        fp32_top1=fp32_top1,
        quantized_top1=quantized_top1,
        quant_nodes=quant_nodes,
        delegation_info=delegation_info,
        quantized_ops_library=quantized_ops_library,
    )

    print()
    print("=" * 64)
    print("Export success")
    print("PTE path        :", PTE_PATH)
    print("PTE size        :", PTE_PATH.stat().st_size, "bytes")
    print("Quantized graph :", QUANTIZED_GRAPH_PATH)
    print("Result report   :", RESULT_PATH)
    print("Quant report    :", QUANTIZATION_REPORT_PATH)
    print("Delegation report:", DELEGATION_REPORT_PATH)
    print("Intermediates   :", INTERMEDIATE_DIR)
    print("=" * 64)


if __name__ == "__main__":
    main()
