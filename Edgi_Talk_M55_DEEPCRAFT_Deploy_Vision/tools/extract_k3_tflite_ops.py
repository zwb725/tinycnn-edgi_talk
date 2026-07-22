#!/usr/bin/env python3
"""
Extract the embedded TFLite FlatBuffer from model.c::_K3 and print the TFLite
operator list.

This is intentionally dependency-free. It reads only the FlatBuffer fields
needed for operator inspection, and it derives BuiltinOperator names from the
local TFLite Micro schema_generated.h checked into this workspace.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import struct
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_C = ROOT / "libraries/Common/deepcraft_ai/model/model.c"
DEFAULT_SCHEMA_H = (
    ROOT
    / "libraries/Common/deepcraft_ai/third_party/ml-tflite-micro"
    / "COMPONENT_ML_TFLM/include/tensorflow/lite/schema/schema_generated.h"
)
DEFAULT_OUT_DIR = ROOT / "tools/extracted_model"


VT_MODEL_OPERATOR_CODES = 6
VT_MODEL_SUBGRAPHS = 8
VT_OPERATOR_CODE_DEPRECATED_BUILTIN_CODE = 4
VT_OPERATOR_CODE_CUSTOM_CODE = 6
VT_OPERATOR_CODE_VERSION = 8
VT_OPERATOR_CODE_BUILTIN_CODE = 10
VT_SUBGRAPH_OPERATORS = 10
VT_SUBGRAPH_NAME = 12
VT_OPERATOR_OPCODE_INDEX = 4
VT_OPERATOR_INPUTS = 6
VT_OPERATOR_OUTPUTS = 8


class FlatBuffer:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def u8(self, off: int) -> int:
        return self.data[off]

    def i8(self, off: int) -> int:
        return struct.unpack_from("<b", self.data, off)[0]

    def u16(self, off: int) -> int:
        return struct.unpack_from("<H", self.data, off)[0]

    def i32(self, off: int) -> int:
        return struct.unpack_from("<i", self.data, off)[0]

    def u32(self, off: int) -> int:
        return struct.unpack_from("<I", self.data, off)[0]

    def root_table(self) -> int:
        return self.u32(0)

    def table_field_pos(self, table: int, vt_offset: int) -> int | None:
        vtable = table - self.i32(table)
        vtable_len = self.u16(vtable)
        if vt_offset >= vtable_len:
            return None
        rel = self.u16(vtable + vt_offset)
        if rel == 0:
            return None
        return table + rel

    def field_i8(self, table: int, vt_offset: int, default: int = 0) -> int:
        pos = self.table_field_pos(table, vt_offset)
        return default if pos is None else self.i8(pos)

    def field_i32(self, table: int, vt_offset: int, default: int = 0) -> int:
        pos = self.table_field_pos(table, vt_offset)
        return default if pos is None else self.i32(pos)

    def field_u32(self, table: int, vt_offset: int, default: int = 0) -> int:
        pos = self.table_field_pos(table, vt_offset)
        return default if pos is None else self.u32(pos)

    def indirect(self, pos: int) -> int:
        return pos + self.u32(pos)

    def field_table(self, table: int, vt_offset: int) -> int | None:
        pos = self.table_field_pos(table, vt_offset)
        return None if pos is None else self.indirect(pos)

    def field_vector(self, table: int, vt_offset: int) -> int | None:
        pos = self.table_field_pos(table, vt_offset)
        return None if pos is None else self.indirect(pos)

    def vector_len(self, vec: int) -> int:
        return self.u32(vec)

    def vector_table(self, vec: int, index: int) -> int:
        item_pos = vec + 4 + index * 4
        return self.indirect(item_pos)

    def vector_i32_values(self, vec: int | None) -> list[int]:
        if vec is None:
            return []
        count = self.vector_len(vec)
        return [self.i32(vec + 4 + i * 4) for i in range(count)]

    def string_at(self, off: int) -> str:
        length = self.u32(off)
        raw = self.data[off + 4 : off + 4 + length]
        return raw.decode("utf-8", errors="replace")

    def field_string(self, table: int, vt_offset: int) -> str:
        pos = self.table_field_pos(table, vt_offset)
        return "" if pos is None else self.string_at(self.indirect(pos))


def extract_k3_bytes(model_c: Path) -> bytes:
    text = model_c.read_text(encoding="utf-8", errors="ignore")
    start_match = re.search(
        r"static\s+IM_ML_MODEL_MEM\s+ALIGNED\(16\)\s+uint32_t\s+_K3\[\]\s*=\s*\{",
        text,
    )
    if not start_match:
        raise RuntimeError(f"Cannot find _K3 uint32_t array in {model_c}")

    end_match = re.search(r"\n\s*\};", text[start_match.end() :])
    if not end_match:
        raise RuntimeError("Cannot find end of _K3 array")

    body = text[start_match.end() : start_match.end() + end_match.start()]
    words = [int(token, 16) for token in re.findall(r"0x[0-9a-fA-F]{1,8}", body)]
    if not words:
        raise RuntimeError("No uint32_t words found in _K3 array")

    data = b"".join(struct.pack("<I", word) for word in words)
    root = struct.unpack_from("<I", data, 0)[0]
    if data[4:8] != b"TFL3":
        raise RuntimeError(f"Extracted buffer does not look like TFLite: magic={data[4:8]!r}")
    if root >= len(data):
        raise RuntimeError(f"Invalid FlatBuffer root offset {root} for {len(data)} bytes")
    return data


def load_builtin_operator_names(schema_h: Path) -> dict[int, str]:
    text = schema_h.read_text(encoding="utf-8", errors="ignore")
    enum_match = re.search(r"enum BuiltinOperator\s*:\s*int32_t\s*\{(?P<body>.*?)\n\};", text, re.S)
    if not enum_match:
        raise RuntimeError(f"Cannot find BuiltinOperator enum in {schema_h}")

    names: dict[int, str] = {}
    current = -1
    for raw_line in enum_match.group("body").splitlines():
        line = raw_line.split("//", 1)[0].strip().rstrip(",")
        if not line or not line.startswith("BuiltinOperator_"):
            continue
        if "=" in line:
            name_part, value_part = [part.strip() for part in line.split("=", 1)]
            if value_part.startswith("BuiltinOperator_"):
                if value_part not in {f"BuiltinOperator_{v}" for v in names.values()}:
                    continue
                reverse = {f"BuiltinOperator_{v}": k for k, v in names.items()}
                current = reverse[value_part]
            else:
                current = int(value_part, 0)
            enum_name = name_part.removeprefix("BuiltinOperator_")
        else:
            current += 1
            enum_name = line.removeprefix("BuiltinOperator_")
        names[current] = enum_name
    return names


def parse_model(data: bytes, builtin_names: dict[int, str]) -> tuple[list[dict], list[dict]]:
    fb = FlatBuffer(data)
    model = fb.root_table()

    op_codes_vec = fb.field_vector(model, VT_MODEL_OPERATOR_CODES)
    if op_codes_vec is None:
        raise RuntimeError("Model has no operator_codes vector")

    operator_codes: list[dict] = []
    for index in range(fb.vector_len(op_codes_vec)):
        table = fb.vector_table(op_codes_vec, index)
        builtin_code = fb.field_i32(table, VT_OPERATOR_CODE_BUILTIN_CODE, 0)
        deprecated_code = fb.field_i8(table, VT_OPERATOR_CODE_DEPRECATED_BUILTIN_CODE, 0)
        custom_code = fb.field_string(table, VT_OPERATOR_CODE_CUSTOM_CODE)
        version = fb.field_i32(table, VT_OPERATOR_CODE_VERSION, 1)
        operator_codes.append(
            {
                "index": index,
                "builtin_code": builtin_code,
                "builtin_name": builtin_names.get(builtin_code, f"UNKNOWN_{builtin_code}"),
                "deprecated_builtin_code": deprecated_code,
                "custom_code": custom_code,
                "version": version,
            }
        )

    subgraphs_vec = fb.field_vector(model, VT_MODEL_SUBGRAPHS)
    if subgraphs_vec is None:
        raise RuntimeError("Model has no subgraphs vector")

    operators: list[dict] = []
    for subgraph_index in range(fb.vector_len(subgraphs_vec)):
        subgraph = fb.vector_table(subgraphs_vec, subgraph_index)
        subgraph_name = fb.field_string(subgraph, VT_SUBGRAPH_NAME)
        operators_vec = fb.field_vector(subgraph, VT_SUBGRAPH_OPERATORS)
        if operators_vec is None:
            continue
        for op_index in range(fb.vector_len(operators_vec)):
            op_table = fb.vector_table(operators_vec, op_index)
            opcode_index = fb.field_u32(op_table, VT_OPERATOR_OPCODE_INDEX, 0)
            if opcode_index >= len(operator_codes):
                raise RuntimeError(f"Operator {op_index} references invalid opcode_index {opcode_index}")
            code = operator_codes[opcode_index]
            op_name = code["custom_code"] if code["custom_code"] else code["builtin_name"]
            operators.append(
                {
                    "subgraph_index": subgraph_index,
                    "subgraph_name": subgraph_name,
                    "operator_index": op_index,
                    "opcode_index": opcode_index,
                    "operator": op_name,
                    "builtin_name": code["builtin_name"],
                    "custom_code": code["custom_code"],
                    "version": code["version"],
                    "inputs": fb.vector_i32_values(fb.field_vector(op_table, VT_OPERATOR_INPUTS)),
                    "outputs": fb.vector_i32_values(fb.field_vector(op_table, VT_OPERATOR_OUTPUTS)),
                }
            )

    return operator_codes, operators


def write_outputs(out_dir: Path, data: bytes, operator_codes: list[dict], operators: list[dict]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    tflite_path = out_dir / "model_from_K3.tflite"
    json_path = out_dir / "operator_list.json"
    csv_path = out_dir / "operator_list.csv"
    txt_path = out_dir / "operator_summary.txt"

    tflite_path.write_bytes(data)
    json_path.write_text(json.dumps({"operator_codes": operator_codes, "operators": operators}, indent=2), encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "subgraph_index",
                "subgraph_name",
                "operator_index",
                "opcode_index",
                "operator",
                "builtin_name",
                "custom_code",
                "version",
                "inputs",
                "outputs",
            ],
        )
        writer.writeheader()
        for row in operators:
            csv_row = dict(row)
            csv_row["inputs"] = " ".join(map(str, row["inputs"]))
            csv_row["outputs"] = " ".join(map(str, row["outputs"]))
            writer.writerow(csv_row)

    counts = Counter(op["operator"] for op in operators)
    lines = [
        f"TFLite bytes: {len(data)}",
        f"OperatorCodes: {len(operator_codes)}",
        f"Operators: {len(operators)}",
        "",
        "Operator histogram:",
    ]
    lines += [f"- {name}: {count}" for name, count in counts.most_common()]
    lines += ["", "Operators:"]
    lines += [
        (
            f"- subgraph {op['subgraph_index']} #{op['operator_index']}: "
            f"{op['operator']} "
            f"(opcode_index={op['opcode_index']}, builtin={op['builtin_name']}, "
            f"custom={op['custom_code'] or '-'}, version={op['version']}, "
            f"inputs={op['inputs']}, outputs={op['outputs']})"
        )
        for op in operators
    ]
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-c", type=Path, default=DEFAULT_MODEL_C)
    parser.add_argument("--schema-h", type=Path, default=DEFAULT_SCHEMA_H)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    data = extract_k3_bytes(args.model_c)
    builtin_names = load_builtin_operator_names(args.schema_h)
    operator_codes, operators = parse_model(data, builtin_names)
    write_outputs(args.out_dir, data, operator_codes, operators)

    counts = Counter(op["operator"] for op in operators)
    print(f"Wrote {args.out_dir / 'model_from_K3.tflite'} ({len(data)} bytes)")
    print(f"OperatorCodes: {len(operator_codes)}")
    print(f"Operators: {len(operators)}")
    for name, count in counts.most_common():
        print(f"{name}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
