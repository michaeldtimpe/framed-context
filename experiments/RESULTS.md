# Legibility experiments

Date: 2026-07-21. Model: Claude Fable 5 reading through Claude Code's real
`Read`-tool image pipeline at 1568×1568.

## Protocol

Every run is uncontaminated: `gen_testdata.py <tag> [alphabet]` synthesizes
~18k chars of project-context-style filler seeded with 20 probes whose values
come from `random.SystemRandom` — 12 random 8-char canaries, 6 service-port
facts, 2 full-sentence verbatim transcriptions. The model never sees the text;
it reads only the PNG rendered by `render.py`, writes its transcriptions, and
`check.py` scores them against the ground-truth sidecar. The "zoom pass" lets
the model re-read 4× crops (`zoom_canaries.py`, `zoom_verbatim.py` — scripts
that locate targets in the corpus but output only images).

## Results (exact matches / 20)

| Run | Font | Packed | Canary alphabet | Raw | Zoom |
|---|---|---|---|---|---|
| v0 | 8×16 | no | full alnum | 16 | 19 |
| v1 | 6×12 | no | full alnum | 19 | 20 |
| v2 | 5×8 | no | full alnum | 9 | 16 |
| v3 | 6×12 | yes | full alnum | 13 | 18 |
| v4 | 6×12 patched | yes | confusables only¹ | 11 | 19 |

¹ `S5UV06GOsuvglIl1Zz2B8` — every canary character drawn from confusable
pairs; a deliberate torture test of the glyph patches.

## Findings

1. **6×12 (72 px²/char) is the sweet spot** — better than 8×16 at 1.8× the
   density. 5×8 (40 px²/char) sits at the documented legibility cliff: raw
   canaries fell to 3/12 and a *port digit* was silently misread (4161 vs
   4181). Below the cliff, digits corrupt without warning.
2. **Errors concentrate in random strings on confusable glyph pairs**
   (S/5, U/V, l/1/I, O/0, G/6, and case pairs like K/k). Prose, code-shaped
   text, and numbers read essentially perfectly at 6×12+.
3. **Packing (newlines→`¶`, rows filled) is required for the token win** but
   costs raw-read navigation: twice the model transcribed the wrong sentence
   for a verbatim probe until the zoom pass located it. Content accuracy is
   unaffected.
4. **The zoom pass is the great equalizer** — a 4× nearest-neighbor crop
   recovered nearly every raw error in every configuration.
5. **Glyph patches work**: with rounded S, pointed V, and open-top 6
   (`tools/patch_glyphs.py`), the confusable-only torture test scored 19/20
   zoomed — matching the unpatched font's score on an easy full-alphabet test.
6. Incidents from live use, all now designed around: the bitmap font is
   Latin-1 only (real READMEs aren't); a selftest alphabet must be
   single-case (K/k is itself a confusable pair) with no glyph adjacent to
   `¶` (a terminal P read as M); and m/n must not coexist in the alphabet —
   stem-count blur at 6×12 caused a live m→n misread that survived 4× zoom.
   Each failure was caught by the verify gate before it could propagate,
   which is the strongest evidence for shipping one.

## Token economics

18k chars of line-structured context rendered unpacked = 3–4 frames ≈ 9.8–13k
image tokens — *worse* than the ~4.5k text tokens it replaces. Packed, the
same corpus = 1 frame ≈ 3,279 tokens. A full packed 6×12 frame ≈ 34k chars
(~8.5k text tokens) for 3,279 image tokens ≈ 2.6×. Real-repo check
(psf/requests): 25.6k serialized chars → 1 frame, 3,278 vs ~6,400 tokens.
