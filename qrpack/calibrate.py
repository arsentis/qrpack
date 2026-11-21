"""Calibration: what ECC levels cost, and what survives printing (issues #41, #42).

Raising the ECC level lets a code survive more damage, but it also needs more
modules, so each module gets smaller in the same printed square. Decoders start
failing at roughly 3 px/module, so the table `ecc_cost` returns says which level
is usable on a given printer, not in theory. `survives` goes one step further:
it simulates print + photo and asks whether the code still decodes.
"""

from __future__ import annotations

import io
import random
import tempfile
from pathlib import Path

import segno
from PIL import Image, ImageFilter

from qrpack.core import chunk
from qrpack.scan import decode_one
from qrpack.sheet import ECC_LEVELS, QUIET_ZONE, _check_ecc, _validated_qr, render_codes

# 40 mm cell at 300 DPI -- what we actually print.
PRINTED_PX = 472

# Raw bytes of the blob per code, the ladder `sweep` climbs by default.
LADDER = (100, 300, 600, 900, 1200, 1500)


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

    Raises TypeError/ValueError for bad arguments and segno.DataOverflowError
    if the payload does not fit in any QR code: an unencodable payload is a
    caller error, not a code that failed to survive.
    """
    _check_args(printed_px, blur, jpeg_quality, ecc)
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


def _check_int(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")


def _check_args(printed_px: int, blur: int, jpeg_quality: int, ecc: str) -> None:
    _check_int("printed_px", printed_px)
    if printed_px <= 0:
        raise ValueError("printed_px must be positive")
    _check_int("blur", blur)
    if blur < 0:
        raise ValueError("blur must not be negative")
    _check_int("jpeg_quality", jpeg_quality)
    if not 1 <= jpeg_quality <= 100:
        raise ValueError("jpeg_quality must be between 1 and 100")
    _check_ecc(ecc)


def _payload_of(chunk_bytes: int) -> str:
    """A deterministic, realistic payload line carrying `chunk_bytes` bytes."""
    raw = random.Random(0).randbytes(chunk_bytes)
    return chunk(raw, chunk_bytes)[0].decode("ascii")


def sweep(
    chunk_sizes=LADDER,
    printed_px: int = PRINTED_PX,
    blur: int = 0,
    jpeg_quality: int = 100,
    ecc: str = "m",
) -> list[dict]:
    """One pass/fail row per payload size, every code at the same printed size.

    `chunk_sizes` counts raw blob bytes per code, like `--chunk`. A row has
    chunk_bytes, payload_chars, fits, version, modules, px_per_module and
    survives. A size too big for any QR code at this `ecc` gets fits=False,
    survives=False and None for the rest, so a sweep can run past the limit.
    """
    _check_args(printed_px, blur, jpeg_quality, ecc)
    sizes = tuple(chunk_sizes)
    if not sizes:
        raise ValueError("chunk_sizes must not be empty")
    for size in sizes:
        _check_int("chunk size", size)
        if size <= 0:
            raise ValueError("chunk size must be positive")

    rows = []
    for size in sizes:
        payload = _payload_of(size)
        try:
            qr = _validated_qr(payload, ecc)
        except segno.DataOverflowError:
            rows.append(
                {
                    "chunk_bytes": size,
                    "payload_chars": len(payload),
                    "fits": False,
                    "version": None,
                    "modules": None,
                    "px_per_module": None,
                    "survives": False,
                }
            )
            continue
        modules = qr.symbol_size(scale=1, border=QUIET_ZONE)[0]
        rows.append(
            {
                "chunk_bytes": size,
                "payload_chars": len(payload),
                "fits": True,
                "version": qr.version,
                "modules": modules,
                "px_per_module": printed_px / modules,
                "survives": survives(payload, printed_px, blur, jpeg_quality, ecc),
            }
        )
    return rows
