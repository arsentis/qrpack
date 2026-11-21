"""Command-line entry point: ``qrpack estimate | pack | restore | calibrate``.

Owned by @dreamboy17. Each module owner adds or wires their own subcommand;
keep edits to your subcommand's ``_add_*`` function and its ``_cmd_*`` handler.

Day 1: the interface exists and every subcommand parses its arguments.
Day 2: the handlers are wired to core / sheet / scan.
"""

from __future__ import annotations

import argparse
import io
import sys
import tarfile
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .core import chunk, compress, decompress, pack_bytes, unpack_bytes, verify_digest
from .calibrate import LADDER, PRINTED_PX, format_table, recommend, sweep
from .scan import reassemble, scan_image
from .sheet import make_sheet

# Bytes of compressed data per QR code. In the prototype measurements quoted in
# the project proposal, 1,200 B chunks decoded 5 of 5 cells where version-40
# symbols decoded 0 of 2. A starting point only: `qrpack calibrate` is meant
# to measure the right value for each printer and camera.
DEFAULT_CHUNK = 1200
# A full 1,200-byte chunk makes a QR symbol too wide for four columns on A4
# (make_sheet refuses rather than shrink it); three fit, 12 codes per page.
DEFAULT_COLS = 3


def _fail(name: str, message: str) -> int:
    print(f"qrpack {name}: {message}", file=sys.stderr)
    return 1


def _cmd_estimate(args: argparse.Namespace) -> int:
    if not args.src.exists():
        return _fail("estimate", f"{args.src} does not exist")
    if args.chunk <= 0:
        return _fail("estimate", f"--chunk must be positive, got {args.chunk}")
    raw = pack_bytes(args.src)
    compressed = compress(raw)
    payloads = chunk(compressed, args.chunk)
    encoded = sum(len(p) for p in payloads)
    print(
        f"{len(raw)} B raw -> {len(compressed)} B compressed -> "
        f"{encoded} chars encoded -> {len(payloads)} codes"
    )
    return 0


def _cmd_pack(args: argparse.Namespace) -> int:
    if not args.src.exists():
        return _fail("pack", f"{args.src} does not exist")
    if args.chunk <= 0:
        return _fail("pack", f"--chunk must be positive, got {args.chunk}")
    raw = pack_bytes(args.src)
    compressed = compress(raw)
    # chunk() returns bytes; make_sheet() takes the payloads as text.
    payloads = [p.decode("ascii") for p in chunk(compressed, args.chunk)]
    title = f"qrpack backup of {args.src.resolve().name}"
    try:
        pages, codes = make_sheet(payloads, title, args.output, cols=args.cols)
    except (TypeError, ValueError) as exc:
        # make_sheet explains what is wrong (too many columns, bad extension);
        # show that message instead of a traceback.
        return _fail("pack", str(exc))
    print(f"{codes} codes on {pages} page(s) -> {args.output}")
    return 0


def _cmd_restore(args: argparse.Namespace) -> int:
    for image in args.images:
        if not image.exists():
            return _fail("restore", f"{image} does not exist")
    texts = []
    for image in args.images:
        texts.extend(scan_image(image, args.cols))
    if not texts:
        return _fail("restore", "no qrpack codes found in the image(s)")
    try:
        blob, digest, missing = reassemble(texts)
    except ValueError as exc:
        return _fail("restore", str(exc))
    if missing:
        # Name the lost parts instead of writing a corrupt archive.
        return _fail("restore", f"missing parts {missing}; rescan them and pass every sheet")
    try:
        verify_digest(blob, digest)
    except ValueError as exc:
        return _fail("restore", str(exc))
    raw = decompress(blob)
    args.output.mkdir(parents=True, exist_ok=True)
    if not tarfile.is_tarfile(io.BytesIO(raw)):
        # pack_bytes stores a single file as its raw bytes, without a name.
        target = args.output / "restored.bin"
        target.write_bytes(raw)
        print(f"restored 1 file ({len(raw)} B) -> {target}")
        return 0
    try:
        names = unpack_bytes(raw, args.output)
    except ValueError as exc:
        return _fail("restore", str(exc))
    print(f"restored {len(names)} file(s) -> {args.output}")
    return 0


def _cmd_calibrate(args: argparse.Namespace) -> int:
    try:
        rows = sweep(
            LADDER,
            printed_px=args.printed_px,
            blur=args.blur,
            jpeg_quality=args.jpeg_quality,
            ecc=args.ecc,
        )
    except (TypeError, ValueError) as exc:
        return _fail("calibrate", str(exc))
    print(format_table(rows))
    best = recommend(rows)
    if best is None:
        return _fail("calibrate", "no payload size decoded; raise --printed-px or lower --blur")
    print()
    print(f"recommended --chunk : {best} B")
    return 0


def _add_chunk_option(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--chunk",
        type=int,
        default=DEFAULT_CHUNK,
        metavar="BYTES",
        help=f"compressed bytes per QR code (default {DEFAULT_CHUNK})",
    )


def _add_estimate(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "estimate",
        help="report how many codes and sheets SRC would take",
        description="Report raw -> compressed -> encoded size and the number of codes.",
    )
    p.add_argument("src", type=Path, metavar="SRC", help="file or folder to measure")
    _add_chunk_option(p)
    p.set_defaults(func=_cmd_estimate)


def _add_pack(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "pack",
        help="turn a file or folder into a printable sheet of QR codes",
        description="Turn a file or folder into a printable sheet of QR codes.",
    )
    p.add_argument("src", type=Path, metavar="SRC", help="file or folder to pack")
    p.add_argument(
        "-o", "--output", type=Path, required=True, metavar="OUT",
        help="output image, e.g. sheet.png",
    )
    _add_chunk_option(p)
    p.add_argument(
        "--cols", type=int, default=DEFAULT_COLS,
        help=f"codes per row on the sheet (default {DEFAULT_COLS})",
    )
    p.set_defaults(func=_cmd_pack)


def _add_restore(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "restore",
        help="rebuild the original files from photos of a sheet",
        description="Rebuild the original files from one or more sheet images.",
    )
    p.add_argument(
        "images", type=Path, nargs="+", metavar="IMG",
        help="sheet image(s); several sheets may be given in any order",
    )
    p.add_argument(
        "-o", "--output", type=Path, required=True, metavar="DIR",
        help="directory to restore into",
    )
    p.add_argument(
        "--cols", type=int, default=DEFAULT_COLS,
        help=f"codes per row the sheet was packed with (default {DEFAULT_COLS})",
    )
    p.set_defaults(func=_cmd_restore)


def _add_calibrate(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "calibrate",
        help="measure which chunk size survives print and photo, and recommend one",
        description="Render a ladder of payload sizes at one printed size, degrade "
        "them, and report which still decode.",
    )
    p.add_argument(
        "--ecc", default="m", metavar="LEVEL",
        help="error-correction level: l, m, q or h (default m)",
    )
    p.add_argument(
        "--printed-px", type=int, default=PRINTED_PX, metavar="PX",
        help=f"printed square size in pixels (default {PRINTED_PX}: 40 mm at 300 DPI)",
    )
    p.add_argument(
        "--blur", type=int, default=0, metavar="RADIUS",
        help="Gaussian blur radius in pixels to simulate a soft photo (default 0)",
    )
    p.add_argument(
        "--jpeg-quality", type=int, default=100, metavar="Q",
        help="JPEG quality 1-100 to simulate compression (default 100: none)",
    )
    p.set_defaults(func=_cmd_calibrate)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrpack",
        description="Pack a folder into printable QR codes and restore it from a photo.",
    )
    parser.add_argument("--version", action="version", version=f"qrpack {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    _add_estimate(sub)
    _add_pack(sub)
    _add_restore(sub)
    _add_calibrate(sub)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help(sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
