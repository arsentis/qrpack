"""Core archiving: a directory becomes one compressed blob, and back again.

Issue #1. This module owns only the *archiving* half of core; the framing half
(`Header`, `chunk`, `estimate`, sha256) belongs to issue #2 and is added by
@Rustlingrass. Agreed signatures (Hour 0):

    pack_bytes(src: Path) -> bytes
    unpack_bytes(blob: bytes, dest: Path) -> list[str]
"""

from __future__ import annotations

import io
import tarfile
from pathlib import Path


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
