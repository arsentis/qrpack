"""Tests for the decoding layer of qrpack.scan (day 1: decode_one).

Written before the implementation: decode_one must turn one QR image
into the exact text that was encoded in it.
"""

import cv2
import numpy as np
import pytest
import segno

from qrpack.scan import decode_one


LINE = "QRPK1|0123456789abcdef|1/3|SGVsbG8="   # frozen payload format


def make_qr_png(tmp_path, text, error="m"):
    path = tmp_path / "code.png"
    segno.make(text, error=error).save(path, scale=8, border=4)
    return path


def test_decode_one_returns_the_encoded_text(tmp_path):
    path = make_qr_png(tmp_path, LINE)
    assert decode_one(path) == LINE


def test_decode_one_rejects_a_missing_file(tmp_path):
    with pytest.raises(ValueError, match="read"):
        decode_one(tmp_path / "does_not_exist.png")


def test_decode_one_rejects_an_image_without_a_code(tmp_path):
    blank = tmp_path / "blank.png"
    cv2.imwrite(str(blank), np.full((200, 200, 3), 255, dtype="uint8"))
    with pytest.raises(ValueError, match="QR"):
        decode_one(blank)
