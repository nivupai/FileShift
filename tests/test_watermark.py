"""Tests for the Watermark tool."""
from pathlib import Path

import pytest
from PIL import Image

from fileshift import convert, imaging


@pytest.fixture
def img(tmp_path) -> Path:
    im = Image.new("RGB", (400, 300), (30, 60, 90))
    p = tmp_path / "photo.jpg"
    im.save(p, quality=90)
    return p


def _pixel_changed(a: Image.Image, b: Image.Image, box) -> bool:
    ca, cb = a.crop(box), b.crop(box)
    return list(ca.getdata()) != list(cb.getdata())


def test_watermark_bottom_right_default(img):
    base = convert.open_image(img)
    wm = imaging.apply_watermark(base, imaging.Watermark(text="Test", opacity=100))
    assert wm.size == base.size
    # bottom-right quadrant changed, top-left did not
    assert _pixel_changed(base.convert("RGBA"), wm, (300, 220, 400, 300))
    assert not _pixel_changed(base.convert("RGBA"), wm, (0, 0, 60, 40))


@pytest.mark.parametrize("position", imaging.POSITIONS)
def test_watermark_every_position(img, position):
    base = convert.open_image(img)
    out = imaging.apply_watermark(base, imaging.Watermark(text="©", position=position, opacity=100))
    assert out.size == base.size


def test_watermark_tile_covers_more_area(img):
    base = convert.open_image(img)
    single = imaging.apply_watermark(base, imaging.Watermark(text="X", opacity=100, tile=False))
    tiled = imaging.apply_watermark(base, imaging.Watermark(text="X", opacity=100, tile=True))

    def changed_pixels(out):
        return sum(1 for a, b in zip(base.convert("RGBA").getdata(), out.getdata()) if a != b)

    assert changed_pixels(tiled) > changed_pixels(single)


def test_watermark_opacity_scales_effect(img):
    base = convert.open_image(img).convert("RGBA")
    faint = imaging.apply_watermark(base, imaging.Watermark(text="X", opacity=10, color="#ffffff"))
    strong = imaging.apply_watermark(base, imaging.Watermark(text="X", opacity=90, color="#ffffff"))
    box = (300, 220, 400, 300)

    def diff(out):
        return sum(abs(p1[0] - p2[0]) for p1, p2 in zip(base.crop(box).getdata(), out.crop(box).getdata()))

    assert diff(strong) > diff(faint)


def test_watermark_through_save_like(img):
    im = convert.open_image(img)
    out_im = imaging.apply_watermark(im, imaging.Watermark(text="© FileShift"))
    out = imaging.save_like(out_im, img, "Watermarked")
    assert out.exists() and out.suffix == ".jpg"
    Image.open(out).load()
