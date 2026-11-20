#!/usr/bin/env python3
"""Measure what the junk-skip and determinism rules actually buy (issue #6).

Run from the repo root:  python3 tests/measure_archive_rules.py
Numbers quoted in core.py's docstrings come from here, so a reviewer can check
them instead of trusting a comment.
"""
from __future__ import annotations

import io
import shutil
import tarfile
import tempfile
from pathlib import Path

from qrpack.core import SKIP_DIRS, compress, pack_bytes

CHUNK = 1200  # bytes of payload per QR code


def _pack_without_skipping(source: Path) -> bytes:
    """What pack_bytes would produce if SKIP_DIRS were empty."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            info = tf.gettarinfo(path, arcname=str(path.relative_to(source)))
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            with path.open("rb") as fh:
                tf.addfile(info, fh)
    return buf.getvalue()


def main() -> None:
    repo = Path(__file__).resolve().parent.parent
    work = Path(tempfile.mkdtemp()) / "sample"
    shutil.copytree(repo, work, ignore=shutil.ignore_patterns(".git"))

    # simulate the junk a real checkout carries
    for junk in ("__pycache__", "node_modules", ".venv"):
        d = work / junk
        d.mkdir(exist_ok=True)
        (d / "garbage.bin").write_bytes(b"\x00" * 200_000)

    dirty = compress(_pack_without_skipping(work))
    clean = compress(pack_bytes(work))

    codes = lambda n: -(-(n * 4 // 3) // CHUNK)  # base64 inflates by 4/3

    print(f"skipped directories : {sorted(SKIP_DIRS)}")
    print()
    print(f"with junk    : {len(dirty):>8,} B compressed -> {codes(len(dirty)):>4} QR codes")
    print(f"without junk : {len(clean):>8,} B compressed -> {codes(len(clean)):>4} QR codes")
    print(f"saved        : {len(dirty) - len(clean):>8,} B, "
          f"{codes(len(dirty)) - codes(len(clean))} fewer codes")
    print()
    print(f"deterministic: {pack_bytes(work) == pack_bytes(work)}")


if __name__ == "__main__":
    main()
