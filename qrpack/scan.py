"""Decoding layer of qrpack: turn QR images back into text."""

import base64
from pathlib import Path

import cv2

from qrpack.core import Header


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


def reassemble(texts: list[str]) -> tuple[bytes, str, list[int]]:
    """Join payload lines into the original blob.

    Returns (blob, digest, missing). If any part is missing, blob is
    empty and missing lists the part numbers, so a damaged sheet is
    reported rather than silently restored wrong.
    """
    if not texts:
        raise ValueError("no payloads to reassemble")
    headers = [Header.parse(t) for t in texts]
    if len({h.digest for h in headers}) != 1:
        raise ValueError("payloads come from different archives")
    if len({h.total for h in headers}) != 1:
        raise ValueError("payloads disagree on the number of parts")

    digest = headers[0].digest
    total = headers[0].total
    by_index = {h.index: h for h in headers}
    missing = [i for i in range(1, total + 1) if i not in by_index]
    if missing:
        return b"", digest, missing

    blob = b"".join(
        base64.b64decode(by_index[i].payload) for i in range(1, total + 1)
    )
    return blob, digest, []
