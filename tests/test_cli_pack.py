"""Tests for `qrpack pack` (issue #10, day 2)."""

import random

from qrpack import cli


def run(argv):
    """Call the CLI the way the console script does and return its exit code."""
    try:
        return cli.main(argv)
    except SystemExit as exc:
        return int(exc.code or 0)


def test_pack_writes_a_sheet_with_the_default_settings(tmp_path, capsys):
    # Random bytes do not compress, so this makes several full-size QR codes:
    # exactly the case where the default column count must still fit on A4.
    folder = tmp_path / "data"
    folder.mkdir()
    (folder / "noise.bin").write_bytes(random.Random(0).randbytes(5000))
    sheet = tmp_path / "sheet.png"

    assert run(["pack", str(folder), "-o", str(sheet)]) == 0
    assert sheet.is_file()
    assert "codes" in capsys.readouterr().out


def test_pack_fails_on_a_missing_source(tmp_path, capsys):
    sheet = tmp_path / "sheet.png"
    assert run(["pack", str(tmp_path / "no-such-folder"), "-o", str(sheet)]) != 0
    assert "does not exist" in capsys.readouterr().err
    assert not sheet.exists()


def test_pack_reports_a_layout_that_does_not_fit_instead_of_crashing(tmp_path, capsys):
    # Four full-size codes are wider than A4: the user must get a message,
    # not a Python traceback.
    folder = tmp_path / "data"
    folder.mkdir()
    (folder / "noise.bin").write_bytes(random.Random(0).randbytes(5000))
    sheet = tmp_path / "sheet.png"

    assert run(["pack", str(folder), "-o", str(sheet), "--cols", "4"]) != 0
    assert "A4" in capsys.readouterr().err


def test_pack_rejects_an_unsupported_output_format(tmp_path, capsys):
    (tmp_path / "a.txt").write_text("x")
    assert run(["pack", str(tmp_path / "a.txt"), "-o", str(tmp_path / "sheet.jpg")]) != 0
    assert ".png" in capsys.readouterr().err
