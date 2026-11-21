"""Release checks for v0.1.0 (issue #15)."""

from pathlib import Path

import pytest

import qrpack

ROOT = Path(__file__).resolve().parent.parent


def test_readme_shows_the_ci_badge():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "actions/workflows/ci.yml/badge.svg" in readme


def test_package_and_pyproject_agree_on_the_version():
    # Two places hold the version; a release that bumps only one of them
    # would report the wrong number from `qrpack --version`.
    tomllib = pytest.importorskip("tomllib")  # stdlib from Python 3.11
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["version"] == qrpack.__version__
