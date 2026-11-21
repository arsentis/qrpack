"""Keep the README's transcripts honest (issue #17).

A pasted transcript rots the moment the CLI changes, and a README that claims
output the program no longer produces is worse than no README. These tests
re-run the documented commands and compare against what the README says.

They assert the *shape and wording* of the output, not byte counts: the counts
depend on the demo folder in tests/capture_usage.sh, and pinning them here
would mean two places to update. `bash tests/capture_usage.sh` regenerates the
numbers themselves.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from PIL import Image

from qrpack import cli

README = Path(__file__).resolve().parent.parent / "README.md"


def run(argv):
    try:
        return cli.main(argv)
    except SystemExit as exc:
        return int(exc.code or 0)


@pytest.fixture(scope="module")
def readme() -> str:
    return README.read_text()


def test_readme_documents_every_subcommand(readme: str):
    for name in ("estimate", "pack", "restore"):
        assert f"qrpack {name}" in readme, f"{name} is undocumented"


def test_readme_no_longer_claims_the_commands_are_stubs(readme: str):
    """They were wired up in #40; this guards against the old text returning."""
    assert "not implemented yet" not in readme


def test_estimate_output_matches_the_documented_shape(tmp_path, capsys):
    folder = tmp_path / "notes"
    folder.mkdir()
    (folder / "a.md").write_text("# Todo\n\n- back up the keys\n" * 12)

    assert run(["estimate", str(folder)]) == 0
    out = capsys.readouterr().out.strip()

    # README line: "10240 B raw -> 692 B compressed -> 951 chars encoded -> 1 codes"
    assert re.fullmatch(
        r"\d+ B raw -> \d+ B compressed -> \d+ chars encoded -> \d+ codes", out
    ), f"estimate output no longer matches the README: {out!r}"


def test_pack_output_matches_the_documented_shape(tmp_path, capsys):
    folder = tmp_path / "notes"
    folder.mkdir()
    (folder / "a.md").write_text("hello\n" * 40)
    sheet = tmp_path / "sheet.png"

    assert run(["pack", str(folder), "-o", str(sheet), "--chunk", "300"]) == 0
    out = capsys.readouterr().out.strip()

    # README line: "3 codes on 1 page(s) -> sheet.png"
    assert re.fullmatch(r"\d+ codes on \d+ page\(s\) -> .+", out), out


def test_restore_output_matches_the_documented_shape(tmp_path, capsys):
    folder = tmp_path / "notes"
    (folder / "sub").mkdir(parents=True)
    (folder / "a.md").write_text("hello\n" * 40)
    (folder / "sub" / "b.txt").write_text("world\n" * 20)
    sheet = tmp_path / "sheet.png"
    out_dir = tmp_path / "restored"

    assert run(["pack", str(folder), "-o", str(sheet), "--chunk", "300"]) == 0
    capsys.readouterr()
    assert run(["restore", str(sheet), "-o", str(out_dir)]) == 0
    out = capsys.readouterr().out.strip()

    # README line: "restored 3 file(s) -> restored"
    assert re.fullmatch(r"restored \d+ file\(s\) -> .+", out), out
    # and the claim the whole README rests on
    assert (out_dir / "a.md").read_bytes() == (folder / "a.md").read_bytes()
    assert (out_dir / "sub" / "b.txt").read_bytes() == (folder / "sub" / "b.txt").read_bytes()


def test_documented_failure_messages_are_still_produced(tmp_path, capsys):
    assert run(["pack", str(tmp_path / "does-not-exist"), "-o", str(tmp_path / "x.png")]) != 0
    assert "does not exist" in capsys.readouterr().err

    blank = tmp_path / "blank.png"
    Image.new("RGB", (400, 400), "white").save(blank)
    assert run(["restore", str(blank), "-o", str(tmp_path / "out")]) != 0
    assert "no qrpack codes found" in capsys.readouterr().err


def test_readme_quotes_the_failure_messages_verbatim(readme: str):
    for message in ("does not exist", "no qrpack codes found in the image(s)"):
        assert message in readme, f"README does not show the real message {message!r}"


def test_readme_points_at_the_capture_script(readme: str):
    """A reader must be able to reproduce the transcripts, not just trust them."""
    assert "tests/capture_usage.sh" in readme
    assert (README.parent / "tests" / "capture_usage.sh").is_file()
