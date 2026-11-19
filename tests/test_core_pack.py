"""Tests for qrpack.core archiving: pack_bytes / unpack_bytes.

Written before the implementation (issue #1), so the first commit of this
branch is a red test that states what "done" means.
"""

from pathlib import Path

import pytest

from qrpack.core import compress, decompress, pack_bytes, unpack_bytes


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A small, realistic project tree: nested dirs and two file types."""
    root = tmp_path / "proj"
    (root / "sub").mkdir(parents=True)
    (root / "a.py").write_text("def hello():\n    return 'world'\n")
    (root / "sub" / "b.txt").write_text("lorem ipsum\n" * 20)
    return root


def test_round_trip_restores_identical_files(tree: Path, tmp_path: Path):
    """The core invariant: unpack(pack(x)) gives back exactly x."""
    blob = pack_bytes(tree)
    dest = tmp_path / "restored"
    names = unpack_bytes(blob, dest)

    assert names == ["a.py", "sub/b.txt"]
    assert (dest / "a.py").read_bytes() == (tree / "a.py").read_bytes()
    assert (dest / "sub" / "b.txt").read_bytes() == (tree / "sub" / "b.txt").read_bytes()


def test_entries_are_sorted_by_name(tree: Path):
    """Sorted entries make the archive reproducible across filesystems."""
    blob = pack_bytes(tree)
    assert blob.index(b"a.py") < blob.index(b"b.txt")


def test_packing_a_single_file_returns_its_bytes(tmp_path: Path):
    f = tmp_path / "one.txt"
    f.write_bytes(b"just me")
    assert pack_bytes(f) == b"just me"


def test_compression_round_trips(tree: Path):
    blob = pack_bytes(tree)
    assert decompress(compress(blob)) == blob


def test_compression_actually_shrinks_a_tar(tree: Path):
    """A tar is 512-byte padded, so this should be a large win, not a few bytes."""
    blob = pack_bytes(tree)
    assert len(compress(blob)) < len(blob) / 2


def test_full_pipeline_through_compression(tree: Path, tmp_path: Path):
    """pack -> compress -> decompress -> unpack must be lossless."""
    restored = decompress(compress(pack_bytes(tree)))
    dest = tmp_path / "out"
    names = unpack_bytes(restored, dest)
    assert names == ["a.py", "sub/b.txt"]
    assert (dest / "a.py").read_text() == (tree / "a.py").read_text()
