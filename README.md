# snapctx

Load condensed project context into [Claude Code](https://claude.com/claude-code)
as pixel-font PNG images — SnapCompact-style visual context compression,
rebuilt as a standalone skill.

A full 1568×1568 frame carries ~34,000 characters (~8,500 text-tokens' worth)
of project context for ~3,279 image tokens under Anthropic's pixel billing —
about **2.6× more context per token**, loaded through the ordinary `Read`
tool. No MCP server, no API changes, no external calls.

Inspired by [stencil.so's SnapCompact](https://stencil.so/blog/snapcompact)
and the [oh-my-pi](https://github.com/can1357/oh-my-pi) implementation; this
project applies the idea to *loading* context rather than replacing
compaction, which fits Claude Code without touching its internals.

## How it works

`snapctx.py render` serializes a project — compact file tree, README/CLAUDE.md,
configs, function/class signatures across 9 languages, recent git log — packs
it into a continuous `¶`-separated stream, and rasterizes it with a patched
[Spleen](https://github.com/fcambus/spleen) 6×12 bitmap font into PNG frames.
The model reads the frames as vision input and uses them as its project map.

Safety rails, each one earned by a measured failure:

- **`SELFTEST:` line** — every render embeds a random code from a
  glyph-unambiguous alphabet; `snapctx.py verify` confirms the model actually
  read it correctly before the session trusts the frames.
- **`zoom` escape hatch** — random-looking strings (hashes, tokens) confuse
  even patched glyphs on a first read; `snapctx.py zoom '<regex>'` writes a
  4× crop that resolves them reliably.
- **`context.txt` sidecar** — the identical text stays on disk for grep, so
  exactness is never hostage to OCR.
- **Patched glyphs** — Spleen's `S/5`, `U/V`, and `G/6` pairs differ by only
  a pixel or two at 6×12; this repo ships versions with a rounded `S`,
  pointed `V`, and open-top `6` (see `tools/patch_glyphs.py`).

## Measured results

All experiments used an uncontaminated protocol: a script generates corpora
seeded with random canaries, the model only ever sees the rendered pixels, and
a scorer compares transcriptions to ground truth (details in
`experiments/RESULTS.md`). Read through Claude Code's real image pipeline with
Claude Fable 5:

| Configuration | Chars/frame | Raw read | After zoom pass |
|---|---|---|---|
| Spleen 8×16 | 19.2k | 16/20 | 19/20 |
| Spleen 6×12 | 33.9k | 19/20 | **20/20** |
| Spleen 5×8 | 61.3k | 9/20 | 16/20 — below the legibility cliff, do not use |
| 6×12 packed | 33.9k | 13/20 | 18/20 |
| 6×12 packed, patched font, **confusable-only strings** | 33.9k | 11/20 | **19/20** |

Prose, code, and numbers read essentially perfectly at 6×12; residual errors
concentrate in adversarial random strings, which the zoom pass resolves.

## Install

Requires Python 3 with Pillow, and a high-resolution-vision Claude model
(Fable 5, Sonnet 5, Opus 4.8 — lower tiers downscale 1568px images, which
destroys the font).

```sh
git clone https://github.com/michaeldtimpe/snapctx
cd snapctx && ./install.sh   # copies the skill to ~/.claude/skills/loadcontext
```

Then in any project, in Claude Code: `/loadcontext`

## CLI

```sh
python3 snapctx.py render [DIR]            # frames -> DIR/.claude/snapctx/
python3 snapctx.py verify CODE --out OUT   # check the SELFTEST reading
python3 snapctx.py zoom 'REGEX' --out OUT  # 4x crop of matching rows
```

`render` options: `--font 6x12|8x16`, `--max-chars N` (default 60000),
`--max-frames N` (default 4), `--out DIR`.

## Notes and limits

- The frames are a **map, not an editing source** — the skill still reads
  real files before modifying them.
- Images cost extra "mental OCR" reasoning when the model retrieves from
  them; this wins for once-per-session context loads, not per-turn hot data.
- `.claude/snapctx/` is derived state — gitignore it.

## License

MIT for the code. Fonts are patched builds of
[Spleen](https://github.com/fcambus/spleen) (BSD 2-Clause, license included
in `fonts/`).
