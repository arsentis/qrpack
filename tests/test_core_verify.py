"""Tests for restore-time digest verification (issue #7).

The restore path is not wired yet (CLI stubs, no ``reassemble``), so these
tests simulate it with the framing primitives from core: chunk -> parse ->
base64 decode -> join -> verify. The real restore path must call
``verify_digest`` before decompressing and unpacking.
"""

import base64

import pytest

from qrpack.core import DigestMismatchError, Header, chunk, sha256_digest, verify_digest


BLOB = bytes(range(256)) * 10
CHUNK = 1000


def reassemble_like_scan(payloads: list[bytes]) -> tuple[bytes, str]:
    """Local stand-in for scan.reassemble until that module lands."""
    headers = [Header.parse(p.decode("ascii")) for p in payloads]
    blob = b"".join(base64.b64decode(h.payload) for h in headers)
    return blob, headers[0].digest


def test_verify_digest_accepts_a_matching_blob():
    assert verify_digest(BLOB, sha256_digest(BLOB)) is None


def test_verify_digest_refuses_a_single_flipped_byte():
    digest = sha256_digest(BLOB)
    corrupt = bytearray(BLOB)
    corrupt[123] ^= 0x01
    with pytest.raises(DigestMismatchError, match="digest"):
        verify_digest(bytes(corrupt), digest)


def test_restore_path_refuses_a_corrupted_chunk():
    payloads = chunk(BLOB, CHUNK)
    headers = [Header.parse(p.decode("ascii")) for p in payloads]
    parts = [bytearray(base64.b64decode(h.payload)) for h in headers]
    parts[1][0] ^= 0x01                      # flip one byte of the middle chunk
    corrupt_blob = b"".join(bytes(p) for p in parts)
    with pytest.raises(DigestMismatchError, match="digest"):
        verify_digest(corrupt_blob, headers[0].digest)


def test_restore_path_accepts_an_intact_set_of_chunks():
    payloads = chunk(BLOB, CHUNK)
    blob, digest = reassemble_like_scan(payloads)
    assert verify_digest(blob, digest) is None
    assert blob == BLOB


@pytest.mark.parametrize("expected", ["", "abcdef", "z" * 16, "a" * 17])
def test_verify_digest_rejects_malformed_expected(expected):
    with pytest.raises(ValueError, match="digest") as caught:
        verify_digest(BLOB, expected)
    assert not isinstance(caught.value, DigestMismatchError)


def test_verify_digest_accepts_uppercase_expected():
    assert verify_digest(BLOB, sha256_digest(BLOB).upper()) is None


def test_verify_digest_accepts_empty_blob():
    assert verify_digest(b"", sha256_digest(b"")) is None


def test_mismatch_message_shows_both_digests():
    expected = sha256_digest(BLOB)
    corrupt = b"x" + BLOB[1:]
    with pytest.raises(DigestMismatchError) as caught:
        verify_digest(corrupt, expected)
    assert expected in str(caught.value)
    assert sha256_digest(corrupt) in str(caught.value)


def test_digest_mismatch_error_is_a_value_error():
    assert issubclass(DigestMismatchError, ValueError)


@pytest.mark.parametrize("bad_index", [0, 1, 2])
def test_corruption_in_any_chunk_is_caught(bad_index):
    headers = [Header.parse(p.decode("ascii")) for p in chunk(BLOB, CHUNK)]
    parts = [bytearray(base64.b64decode(h.payload)) for h in headers]
    parts[bad_index][0] ^= 0x01
    corrupt_blob = b"".join(bytes(p) for p in parts)
    with pytest.raises(DigestMismatchError, match="digest"):
        verify_digest(corrupt_blob, headers[0].digest)
