"""Command-line entry point: ``qrpack estimate | pack | restore``.

Owned by @dreamboy17. Each module owner adds or wires their own subcommand;
keep edits to your subcommand's ``_add_*`` function and its ``_cmd_*`` handler.

Day 1: the interface exists and every subcommand parses its arguments.
Day 2: the handlers are wired to core / sheet / scan.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .core import chunk, compress, pack_bytes
from .sheet import make_sheet

# Bytes of compressed data per QR code. In the prototype measurements quoted in
# the project proposal, 1,200 B chunks decoded 5 of 5 cells where version-40
# symbols decoded 0 of 2. A starting point only: `qrpack calibrate` is meant
# to measure the right value for each printer and camera.
DEFAULT_CHUNK = 1200
# A full 1,200-byte chunk makes a QR symbol too wide for four columns on A4
# (make_sheet refuses rather than shrink it); three fit, 12 codes per page.
DEFAULT_COLS = 3


def _not_ready(name: str) -> int:
    print(f"qrpack {name}: not implemented yet (lands on day 2)", file=sys.stderr)
    return 1


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
    raw = pack_bytes(args.src)
    compressed = compress(raw)
    # chunk() returns bytes; make_sheet() takes the payloads as text.
    payloads = [p.decode("ascii") for p in chunk(compressed, args.chunk)]
    title = f"qrpack backup of {args.src.resolve().name}"
    pages, codes = make_sheet(payloads, title, args.output, cols=args.cols)
    print(f"{codes} codes on {pages} page(s) -> {args.output}")
    return 0


def _cmd_restore(args: argparse.Namespace) -> int:
    return _not_ready("restore")


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
