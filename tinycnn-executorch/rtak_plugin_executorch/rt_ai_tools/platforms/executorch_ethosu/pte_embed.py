from __future__ import annotations

import hashlib
import re
from pathlib import Path


_BYTES_PER_LINE = 12


def sanitize_c_identifier(name: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_]", "_", name.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = "model"
    if cleaned[0].isdigit():
        cleaned = f"m_{cleaned}"
    return cleaned


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _array_lines(data: bytes) -> list[str]:
    lines: list[str] = []
    for offset in range(0, len(data), _BYTES_PER_LINE):
        chunk = data[offset : offset + _BYTES_PER_LINE]
        values = ", ".join(f"0x{byte:02x}" for byte in chunk)
        lines.append(f"    {values},")
    return lines


def embedded_symbol(model_name: str) -> str:
    return f"rt_ai_{sanitize_c_identifier(model_name)}_model_data"


def write_embedded_pte(pte_path: Path, output_dir: Path, model_name: str) -> tuple[Path, Path]:
    data = pte_path.read_bytes()
    symbol = embedded_symbol(model_name)
    header_guard = f"{symbol}_h_".upper()
    c_path = output_dir / f"{symbol}.c"
    h_path = output_dir / f"{symbol}.h"
    output_dir.mkdir(parents=True, exist_ok=True)

    h_path.write_text(
        "\n".join(
            [
                f"#ifndef {header_guard}",
                f"#define {header_guard}",
                "",
                "#include <stdint.h>",
                "",
                "#ifdef __cplusplus",
                "extern \"C\" {",
                "#endif",
                "",
                f"extern const uint8_t {symbol}[];",
                f"extern const unsigned int {symbol}_len;",
                "",
                "#ifdef __cplusplus",
                "}",
                "#endif",
                "",
                f"#endif /* {header_guard} */",
                "",
            ]
        ),
        encoding="utf-8",
    )

    c_path.write_text(
        "\n".join(
            [
                f"#include \"{h_path.name}\"",
                "",
                f"const uint8_t {symbol}[] __attribute__((aligned(16))) = {{",
                *_array_lines(data),
                "};",
                "",
                f"const unsigned int {symbol}_len = sizeof({symbol});",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return c_path, h_path
