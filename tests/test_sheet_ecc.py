"""Tests for the error-correction parameter on the sheet renderers (issue #3).

The last open criterion of #3: "the error-correction level is a parameter, not
hard-coded". It matters beyond tidiness — ECC level is the main knob deciding
whether a *printed* code still scans, and the calibration work in #11 has to
vary it to produce a px/module table.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import segno
from PIL import Image

from qrpack.sheet import DEFAULT_ECC, make_sheet, render_qr

PAYLOAD = "QRPK1|0123456789abcdef|1/1|" + "A" * 400


def test_default_is_unchanged(tmp_path: Path):
    """Callers that pass no ecc must keep the previous behaviour."""
    assert DEFAULT_ECC == "m"
    default = render_qr(PAYLOAD, tmp_path / "default.png")
    explicit = render_qr(PAYLOAD, tmp_path / "explicit.png", ecc="m")
    with Image.open(default) as a, Image.open(explicit) as b:
        assert a.size == b.size


@pytest.mark.parametrize("ecc", ["l", "m", "q", "h"])
def test_every_level_renders(ecc: str, tmp_path: Path):
    out = render_qr(PAYLOAD, tmp_path / f"{ecc}.png", ecc=ecc)
    assert out.is_file()
    with Image.open(out) as image:
        assert image.size[0] == image.size[1], "a QR symbol must be square"


def test_higher_correction_needs_a_bigger_symbol(tmp_path: Path):
    """The trade-off made visible: more recovery data, more modules.

    This is the measurement #11 depends on, so assert the ordering rather than
    trusting the library.
    """
    sizes = {}
    for ecc in ("l", "m", "q", "h"):
        with Image.open(render_qr(PAYLOAD, tmp_path / f"s-{ecc}.png", ecc=ecc)) as image:
            sizes[ecc] = image.size[0]
    assert sizes["l"] <= sizes["m"] <= sizes["q"] <= sizes["h"]
    assert sizes["h"] > sizes["l"], "H must cost more modules than L"


def test_level_is_actually_applied_not_just_accepted(tmp_path: Path):
    """Guards against an `ecc` argument that is parsed and then ignored."""
    render_qr(PAYLOAD, tmp_path / "h.png", ecc="h")
    expected = segno.make(PAYLOAD, error="h", micro=False, boost_error=False)
    with Image.open(tmp_path / "h.png") as image:
        assert image.size == expected.symbol_size(scale=8, border=4)


@pytest.mark.parametrize("bad", ["x", "", "medium", "H!", None, 2])
def test_rejects_an_unknown_level(bad, tmp_path: Path):
    with pytest.raises((TypeError, ValueError)):
        render_qr(PAYLOAD, tmp_path / "bad.png", ecc=bad)
    assert not (tmp_path / "bad.png").exists()


def test_level_is_case_insensitive(tmp_path: Path):
    """`-e H` from a CLI must behave like `h`, not raise."""
    upper = render_qr(PAYLOAD, tmp_path / "upper.png", ecc="H")
    lower = render_qr(PAYLOAD, tmp_path / "lower.png", ecc="h")
    with Image.open(upper) as a, Image.open(lower) as b:
        assert a.size == b.size


def test_make_sheet_accepts_the_level(tmp_path: Path):
    """The sheet path must thread ecc through, not only the single renderer."""
    target = tmp_path / "sheet.png"
    pages, codes = make_sheet([PAYLOAD, PAYLOAD], "ECC test", target, cols=2, scale=4, ecc="q")
    assert (pages, codes) == (1, 2)
    assert target.is_file()


def test_make_sheet_rejects_an_unknown_level(tmp_path: Path):
    with pytest.raises((TypeError, ValueError)):
        make_sheet([PAYLOAD], "bad", tmp_path / "sheet.png", ecc="nope")
    assert not (tmp_path / "sheet.png").exists()
