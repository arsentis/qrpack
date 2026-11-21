"""Calibration: what ECC levels cost, and what survives printing (issues #41, #42).

Raising the ECC level lets a code survive more damage, but it also needs more
modules, so each module gets smaller in the same printed square. Decoders start
failing at roughly 3 px/module, so the table `ecc_cost` returns says which level
is usable on a given printer, not in theory. `survives` goes one step further:
it simulates print + photo and asks whether the code still decodes.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

from PIL import Image, ImageFilter

from qrpack.scan import decode_one
from qrpack.sheet import ECC_LEVELS, QUIET_ZONE, _validated_qr, render_codes

# 40 mm cell at 300 DPI -- what we actually print.
PRINTED_PX = 472


def ecc_cost(payload: str, printed_px: int = PRINTED_PX) -> list[dict]:
    """One row per ECC level: version, modules, px/module.

    `modules` counts the quiet zone too, because that is part of the printed
    square. `px_per_module` is `printed_px / modules`.

    Raises ValueError for an empty payload or a non-positive `printed_px`,
    TypeError for a non-string payload or non-integer `printed_px`, and
    segno.DataOverflowError if the payload does not fit at some level.
    """
    if isinstance(printed_px, bool) or not isinstance(printed_px, int):
        raise TypeError("printed_px must be an integer")
    if printed_px <= 0:
        raise ValueError("printed_px must be positive")
    rows = []
    for ecc in ECC_LEVELS:
        qr = _validated_qr(payload, ecc)
        modules = qr.symbol_size(scale=1, border=QUIET_ZONE)[0]
        rows.append(
            {
                "ecc": ecc,
                "version": qr.version,
                "modules": modules,
                "px_per_module": printed_px / modules,
            }
        )
    return rows


def survives(
    payload: str,
    printed_px: int,
    blur: int = 0,
    jpeg_quality: int = 100,
    ecc: str = "m",
) -> bool:
    """Render one code, simulate print + photo, and report whether it decodes.

    The code is rendered with `sheet.render_codes`, then resized to a square of
    `printed_px` pixels. That is the point of the function: on paper every cell
    occupies the same physical square, so a denser symbol gets fewer pixels per
    module. Scaling every code by the same *fraction* instead would make big
    codes look artificially good. `blur` is a Gaussian radius in pixels and
    `jpeg_quality` below 100 adds a JPEG round trip (100 means none).

    True only if `scan.decode_one` returns exactly the original payload.
    """
    cell = render_codes([payload], ecc=ecc)[0]
    image = cell.resize((printed_px, printed_px), Image.Resampling.BOX)
    if blur:
        image = image.filter(ImageFilter.GaussianBlur(blur))
    if jpeg_quality < 100:
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=jpeg_quality)
        buffer.seek(0)
        with Image.open(buffer) as jpeg:
            image = jpeg.convert("RGB")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "photo.png"
        image.save(path)
        try:
            return decode_one(path) == payload
        except ValueError:
            return False
