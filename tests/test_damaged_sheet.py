"""Day 3: black out one code on a rendered sheet and name the lost part (#12).

The pieces under test already exist: ``sheet.make_sheet`` renders the sheet,
``scan.scan_image`` reads what is left, ``scan.reassemble`` refuses a partial
set, and the CLI restore refuses to write a corrupt archive. This test wires
them together with one QR symbol painted out, the way a stain or a folded
corner would destroy one code on a printed sheet.
"""

import random
from pathlib import Path

import segno
from PIL import Image, ImageDraw

from qrpack.cli import main
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


def _sheet_with_one_code_blacked_out(tmp_path: Path) -> tuple[Path, int]:
    """Pack a deterministic file, render it, paint out one QR symbol."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "secret.bin").write_bytes(random.Random(0).randbytes(4000))
    blob = compress(pack_bytes(source))
    payloads = [p.decode("ascii") for p in chunk(blob, CHUNK)]
    total = len(payloads)
    assert total > BLACKED_PART  # need a middle part, not the first or last

    sheet = tmp_path / "sheet.png"
    pages, codes = make_sheet(payloads, "damage test", sheet, cols=COLS, scale=SCALE)
    assert (pages, codes) == (1, total)

    # Reproduce make_sheet's cell geometry so exactly one symbol is covered.
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
    return sheet, total


def test_blacked_out_code_is_named_and_restore_is_refused(tmp_path, capsys):
    sheet, total = _sheet_with_one_code_blacked_out(tmp_path)

    texts = scan_image(sheet, COLS)
    indices = {Header.parse(t).index for t in texts}
    assert indices == set(range(1, total + 1)) - {BLACKED_PART}

    blob, digest, missing = reassemble(texts)
    assert missing == [BLACKED_PART]
    assert blob == b""                  # never hand back a partial archive
    assert len(digest) == 16

    output = tmp_path / "restored"
    assert main(["restore", str(sheet), "-o", str(output)]) == 1
    assert f"missing parts [{BLACKED_PART}]" in capsys.readouterr().err
    assert not list(output.glob("*"))   # no corrupt files were written
