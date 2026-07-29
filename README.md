# framed-context

Condensed project and corpus context for [Claude Code](https://claude.com/claude-code)
— a serializer that turns a repo or document archive into one compact text
artifact, preloaded at session start.

**Measured wins** (paired A/B/C, 162 scored runs, Claude Sonnet 5,
end-to-end billed cost — full methodology and data in
[`experiments/pretest/`](experiments/pretest/RESULTS.md)):

- **−42%** cost per multi-question session on repos the model has never seen
- **−68%** cost per question against a 160-document / ~750k-char archive,
  versus organic retrieval, at parity accuracy

```sh
python3 snapctx.py render <project>     # -> .claude/snapctx/context.txt
# in Claude Code: read .claude/snapctx/context.txt at session start
```

## The honest history: this project began as something else

framed-context started as a pixel-font **image** compression scheme:
serialize the project, rasterize it with a patched 6×12 bitmap font into PNG
frames, and load ~2.6× more context per token under image billing
(SnapCompact-style). The glyph legibility work succeeded — 20/20
transcription with a zoom pass, selftest canaries, patched confusable
glyphs.

Then we asked the $6 question: *does it actually lower end-to-end cost?*
Three rounds of paired testing later, the answer is no, everywhere:

| regime | frames vs plain text, same content |
|---|---|
| single lookups, famous repos | **+34% cost** |
| multi-question, unseen repos | **+50% cost** |
| archive synthesis (188k chars) | **+72% $/success, 5/9 vs 9/9 accuracy** |
| archive synthesis (750k chars, 23 frames) | **+230% $/success, 6/9 vs 8/9** |

The 2.6× input-token density is real — and irrelevant. Sessions are billed
mostly for output tokens (5× the input price) and turns, and reading pixels
inflates both: the model spends "mental OCR" reasoning re-deriving what a
text file would have handed it for free. Worse, at synthesis tasks pixel
reading **fails silently** — exhaustive-identification answers came back
looking complete with items missing, a failure no glyph selftest can catch
because it happens at attention level, not OCR level. (This mirrors what
[JetBrains found for rtk](https://blog.jetbrains.com/ai/2026/07/rtk-claude-code-token-savings/):
compressing the cheap component of an agent bill while inflating the
expensive one.)

What *survived* testing was the part we almost didn't notice we'd built: the
serializer. Preloading its plain-text output beat letting the agent explore
organically in every regime with more than one question per session — the
map pays for itself as soon as it's consulted twice.

So that's what this tool is now. `render` emits `context.txt`; the PNG
pipeline is kept behind `--frames` for reproducibility of the negative
result, and `experiments/` preserves the whole record.

## How it works

`snapctx.py render` serializes a project — compact file tree, README /
CLAUDE.md, configs, function and class signatures across 9 languages, recent
git log — into `.claude/snapctx/context.txt`. Load it with one Read at
session start; grep the real files for anything that needs exactness.

### Docs mode

For prose corpora (notes, journals, research archives) the code-map
serializer misses the content — serialize the documents themselves:

```sh
python3 snapctx.py render DIR --docs 'notes/*.md' --max-chars 0
```

One scope note from testing: for *exhaustive* multi-concept audits over very
large archives, ask one concept per pass — single-pass recall over any
monolithic preload (text or pixels) degrades around the 160-document scale,
while per-file retrieval reading stays exact. Cost still favors the preload
by ~3× per question.

## When NOT to use this

Measured, not vibes: for a session that asks **one** quick question of a
repo, plain agentic grep is cheaper than any preload (round 1: baseline
$0.069 vs text $0.097 per task). Preload when the session will consult the
map repeatedly; skip it for one-shot lookups.

## Install

```sh
git clone https://github.com/michaeldtimpe/framed-context
cd framed-context && ./install.sh   # copies the skill to ~/.claude/skills/loadcontext
```

Then in any project, in Claude Code: `/loadcontext`

## CLI

```sh
python3 snapctx.py render [DIR]            # context.txt -> DIR/.claude/snapctx/
python3 snapctx.py render [DIR] --frames   # legacy pixel frames + selftest
python3 snapctx.py verify CODE --out OUT   # frames only: check SELFTEST reading
python3 snapctx.py zoom 'REGEX' --out OUT  # frames only: 4x crop escape hatch
```

`render` options: `--docs 'globs'`, `--max-chars N` (default 60000, 0 =
unlimited), `--out DIR`; `--frames` adds `--font 6x12|8x16`, `--max-frames N`.

## The experiments

- [`experiments/RESULTS.md`](experiments/RESULTS.md) — the original glyph
  legibility work (fonts, selftest alphabet, zoom pass). The pixels are
  *legible*; that was never the problem.
- [`experiments/pretest/`](experiments/pretest/RESULTS.md) — the three-round
  cost/success campaign that killed the frames and validated the serializer:
  harness, task sets, corpora generators, and full numbers. ~$62 of API
  credits, reproducible end to end.

## License

MIT for the code. Fonts are patched builds of
[Spleen](https://github.com/fcambus/spleen) (BSD 2-Clause, license included
in `fonts/`).
