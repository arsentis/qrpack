"""Decoding layer of qrpack: turn QR images back into text."""

from pathlib import Path

import cv2


def decode_one(path: Path) -> str:
    """Decode a single QR image and return the text it encodes.

    Raises ValueError if the file cannot be read as an image, or if no
    QR code can be decoded from it. A silent empty string would hide a
    damaged code, so failures are always loud.
    """
    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"cannot read image: {path}")
    text, _, _ = cv2.QRCodeDetector().detectAndDecode(image)
    if not text:
        raise ValueError(f"no QR code found in {path}")
    return text
