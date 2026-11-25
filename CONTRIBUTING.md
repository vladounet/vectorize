# Contributing

Open an issue or pull request at https://github.com/vladounet/vectorize.
For bugs, include your OS, Python/tool versions, command, and error output.
Only attach input artwork you have permission to share publicly.

## Development

Install Potrace and librsvg as described in the README, then:

```sh
git clone https://github.com/vladounet/vectorize.git
cd vectorize
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest
python -m build
python -m twine check dist/*
```

Tests generate their own artwork; no private logos are needed. Integration
checks exercise the actual external tools and are skipped if either is
missing. CI installs both tools and runs the suite on Linux.

Keep changes focused, add regression tests for behavior changes, and update
the README for CLI/output changes. Do not commit generated exports, local
logos, credentials, or third-party binaries. Contributions are under the
project's MIT license; do not add code or assets you cannot license that way.
