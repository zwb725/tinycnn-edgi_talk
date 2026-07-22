from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .deploy import DeploymentConfig, DeploymentError, deploy
from .manifest import parse_shape


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate RT-AK ExecuTorch Ethos-U prototype files.")
    parser.add_argument("--pte", required=True, type=Path)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--input-shape", required=True)
    parser.add_argument("--output-shape", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--load-mode", choices=("embedded", "qspi"), required=True)
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--delegated-subgraphs", type=int, default=1)
    parser.add_argument("--delegated-nodes", type=int, default=29)
    parser.add_argument("--npu-operators", type=int, default=7)
    parser.add_argument("--cpu-operators", type=int, default=0)
    parser.add_argument("--fvp-status", default="PASS")
    parser.add_argument("--fvp-log", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = DeploymentConfig(
            pte=args.pte.resolve(),
            project=args.project.resolve(),
            model_name=args.model_name,
            input_shape=parse_shape(args.input_shape),
            output_shape=parse_shape(args.output_shape),
            target=args.target,
            load_mode=args.load_mode,
            manifest_only=args.manifest_only,
            dry_run=args.dry_run,
            force=args.force,
            delegated_subgraphs=args.delegated_subgraphs,
            delegated_nodes=args.delegated_nodes,
            npu_operators=args.npu_operators,
            cpu_operators=args.cpu_operators,
            fvp_status=args.fvp_status,
            fvp_log=args.fvp_log,
        )
        result = deploy(config)
    except (DeploymentError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for action in result.actions:
        print(action)
    print(f"manifest:{result.manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
