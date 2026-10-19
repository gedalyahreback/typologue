# Font Family Merger v3 — Foundation Prototype

This prototype begins the parametric-family roadmap.

## Implemented now

- Reads OpenType variable axes directly from a variable TTF.
- Preserves actual min/default/max coordinates.
- Produces a machine-readable `report.json`.
- Performs a glyph-read/outline sanity pass across the full glyph set.
- Extracts canonical named static width × weight instances that fall inside the font's real axis ranges.
- Supports a global geometric slant transform, including negative angles for reverse oblique.
- Emits a starter `family.designspace` axis descriptor.

## Noto Serif Hebrew test

Source: `NotoSerifHebrew-VariableFont_wdth,wght.ttf`

Detected:
- 472 glyphs
- Weight (`wght`): 100 / 400 default / 900
- Width (`wdth`): 62.5 / 100 default / 100

Canonical extraction produces 36 static fonts:
- Extra Condensed: 9 weights
- Condensed: 9 weights
- Semi Condensed: 9 weights
- Normal: 9 weights

## Run

```bash
python3 build_v3.py NotoSerifHebrew-VariableFont_wdth,wght.ttf --extract-matrix
```

Reverse-oblique test at -20 degrees:

```bash
python3 build_v3.py NotoSerifHebrew-VariableFont_wdth,wght.ttf --extract-matrix --slant -20
```

Forward oblique at +20 degrees:

```bash
python3 build_v3.py NotoSerifHebrew-VariableFont_wdth,wght.ttf --extract-matrix --slant 20
```

## Important limitation of this prototype

The generated `family.designspace` currently describes the detected axes; it does **not yet reconstruct editable UFO masters from the compiled variable font**. That is the next major engineering step for Fontra-style source editing. Likewise, slant is currently geometric oblique generation, not semantic true-italic construction.

## Next implementation targets

1. Reconstruct/source UFO-compatible masters and populate Designspace sources.
2. Compare corresponding glyph topology across masters and report contour/point incompatibilities.
3. Add controlled width behavior: outlines vs stems vs sidebearings vs anchors.
4. Add semantic region tagging schema (`stem`, `serif`, `terminal`, etc.).
5. Add serif-prominence transformations.
6. Add relational small-cap generation.
7. Wrap related designspaces and metadata into `.fontfamily`.