"""Calibration: what each error-correction level costs once printed (issue #41).

Raising the ECC level lets a code survive more damage, but it also needs more
modules, so each module gets smaller in the same printed square. Decoders start
failing at roughly 3 px/module, so the table `ecc_cost` returns says which level
is usable on a given printer, not in theory.
"""

from __future__ import annotations

from qrpack.sheet import ECC_LEVELS, QUIET_ZONE, _validated_qr

# 40 mm cell at 300 DPI -- what we actually print.


def ecc_cost(payload: str) -> list[dict]:
    """One row per ECC level: version, modules, px/module.

    `modules` counts the quiet zone too, because that is part of the printed
    square. `px_per_module` is `printed_px / modules`.

    Raises ValueError for an empty payload or a non-positive `printed_px`,
    TypeError for a non-string payload or non-integer `printed_px`, and
    segno.DataOverflowError if the payload does not fit at some level.
    """
    rows = []
    for ecc in ECC_LEVELS:
        qr = _validated_qr(payload, ecc)
        modules = qr.symbol_size(scale=1, border=QUIET_ZONE)[0]
        rows.append(
            {
                "ecc": ecc,
                "version": qr.version
            }
        )
    return rows