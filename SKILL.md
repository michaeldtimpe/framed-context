---
name: loadcontext
description: Load condensed project context as pixel-font PNG images (SnapCompact-style) — ~2.6x more context per token than plain text. Use when the user asks to /loadcontext, "load project context", or wants a cheap full-project overview loaded into the session. ALSO use when the user says "update the frames", "refresh/regenerate frames", "re-render the context", or similar — that means re-running the render step for the current project's .claude/snapctx/ frames.
---

# loadcontext — dense visual project context

Renders a condensed snapshot of a project (file tree, docs, configs, code
signatures, git log) into 1568x1568 pixel-font PNGs and loads them as vision
input. A full frame carries ~34,000 chars (~8.5k text-tokens' worth) for
~3,279 image tokens.

## Steps

1. Run the renderer against the target project (defaults to cwd):

   python3 ~/.claude/skills/loadcontext/snapctx.py render [PROJECT_DIR]

   It prints one `FRAME: <path>` line per PNG plus token stats. If it prints
   a `SMALL_PROJECT:` line instead, the project is cheaper as plain text —
   Read the indicated `context.txt` and skip the frames and selftest.

2. Read every FRAME path with the Read tool. The frames are packed text in a
   6x12 pixel font; `¶` glyphs mark line breaks in the original text.

3. Self-test: the stream begins with `SELFTEST:` followed by 8 space-separated
   glyphs (lowercase letters + digits only — no uppercase). Verify your reading
   (spaces optional; verify strips them):

   python3 ~/.claude/skills/loadcontext/snapctx.py verify <code-you-read> --out <outdir>

   On FAIL, zoom the code first (`zoom SELFTEST --out <outdir>`) and
   retry once — a misread of the code itself is not a degraded pipeline. If it
   still fails, warn the user that the image pipeline degraded the frames
   (likely a non-high-res model tier) and fall back to normal file reading.

4. Tell the user what was loaded: sections, char count, and the token cost
   printed by the renderer. Then proceed with the session normally, using the
   imaged context as your project map.

## Retrieving exact strings later

Pixel text is near-perfect for prose, code, and numbers, but random-looking
strings (hashes, tokens) can confuse glyph pairs (S/5, U/V, l/1, O/0). When
you need such a string exactly, do NOT trust your first read — either:

- grep the sidecar: `<outdir>/context.txt` holds the identical text, or
- zoom: `python3 ~/.claude/skills/loadcontext/snapctx.py zoom '<regex>' --out <outdir>`
  writes a 4x-magnified crop (`ZOOM: <path>`) — Read it.

The default outdir is `PROJECT_DIR/.claude/snapctx/`. Add it to .gitignore if
the user commits — it is derived state.

## Docs mode (prose projects)

For projects whose value is documents rather than code (notes, journals,
research), the code-map serializer misses the content. Use `--docs` to image
the files themselves, in full:

    python3 ~/.claude/skills/loadcontext/snapctx.py render DIR \
      --docs 'START-HERE.md,notes/*.md' --out DIR/.claude/snapctx/core \
      --max-chars 0 --max-frames 16

Separate `--out` subdirectories act as named frame sets (e.g. a small `core`
set loaded by default, big reference files as their own on-demand sets). Each
set has its own selftest and sidecars. Same reading rules apply.

## Updating frames

When the user says "update the frames", "refresh the frames", "regenerate
context", or similar, they mean re-running step 1 for the current project so
`.claude/snapctx/` reflects the repo as it is now:

    python3 ~/.claude/skills/loadcontext/snapctx.py render [PROJECT_DIR]

Report the new stats line. Only Read the regenerated frames if the user also
wants the context loaded into this session (e.g. they say "update and load");
a bare update is just the render. If the project has no `.claude/snapctx/`
yet, this is a first-time setup — same command, and mention adding
`.claude/snapctx/` to .gitignore.

## Notes

- Requires Pillow (`python3 -c "import PIL"`); if missing, `pip install pillow`.
- Editing files still means Reading the real file first — the frames are a
  map, not an editing source.
- `--max-chars` (default 60000) and `--max-frames` (default 4) bound cost.
