"""Day 3: black out one code on a rendered sheet and name the lost part (#12).

The pieces under test already exist: ``sheet.make_sheet`` renders the sheet,
``scan.scan_image`` reads what is left, ``scan.reassemble`` refuses a partial
set, and the CLI restore refuses to write a corrupt archive. This test wires
them together with one QR symbol painted out, the way a stain or a folded
corner would destroy one code on a printed sheet.
"""

import random
from pathlib import Path

import pytest
import segno
from PIL import Image, ImageDraw

from qrpack.cli import main
from qrpack.core import Header, chunk, compress, pack_bytes
from qrpack.scan import reassemble, scan_image
from qrpack.sheet import (
    CELL_GAP,
    DEFAULT_ECC,
    FOOTER_HEIGHT,
    HEADER_HEIGHT,
    LABEL_HEIGHT,
    MARGIN,
    PAGE_HEIGHT,
    QUIET_ZONE,
    make_sheet,
)

COLS = 3
SCALE = 4
CHUNK = 1000
BLACKED_PART = 3


def _packed_payloads(tmp_path: Path, size: int = 4000) -> tuple[list[str], Path]:
    """Pack a deterministic file into payload lines, and return its source."""
    source = tmp_path / "source"
    source.mkdir(exist_ok=True)
    (source / "secret.bin").write_bytes(random.Random(0).randbytes(size))
    blob = compress(pack_bytes(source))
    return [p.decode("ascii") for p in chunk(blob, CHUNK)], source


def _black_out(
    sheet: Path,
    payloads: list[str],
    part: int,
    cols: int,
    scale: int,
    per_page: int | None = None,
) -> None:
    """Paint one QR symbol black, using make_sheet's own cell geometry.

    ``per_page`` is needed when the part lives on a later page: the row/column
    is local to the page, not to the whole sheet.
    """
    qrs = [
        segno.make(p, error=DEFAULT_ECC, micro=False, boost_error=False)
        for p in payloads
    ]
    sizes = [qr.symbol_size(scale=scale, border=QUIET_ZONE) for qr in qrs]
    cell_width = max(width for width, _ in sizes)
    symbol_height = max(height for _, height in sizes)
    index = part - 1
    if per_page is not None:
        index %= per_page
    row, col = divmod(index, cols)
    x = MARGIN + col * (cell_width + CELL_GAP)
    y = MARGIN + HEADER_HEIGHT + row * (symbol_height + LABEL_HEIGHT + CELL_GAP)
    with Image.open(sheet) as image:
        damaged = image.copy()
    ImageDraw.Draw(damaged).rectangle(
        [x, y, x + cell_width, y + symbol_height], fill="black"
    )
    damaged.save(sheet)


def _sheet_with_one_code_blacked_out(tmp_path: Path) -> tuple[Path, int]:
    payloads, _ = _packed_payloads(tmp_path)
    total = len(payloads)
    assert total > BLACKED_PART  # need a middle part, not the first or last

    sheet = tmp_path / "sheet.png"
    pages, codes = make_sheet(payloads, "damage test", sheet, cols=COLS, scale=SCALE)
    assert (pages, codes) == (1, total)
    _black_out(sheet, payloads, BLACKED_PART, COLS, SCALE)
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


@pytest.mark.parametrize("part", [1, BLACKED_PART, 5])
def test_any_single_code_can_be_blacked_out_and_named(tmp_path, part):
    payloads, _ = _packed_payloads(tmp_path)
    total = len(payloads)
    assert total >= 5

    sheet = tmp_path / f"sheet-{part}.png"
    make_sheet(payloads, "damage test", sheet, cols=COLS, scale=SCALE)
    _black_out(sheet, payloads, part, COLS, SCALE)

    texts = scan_image(sheet, COLS)
    assert {Header.parse(t).index for t in texts} == set(range(1, total + 1)) - {part}
    _, _, missing = reassemble(texts)
    assert missing == [part]
    assert main(["restore", str(sheet), "-o", str(tmp_path / f"out-{part}")]) == 1


def test_blacked_out_code_on_a_later_page_is_named(tmp_path):
    payloads, _ = _packed_payloads(tmp_path)
    total = len(payloads)

    sheet = tmp_path / "multipage.png"
    pages, codes = make_sheet(payloads, "damage test", sheet, cols=1, scale=SCALE)
    assert (pages, codes) > (1, total)   # one column spreads the parts over pages

    # Mirror make_sheet's page arithmetic to locate the last part's page/cell.
    qrs = [
        segno.make(p, error=DEFAULT_ECC, micro=False, boost_error=False)
        for p in payloads
    ]
    symbol_height = max(
        qr.symbol_size(scale=SCALE, border=QUIET_ZONE)[1] for qr in qrs
    )
    available = PAGE_HEIGHT - MARGIN - HEADER_HEIGHT - FOOTER_HEIGHT - MARGIN
    rows = (available + CELL_GAP) // (symbol_height + LABEL_HEIGHT + CELL_GAP)
    per_page = rows                       # one column
    last_page = (total - 1) // per_page + 1

    page_path = tmp_path / f"multipage-{last_page:03d}.png"
    _black_out(page_path, payloads, total, cols=1, scale=SCALE, per_page=per_page)

    page_paths = sorted(tmp_path.glob("multipage-*.png"))
    assert len(page_paths) == pages
    texts = []
    for path in page_paths:
        texts.extend(scan_image(path, 1))
    _, _, missing = reassemble(texts)
    assert missing == [total]
    assert main(["restore", *map(str, page_paths), "-o", str(tmp_path / "out")]) == 1


def test_intact_duplicate_rescues_a_damaged_sheet(tmp_path):
    payloads, source = _packed_payloads(tmp_path)
    damaged, total = _sheet_with_one_code_blacked_out(tmp_path)
    intact = tmp_path / "intact.png"
    make_sheet(payloads, "intact copy", intact, cols=COLS, scale=SCALE)

    output = tmp_path / "restored"
    assert main(["restore", str(damaged), str(intact), "-o", str(output)]) == 0
    assert (output / "secret.bin").read_bytes() == (source / "secret.bin").read_bytes()
