#!/usr/bin/env python3
"""What does each error-correction level cost? (issue #3)

The numbers quoted in sheet.py come from here, so a reviewer can reproduce
them instead of trusting a comment.

    python3 tests/measure_ecc_cost.py
"""
from __future__ import annotations

import segno

from qrpack.sheet import ECC_LEVELS, QUIET_ZONE, render_codes

# A realistic qrpack payload: header plus a 1,200-byte base64 chunk.
PAYLOAD = "QRPK1|0123456789abcdef|1/9|" + "QRPKdata" * 150

# Printed cell size we design for: 40 mm at 300 DPI.
PRINTED_PX = 472

RECOVERY = {"l": "~7%", "m": "~15%", "q": "~25%", "h": "~30%"}


def main() -> None:
    print(f"payload: {len(PAYLOAD)} characters\n")
    print(f"{'ecc':>4}  {'version':>7}  {'modules':>7}  {'px/module':>9}  recovers")
    baseline = None
    for ecc in ECC_LEVELS:
        qr = segno.make(PAYLOAD, error=ecc, micro=False, boost_error=False)
        modules = qr.symbol_size(scale=1, border=QUIET_ZONE)[0]
        per_module = PRINTED_PX / modules
        if baseline is None:
            baseline = modules
        print(f"{ecc:>4}  {qr.version:>7}  {modules:>7}  {per_module:>9.2f}  {RECOVERY[ecc]}")

    worst = segno.make(PAYLOAD, error="h", micro=False, boost_error=False)
    worst_modules = worst.symbol_size(scale=1, border=QUIET_ZONE)[0]
    print()
    print(f"l -> h costs {worst_modules - baseline} more modules "
          f"({worst_modules / baseline:.2f}x) in the same printed square")

    # the uniform-cell guarantee render_codes provides
    short = "QRPK1|0123456789abcdef|9/9|AA"
    cells = render_codes([short, PAYLOAD])
    print(f"render_codes uniform cells: {[c.size for c in cells]}")


if __name__ == "__main__":
    main()
