"""Core: archiving and framing for the printable-QR backup pipeline.

Archiving (issue #1, @arsentis) turns a folder into one compressed blob;
framing (issue #2, @Rustlingrass) splits that blob into labelled QR payloads.
Agreed signatures (Hour 0):

    pack_bytes(src: Path) -> bytes
    unpack_bytes(blob: bytes, dest: Path) -> list[str]
    chunk(blob: bytes, chunk_size: int) -> list[bytes]
    sha256_digest(blob: bytes) -> str
    verify_digest(blob: bytes, expected: str) -> None
"""

from __future__ import annotations

import base64
import hashlib
import io
import lzma
import string
import tarfile
from dataclasses import dataclass
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


# --- framing (issue #2, @Rustlingrass) ---------------------------------------
# Frozen payload format (Hour 0, never change it):
#   QRPK1|<sha256-first-16>|<index>/<total>|<base64 chunk>

MAGIC = "QRPK1"
DIGEST_HEX = 16


def sha256_digest(blob: bytes) -> str:
    """Return the first 16 hex characters of the blob's sha256.

    Truncating to 64 bits is enough to detect accidental corruption during
    scanning; it is not a tamper-proof signature. Restore (issue #7) compares
    the digest in the header against the reassembled blob before unpacking.
    """
    return hashlib.sha256(blob).hexdigest()[:DIGEST_HEX]


@dataclass(frozen=True)
class Header:
    """One labelled payload: version, digest, part number and base64 data.

    The rendered form is the frozen Hour-0 line:

        QRPK1|<sha256-first-16>|<index>/<total>|<base64 chunk>

    `payload` may be empty: a zero-byte blob still yields one `1/1` payload,
    so backing up an empty file is representable.
    """

    digest: str
    index: int
    total: int
    payload: str

    def render(self) -> str:
        """Render the frozen `QRPK1|digest|index/total|base64` line."""
        return f"{MAGIC}|{self.digest}|{self.index}/{self.total}|{self.payload}"

    @classmethod
    def parse(cls, line: str) -> Header:
        """Parse a rendered line back into a Header, rejecting malformed input."""
        fields = line.split("|")
        if len(fields) != 4:
            raise ValueError(f"expected 4 fields, got {len(fields)}")
        magic, digest, counters, payload = fields
        if magic != MAGIC:
            raise ValueError(f"bad payload magic {magic!r}, expected {MAGIC!r}")
        if len(digest) != DIGEST_HEX or any(c not in string.hexdigits for c in digest):
            raise ValueError(f"digest must be {DIGEST_HEX} hex characters, got {digest!r}")
        parts = counters.split("/")
        if len(parts) != 2:
            raise ValueError(f"bad index/total {counters!r}, expected 'index/total'")
        try:
            index, total = int(parts[0]), int(parts[1])
        except ValueError as exc:
            raise ValueError(f"bad index/total {counters!r}, expected integers") from exc
        if not 1 <= index <= total:
            raise ValueError(f"index must satisfy 1 <= index <= total, got {counters!r}")
        return cls(digest.lower(), index, total, payload)


def chunk(blob: bytes, chunk_size: int) -> list[bytes]:
    """Split a blob into labelled, ASCII-encoded payloads.

    `chunk_size` counts raw blob bytes, not QR characters: base64 expands the
    data and the label adds a fixed prefix. Measured on this machine, 1000 raw
    bytes became 1336 base64 characters and a 1363-character payload line
    (16 of those characters are the truncated digest).

    Reproduce:
        python -c "from qrpack.core import chunk; b=b'x'*1000; p=chunk(b,1000)[0].decode(); print(len(b), len(p.split('|')[3]), len(p))"
    """
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")
    digest = sha256_digest(blob)
    parts = [blob[i:i + chunk_size] for i in range(0, len(blob), chunk_size)] or [b""]
    total = len(parts)
    return [
        Header(
            digest, index, total, base64.b64encode(part).decode("ascii")
        ).render().encode("ascii")
        for index, part in enumerate(parts, 1)
    ]


class DigestMismatchError(ValueError):
    """Reassembled bytes do not match the digest carried in the header.

    Subclasses ValueError so callers that already catch malformed framing
    also catch corruption. It is raised only for a well-formed digest whose
    bytes do not match; malformed digests raise plain ValueError.
    """


def verify_digest(blob: bytes, expected: str) -> None:
    """Refuse reassembled bytes whose sha256 differs from the header digest.

    `expected` is the 16-hex-character digest from a parsed `Header`; the hash
    is taken over the *reassembled compressed blob*, before decompression or
    unpacking. The restore path (CLI issue #10) must call this before
    `decompress` / `unpack_bytes`, so a mismatch can never be written out as
    a corrupt file. The function returns nothing: it either passes or raises.

    Measured on this machine, flipping one byte of a 2560-byte blob changed
    the digest from e392378f849d67bb to 1df94a4f60d45b4a and was refused.

    Reproduce:
        python -c "from qrpack.core import sha256_digest, verify_digest; b=bytes(range(256))*10; d=sha256_digest(b); c=bytearray(b); c[123]^=1; print(d, sha256_digest(bytes(c))); verify_digest(bytes(c), d)"
    """
    if (
        not isinstance(expected, str)
        or len(expected) != DIGEST_HEX
        or any(c not in string.hexdigits for c in expected)
    ):
        raise ValueError(f"digest must be {DIGEST_HEX} hex characters, got {expected!r}")
    actual = sha256_digest(blob)
    if actual != expected.lower():
        raise DigestMismatchError(
            f"digest mismatch: header says {expected!r}, reassembled bytes "
            f"hash to {actual!r}"
        )
