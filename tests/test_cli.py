"""CLI skeleton: the entry point exists and advertises every subcommand.

Issue: "infra: CLI skeleton, CI, README problem and aim" (@dreamboy17).
The subcommands are stubs on day 1; these tests pin the *interface* so the
day-2 wiring cannot silently drop or rename a command.
"""

from __future__ import annotations

import pytest

from qrpack import cli

SUBCOMMANDS = ("estimate", "pack", "restore")


def run(argv: list[str]) -> int:
    """Call the CLI the way the console script does and return its exit code."""
    try:
        return cli.main(argv)
    except SystemExit as exc:  # argparse exits for --help, --version, bad args
        return int(exc.code or 0)


def test_help_lists_every_subcommand(capsys):
    assert run(["--help"]) == 0
    out = capsys.readouterr().out
    for name in SUBCOMMANDS:
        assert name in out


@pytest.mark.parametrize("name", SUBCOMMANDS)
def test_each_subcommand_has_its_own_help(name, capsys):
    assert run([name, "--help"]) == 0
    assert "usage:" in capsys.readouterr().out


def test_no_command_prints_usage_and_fails(capsys):
    assert run([]) == 2
    assert "usage:" in capsys.readouterr().err


def test_version_matches_package(capsys):
    import qrpack

    assert run(["--version"]) == 0
    assert qrpack.__version__ in capsys.readouterr().out


def test_pack_requires_an_output(capsys):
    assert run(["pack", "somefolder"]) != 0
    assert "-o" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv",
    [["estimate", "x"], ["pack", "x", "-o", "sheet.png"], ["restore", "s.png", "-o", "out"]],
)
def test_unwired_subcommand_fails_loudly(argv, capsys):
    # A stub must never exit 0: a script that trusts the exit code would
    # otherwise believe a backup was written when nothing was.
    assert run(argv) != 0
    assert "not implemented" in capsys.readouterr().err


def test_console_script_is_registered():
    tomllib = pytest.importorskip("tomllib")  # stdlib from Python 3.11
    from pathlib import Path

    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    scripts = tomllib.loads(pyproject.read_text())["project"]["scripts"]
    assert scripts["qrpack"] == "qrpack.cli:main"
