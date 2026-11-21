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
