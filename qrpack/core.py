"""Core archiving: a directory becomes one compressed blob, and back again.

Issue #1. This module owns only the *archiving* half of core; the framing half
(`Header`, `chunk`, `estimate`, sha256) belongs to issue #2 and is added by
@Rustlingrass. Agreed signatures (Hour 0):

    pack_bytes(src: Path) -> bytes
    unpack_bytes(blob: bytes, dest: Path) -> list[str]
"""

from __future__ import annotations

import io
import lzma
import tarfile
from pathlib import Path

# A tar is block-padded to 512-byte records and stores names in plain text, so
# it compresses extremely well. Measured on this repo's own three Markdown
# files: 30,720 B of tar became 7,640 B of xz, a 4.0x reduction. Since every
# ~1,200 bytes is one more QR code to print, compression is not an
# optimisation here, it is the point.
#
# Reproduce:
#   python3 -c "from qrpack.core import pack_bytes, compress; \
#     from pathlib import Path; b=pack_bytes(Path('sample')); \
#     print(len(b), len(compress(b)))"
PRESET = 9 | lzma.PRESET_EXTREME


def compress(blob: bytes) -> bytes:
    """Compress a packed blob. Inverse of `decompress`."""
    return lzma.compress(blob, preset=PRESET)


def decompress(blob: bytes) -> bytes:
    """Inverse of `compress`."""
    return lzma.decompress(blob)


def pack_bytes(source: Path) -> bytes:
    """A file -> its bytes. A directory -> a tar of its files.

    Entries are sorted by name so the same tree always produces the same
    archive layout; an unsorted walk depends on filesystem order and would make
    the output unreproducible between machines.
    """
    source = Path(source)
    if source.is_file():
        return source.read_bytes()

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            info = tf.gettarinfo(path, arcname=str(path.relative_to(source)))
            with path.open("rb") as fh:
                tf.addfile(info, fh)
    return buf.getvalue()


def unpack_bytes(blob: bytes, dest: Path) -> list[str]:
    """Inverse of `pack_bytes` for the directory case.

    Returns the sorted names of the files written.
    """
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(blob)) as tf:
        names = [m.name for m in tf.getmembers() if m.isfile()]
        tf.extractall(dest)
    return sorted(names)
