#!/usr/bin/env python3
"""How well do OpenCV's QR decoders read qrpack codes? (scan findings)

Every number in the README "Measured Findings" section comes from this
output, so a reviewer can reproduce it instead of trusting a table.

    python3 tests/measure_scan_decoders.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import cv2
import segno

from qrpack.core import chunk
from qrpack.scan import _find_cells
from qrpack.sheet import make_sheet

BLOB = bytes(range(256)) * 10          # 2560 bytes -> 3 payloads at chunk 1000
FACTORS = (0.5, 0.75, 1.0, 1.5, 2.0, 3.0)


def detectors():
    yield "classic", cv2.QRCodeDetector()
    if hasattr(cv2, "QRCodeDetectorAruco"):
        yield "aruco", cv2.QRCodeDetectorAruco()


def reads(detector, image, factor: float) -> bool:
    method = cv2.INTER_AREA if factor < 1 else cv2.INTER_NEAREST
    resized = cv2.resize(image, None, fx=factor, fy=factor, interpolation=method)
    text, _, _ = detector.detectAndDecode(resized)
    return bool(text)


def measure_sheet(lines: list[str], tmp: Path, scale: int, cols: int) -> None:
    out = tmp / "sheet.png"
    try:
        pages, codes = make_sheet(lines, "measure", out, cols, scale)
    except ValueError as err:
        print(f"sheet scale={scale} cols={cols}: not generated ({err})")
        return
    page = out if pages == 1 else tmp / "sheet-001.png"
    gray = cv2.imread(str(page), cv2.IMREAD_GRAYSCALE)
    cells = _find_cells(gray)
    print(f"sheet scale={scale} cols={cols}: {pages} page(s), "
          f"{codes} codes, {len(cells)} cells found")
    for name, det in detectors():
        row = []
        for factor in FACTORS:
            ok = 0
            for y, x, w, h in cells:
                cell = cv2.copyMakeBorder(
                    gray[y:y + h, x:x + w], 40, 40, 40, 40,
                    cv2.BORDER_CONSTANT, value=255,
                )
                ok += reads(det, cell, factor)
            row.append(f"x{factor}: {ok}/{len(cells)}")
        print(f"  {name:8}", "  ".join(row))


def measure_direct(lines: list[str], tmp: Path) -> None:
    path = tmp / "direct.png"
    for err in "lmq":
        qr = segno.make(lines[0], error=err)
        for scale in (4, 6, 8):
            qr.save(path, scale=scale, border=4)
            image = cv2.imread(str(path))
            res = [f"{name}: {'OK' if reads(det, image, 1.0) else '--'}"
                   for name, det in detectors()]
            print(f"direct ecc={err.upper()} version={qr.version} "
                  f"scale={scale}  " + "  ".join(res))


def main() -> None:
    print("opencv", cv2.__version__)
    lines = [p.decode("ascii") for p in chunk(BLOB, 1000)]
    print("payload lengths:", [len(s) for s in lines])
    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        measure_sheet(lines, tmp, scale=4, cols=3)
        measure_direct(lines, tmp)


if __name__ == "__main__":
    main()
