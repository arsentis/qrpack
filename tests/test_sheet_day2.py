"""Day 2 layout tests. All generated images stay in pytest's temporary directory."""

from pathlib import Path

import pytest
from PIL import Image

from qrpack.sheet import PAGE_HEIGHT, PAGE_WIDTH, make_sheet, render_qr


def test_single_sheet_png(tmp_path):
    target = tmp_path / "sheet.png"
    assert make_sheet(["one", "two", "three"], "Example", target, cols=2, scale=4) == (1, 3)
    with Image.open(target) as image:
        assert image.size == (PAGE_WIDTH, PAGE_HEIGHT)
        assert image.info.get("dpi")[0] == pytest.approx(300, abs=1)


def test_multipage_png_names_and_counts(tmp_path):
    # 48 codes cannot fit in a single A4 page at 4 columns / scale 4.
    target = tmp_path / "sheet.png"
    pages, codes = make_sheet([f"QRPK1|part-{i}" for i in range(100)], "Backup", target, 4, 4)
    assert pages > 1
    assert codes == 100
    assert not target.exists()
    assert len(list(tmp_path.glob("sheet-*.png"))) == pages
    assert (tmp_path / "sheet-001.png").is_file()


def test_pdf_output_and_multipage(tmp_path):
    target = tmp_path / "sheet.pdf"
    pages, codes = make_sheet([str(i) for i in range(100)], "Backup", target, 4, 4)
    assert codes == 100
    assert pages > 1
    assert target.read_bytes().startswith(b"%PDF-")


def test_preserves_render_qr_from_day_one(tmp_path):
    path = render_qr("QRPK1|abc|0/1|SGVsbG8=", tmp_path / "single.png")
    assert path.is_file()


@pytest.mark.parametrize("payloads", [[], [""], ["ok", None]])
def test_rejects_invalid_payloads(tmp_path, payloads):
    with pytest.raises((TypeError, ValueError)):
        make_sheet(payloads, "test", tmp_path / "sheet.png")
    assert not (tmp_path / "sheet.png").exists()


@pytest.mark.parametrize("cols,scale", [(0, 4), (True, 4), (4, 0), (4, True), (100, 4)])
def test_rejects_invalid_layout(tmp_path, cols, scale):
    with pytest.raises((TypeError, ValueError)):
        make_sheet(["abc"], "test", tmp_path / "sheet.png", cols, scale)


def test_unsupported_output_type(tmp_path):
    with pytest.raises(ValueError, match="extension"):
        make_sheet(["test"], "title", tmp_path / "sheet.jpg")
