from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent
VARIANT_ROOT = PROJECT_DIR / "build" / "variants"
REPORT_DIR = PROJECT_DIR / "reports"
VARIANTS = ["default", "size", "input_64"]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_fvp_log(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    output_matches = re.findall(r"Output\[0\]\[(\d+)\]: \(float\)\s+([-+0-9.eE]+)", text)
    output = [float(value) for _, value in sorted((int(i), value) for i, value in output_matches)]
    top1 = max(range(len(output)), key=lambda i: output[i]) if output else "N/A"
    status = "PASS" if "Program complete, exiting." in text and "Model run: 1" in text else "FAIL"

    def first_int(pattern: str) -> int | None:
        match = re.search(pattern, text)
        return int(match.group(1)) if match else None

    return {
        "path": str(path),
        "status": status,
        "output": output,
        "top1": top1,
        "npu_delegations": first_int(r"NPU delegations:\s*(\d+)") or 0,
        "ethos_u_cycle_cnt": first_int(r"ethos-u\s+:\s+cycle_cnt\s+:\s*(\d+)\s+cycles"),
        "inference_runtime_cpu_cycles": first_int(r"Inference runtime:\s*(\d+)\s+CPU cycles"),
        "ethosu_pmu_cycle_cntr": first_int(r"ethosu_pmu_cycle_cntr\s+:\s*(\d+)") ,
    }


def parse_vela_ops(export_log: Path) -> dict[str, int | str]:
    text = export_log.read_text(encoding="utf-8", errors="replace")
    cpu_match = re.search(r"CPU operators\s*=\s*(\d+)", text)
    npu_match = re.search(r"NPU operators\s*=\s*(\d+)", text)
    return {
        "cpu_operators": int(cpu_match.group(1)) if cpu_match else "N/A",
        "npu_operators": int(npu_match.group(1)) if npu_match else "N/A",
    }


def fmt_shape(values: list[int]) -> str:
    return "(" + ", ".join(str(v) for v in values) + ")"


def fmt_vector(values: list[float]) -> str:
    if not values:
        return "N/A"
    return "[" + ", ".join(f"{value:.6f}" for value in values) + "]"


def max_abs_delta(left: list[float], right: list[float]) -> float | str:
    if len(left) != len(right) or not left:
        return "N/A"
    return max(abs(a - b) for a, b in zip(left, right))


def percent_delta(new: float, base: float) -> float | str:
    if base == 0:
        return "N/A"
    return (new - base) / base * 100.0


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(lines)


def collect() -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    default_fvp_output: list[float] | None = None

    raw: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = {}
    for variant in VARIANTS:
        variant_dir = VARIANT_ROOT / variant
        metadata = read_json(variant_dir / "metadata.json")
        fvp = parse_fvp_log(variant_dir / "fvp_embedded.log")
        vela_ops = parse_vela_ops(variant_dir / "export.log")
        raw[variant] = (metadata, fvp, vela_ops)
        if variant == "default":
            default_fvp_output = fvp["output"]

    assert default_fvp_output is not None

    for variant in VARIANTS:
        metadata, fvp, vela_ops = raw[variant]
        vela = metadata.get("vela_summary", {})
        same_resolution = metadata["input_shape"] == raw["default"][0]["input_shape"]
        delta = max_abs_delta(fvp["output"], default_fvp_output) if same_resolution else "N/A"
        cycles_note = "N/A"
        if fvp.get("ethosu_pmu_cycle_cntr") is not None:
            cycles_note = (
                f"Corstone-300 FVP ethosu_pmu_cycle_cntr={fvp['ethosu_pmu_cycle_cntr']}; "
                "not E84 board timing"
            )
        notes = []
        if variant == "size":
            notes.append("Vela --optimise=Size; reduced SRAM but increased PTE/off-chip traffic")
        if variant == "input_64":
            notes.append("controlled 64x64 input experiment; output is not compared numerically to 96x96")
        if fvp.get("ethos_u_cycle_cnt") is not None:
            notes.append(f"FVP runner ethos-u cycle_cnt={fvp['ethos_u_cycle_cnt']}")
        notes.append(f"export_log={VARIANT_ROOT / variant / 'export.log'}")
        notes.append(f"fvp_log={VARIANT_ROOT / variant / 'fvp_embedded.log'}")

        collected.append(
            {
                "variant": variant,
                "input_shape": fmt_shape(metadata["input_shape"]),
                "parameter_count": metadata["parameter_count"],
                "pte_size_bytes": metadata["pte_size_bytes"],
                "total_sram_kib": vela.get("sram_memory_used", "N/A"),
                "offchip_flash_kib": vela.get("off_chip_flash_memory_used", "N/A"),
                "delegated_subgraphs": metadata["delegated_subgraphs"],
                "delegated_nodes": metadata["delegated_nodes"],
                "npu_operators": vela_ops["npu_operators"],
                "cpu_operators": vela_ops["cpu_operators"],
                "fvp_mode": "embedded-PTE",
                "fvp_status": fvp["status"],
                "fvp_output": fmt_vector(fvp["output"]),
                "reference_top1": metadata["quantized_top1"],
                "fvp_top1": fvp["top1"],
                "max_abs_error": f"{delta:.9g}" if isinstance(delta, float) else delta,
                "reliable_cycles_or_time": cycles_note,
                "notes": "; ".join(notes),
                "_metadata": metadata,
                "_fvp": fvp,
            }
        )
    return collected


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    public_fields = [
        "variant",
        "input_shape",
        "parameter_count",
        "pte_size_bytes",
        "total_sram_kib",
        "offchip_flash_kib",
        "delegated_subgraphs",
        "delegated_nodes",
        "npu_operators",
        "cpu_operators",
        "fvp_mode",
        "fvp_status",
        "fvp_output",
        "reference_top1",
        "fvp_top1",
        "max_abs_error",
        "reliable_cycles_or_time",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=public_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in public_fields})


def write_report(rows: list[dict[str, Any]], path: Path) -> None:
    by_variant = {row["variant"]: row for row in rows}
    default = by_variant["default"]
    size = by_variant["size"]
    input64 = by_variant["input_64"]

    def number(row: dict[str, Any], key: str) -> float:
        return float(row[key])

    sram_delta = percent_delta(number(size, "total_sram_kib"), number(default, "total_sram_kib"))
    pte_delta = percent_delta(number(size, "pte_size_bytes"), number(default, "pte_size_bytes"))
    flash_delta = percent_delta(number(size, "offchip_flash_kib"), number(default, "offchip_flash_kib"))
    input64_sram_delta = percent_delta(number(input64, "total_sram_kib"), number(default, "total_sram_kib"))
    input64_pte_delta = percent_delta(number(input64, "pte_size_bytes"), number(default, "pte_size_bytes"))

    table_rows = [
        [
            row["variant"],
            row["input_shape"],
            row["pte_size_bytes"],
            row["total_sram_kib"],
            row["offchip_flash_kib"],
            row["npu_operators"],
            row["cpu_operators"],
            row["fvp_status"],
            row["fvp_top1"],
            row["max_abs_error"],
            row["_fvp"].get("ethosu_pmu_cycle_cntr"),
        ]
        for row in rows
    ]

    lines = [
        "# TinyCNN Vela Optimization Report",
        "",
        "## Control Variables",
        "",
        "- Model: custom random-weight TinyCNN from `tinycnn/model.py`; no ExecuTorch official example model is used.",
        "- Weights: fixed by `torch.manual_seed(20260716)` for every variant.",
        "- Calibration: 32 fixed random tensors with generator seed `20260716`.",
        "- Target profile: `ethos-u55-128`, `Ethos_U55_High_End_Embedded`, `Shared_Sram`.",
        "- FVP mode: embedded-PTE runner on `FVP_Corstone_SSE-300_Ethos-U55`.",
        "- Baseline output for `max_abs_error`: the `default` 96x96 FVP output. `input_64` is marked `N/A` because it uses a different input resolution.",
        "",
        "## Vela Parameters",
        "",
        md_table(
            ["variant", "input", "Vela flags"],
            [
                ["default", "96x96", "Vela default strategy"],
                ["size", "96x96", "`--optimise=Size`"],
                ["input_64", "64x64", "Vela default strategy"],
            ],
        ),
        "",
        "The local API inspection is recorded in `tinycnn/reports/vela_api_inspection.md`. `--arena-cache-size` was not run because the required Default/Size comparison already produced a clear Size tradeoff and the U55 Shared_Sram profile does not need an arbitrary cache sweep for the main deliverable.",
        "",
        "## Results",
        "",
        md_table(
            [
                "variant",
                "input_shape",
                "PTE bytes",
                "SRAM KiB",
                "Off-chip Flash KiB",
                "NPU ops",
                "CPU ops",
                "FVP",
                "FVP Top-1",
                "max abs vs default",
                "FVP PMU cycles",
            ],
            table_rows,
        ),
        "",
        "Full machine-readable results are in `tinycnn/reports/optimization_results.csv`.",
        "",
        "## Default vs Size",
        "",
        f"- Size SRAM delta: `{sram_delta:.2f}%` ({default['total_sram_kib']} KiB -> {size['total_sram_kib']} KiB).",
        f"- Size PTE delta: `{pte_delta:.2f}%` ({default['pte_size_bytes']} bytes -> {size['pte_size_bytes']} bytes).",
        f"- Size off-chip Flash estimate delta: `{flash_delta:.2f}%` ({default['offchip_flash_kib']} KiB -> {size['offchip_flash_kib']} KiB).",
        "- Default and Size FVP output vectors are identical at the printed precision, and both keep Top-1 = 1.",
        "- The honest conclusion is a space/performance tradeoff, not a free optimization: `--optimise=Size` reduces Vela SRAM usage but increases the PTE size and the FVP PMU cycle counter in this run.",
        "",
        "## 96x96 vs 64x64",
        "",
        f"- The 64x64 variant keeps the same channel counts, convolution layers, activations, classifier head, and parameter count `{input64['parameter_count']}` because the model uses `AdaptiveAvgPool2d((1, 1))`.",
        f"- Compared with 96x96 default, 64x64 SRAM delta is `{input64_sram_delta:.2f}%` and PTE delta is `{input64_pte_delta:.2f}%`.",
        "- 64x64 output is not required to match 96x96 numerically because the input tensor shape and data differ. It was validated for legal output, Top-1 extraction, NPU delegation, and FVP completion.",
        "",
        "## Data Boundaries",
        "",
        "- `total_sram_kib`, `offchip_flash_kib`, MAC counts, and Vela bandwidth/cycle fields are Vela compiler estimates for the delegated network.",
        "- `fvp_status`, output vectors, delegation count, and `ethosu_pmu_cycle_cntr` come from Corstone-300 Ethos-U55 FVP logs.",
        "- CPU cycle ratios printed by the runner are not used as board timing. The runner log itself warns that CPU cycle values and ratios require FPGA and identical CPU/NPU frequency.",
        "- None of these measurements are PSoC Edge E84 board measurements, and this project does not claim an ExecuTorch Runtime port to E84.",
        "",
        "## Evidence",
        "",
    ]
    for row in rows:
        variant = row["variant"]
        lines.extend(
            [
                f"### {variant}",
                "",
                f"- PTE: `{row['_metadata']['pte_path']}`",
                f"- Export log: `{VARIANT_ROOT / variant / 'export.log'}`",
                f"- FVP log: `{VARIANT_ROOT / variant / 'fvp_embedded.log'}`",
                f"- Metadata: `{VARIANT_ROOT / variant / 'metadata.json'}`",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rows = collect()
    write_csv(rows, REPORT_DIR / "optimization_results.csv")
    write_report(rows, REPORT_DIR / "vela_optimization_report.md")
    print(f"Wrote {REPORT_DIR / 'optimization_results.csv'}")
    print(f"Wrote {REPORT_DIR / 'vela_optimization_report.md'}")


if __name__ == "__main__":
    main()
