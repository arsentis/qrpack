"""Tests for `qrpack calibrate` and calibrate.recommend (issue #43)."""

from __future__ import annotations

import pytest

from qrpack import cli
from qrpack.calibrate import format_table, recommend


def row(size, survives, fits=True):
    return {
        "chunk_bytes": size,
        "payload_chars": size + 60,
        "fits": fits,
        "version": 10 if fits else None,
        "modules": 65 if fits else None,
        "px_per_module": 7.0 if fits else None,
        "survives": survives,
    }


def test_recommend_is_the_largest_size_that_passed():
    assert recommend([row(100, True), row(600, True), row(1200, False)]) == 600


def test_recommend_ignores_a_pass_above_a_failure():
    assert recommend([row(100, True), row(600, False), row(1200, True)]) == 100


def test_recommend_is_none_when_nothing_passed():
    assert recommend([row(100, False), row(600, False)]) is None


def test_recommend_does_not_depend_on_row_order():
    assert recommend([row(1200, False), row(100, True), row(600, True)]) == 600


def test_table_has_one_line_per_size_and_marks_no_fit():
    lines = format_table([row(100, True), row(2200, False, fits=False)]).splitlines()
    assert len(lines) == 3
    assert "PASS" in lines[1]
    assert "no fit" in lines[2]


def test_calibrate_prints_table_and_a_recommendation_that_passed(capsys):
    assert cli.main(["calibrate"]) == 0
    out = capsys.readouterr().out
    passed = {
        int(line.split()[0])
        for line in out.splitlines()
        if line.rstrip().endswith("PASS")
    }
    chunk = int(out.split("recommended --chunk :")[1].split()[0])
    assert chunk in passed


def test_calibrate_fails_when_nothing_decodes(capsys):
    assert cli.main(["calibrate", "--printed-px", "20"]) != 0
    assert "no payload size decoded" in capsys.readouterr().err


def test_a_smaller_printed_size_never_recommends_a_bigger_chunk(capsys):
    def chunk_for(px):
        assert cli.main(["calibrate", "--printed-px", str(px)]) == 0
        return int(capsys.readouterr().out.split("recommended --chunk :")[1].split()[0])

    assert chunk_for(800) >= chunk_for(472) >= chunk_for(300)


def test_ecc_flag_is_passed_through(capsys):
    assert cli.main(["calibrate", "--ecc", "l"]) == 0
    low = capsys.readouterr().out
    assert cli.main(["calibrate", "--ecc", "h"]) == 0
    high = capsys.readouterr().out
    assert low != high


@pytest.mark.parametrize("args", [["--ecc", "x"], ["--printed-px", "0"], ["--jpeg-quality", "0"]])
def test_bad_flags_exit_nonzero_with_a_message(args, capsys):
    assert cli.main(["calibrate", *args]) != 0
    assert "qrpack calibrate:" in capsys.readouterr().err
