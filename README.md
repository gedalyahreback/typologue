# Fontity Serific

**Status: work-in-progress prototype — not yet a working desktop MVP.**

Fontity Serific is an experimental Python tool for inspecting variable font axes and exporting static instances. The longer-term goal is a macOS desktop app that detects related font styles, helps merge families, and produces editable variable-font source packages.

## Current source

The recoverable **Font Family Merger v3 foundation** is in [`build_v3.py`](build_v3.py). This is the command-line core, **not** the later v3.1.1 desktop installer. The latter has not yet been recovered into this repository.

### Implemented in this prototype

- Read `fvar` axis ranges and report glyph-read errors.
- Export a `report.json` summary.
- Generate static width × weight instances within the detected axis bounds.
- Apply an optional geometric slant to TrueType outlines.
- Emit a **starter** `family.designspace` axis descriptor (not a fully editable designspace).

## Run locally

Requires Python 3 and `fonttools`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python build_v3.py /path/to/variable-font.ttf --extract-matrix
```

Optional: `--slant -20` or `--slant 20` (geometric oblique only); `-o output-directory`.

See [prototype notes](docs/v3-prototype-notes.md) for the original test and limitations.

## Known gaps / next steps

- Recover and integrate the v3.1.1 macOS GUI/installer sources; fix the Tkinter / Python packaging issue.
- Validate end-to-end execution on a current Mac.
- Build genuine UFO-compatible editable masters and populate Designspace sources.
- Implement multi-font family detection, compatibility validation, and merging into a variable font.
- Add tests, safe handling of font naming/metadata, and installation instructions.

**Note:** The current script does not merge a set of static fonts into a variable font. Generated files should be reviewed before distribution.
