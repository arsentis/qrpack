"""Tests for qrpack.calibrate.survives (issue #42): does a printed, photographed code still decode?"""

from __future__ import annotations

import random

from qrpack.calibrate import survives
from qrpack.core import chunk


def payload_of(raw_bytes: int) -> str:
    """A real qrpack payload line carrying `raw_bytes` bytes of the blob."""
    return chunk(random.Random(0).randbytes(raw_bytes), raw_bytes)[0].decode("ascii")


SMALL = payload_of(100)


def test_a_clean_large_render_survives():
    assert survives(SMALL, printed_px=800) is True


def test_an_extremely_small_render_does_not():
    assert survives(SMALL, printed_px=20) is False
