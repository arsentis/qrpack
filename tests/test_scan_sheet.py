"""Tests for qrpack.scan.scan_image (day 2): read every code on a sheet.

Written before the implementation: a sheet made by make_sheet must give
back exactly the payload lines that were printed on it.
"""

from qrpack.core import chunk
from qrpack.scan import scan_image
from qrpack.sheet import make_sheet


BLOB = bytes(range(256)) * 10   # 2560 bytes -> 3 payloads at chunk size 1000


def payload_lines():
    return [p.decode("ascii") for p in chunk(BLOB, 1000)]


def test_scan_image_reads_every_code_on_a_sheet(tmp_path):
    lines = payload_lines()
    out = tmp_path / "sheet.png"
    pages, codes = make_sheet(lines, "test sheet", out, 3, 4)
    assert (pages, codes) == (1, 3)
    assert sorted(scan_image(out, 3)) == sorted(lines)
