"""Tests for `render_codes` — the in-memory renderer issue #3 names.

Also covers the uniform-cell property, which is the criterion still open on
issue #8: the scanner finds cells by grid arithmetic, so if a short last chunk
rendered as a smaller symbol every following cell would shift and cropping
would fail silently.
"""

from __future__ import annotations

import pytest
from PIL import Image

from qrpack.sheet import DEFAULT_ECC, render_codes

SHORT = "QRPK1|0123456789abcdef|2/2|AA"
LONG = "QRPK1|0123456789abcdef|1/2|" + "B" * 900


def test_returns_one_image_per_payload():
    images = render_codes([SHORT, LONG, SHORT])
    assert len(images) == 3
    assert all(isinstance(i, Image.Image) for i in images)


def test_every_cell_is_the_same_size_across_qr_versions():
    """The #8 criterion: mixed QR versions must still produce a uniform grid."""
    images = render_codes([SHORT, LONG])
    sizes = {image.size for image in images}
    assert len(sizes) == 1, f"cells differ in size: {sizes}"


def test_cells_are_square():
    for image in render_codes([SHORT, LONG]):
        assert image.size[0] == image.size[1]


def test_cell_is_as_large_as_the_biggest_symbol():
    """Padding must grow the small cells, never shrink the large symbol:
    scaling a QR down would destroy module edges and stop it scanning."""
    small = render_codes([SHORT])[0].size[0]
    large = render_codes([LONG])[0].size[0]
    mixed = render_codes([SHORT, LONG])[0].size[0]
    assert mixed == large
    assert mixed > small


def test_a_padded_cell_keeps_a_white_border():
    """The quiet zone has to survive padding, or the symbol will not decode."""
    cell = render_codes([SHORT, LONG])[0]
    assert cell.getpixel((0, 0)) == (255, 255, 255)
    assert cell.getpixel((cell.width - 1, cell.height - 1)) == (255, 255, 255)


def test_higher_ecc_makes_bigger_cells():
    low = render_codes([LONG], ecc="l")[0].size[0]
    high = render_codes([LONG], ecc="h")[0].size[0]
    assert high > low


def test_scale_changes_the_cell_size():
    assert render_codes([SHORT], scale=4)[0].size[0] < render_codes([SHORT], scale=8)[0].size[0]


@pytest.mark.parametrize("bad", [[], (), "not a list", None])
def test_rejects_bad_payload_collections(bad):
    with pytest.raises((TypeError, ValueError)):
        render_codes(bad)


@pytest.mark.parametrize("bad", ["x", "", None, 3])
def test_rejects_an_unknown_ecc(bad):
    with pytest.raises((TypeError, ValueError)):
        render_codes([SHORT], ecc=bad)


def test_default_ecc_matches_the_module_default():
    a = render_codes([LONG])[0].size
    b = render_codes([LONG], ecc=DEFAULT_ECC)[0].size
    assert a == b
