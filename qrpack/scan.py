"""Decoding layer of qrpack: turn QR images back into text."""

import base64
from pathlib import Path

import cv2
import numpy as np

from qrpack.core import Header

# OpenCV's decoder is not monotonic in scale: a code that fails at one
# size can decode at another, so each cell is tried at several sizes.
SCALES = (1.0, 0.75, 1.5, 2.0, 0.5, 0.35, 0.25)
MIN_CELL = 40      # ignore blobs smaller than this many pixels (text, specks)
BORDER = 40        # white margin re-added around a cropped code


def _detectors() -> list:
    """Return the available QR detectors, best first.

    Measured on dense codes (~1,360 chars): the Aruco-based detector reads
    them, the classic QRCodeDetector reads none. The classic one stays as
    a fallback for OpenCV builds without Aruco.
    """
    found = []
    if hasattr(cv2, "QRCodeDetectorAruco"):
        found.append(cv2.QRCodeDetectorAruco())
    found.append(cv2.QRCodeDetector())
    return found


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


def _find_cells(gray) -> list[tuple[int, int, int, int]]:
    """Locate square dark blobs (the QR symbols) on a grayscale sheet.

    Dilating merges the modules of each symbol into one solid blob, while
    titles and captions stay wide and short and are filtered out by shape.
    Returns (y, x, width, height) boxes in reading order.
    """
    _, binary = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )
    blobs = cv2.dilate(binary, np.ones((9, 9), np.uint8))
    contours, _ = cv2.findContours(
        blobs, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w >= MIN_CELL and h >= MIN_CELL and 0.8 <= w / h <= 1.25:
            boxes.append((y, x, w, h))
    return sorted(boxes)


def _decode_cell(cell) -> str:
    """Try to decode one cropped code with each detector at several scales."""
    for detector in _detectors():
        for factor in SCALES:
            method = cv2.INTER_AREA if factor < 1 else cv2.INTER_NEAREST
            resized = cv2.resize(
                cell, None, fx=factor, fy=factor, interpolation=method
            )
            text, _, _ = detector.detectAndDecode(resized)
            if text:
                return text
    return ""


def scan_image(path: Path, cols: int) -> list[str]:
    """Decode every QR code on a sheet image and return their texts.

    Each code is located, cropped and decoded on its own. Codes that
    cannot be decoded are simply absent from the result; reassemble()
    then names the missing part numbers instead of guessing.

    ``cols`` is part of the agreed signature but is not needed yet,
    because codes are found by image analysis, not grid arithmetic.
    """
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"cannot read image: {path}")
    texts = []
    for y, x, w, h in _find_cells(image):
        cell = image[y : y + h, x : x + w]
        cell = cv2.copyMakeBorder(
            cell, BORDER, BORDER, BORDER, BORDER,
            cv2.BORDER_CONSTANT, value=255,
        )
        text = _decode_cell(cell)
        if text.startswith("QRPK1|"):
            texts.append(text)
    return texts


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
