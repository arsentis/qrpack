"""Tests for qrpack.scan.reassemble (day 2).

Written before the implementation: reassemble must rebuild the blob from
payload lines, or name the parts that are missing instead of guessing.
"""

import pytest

from qrpack.core import chunk, sha256_digest
from qrpack.scan import reassemble


BLOB = bytes(range(256)) * 10   # 2560 bytes -> 3 payloads at chunk size 1000


def lines():
    return [p.decode("ascii") for p in chunk(BLOB, 1000)]


def test_reassemble_restores_the_blob():
    blob, digest, missing = reassemble(lines())
    assert blob == BLOB
    assert digest == sha256_digest(BLOB)
    assert missing == []


def test_reassemble_ignores_the_order_of_lines():
    blob, _, missing = reassemble(list(reversed(lines())))
    assert blob == BLOB
    assert missing == []


def test_reassemble_names_the_missing_part():
    got = lines()
    del got[1]                      # drop part 2 of 3
    blob, _, missing = reassemble(got)
    assert missing == [2]
    assert blob == b""              # never return a corrupt archive


def test_reassemble_rejects_lines_from_different_archives():
    other = [p.decode("ascii") for p in chunk(b"another archive", 1000)]
    with pytest.raises(ValueError, match="different"):
        reassemble(lines()[:1] + other)


def test_reassemble_rejects_empty_input():
    with pytest.raises(ValueError, match="no payloads"):
        reassemble([])
