import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np
import pytest
from PIL import Image, ImageDraw

import vectorize


def make_logo(path, size=(80, 120), transparent=True):
    image = Image.new("RGBA", size, (0, 0, 0, 0) if transparent else "white")
    ImageDraw.Draw(image).rectangle((20, 20, size[0] - 21, size[1] - 21), fill="black")
    image.save(path)


@pytest.mark.parametrize("transparent", [True, False])
def test_load_mask(tmp_path, transparent):
    path = tmp_path / "logo.png"
    make_logo(path, transparent=transparent)
    mask = vectorize.load_mask(path)
    assert mask.dtype == bool
    assert mask[40, 40]
    assert not mask[0, 0]


def test_empty_mask():
    with pytest.raises(ValueError, match="no foreground"):
        vectorize.crop_to_bbox(np.zeros((10, 10), dtype=bool))


def test_crop():
    mask = np.zeros((20, 30), dtype=bool)
    mask[2:10, 5:15] = True
    assert vectorize.crop_to_bbox(mask).shape == (8, 10)


def test_pbm_non_byte_width(tmp_path):
    path = tmp_path / "mask.pbm"
    mask = np.array([[True, False, True, False, False, False, False, True, True]])
    vectorize.mask_to_pbm(mask, path)
    assert path.read_bytes() == b"P4\n9 1\n\xa1\x80"


def test_svg_padding_and_style(tmp_path):
    path = tmp_path / "raw.svg"
    path.write_text(
        f'<svg xmlns="{vectorize.SVG_NS}" viewBox="0 0 100 50">'
        '<g fill="#000000"><path d="M0 0h100v50z"/></g></svg>'
    )
    root = vectorize.pad_svg(path, 10)
    assert root.get("viewBox") == "0 0 120.000 70.000"
    styled = ET.fromstring(vectorize.style_svg(root, "#ffffff", "#000000"))
    assert styled[0].tag.endswith("rect")
    assert styled[0].get("fill") == "#000000"
    assert styled.find(f".//{{{vectorize.SVG_NS}}}g[@fill='#ffffff']") is not None
    assert root.find(f".//{{{vectorize.SVG_NS}}}g[@fill='#000000']") is not None


@pytest.mark.parametrize("option,value", [
    ("--padding", "-1"), ("--padding", "nan"),
    ("--alphamax", "2"), ("--alphamax", "inf"), ("--width", "0"),
])
def test_invalid_arguments(option, value):
    result = subprocess.run(
        [sys.executable, "-m", "vectorize", "missing.png", option, value],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert option in result.stderr


def test_duplicate_stems():
    result = subprocess.run(
        [sys.executable, "-m", "vectorize", "one/logo.png", "two/logo.png"],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "unique stems" in result.stderr


@pytest.mark.skipif(
    not all(shutil.which(tool) for tool in ("potrace", "rsvg-convert")),
    reason="requires Potrace and librsvg",
)
@pytest.mark.parametrize("size", [(80, 120), (120, 80)])
def test_end_to_end(tmp_path, size):
    source = tmp_path / "sample.png"
    make_logo(source, size=size)
    out = tmp_path / "exports"
    vectorize.process(source, out, 1.0, 10, width=240)
    folder = out / "sample"
    assert len(list(folder.iterdir())) == 19
    ET.parse(folder / "sample.svg")
    for suffix in ("black_transparent", "white_transparent", "black_on_white", "white_on_black"):
        assert (folder / f"sample_{suffix}.pdf").read_bytes().startswith(b"%PDF")
        ET.parse(folder / f"sample_{suffix}.svg")
        with Image.open(folder / f"sample_{suffix}.png") as image:
            assert max(image.size) == 240
            rgba = image.convert("RGBA")
            corner = rgba.getpixel((0, 0))
            center = rgba.getpixel((image.width // 2, image.height // 2))
            if suffix.endswith("transparent"):
                assert corner[3] == 0
            else:
                assert corner[3] == 255
            assert center == ((255, 255, 255, 255) if suffix.startswith("white") else (0, 0, 0, 255))
        with Image.open(folder / f"sample_{suffix}.webp") as image:
            assert max(image.size) == 240
        if "on" in suffix:
            with Image.open(folder / f"sample_{suffix}.jpg") as image:
                assert image.mode == "RGB"
