"""Tests for `qrpack restore` (issue #10, day 2)."""

import random

from PIL import Image

from qrpack import cli


def run(argv):
    """Call the CLI the way the console script does and return its exit code."""
    try:
        return cli.main(argv)
    except SystemExit as exc:
        return int(exc.code or 0)


def test_restore_round_trips_a_packed_folder(tmp_path):
    # The whole point of the project: folder -> sheet -> folder, byte for byte.
    # A small --chunk keeps every QR code small enough to decode reliably.
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    (src / "a.txt").write_text("hello\n" * 50)
    (src / "sub" / "b.bin").write_bytes(random.Random(1).randbytes(700))
    sheet = tmp_path / "sheet.png"
    out = tmp_path / "out"

    assert run(["pack", str(src), "-o", str(sheet), "--chunk", "300"]) == 0
    assert run(["restore", str(sheet), "-o", str(out)]) == 0
    assert (out / "a.txt").read_text() == (src / "a.txt").read_text()
    assert (out / "sub" / "b.bin").read_bytes() == (src / "sub" / "b.bin").read_bytes()


def test_restore_fails_on_a_missing_image(tmp_path, capsys):
    assert run(["restore", str(tmp_path / "nope.png"), "-o", str(tmp_path / "out")]) != 0
    assert "does not exist" in capsys.readouterr().err


def test_restore_fails_on_an_image_without_codes(tmp_path, capsys):
    blank = tmp_path / "blank.png"
    Image.new("RGB", (400, 400), "white").save(blank)
    assert run(["restore", str(blank), "-o", str(tmp_path / "out")]) != 0
    assert "no qrpack codes" in capsys.readouterr().err
