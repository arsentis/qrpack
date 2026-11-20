"""Tests for the archiving guarantees of qrpack.core (issue #6).

Three properties, written before the implementation:

1. junk directories never enter the archive
2. packing the same tree twice is byte-identical (so the sha256 in the header
   is a property of the *content*, not of when or where you packed it)
3. an archive entry containing `..` cannot write outside the destination
"""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from qrpack.core import pack_bytes, unpack_bytes


@pytest.fixture
def messy_tree(tmp_path: Path) -> Path:
    """A project tree with the junk a real checkout accumulates."""
    root = tmp_path / "proj"
    (root / "sub").mkdir(parents=True)
    (root / "a.py").write_text("print('hi')\n")
    (root / "sub" / "b.txt").write_text("data\n")

    for junk in ("__pycache__", ".git", "node_modules", ".venv"):
        d = root / junk
        d.mkdir()
        (d / "garbage.bin").write_bytes(b"\x00" * 256)

    return root


def _names(blob: bytes) -> list[str]:
    with tarfile.open(fileobj=io.BytesIO(blob)) as tf:
        return sorted(m.name for m in tf.getmembers())


def test_junk_directories_are_excluded(messy_tree: Path):
    """Build output and VCS metadata waste QR codes and leak local state."""
    names = _names(pack_bytes(messy_tree))
    assert names == ["a.py", "sub/b.txt"]
    for junk in ("__pycache__", ".git", "node_modules", ".venv"):
        assert not any(junk in n for n in names), f"{junk} leaked into the archive"


def test_packing_twice_is_byte_identical(messy_tree: Path):
    """Without this, the same folder gets a different sha256 on every machine,
    and the digest in the QR header would verify nothing useful."""
    assert pack_bytes(messy_tree) == pack_bytes(messy_tree)


def test_archive_metadata_carries_no_local_identity(messy_tree: Path):
    """mtime/uid/gid/uname must be zeroed: they differ per machine and per
    checkout, and they would also publish the packer's username on paper."""
    with tarfile.open(fileobj=io.BytesIO(pack_bytes(messy_tree))) as tf:
        for m in tf.getmembers():
            assert m.mtime == 0, f"{m.name} kept its mtime"
            assert m.uid == 0 and m.gid == 0, f"{m.name} kept uid/gid"
            assert m.uname == "" and m.gname == "", f"{m.name} kept a username"


def test_unpack_rejects_path_traversal(tmp_path: Path):
    """A malicious or corrupted archive must not write outside the destination."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        payload = b"escaped"
        info = tarfile.TarInfo("../escape.txt")
        info.size = len(payload)
        tf.addfile(info, io.BytesIO(payload))

    with pytest.raises(ValueError, match="unsafe path"):
        unpack_bytes(buf.getvalue(), tmp_path / "out")

    assert not (tmp_path / "escape.txt").exists()


def test_unpack_rejects_absolute_paths(tmp_path: Path):
    """The other half of the same attack: an absolute member name."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        info = tarfile.TarInfo("/tmp/qrpack-absolute-escape.txt")
        info.size = 0
        tf.addfile(info, io.BytesIO(b""))

    with pytest.raises(ValueError, match="unsafe path"):
        unpack_bytes(buf.getvalue(), tmp_path / "out")
