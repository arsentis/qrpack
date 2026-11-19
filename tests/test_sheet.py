"""Day 1 tests for generating a single QR code."""

from pathlib import Path

import cv2
import pytest

from qrpack.sheet import render_qr


PAYLOAD = "QRPK1|1234567890abcdef|0/1|SGVsbG8="


def test_render_qr_creates_png(tmp_path: Path) -> None:
    target = tmp_path / "code.png"
    result = render_qr(PAYLOAD, target)

    assert result == target
    assert target.is_file()
    assert target.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_render_qr_round_trips_payload(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "code.png"
    render_qr(PAYLOAD, target)

    image = cv2.imread(str(target))
    assert image is not None
    decoded, points, _ = cv2.QRCodeDetector().detectAndDecode(image)
    assert points is not None
    assert decoded == PAYLOAD


@pytest.mark.parametrize("payload", ["", None, b"bytes"])
def test_rejects_invalid_payload(payload, tmp_path: Path) -> None:
    with pytest.raises((TypeError, ValueError)):
        render_qr(payload, tmp_path / "code.png")


@pytest.mark.parametrize("scale", [0, -1, 1.5, True])
def test_rejects_invalid_scale(scale, tmp_path: Path) -> None:
    with pytest.raises((TypeError, ValueError)):
        render_qr(PAYLOAD, tmp_path / "code.png", scale=scale)


def test_rejects_non_png_output(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="png"):
        render_qr(PAYLOAD, tmp_path / "code.pdf")
