# snap-serializer

Condense a repository or document archive into one compact text map, and
preload it into a [Claude Code](https://claude.com/claude-code) session so the
agent orients itself once instead of re-discovering the project through a
dozen exploratory tool calls.

**Measured wins** (paired A/B/C testing, 162 scored runs, Claude Sonnet 5,
end-to-end billed cost — full method and data in
[`experiments/pretest/`](experiments/pretest/RESULTS.md)):

- **−42%** cost per multi-question session on repos the model has never seen
- **−68%** cost per question against a 160-document / ~750k-char archive,
  versus letting the agent explore, at parity accuracy

Pure Python standard library, no dependencies.

```sh
python3 snap_serializer.py render <project>   # -> .claude/snap-serializer/context.txt
# in Claude Code: read .claude/snap-serializer/context.txt at session start
```

## What it does

`render` walks a project and writes a compact text index to
`.claude/snap-serializer/context.txt`:

- the file tree (one line per directory)
- README / CLAUDE.md and key config files
- function and class **signatures** across 9 languages (names and shapes, not
  bodies)
- the recent git log

The agent reads that once and already knows the project's shape and where
things live, so it goes straight to the right file instead of searching for
it. The map is for orientation only — the agent still Reads or greps the real
files before editing or quoting anything exactly.

### Docs mode

For prose projects (notes, journals, research archives) the code-map
serializer misses the content, so serialize the documents themselves:

```sh
python3 snap_serializer.py render DIR --docs 'notes/*.md' --max-chars 0
```

Scope note from testing: for *exhaustive* multi-concept audits over very
large archives (~150+ documents), ask one concept per pass — single-pass
recall over any monolithic preload degrades at that scale, while per-file
retrieval reading stays exact. Cost still favors the preload ~3× per question.

## When to use it, and when not

Measured, not guessed. The map pays for itself as soon as a session consults
it more than once, so preload it for real working sessions and for repos the
model has no strong priors on. For a **single** quick lookup, plain agentic
grep is cheaper than paying to load a map you'll read once (round 1: baseline
$0.069 vs preload $0.097 per one-shot task) — skip it there.

## Install

```sh
git clone https://github.com/michaeldtimpe/snap-serializer
cd snap-serializer && ./install.sh   # copies the skill to ~/.claude/skills/loadcontext
```

Then in any project, in Claude Code: `/loadcontext`

## CLI

```sh
python3 snap_serializer.py render [DIR]              # -> DIR/.claude/snap-serializer/context.txt
python3 snap_serializer.py render [DIR] --docs 'globs'   # prose mode: serialize named files in full
```

`render` options: `--out DIR`, `--max-chars N` (default 60000, `0` =
unlimited — use for docs mode).

## History: this project began as a pixel-font image trick

snap-serializer started as **framed-context**: serialize the project, then
rasterize it with a patched 6×12 bitmap font into PNG frames, loading ~2.6×
more context per token under image billing. The glyph work succeeded — the
pixels were legible (20/20 transcription with a zoom pass, selftest canaries,
patched confusable glyphs).

Then came the question that mattered: *does it actually lower end-to-end
cost?* Three rounds of paired testing said no, everywhere. The frames cost
+34% to +50% over the identical content as plain text, and at synthesis tasks
they **lost recall silently** — exhaustive answers came back looking complete
with items missing, a failure no glyph selftest can catch. The 2.6×
input-token density was real and irrelevant: sessions are billed mostly for
output tokens (5× the input price) and turns, and reading pixels inflates
both. (Same shape as the
[rtk finding](https://blog.jetbrains.com/ai/2026/07/rtk-claude-code-token-savings/):
compressing the cheap part of an agent bill while inflating the expensive
part.)

What survived was the serializer underneath. So that is the whole tool now.
The retired frame renderer, fonts, and glyph tooling are preserved under
[`experiments/legacy-frames/`](experiments/legacy-frames/), and the full
campaign — harness, tasks, corpora, numbers — under
[`experiments/pretest/`](experiments/pretest/RESULTS.md). ~$62 of API
credits, reproducible end to end.

## License

MIT for the code. The retired bitmap fonts under `experiments/legacy-frames/`
are patched builds of [Spleen](https://github.com/fcambus/spleen)
(BSD 2-Clause, license included alongside them).
