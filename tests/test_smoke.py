"""Smoke test: the package imports and reports a version.

Deliberately tiny. Its job is to make CI meaningful from the first commit, so
every later pull request has a green check to compare against.
"""

import qrpack


def test_package_imports():
    assert qrpack.__version__


def test_version_is_a_dotted_string():
    parts = qrpack.__version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)
