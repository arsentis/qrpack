"""Tests for qrpack.calibrate.survives (issue #42): does a printed, photographed code still decode?"""

from __future__ import annotations

import random

import pytest
import segno

import qrpack.calibrate
from qrpack.calibrate import survives, sweep
from qrpack.core import chunk


def payload_of(raw_bytes: int) -> str:
    """A real qrpack payload line carrying `raw_bytes` bytes of the blob."""
    return chunk(random.Random(0).randbytes(raw_bytes), raw_bytes)[0].decode("ascii")


SMALL = payload_of(100)


def test_a_clean_large_render_survives():
    assert survives(SMALL, printed_px=800) is True


def test_an_extremely_small_render_does_not():
    assert survives(SMALL, printed_px=20) is False


def test_decoded_text_that_differs_is_not_survival(monkeypatch):
    """True only when the decoded text equals the original payload."""
    monkeypatch.setattr(qrpack.calibrate, "decode_one", lambda path: "something else")
    assert survives(SMALL, printed_px=800) is False


def test_heavy_blur_destroys_a_clean_code():
    assert survives(SMALL, printed_px=472) is True
    assert survives(SMALL, printed_px=472, blur=12) is False


def test_a_jpeg_round_trip_still_returns_a_bool():
    assert survives(SMALL, printed_px=472, jpeg_quality=90) is True


@pytest.mark.parametrize("bad", [0, -472])
def test_non_positive_printed_size_is_rejected(bad):
    with pytest.raises(ValueError, match="printed_px"):
        survives(SMALL, printed_px=bad)


@pytest.mark.parametrize("bad", [472.0, "472", True])
def test_non_integer_printed_size_is_rejected(bad):
    with pytest.raises(TypeError):
        survives(SMALL, printed_px=bad)


def test_negative_blur_is_rejected():
    with pytest.raises(ValueError, match="blur"):
        survives(SMALL, printed_px=472, blur=-1)


def test_non_integer_blur_is_rejected():
    with pytest.raises(TypeError):
        survives(SMALL, printed_px=472, blur=1.5)


@pytest.mark.parametrize("bad", [0, 101])
def test_jpeg_quality_outside_1_to_100_is_rejected(bad):
    with pytest.raises(ValueError, match="jpeg_quality"):
        survives(SMALL, printed_px=472, jpeg_quality=bad)


def test_unknown_ecc_level_is_rejected():
    with pytest.raises(ValueError, match="error-correction"):
        survives(SMALL, printed_px=472, ecc="x")


def test_a_payload_that_cannot_be_encoded_fails_loudly():
    with pytest.raises(segno.DataOverflowError):
        survives("A" * 5000, printed_px=472)


SIZES = (100, 300, 600, 1500)


def test_sweep_returns_a_row_per_size():
    rows = sweep(SIZES, printed_px=472)
    assert [row["chunk_bytes"] for row in rows] == list(SIZES)
    expected = {
        "chunk_bytes", "payload_chars", "fits", "version",
        "modules", "px_per_module", "survives",
    }
    assert all(set(row) == expected for row in rows)


def test_sweep_resizes_every_code_to_the_same_printed_size():
    """The trap in #42: scaling by a fraction would give big codes the same
    pixels per module as small ones. At one printed size they get fewer."""
    rows = sweep(SIZES, printed_px=472)
    for row in rows:
        assert row["px_per_module"] == pytest.approx(472 / row["modules"])
    per_module = [row["px_per_module"] for row in rows]
    assert per_module == sorted(per_module, reverse=True)
    assert len(set(per_module)) == len(per_module)


def test_a_bigger_code_never_survives_where_a_smaller_one_failed():
    """The nonsense result the issue warns about: a big code passing while a
    smaller one fails."""
    results = [row["survives"] for row in sweep(SIZES, printed_px=472)]
    assert results[0] is True      # small codes survive
    assert results[-1] is False    # the biggest does not at this printed size
    assert results == sorted(results, reverse=True)


def test_sweep_passes_blur_through():
    assert sweep((100,), printed_px=472, blur=12)[0]["survives"] is False


def test_sweep_marks_a_size_that_does_not_fit_instead_of_crashing():
    rows = sweep((100, 2200), printed_px=472)
    assert rows[0]["fits"] is True
    assert rows[1]["fits"] is False
    assert rows[1]["survives"] is False
    assert rows[1]["version"] is None


@pytest.mark.parametrize("bad", [(), (0,), (-5, 100)])
def test_sweep_rejects_empty_or_non_positive_sizes(bad):
    with pytest.raises(ValueError):
        sweep(bad)


def test_sweep_rejects_a_non_integer_size():
    with pytest.raises(TypeError):
        sweep((100.5,))
