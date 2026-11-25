#!/usr/bin/env python3
"""
vectorize.py — turn a raster logo PNG into a clean print-ready vector (SVG)
plus a standard set of colored raster/vector variations, all centered on a
canvas with a configurable margin.

Usage:
    python3 vectorize.py logo1.png logo2.png [--out out] [--alphamax 1.0] [--padding 10]

For each input image, writes to <out>/<name>/:
    <name>.svg                          clean vector, black fill, transparent bg (print-ready master)
    <name>_black_on_white.svg/.png/.jpg/.webp/.pdf
    <name>_white_on_black.svg/.png/.jpg/.webp/.pdf
    <name>_black_transparent.svg/.png/.webp/.pdf
    <name>_white_transparent.svg/.png/.webp/.pdf

--padding is a percentage of the logo's longest side, applied as equal
empty margin on all four sides of every exported variant (svg included).
"""
import argparse
import math
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError
from scipy import ndimage

__version__ = "0.1.0"

RASTER_WIDTH = 2400  # px, long-edge target for exported raster variations
SVG_NS = "http://www.w3.org/2000/svg"

ET.register_namespace("", SVG_NS)


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        sys.exit(f"error: required tool '{name}' not found on PATH")


def load_mask(path: Path) -> np.ndarray:
    """Return a boolean foreground mask (True = logo shape) for an input PNG.

    Auto-detects the mask source:
      - if the image has pixels with alpha below 250, use alpha (shape on
        transparent background)
      - otherwise treat it as an opaque image and use luminance, assuming
        the shape is the minority-colored region (light-on-dark or
        dark-on-light square/card logos)
    """
    with Image.open(path) as im:
        arr = np.array(im.convert("RGBA"))
    alpha = arr[:, :, 3]

    if alpha.min() < 250:
        # alpha channel carries the shape
        mask = alpha > 127
    else:
        # opaque image: threshold on luminance, pick minority region as fg
        rgb = arr[:, :, :3].astype(np.float32)
        luminance = rgb @ np.array([0.2126, 0.7152, 0.0722])
        thresh = (luminance.max() + luminance.min()) / 2
        bright = luminance > thresh
        # foreground = whichever side is the minority (the "shape" on a card/bg)
        mask = bright if bright.sum() < (~bright).sum() else ~bright

    return mask


def clean_mask(mask: np.ndarray) -> np.ndarray:
    """Denoise a binary mask: close small gaps/broken edges from pixel
    imperfections, then drop speckle noise. Deliberately left at native
    resolution — potrace's own corner/curve fitting is tuned for that scale;
    naively upscaling the binary mask first (e.g. nearest-neighbor) only
    blows up jitter into a staircase that its default tolerances can't
    re-merge into clean straight lines."""
    closed = ndimage.binary_closing(mask, structure=np.ones((3, 3)), iterations=1)
    opened = ndimage.binary_opening(closed, structure=np.ones((2, 2)), iterations=1)

    # drop tiny connected components (noise) relative to the largest shape
    labeled, n = ndimage.label(opened)
    if n > 1:
        sizes = ndimage.sum(opened, labeled, range(1, n + 1))
        keep_thresh = max(sizes) * 0.002 if len(sizes) else 0
        small_labels = [i + 1 for i, s in enumerate(sizes) if s < keep_thresh]
        if small_labels:
            opened[np.isin(labeled, small_labels)] = False

    return opened


def crop_to_bbox(mask: np.ndarray) -> np.ndarray:
    """Crop tightly to the foreground bounding box so the traced SVG's
    viewBox exactly matches the ink — required for exact, symmetric padding
    later (no hidden dead space to throw the margins off)."""
    if not np.any(mask):
        raise ValueError("no foreground remains after cleanup; use a larger, high-contrast logo")
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    r0, r1 = np.where(rows)[0][[0, -1]]
    c0, c1 = np.where(cols)[0][[0, -1]]
    return mask[r0:r1 + 1, c0:c1 + 1]


def mask_to_pbm(mask: np.ndarray, path: Path) -> None:
    """Write a boolean mask as a binary PBM (P4) for potrace."""
    h, w = mask.shape
    packed = np.packbits(mask, axis=1)
    with open(path, "wb") as f:
        f.write(f"P4\n{w} {h}\n".encode("ascii"))
        f.write(packed.tobytes())


def trace_to_svg(pbm_path: Path, svg_path: Path, alphamax: float) -> None:
    """Run potrace to produce a clean SVG with sharp straight edges.

    alphamax controls corner smoothing: lower = sharper/straighter corners,
    which suits geometric logos better than potrace's curve-happy default.
    """
    subprocess.run(
        [
            "potrace",
            str(pbm_path),
            "--svg",
            "--output", str(svg_path),
            "--alphamax", str(alphamax),
            "--opttolerance", "0.2",
            "--turdsize", "2",
        ],
        check=True,
    )


def pad_svg(svg_path: Path, padding_pct: float) -> ET.Element:
    """Load potrace's output and wrap it in an outer canvas with an equal
    margin on all four sides, sized as a percentage of the logo's longest
    side. Since the traced mask was cropped tight to its bounding box, the
    inner viewBox exactly matches the ink, so the padding comes out exactly
    symmetric — no eyeballing needed."""
    tree = ET.parse(svg_path)
    root = tree.getroot()
    _, _, w, h = (float(v) for v in root.get("viewBox").split())

    margin = (padding_pct / 100.0) * max(w, h)
    new_w, new_h = w + 2 * margin, h + 2 * margin

    wrapper = ET.Element(f"{{{SVG_NS}}}g")
    wrapper.set("transform", f"translate({margin},{margin})")
    for child in list(root):
        root.remove(child)
        wrapper.append(child)
    root.append(wrapper)

    root.set("viewBox", f"0 0 {new_w:.3f} {new_h:.3f}")
    root.set("width", f"{new_w:.3f}pt")
    root.set("height", f"{new_h:.3f}pt")
    return root


def style_svg(root: ET.Element, fill: str, bg: str | None) -> str:
    """Return SVG text with the logo recolored and, if bg is given, an
    opaque background rect painted behind it (baked into the vector itself
    so PDF exports stay truly vector, not raster-composited)."""
    root = ET.fromstring(ET.tostring(root))  # deep copy
    for el in root.iter():
        if el.get("fill") == "#000000":
            el.set("fill", fill)
    if bg is not None:
        _, _, w, h = root.get("viewBox").split()
        rect = ET.Element(f"{{{SVG_NS}}}rect")
        rect.set("x", "0")
        rect.set("y", "0")
        rect.set("width", w)
        rect.set("height", h)
        rect.set("fill", bg)
        root.insert(0, rect)
    return ET.tostring(root, encoding="unicode")


def render_png(svg_text: str, out_path: Path, width: int) -> None:
    with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as tmp:
        tmp.write(svg_text)
        tmp_path = tmp.name
    try:
        root = ET.fromstring(svg_text)
        _, _, w, h = map(float, root.get("viewBox").split())
        dimension = "-w" if w >= h else "-h"
        subprocess.run(
            ["rsvg-convert", dimension, str(width), "-o", str(out_path), tmp_path],
            check=True,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def render_pdf(svg_text: str, out_path: Path) -> None:
    with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as tmp:
        tmp.write(svg_text)
        tmp_path = tmp.name
    try:
        subprocess.run(
            ["rsvg-convert", "-f", "pdf", "-o", str(out_path), tmp_path],
            check=True,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def process(
    input_path: Path, out_dir: Path, alphamax: float, padding_pct: float,
    width: int = RASTER_WIDTH,
) -> None:
    name = input_path.stem
    work_dir = out_dir / name
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"[{name}] loading + building mask from {input_path.name}")
    mask = load_mask(input_path)

    print(f"[{name}] cleaning mask (closing gaps, dropping speckle)")
    cleaned = crop_to_bbox(clean_mask(mask))

    with tempfile.TemporaryDirectory() as tmp:
        pbm_path = Path(tmp) / f"{name}.pbm"
        mask_to_pbm(cleaned, pbm_path)

        raw_svg_path = Path(tmp) / f"{name}_raw.svg"
        print(f"[{name}] tracing to vector (potrace, alphamax={alphamax})")
        trace_to_svg(pbm_path, raw_svg_path, alphamax)

        print(f"[{name}] centering with {padding_pct}% margin")
        padded_root = pad_svg(raw_svg_path, padding_pct)

    # master vector: black fill, transparent background (print-ready)
    master_svg = style_svg(padded_root, "#000000", None)
    (work_dir / f"{name}.svg").write_text(master_svg, encoding="utf-8")
    print(f"[{name}] wrote {name}.svg")

    variants = [
        ("black_transparent", "#000000", None, False),
        ("white_transparent", "#ffffff", None, False),
        ("black_on_white", "#000000", "#ffffff", True),
        ("white_on_black", "#ffffff", "#000000", True),
    ]

    for suffix, fill, bg, also_jpg in variants:
        svg_text = style_svg(padded_root, fill, bg)
        (work_dir / f"{name}_{suffix}.svg").write_text(svg_text, encoding="utf-8")

        png_path = work_dir / f"{name}_{suffix}.png"
        render_png(svg_text, png_path, width)
        print(f"[{name}] wrote {png_path.name}")

        pdf_path = work_dir / f"{name}_{suffix}.pdf"
        render_pdf(svg_text, pdf_path)
        print(f"[{name}] wrote {pdf_path.name}")

        webp_path = work_dir / f"{name}_{suffix}.webp"
        with Image.open(png_path) as image:
            image.save(webp_path, format="WEBP", lossless=True)
        print(f"[{name}] wrote {webp_path.name}")

        if also_jpg:
            jpg_path = work_dir / f"{name}_{suffix}.jpg"
            with Image.open(png_path) as image:
                image.convert("RGB").save(jpg_path, quality=95)
            print(f"[{name}] wrote {jpg_path.name}")

    print(f"[{name}] done -> {work_dir}/")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Turn monochrome PNG logos into SVG, PDF, PNG, WebP, and JPEG assets."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--width", type=int, default=RASTER_WIDTH,
                        help="raster long-edge size in pixels (default: 2400)")
    parser.add_argument("inputs", nargs="+", type=Path, help="input PNG logo files")
    parser.add_argument("--out", type=Path, default=Path("out"), help="output directory")
    parser.add_argument("--alphamax", type=float, default=1.0,
                         help="potrace corner smoothing (lower = sharper straight corners, "
                              "higher = smoother curves; potrace default is 1.0)")
    parser.add_argument("--padding", type=float, default=10.0,
                         help="margin around the logo, as a percentage of its longest side, "
                              "applied equally on all 4 sides (default 10)")
    args = parser.parse_args()

    if not math.isfinite(args.padding) or args.padding < 0:
        parser.error("--padding must be finite and nonnegative")
    if not math.isfinite(args.alphamax) or not 0 <= args.alphamax <= 1.334:
        parser.error("--alphamax must be between 0 and 1.334")
    if args.width < 1:
        parser.error("--width must be positive")
    names = [path.stem for path in args.inputs]
    if len(names) != len(set(names)):
        parser.error("input filenames must have unique stems to avoid overwriting outputs")
    for input_path in args.inputs:
        if not input_path.is_file():
            parser.error(f"input not found or not a file: {input_path}")

    require_tool("potrace")
    require_tool("rsvg-convert")

    for input_path in args.inputs:
        try:
            process(input_path, args.out, args.alphamax, args.padding, args.width)
        except (OSError, ValueError, UnidentifiedImageError, subprocess.CalledProcessError) as exc:
            sys.exit(f"error: {input_path}: {exc}")


if __name__ == "__main__":
    main()
