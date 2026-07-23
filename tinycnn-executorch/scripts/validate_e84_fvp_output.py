#!/usr/bin/env python3
"""Validate TinyCNN E84 board output against Corstone-300 FVP output."""

from __future__ import annotations

import argparse
import re
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

EXPECTED_OUTPUT_COUNT = 4
EXPECTED_PTE_SIZE_LINE = "PTE Model data loaded. Size: 31696 bytes."
EXPECTED_NPU_DELEGATE_LINE = "NPU delegations: 1"
EXPECTED_PROGRAM_COMPLETE_LINE = "Program complete, exiting."

FVP_OUTPUT_RE = re.compile(
    r"Output\[0\]\[(?P<index>\d+)\]:\s*\(float\)\s*"
    r"(?P<value>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
)
E84_BITS_RE = re.compile(r"output0\[(?P<index>\d+)\]\s+float_bits=(?P<bits>\S+)")
HEX_BITS_RE = re.compile(r"0x[0-9a-fA-F]{1,8}\Z")


class ValidationError(Exception):
    """Raised when an input log is present but cannot satisfy validation."""


@dataclass(frozen=True)
class ComparisonResult:
    fvp_outputs: list[float]
    e84_outputs: list[float]
    abs_errors: list[float]
    max_abs_error: float
    fvp_top1: int
    e84_top1: int
    pte_loaded: bool
    npu_delegate: bool
    program_complete: bool
    top1_match: bool
    output_match: bool

    @property
    def passed(self) -> bool:
        return all(
            [
                self.pte_loaded,
                self.npu_delegate,
                self.program_complete,
                self.top1_match,
                self.output_match,
            ]
        )


def positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid tolerance {value!r}: not a float") from exc
    if parsed <= 0.0:
        raise argparse.ArgumentTypeError("tolerance must be greater than 0")
    return parsed


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare TinyCNN E84 float_bits output with FVP float output."
    )
    parser.add_argument("--fvp-log", required=True, type=Path, help="Path to FVP log")
    parser.add_argument("--e84-log", required=True, type=Path, help="Path to E84 serial log")
    parser.add_argument(
        "--tolerance",
        type=positive_float,
        default=1e-6,
        help="Maximum allowed absolute error, default: 1e-6",
    )
    return parser.parse_args(argv)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ValidationError(f"failed to read {path}: {exc}") from exc


def require_four_outputs(values_by_index: dict[int, float], source: str) -> list[float]:
    missing = [index for index in range(EXPECTED_OUTPUT_COUNT) if index not in values_by_index]
    if missing:
        raise ValidationError(f"{source} log is missing output index(es): {missing}")
    extra = sorted(index for index in values_by_index if index >= EXPECTED_OUTPUT_COUNT)
    if extra:
        raise ValidationError(f"{source} log has unexpected output index(es): {extra}")
    return [values_by_index[index] for index in range(EXPECTED_OUTPUT_COUNT)]


def parse_fvp_outputs(text: str) -> list[float]:
    values: dict[int, float] = {}
    for match in FVP_OUTPUT_RE.finditer(text):
        index = int(match.group("index"))
        if index in values:
            raise ValidationError(f"FVP log has duplicate output index: {index}")
        values[index] = float(match.group("value"))
    return require_four_outputs(values, "FVP")


def decode_float_bits(bits_text: str, index: int) -> float:
    if not HEX_BITS_RE.fullmatch(bits_text):
        raise ValidationError(f"E84 output index {index} has invalid float_bits value: {bits_text}")
    bits = int(bits_text, 16)
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def parse_e84_outputs(text: str) -> list[float]:
    values: dict[int, float] = {}
    for match in E84_BITS_RE.finditer(text):
        index = int(match.group("index"))
        if index in values:
            raise ValidationError(f"E84 log has duplicate output index: {index}")
        values[index] = decode_float_bits(match.group("bits"), index)
    return require_four_outputs(values, "E84")


def top1(values: list[float]) -> int:
    return max(range(len(values)), key=lambda index: values[index])


def compare_logs(fvp_text: str, e84_text: str, tolerance: float) -> ComparisonResult:
    fvp_outputs = parse_fvp_outputs(fvp_text)
    e84_outputs = parse_e84_outputs(e84_text)
    abs_errors = [abs(e84_value - fvp_value) for e84_value, fvp_value in zip(e84_outputs, fvp_outputs)]
    max_abs_error = max(abs_errors)
    e84_top1 = top1(e84_outputs)
    fvp_top1 = top1(fvp_outputs)

    return ComparisonResult(
        fvp_outputs=fvp_outputs,
        e84_outputs=e84_outputs,
        abs_errors=abs_errors,
        max_abs_error=max_abs_error,
        fvp_top1=fvp_top1,
        e84_top1=e84_top1,
        pte_loaded=EXPECTED_PTE_SIZE_LINE in fvp_text,
        npu_delegate=EXPECTED_NPU_DELEGATE_LINE in fvp_text,
        program_complete=EXPECTED_PROGRAM_COMPLETE_LINE in fvp_text,
        top1_match=e84_top1 == fvp_top1,
        output_match=max_abs_error <= tolerance,
    )


def pass_fail(value: bool) -> str:
    return "PASS" if value else "FAIL"


def print_result(result: ComparisonResult) -> None:
    for index, (e84_value, fvp_value, abs_error) in enumerate(
        zip(result.e84_outputs, result.fvp_outputs, result.abs_errors)
    ):
        print(
            f"output[{index}] e84={e84_value:.10f} "
            f"fvp={fvp_value:.10f} abs_error={abs_error:.9e}"
        )
    print(f"e84_top1={result.e84_top1}")
    print(f"fvp_top1={result.fvp_top1}")
    print(f"pte_loaded={pass_fail(result.pte_loaded)}")
    print(f"npu_delegate={pass_fail(result.npu_delegate)}")
    print(f"program_complete={pass_fail(result.program_complete)}")
    print(f"top1_match={pass_fail(result.top1_match)}")
    print(f"output_match={pass_fail(result.output_match)}")
    print(f"max_abs_error={result.max_abs_error:.9e}")
    print(f"TINYCNN_E84_FVP_FINAL_COMPARE={pass_fail(result.passed)}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        fvp_text = read_text(args.fvp_log)
        e84_text = read_text(args.e84_log)
        result = compare_logs(fvp_text, e84_text, args.tolerance)
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print_result(result)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())