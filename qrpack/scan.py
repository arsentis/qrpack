"""Decoding layer of qrpack: turn QR images back into text."""

from pathlib import Path

import cv2


def decode_one(path: Path) -> str:
    """Decode a single QR image and return its text."""
    image = cv2.imread(str(path))
    text, _, _ = cv2.QRCodeDetector().detectAndDecode(image)
    return text
