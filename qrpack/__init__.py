"""qrpack — pack a folder into printable QR codes and restore it from a photo.

Modules:
    core.py       archiving, framing, checksums
    sheet.py      layout and printable output
    scan.py       decoding and recovery
    calibrate.py  measuring the resolution limit of a print-and-scan chain
"""

__version__ = "0.1.0"

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
