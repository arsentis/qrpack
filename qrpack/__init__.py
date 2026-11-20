"""qrpack — pack a folder into printable QR codes and restore it from a photo.

Modules land during the sprint (see PLAN.md):
    core.py       archiving, framing, checksums
    sheet.py      layout and printable output
    scan.py       decoding and recovery
    calibrate.py  measuring the real limit of a scanner
"""

__version__ = "0.0.1"

from .core import (
    DigestMismatchError,
    Header,
    chunk,
    compress,
    decompress,
    pack_bytes,
    sha256_digest,
    unpack_bytes,
    verify_digest,
)

__all__ = [
    "__version__",
    "pack_bytes",
    "unpack_bytes",
    "compress",
    "decompress",
    "Header",
    "chunk",
    "sha256_digest",
    "DigestMismatchError",
    "verify_digest",
]
