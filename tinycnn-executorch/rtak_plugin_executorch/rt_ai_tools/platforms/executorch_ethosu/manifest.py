from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .pte_embed import sha256_file


SCHEMA_VERSION = "0.1.0"
VALIDATION_PLATFORM = "Corstone-300 Ethos-U55 FVP"
TASK = "classification_benchmark"


def parse_shape(value: str) -> list[int]:
    try:
        dims = [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise ValueError(f"invalid shape '{value}': expected comma-separated integers") from exc
    if not dims or any(dim <= 0 for dim in dims):
        raise ValueError(f"invalid shape '{value}': dimensions must be positive")
    return dims


def build_manifest(
    *,
    model_name: str,
    pte_path: Path,
    pte_filename: str,
    load_mode: str,
    load_path: str,
    input_shape: list[int],
    output_shape: list[int],
    target: str,
    delegated_subgraphs: int = 1,
    delegated_nodes: int = 29,
    npu_operators: int = 7,
    cpu_operators: int = 0,
    fvp_status: str = "PASS",
    fvp_log: str = "",
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "model_name": model_name,
        "task": TASK,
        "source_format": "ExecuTorch PTE",
        "runtime": "ExecuTorch with Ethos-U delegate artifact; target runtime port is not included",
        "target": target,
        "validation_platform": VALIDATION_PLATFORM,
        "input_shape": input_shape,
        "output_shape": output_shape,
        "input_dtype": "float32",
        "output_dtype": "float32",
        "quantization": "PT2E INT8 for Ethos-U delegated subgraph",
        "pte_filename": pte_filename,
        "pte_size_bytes": pte_path.stat().st_size,
        "pte_sha256": sha256_file(pte_path),
        "load_mode": load_mode,
        "load_path": load_path,
        "delegated_subgraphs": delegated_subgraphs,
        "delegated_nodes": delegated_nodes,
        "npu_operators": npu_operators,
        "cpu_operators": cpu_operators,
        "fvp_validation": {
            "status": fvp_status,
            "platform": VALIDATION_PLATFORM,
            "log": fvp_log,
        },
        "limitations": [
            "Prototype generator only; it does not port ExecuTorch Runtime to PSoC Edge E84.",
            "Validation data is from Corstone-300 Ethos-U55 FVP, not a PSoC Edge E84 board.",
            "TinyCNN is a random-weight classification benchmark, not a real gesture-recognition model.",
            "Target-side backend returns an explicit not-implemented error until a real runtime port is added.",
        ],
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
