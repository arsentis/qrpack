#!/usr/bin/env python3
"""Measure a damaged sheet: black out one code, name the lost part (issue #12).

Run from the repo root:  python3 tests/measure_damaged_sheet.py
Every number quoted in the README finding comes from here, so a reviewer can
reproduce it instead of trusting the prose.
"""
from __future__ import annotations

import contextlib
import io
import random
import tempfile
from pathlib import Path

import segno
from PIL import Image, ImageDraw

from qrpack.cli import main as cli_main
from qrpack.core import Header, chunk, compress, pack_bytes
from qrpack.scan import reassemble, scan_image
from qrpack.sheet import (
    CELL_GAP,
    DEFAULT_ECC,
    HEADER_HEIGHT,
    LABEL_HEIGHT,
    MARGIN,
    QUIET_ZONE,
    make_sheet,
)

COLS = 3
SCALE = 4
CHUNK = 1000
BLACKED_PART = 3
SOURCE_BYTES = 4000


def _restore(*images: Path, output: Path) -> tuple[int, str]:
    """Run the CLI quietly and return (return code, stderr)."""
    err = io.StringIO()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
        code = cli_main(["restore", *map(str, images), "-o", str(output)])
    return code, err.getvalue().strip()


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        source = tmp / "source"
        source.mkdir()
        original = random.Random(0).randbytes(SOURCE_BYTES)
        (source / "secret.bin").write_bytes(original)

        blob = compress(pack_bytes(source))
        payloads = [p.decode("ascii") for p in chunk(blob, CHUNK)]
        total = len(payloads)

        sheet = tmp / "sheet.png"
        make_sheet(payloads, "damage measurement", sheet, cols=COLS, scale=SCALE)

        # Reproduce make_sheet's cell geometry and paint one symbol black.
        qrs = [
            segno.make(p, error=DEFAULT_ECC, micro=False, boost_error=False)
            for p in payloads
        ]
        sizes = [qr.symbol_size(scale=SCALE, border=QUIET_ZONE) for qr in qrs]
        cell_width = max(width for width, _ in sizes)
        symbol_height = max(height for _, height in sizes)
        row, col = divmod(BLACKED_PART - 1, COLS)
        x = MARGIN + col * (cell_width + CELL_GAP)
        y = MARGIN + HEADER_HEIGHT + row * (symbol_height + LABEL_HEIGHT + CELL_GAP)
        with Image.open(sheet) as image:
            damaged = image.copy()
        ImageDraw.Draw(damaged).rectangle(
            [x, y, x + cell_width, y + symbol_height], fill="black"
        )
        damaged.save(sheet)

        texts = scan_image(sheet, COLS)
        indices = sorted(Header.parse(t).index for t in texts)
        joined, digest, missing = reassemble(texts)
        code, message = _restore(sheet, output=tmp / "refused")
        written = len(list((tmp / "refused").glob("*")))

        print(f"parts rendered    : {total}")
        print(f"part blacked out  : {BLACKED_PART}")
        print(f"parts decoded     : {indices}")
        print(f"reassemble        : missing={missing} blob_empty={joined == b''} digest={digest}")
        print(f"cli restore       : rc={code} | {message}")
        print(f"files written     : {written}")

        # Positive control: the same sheet plus an intact copy rescues the set.
        intact = tmp / "intact.png"
        make_sheet(payloads, "intact copy", intact, cols=COLS, scale=SCALE)
        rescued = tmp / "rescued"
        code2, _ = _restore(sheet, intact, output=rescued)
        identical = (rescued / "secret.bin").read_bytes() == original
        print(f"with intact copy  : rc={code2} bytes_identical={identical}")


if __name__ == "__main__":
    main()
