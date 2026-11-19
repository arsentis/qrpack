"""Tests for the framing layer of qrpack.core (issue #2).

Written before the implementation so the code has to satisfy the agreed
Hour-0 contract: QRPK1|<sha256-first-16>|<index>/<total>|<base64 chunk>.
"""

import base64
import hashlib

import pytest

from qrpack.core import Header, chunk, sha256_digest


BLOB = bytes(range(256)) * 10   # 2560 deterministic bytes
CHUNK = 1000                    # -> 3 payloads (1000, 1000, 560)


def test_header_round_trips_all_fields():
    h = Header(digest="0123456789abcdef", index=2, total=5, payload="SGVsbG8=")
    got = Header.parse(h.render())
    assert got == h
    assert (got.digest, got.index, got.total, got.payload) == (
        h.digest, h.index, h.total, h.payload,
    )


def test_rendered_line_uses_the_frozen_format():
    h = Header("0123456789abcdef", 1, 3, "SGVsbG8=")
    assert h.render() == "QRPK1|0123456789abcdef|1/3|SGVsbG8="


def test_digest_is_truncated_sha256():
    blob = b"hello"
    assert sha256_digest(blob) == hashlib.sha256(blob).hexdigest()[:16]
    assert len(sha256_digest(blob)) == 16


def test_chunk_returns_complete_labelled_payloads():
    payloads = chunk(BLOB, CHUNK)
    assert len(payloads) == 3
    assert all(isinstance(p, bytes) for p in payloads)   # frozen signature

    headers = [Header.parse(p.decode("ascii")) for p in payloads]
    assert [h.index for h in headers] == [1, 2, 3]
    assert [h.total for h in headers] == [3, 3, 3]
    assert {h.digest for h in headers} == {sha256_digest(BLOB)}
    assert b"".join(base64.b64decode(h.payload) for h in headers) == BLOB


def test_header_rejects_wrong_magic():
    with pytest.raises(ValueError, match="magic"):
        Header.parse("QRPK2|0123456789abcdef|1/1|SGVsbG8=")


def test_header_rejects_wrong_field_count():
    for line in (
        "QRPK1|0123456789abcdef|1/1",
        "QRPK1|0123456789abcdef|1/1|SGVsbG8=|extra",
    ):
        with pytest.raises(ValueError, match="fields"):
            Header.parse(line)


def test_header_rejects_bad_digest():
    for digest in ("abcdef", "zzzzzzzzzzzzzzzz"):
        with pytest.raises(ValueError, match="digest"):
            Header.parse(f"QRPK1|{digest}|1/1|SGVsbG8=")


def test_header_normalizes_uppercase_digest():
    h = Header.parse("QRPK1|0123456789ABCDEF|1/1|SGVsbG8=")
    assert h.digest == "0123456789abcdef"
    assert h.render() == "QRPK1|0123456789abcdef|1/1|SGVsbG8="


def test_header_rejects_bad_counters():
    for counters in ("0/3", "4/3", "2/1", "1/0", "x/3", "1/"):
        with pytest.raises(ValueError, match="index"):
            Header.parse(f"QRPK1|0123456789abcdef|{counters}|SGVsbG8=")


def test_chunk_rejects_non_positive_sizes():
    for size in (0, -1):
        with pytest.raises(ValueError, match="chunk_size"):
            chunk(BLOB, size)


def test_empty_blob_yields_one_empty_payload():
    payloads = chunk(b"", 100)
    assert len(payloads) == 1
    h = Header.parse(payloads[0].decode("ascii"))
    assert (h.index, h.total, h.payload) == (1, 1, "")
    assert base64.b64decode(h.payload) == b""


def test_chunk_larger_than_blob_preserves_bytes():
    payloads = chunk(b"abc", 100)
    h = Header.parse(payloads[0].decode("ascii"))
    assert len(payloads) == 1
    assert (h.index, h.total) == (1, 1)
    assert base64.b64decode(h.payload) == b"abc"


def test_digest_changes_when_one_byte_changes():
    assert sha256_digest(b"a") != sha256_digest(b"b")
