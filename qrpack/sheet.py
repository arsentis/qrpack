"""Render QR payloads as PNG images.

Day 1 covers individual QR codes; grid and page layout come later.
"""

from pathlib import Path

import segno


def render_qr(payload: str, out_path: str | Path, scale: int = 8) -> Path:
    """Save a payload as a scannable PNG QR code.

    Preserve payload text exactly. A four-module quiet zone helps scanners
    detect the symbol. The caller controls the pixels-per-module ``scale``.

    Args:
        payload: Nonempty QRPK1 payload string (validation of framing is
            handled by the core module).
        out_path: Destination PNG path.
        scale: Positive integer number of pixels per QR module.

    Returns:
        Path to the written PNG.

    Raises:
        TypeError: If the payload or scale has the wrong type.
        ValueError: If payload is empty, scale is invalid, or the QR is too large.
    """
    if not isinstance(payload, str):
        raise TypeError("payload must be a string")
    if not payload:
        raise ValueError("payload must not be empty")
    if isinstance(scale, bool) or not isinstance(scale, int):
        raise TypeError("scale must be an integer")
    if scale <= 0:
        raise ValueError("scale must be positive")

    output = Path(out_path)
    if output.suffix.lower() != ".png":
        raise ValueError("output file must have a .png extension")

    # Use an ordinary QR Code (not a Micro QR Code), so downstream scanners
    # can always expect the standard four-module quiet zone.
    qr = segno.make(payload, error="m", micro=False, boost_error=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    qr.save(str(output), kind="png", scale=scale, border=4)
    return output
