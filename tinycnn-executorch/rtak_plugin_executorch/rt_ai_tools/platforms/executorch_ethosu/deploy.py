from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .manifest import build_manifest, write_manifest
from .pte_embed import sanitize_c_identifier, write_embedded_pte


LoadMode = Literal["embedded", "qspi"]
PLUGIN_ROOT = Path(__file__).resolve().parents[3]


class DeploymentError(RuntimeError):
    pass


@dataclass(frozen=True)
class DeploymentConfig:
    pte: Path
    project: Path
    model_name: str
    input_shape: list[int]
    output_shape: list[int]
    target: str
    load_mode: LoadMode
    manifest_only: bool = False
    dry_run: bool = False
    force: bool = False
    delegated_subgraphs: int = 1
    delegated_nodes: int = 29
    npu_operators: int = 7
    cpu_operators: int = 0
    fvp_status: str = "PASS"
    fvp_log: str = ""


@dataclass(frozen=True)
class DeploymentResult:
    manifest_path: Path
    actions: list[str]


def validate_pte(path: Path) -> None:
    if not path.exists():
        raise DeploymentError(f"PTE does not exist: {path}")
    if not path.is_file():
        raise DeploymentError(f"PTE is not a file: {path}")
    if path.stat().st_size == 0:
        raise DeploymentError(f"PTE is empty: {path}")


def _check_overwrite(paths: list[Path], force: bool) -> None:
    if force:
        return
    existing = [path for path in paths if path.exists()]
    if existing:
        joined = "\n".join(str(path) for path in existing)
        raise DeploymentError(f"Refusing to overwrite existing files without --force:\n{joined}")


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _backend_source_files() -> list[tuple[Path, Path]]:
    src_root = PLUGIN_ROOT / "backend_executorch"
    pairs: list[tuple[Path, Path]] = []
    for path in sorted(src_root.rglob("*")):
        if path.is_file():
            pairs.append((path, Path("backend_executorch") / path.relative_to(src_root)))
    return pairs


def deploy(config: DeploymentConfig) -> DeploymentResult:
    validate_pte(config.pte)
    if config.load_mode not in ("embedded", "qspi"):
        raise DeploymentError(f"unsupported load mode: {config.load_mode}")

    safe_name = sanitize_c_identifier(config.model_name)
    manifest_path = config.project / "model_manifest.json"
    planned_targets = [manifest_path]
    actions = [f"validate_pte:{config.pte}"]

    resource_load_path = ""
    if config.load_mode == "embedded":
        model_dir = config.project / "models" / safe_name
        symbol = f"rt_ai_{safe_name}_model_data"
        planned_targets.extend([model_dir / f"{symbol}.c", model_dir / f"{symbol}.h"])
        resource_load_path = f"models/{safe_name}/{symbol}.c"
    else:
        resource_dir = config.project / "resources"
        resource_name = config.pte.name
        planned_targets.append(resource_dir / resource_name)
        resource_load_path = f"resources/{resource_name}"

    if not config.manifest_only:
        for _, relative in _backend_source_files():
            planned_targets.append(config.project / relative)

    _check_overwrite(planned_targets, config.force)

    if config.dry_run:
        actions.extend(f"would_write:{path}" for path in planned_targets)
        return DeploymentResult(manifest_path=manifest_path, actions=actions)

    config.project.mkdir(parents=True, exist_ok=True)

    if config.load_mode == "embedded" and not config.manifest_only:
        c_path, h_path = write_embedded_pte(config.pte, config.project / "models" / safe_name, config.model_name)
        actions.extend([f"write:{c_path}", f"write:{h_path}"])
    elif config.load_mode == "qspi" and not config.manifest_only:
        dst = config.project / "resources" / config.pte.name
        _copy_file(config.pte, dst)
        actions.append(f"copy:{config.pte}->{dst}")

    if not config.manifest_only:
        for src, relative in _backend_source_files():
            dst = config.project / relative
            _copy_file(src, dst)
            actions.append(f"copy:{src}->{dst}")

    manifest = build_manifest(
        model_name=config.model_name,
        pte_path=config.pte,
        pte_filename=config.pte.name,
        load_mode=config.load_mode,
        load_path=resource_load_path,
        input_shape=config.input_shape,
        output_shape=config.output_shape,
        target=config.target,
        delegated_subgraphs=config.delegated_subgraphs,
        delegated_nodes=config.delegated_nodes,
        npu_operators=config.npu_operators,
        cpu_operators=config.cpu_operators,
        fvp_status=config.fvp_status,
        fvp_log=config.fvp_log,
    )
    write_manifest(manifest_path, manifest)
    actions.append(f"write:{manifest_path}")
    return DeploymentResult(manifest_path=manifest_path, actions=actions)
