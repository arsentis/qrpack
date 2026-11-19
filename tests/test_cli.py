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
