"""Tests for qrpack.calibrate (issue #41): what each ECC level costs in print."""

from __future__ import annotations

import pytest

from qrpack.calibrate import ecc_cost
from qrpack.sheet import ECC_LEVELS

# A realistic qrpack payload: header plus a 1,200-byte base64 chunk.
PAYLOAD = "QRPK1|0123456789abcdef|1/9|" + "QRPKdata" * 150


def test_returns_one_row_per_level():
    rows = ecc_cost(PAYLOAD)
    assert [row["ecc"] for row in rows] == list(ECC_LEVELS)


def test_each_row_has_the_agreed_fields():
    for row in ecc_cost(PAYLOAD):
        assert set(row) == {"ecc", "version", "modules", "px_per_module"}


def test_modules_increase_from_l_to_h():
    """More recovery data cannot need fewer modules."""
    modules = [row["modules"] for row in ecc_cost(PAYLOAD)]
    assert modules == sorted(modules)
    assert len(set(modules)) == len(modules)  # strictly, for this payload


def test_px_per_module_decreases_as_ecc_rises():
    """Fixed printed size, more modules -> each module is smaller."""
    px = [row["px_per_module"] for row in ecc_cost(PAYLOAD, printed_px=472)]
    assert px == sorted(px, reverse=True)
    assert len(set(px)) == len(px)


def test_tiny_payload_never_decreases_modules():
    """A short payload may fit the same version at every level: equal, not fewer."""
    modules = [row["modules"] for row in ecc_cost("QRPK1|0123456789abcdef|1/1|AA")]
    assert modules == sorted(modules)


def test_matches_the_numbers_quoted_in_sheet_py():
    """The table in sheet.py's comment is reproducible from this function."""
    rows = {row["ecc"]: row for row in ecc_cost(PAYLOAD)}
    assert {k: r["modules"] for k, r in rows.items()} == {"l": 125, "m": 141, "q": 161, "h": 185}
    assert {k: round(r["px_per_module"], 2) for k, r in rows.items()} == {
        "l": 3.78, "m": 3.35, "q": 2.93, "h": 2.55,
    }


def test_empty_payload_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        ecc_cost("")


def test_non_string_payload_is_rejected():
    with pytest.raises(TypeError):
        ecc_cost(b"bytes")


@pytest.mark.parametrize("bad", [0, -472])
def test_non_positive_printed_size_is_rejected(bad):
    with pytest.raises(ValueError, match="positive"):
        ecc_cost(PAYLOAD, printed_px=bad)


@pytest.mark.parametrize("bad", [472.0, "472", True])
def test_non_integer_printed_size_is_rejected(bad):
    with pytest.raises(TypeError):
        ecc_cost(PAYLOAD, printed_px=bad)


def test_payload_too_large_for_any_code_fails_loudly():
    import segno

    with pytest.raises(segno.DataOverflowError):
        ecc_cost("A" * 5000)
