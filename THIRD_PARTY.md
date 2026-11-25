# Dependencies and licensing

The original Python code in this repository is MIT licensed. Dependencies
retain their own licenses; MIT does not relicense them.

| Dependency | License | Use / upstream license |
| --- | --- | --- |
| NumPy | BSD-3-Clause | Python array operations; [license](https://github.com/numpy/numpy/blob/main/LICENSE.txt) |
| SciPy | BSD-3-Clause | Python mask morphology; [license](https://github.com/scipy/scipy/blob/main/LICENSE.txt) |
| Pillow | MIT-CMU (HPND-style PIL license, plus component notices) | Python image I/O; [license](https://github.com/python-pillow/Pillow/blob/main/LICENSE) |
| Potrace | GPL-2.0-or-later | Separately installed executable; [license](https://potrace.sourceforge.net/#license) |
| librsvg / rsvg-convert | LGPL-2.1-or-later | Separately installed executable; [license](https://gitlab.gnome.org/GNOME/librsvg/-/blob/main/COPYING.LIB) |

## Why this repository uses MIT

This package contains the Python orchestration code, not Potrace or librsvg
code or binaries. It invokes the independently installed `potrace` and
`rsvg-convert` programs through ordinary command-line arguments and exchanges
standard PBM/SVG/PDF/PNG files. It does not link against libpotrace or librsvg.
This process/file boundary is the basis for treating these as separate
programs and licensing this code under MIT, rather than claiming their GPL
or LGPL code is MIT licensed.

There is no identified licensing blocker for publishing this source package
under MIT on that basis. This is a practical licensing assessment, not legal
advice: whether programs form a combined work depends on the integration and
applicable law. Reassess before embedding/linking Potrace, using a libpotrace
binding, or distributing a bundled application.

## Redistribution caveats

- Users install the external executables separately. This repository and its
  Python wheel do not vendor them.
- If you redistribute Potrace or librsvg binaries (including in a container or
  standalone installer), comply with their own licenses, including applicable
  notices and corresponding-source requirements. MIT alone is not sufficient.
- NumPy, SciPy, and Pillow binary wheels may bundle additional libraries with
  their own notices, licenses, and exceptions. For example, NumPy/SciPy wheels
  can include BLAS/LAPACK and GCC runtime libraries. Keep upstream wheel
  notices and review the actual binaries if repackaging them. Dependencies are
  declared, not copied into this package's wheel.
- Converting artwork does not grant rights to the artwork or trademarks. The
  MIT license covers this software, not arbitrary logos supplied by users.
  Tracing an image does not by itself make that artwork GPL licensed.

License review: 2026; checked against upstream license pages, installed Python
package metadata, and Homebrew formula license metadata. Always check the
specific dependency versions you redistribute.
