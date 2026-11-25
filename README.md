# Vectorize

Turn a small, monochrome PNG logo into a reusable set of **SVG, vector PDF,
PNG, lossless WebP, and JPEG** assets—with black/white variations and equal
canvas margins.

A small local CLI built with NumPy, SciPy, Pillow, Potrace, and librsvg.
No API keys, uploads, or hosted services.

## Install

Requires **Python 3.10+**, **Potrace**, and **rsvg-convert** on your `PATH`.

### 1. Install the external tools

macOS ([Homebrew](https://brew.sh)):

```sh
brew install potrace librsvg
```

Debian / Ubuntu:

```sh
sudo apt-get update
sudo apt-get install potrace librsvg2-bin
```

Other platforms: install [Potrace](https://potrace.sourceforge.net/) and
[librsvg](https://gitlab.gnome.org/GNOME/librsvg) using your package manager,
or use WSL on Windows. Native Windows setup is not currently tested.
These tools are not installed by pip.

### 2. Install the Python package

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install "git+https://github.com/vladounet/vectorize.git"
```

Alternatively, with [pipx](https://pipx.pypa.io/):

```sh
pipx install "git+https://github.com/vladounet/vectorize.git"
```

The distribution is named `logo-vectorize`; the command is `vectorize`.
Installation is from GitHub; this project is not currently published to PyPI.

## Use

```sh
vectorize logo.png
vectorize logo1.png logo2.png --out assets --padding 12 --alphamax 0.5
vectorize logo.png --width 1200
vectorize --help
```

From a checkout, `python vectorize.py logo.png` also works after installing
the Python dependencies.

| Option | Default | Meaning |
| --- | --- | --- |
| `--out` | `out` | Output directory |
| `--padding` | `10` | Margin on each side, as a percentage of the cropped logo's longest side |
| `--alphamax` | `1.0` | Potrace corner smoothing, 0–1.334; lower is sharper, higher is smoother |
| `--width` | `2400` | Longest edge of raster outputs in pixels, including padding |
| `--version` | | Print the package version |

### Output

Each input gets its own directory, such as `out/logo/`:

- `logo.svg`: black logo on a transparent background (master).
- `logo_black_transparent.{svg,pdf,png,webp}`
- `logo_white_transparent.{svg,pdf,png,webp}`
- `logo_black_on_white.{svg,pdf,png,webp,jpg}`
- `logo_white_on_black.{svg,pdf,png,webp,jpg}`

That's 19 files per input. SVGs and PDFs contain vector artwork, not embedded
raster images. JPEGs are only made for opaque backgrounds. SVG/PDF sizes
follow the source geometry plus padding; `--width` only affects raster output.
Existing files with these names are overwritten. Inputs in the same run must
have unique filename stems.

## How it works—and limits

1. Use alpha for transparent images; otherwise threshold luminance and treat
   the minority-colored region as the foreground.
2. Close small gaps, remove speckles, and crop the mask at native resolution.
3. Trace with Potrace, add equal canvas margins, and render asset variations.

Best for simple, high-contrast, single-color symbols. This is **not** a
full-color vectorizer, AI upscaler, or font reconstruction tool. Gradients,
photographs, shadows, and multicolor artwork are reduced to a binary shape.
Opaque logos whose foreground occupies most of the image may be inverted.
Cleanup can remove fine lines or small details, and tracing can change
corners; inspect the result before printing. Equal margins are based on the
cropped bitmap bounds, not an optical alignment or exact curve-bounds pass.
Blank or very tiny inputs can leave no foreground and produce an error.

If an external command is missing, install the tools above and check your
`PATH`. If tracing is too rounded, lower `--alphamax`. To preserve more detail,
start with a larger source image when possible.

## Contribute

Bug reports, documentation improvements, and pull requests are welcome!
See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and tests. Please only share
sample artwork you have permission to publish.

## License

The original code is [MIT licensed](LICENSE), copyright Vlad Trifa.
Python dependencies have permissive licenses; Potrace is GPL-2.0-or-later
and librsvg is LGPL-2.1-or-later. They are separately installed command-line
programs, not bundled or linked into this package. See
[THIRD_PARTY.md](THIRD_PARTY.md) for the licensing assessment and redistribution
caveats. The software license does not grant rights to input logos or trademarks.
