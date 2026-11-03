# Typologue

**Status: work-in-progress prototype with a local browser interface.**

Typologue inspects font files, compares glyph outlines, and exports static font instances and editable outlines. The original command-line workflow is also available.

## Launch the interface

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python typologue.py
```

Open [Typologue](http://127.0.0.1:8765) in your browser. The server listens only on your computer. Python 3.9 or later is required.

- **Inspect & Compare:** Open TTF or OTF files and enter a single Unicode character. Compare outlines side by side or overlay two fonts. Missing characters are identified explicitly.
- **Sketch Glyph:** Draw freehand with a mouse, pen, or touch, undo strokes, and download an SVG.
- **Font Family & Export:** Set axis coordinates and export one static instance from a variable font. Download a ZIP with a Designspace and editable UFO outlines for the default and individual axis extremes. These UFOs contain outlines, widths, and Unicode mappings. Kerning, OpenType features, and intermediate variation masters still need export support.
- **Build a Weight Family:** Supply two compatible static TrueType masters to build a single weight axis. The tool checks glyph order, Unicode maps, em sizes, and contour/component structure. Masters still need matching contour order, direction, and point correspondence. Global metrics use the default master.

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

- Package and validate the local UI on macOS.
- Validate end-to-end execution on a current Mac.
- Preserve more source data when reconstructing UFOs, including kerning, features, and intermediate masters.
- Expand family building beyond two compatible TrueType masters on one weight axis. Add automatic family detection and deeper interpolation diagnostics.
- Add tests, safe handling of font naming/metadata, and installation instructions.

**Note:** The current script does not merge a set of static fonts into a variable font. Generated files should be reviewed before distribution.
