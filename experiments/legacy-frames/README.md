# legacy-frames — the retired pixel-font renderer

This is the original **framed-context** implementation: serialize a project,
then rasterize it with a patched Spleen 6×12 bitmap font into 1568×1568 PNG
frames that a vision model reads as dense context under image billing.

It is kept here for one reason: **reproducibility of the negative result.**
Paired testing (see [`../pretest/RESULTS.md`](../pretest/RESULTS.md)) showed
the frames cost more end-to-end than the same content as plain text in every
regime tested, and lose recall silently on synthesis tasks. The live tool
(`snap_serializer.py` at the repo root) is text-only as a result.

## Contents

- `snap_frames.py` — the full frame tool (`render --frames`, `verify`, `zoom`).
  Requires Pillow.
- `fonts/` — patched Spleen bitmap fonts (BSD 2-Clause, license included).
- `tools/` — `mkfont.py`, `patch_glyphs.py`: the glyph-patching pipeline that
  disambiguated S/5, U/V, G/6 at 6×12.

## Reproducing the frame arm

```sh
pip install pillow
python3 snap_frames.py render <project> --frames   # PNG frames + selftest + sidecars
python3 snap_frames.py verify <code> --out <outdir>
python3 snap_frames.py zoom '<regex>' --out <outdir>
```

The pretest harness in `../pretest/` drove this against controlled corpora to
produce the cost/accuracy numbers. Nothing here is needed to use the
serializer.
