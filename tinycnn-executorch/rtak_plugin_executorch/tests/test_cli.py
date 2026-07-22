from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from rt_ai_tools.platforms.executorch_ethosu import cli
from rt_ai_tools.platforms.executorch_ethosu.deploy import DeploymentConfig, DeploymentError, deploy, validate_pte
from rt_ai_tools.platforms.executorch_ethosu.manifest import parse_shape
from rt_ai_tools.platforms.executorch_ethosu.pte_embed import sanitize_c_identifier


def write_pte(path: Path, data: bytes = b"----ET12\x00\x01tinycnn") -> Path:
    path.write_bytes(data)
    return path


def base_args(pte: Path, project: Path, mode: str = "embedded") -> list[str]:
    return [
        "--pte", str(pte),
        "--project", str(project),
        "--model-name", "tinycnn",
        "--input-shape", "1,3,96,96",
        "--output-shape", "1,4",
        "--target", "ethos-u55-128",
        "--load-mode", mode,
    ]


def read_manifest(project: Path) -> dict:
    return json.loads((project / "model_manifest.json").read_text(encoding="utf-8"))


def bytes_from_c_array(path: Path) -> bytes:
    text = path.read_text(encoding="utf-8")
    return bytes(int(match, 16) for match in re.findall(r"0x([0-9a-fA-F]{2})", text))


def test_cli_dry_run_does_not_create_project(tmp_path: Path) -> None:
    pte = write_pte(tmp_path / "sample.pte")
    project = tmp_path / "generated"
    rc = cli.main([*base_args(pte, project), "--dry-run"])
    assert rc == 0
    assert not project.exists()


def test_missing_pte_returns_nonzero(tmp_path: Path) -> None:
    rc = cli.main(base_args(tmp_path / "missing.pte", tmp_path / "generated"))
    assert rc != 0


def test_empty_pte_is_rejected(tmp_path: Path) -> None:
    pte = tmp_path / "empty.pte"
    pte.write_bytes(b"")
    with pytest.raises(DeploymentError):
        validate_pte(pte)
    assert cli.main(base_args(pte, tmp_path / "generated")) != 0


def test_embedded_manifest_and_sha256(tmp_path: Path) -> None:
    data = b"----ET12\x01\x02\x03\x04"
    pte = write_pte(tmp_path / "tinycnn_default.pte", data)
    project = tmp_path / "generated"
    assert cli.main(base_args(pte, project)) == 0
    manifest = read_manifest(project)
    assert manifest["schema_version"] == "0.1.0"
    assert manifest["model_name"] == "tinycnn"
    assert manifest["task"] == "classification_benchmark"
    assert manifest["validation_platform"] == "Corstone-300 Ethos-U55 FVP"
    assert manifest["target"] == "ethos-u55-128"
    assert manifest["input_shape"] == [1, 3, 96, 96]
    assert manifest["output_shape"] == [1, 4]
    assert manifest["pte_size_bytes"] == len(data)
    assert manifest["pte_sha256"] == hashlib.sha256(data).hexdigest()
    assert manifest["delegated_subgraphs"] == 1
    assert manifest["delegated_nodes"] == 29
    assert manifest["npu_operators"] == 7
    assert manifest["cpu_operators"] == 0
    assert "PSoC Edge E84 board" not in manifest["validation_platform"]


def test_embedded_c_array_reconstructs_pte(tmp_path: Path) -> None:
    data = bytes(range(64))
    pte = write_pte(tmp_path / "sample.pte", data)
    project = tmp_path / "generated"
    assert cli.main(base_args(pte, project)) == 0
    c_path = project / "models" / "tinycnn" / "rt_ai_tinycnn_model_data.c"
    h_path = project / "models" / "tinycnn" / "rt_ai_tinycnn_model_data.h"
    assert c_path.exists()
    assert h_path.exists()
    assert "__attribute__((aligned(16)))" in c_path.read_text(encoding="utf-8")
    assert bytes_from_c_array(c_path) == data


def test_qspi_mode_copies_pte_without_c_array(tmp_path: Path) -> None:
    data = b"qspi-pte"
    pte = write_pte(tmp_path / "tinycnn_qspi.pte", data)
    project = tmp_path / "generated_qspi"
    assert cli.main(base_args(pte, project, "qspi")) == 0
    copied = project / "resources" / "tinycnn_qspi.pte"
    assert copied.read_bytes() == data
    assert not (project / "models" / "tinycnn" / "rt_ai_tinycnn_model_data.c").exists()
    manifest = read_manifest(project)
    assert manifest["load_mode"] == "qspi"
    assert manifest["load_path"] == "resources/tinycnn_qspi.pte"


def test_overwrite_requires_force(tmp_path: Path) -> None:
    pte = write_pte(tmp_path / "sample.pte")
    project = tmp_path / "generated"
    assert cli.main(base_args(pte, project)) == 0
    assert cli.main(base_args(pte, project)) != 0
    assert cli.main([*base_args(pte, project), "--force"]) == 0


def test_kconfig_sconscript_and_backend_files_generated(tmp_path: Path) -> None:
    pte = write_pte(tmp_path / "sample.pte")
    project = tmp_path / "generated"
    assert cli.main(base_args(pte, project)) == 0
    assert (project / "backend_executorch" / "Kconfig").exists()
    assert (project / "backend_executorch" / "SConscript").exists()
    assert (project / "backend_executorch" / "include" / "rt_ai_executorch_backend.h").exists()
    assert (project / "backend_executorch" / "src" / "rt_ai_executorch_backend.c").exists()


def test_output_path_is_created(tmp_path: Path) -> None:
    pte = write_pte(tmp_path / "sample.pte")
    project = tmp_path / "missing" / "nested" / "project"
    assert cli.main(base_args(pte, project)) == 0
    assert project.exists()
    assert (project / "model_manifest.json").exists()


def test_illegal_model_name_is_sanitized(tmp_path: Path) -> None:
    pte = write_pte(tmp_path / "sample.pte")
    project = tmp_path / "generated"
    args = base_args(pte, project)
    args[args.index("tinycnn")] = "9 bad-name!"
    assert sanitize_c_identifier("9 bad-name!") == "m_9_bad_name"
    assert cli.main(args) == 0
    assert (project / "models" / "m_9_bad_name" / "rt_ai_m_9_bad_name_model_data.c").exists()


def test_manifest_only_writes_only_manifest(tmp_path: Path) -> None:
    pte = write_pte(tmp_path / "sample.pte")
    project = tmp_path / "generated"
    assert cli.main([*base_args(pte, project), "--manifest-only"]) == 0
    assert (project / "model_manifest.json").exists()
    assert not (project / "backend_executorch").exists()
    assert not (project / "models").exists()


def test_parse_shape_errors() -> None:
    with pytest.raises(ValueError):
        parse_shape("1,0,96,96")
    with pytest.raises(ValueError):
        parse_shape("1,c,96,96")


def test_deploy_api_returns_actions(tmp_path: Path) -> None:
    pte = write_pte(tmp_path / "sample.pte")
    config = DeploymentConfig(
        pte=pte,
        project=tmp_path / "generated",
        model_name="tinycnn",
        input_shape=[1, 3, 96, 96],
        output_shape=[1, 4],
        target="ethos-u55-128",
        load_mode="embedded",
    )
    result = deploy(config)
    assert result.manifest_path.exists()
    assert any(action.startswith("write:") for action in result.actions)
