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
