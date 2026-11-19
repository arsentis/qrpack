"""Tests for the framing layer of qrpack.core (issue #2).

Written before the implementation so the code has to satisfy the agreed
Hour-0 contract: QRPK1|<sha256-first-16>|<index>/<total>|<base64 chunk>.
"""

import base64
import hashlib

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
