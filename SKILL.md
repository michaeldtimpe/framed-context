---
name: loadcontext
description: Load condensed project context — a serialized text map of the repo (file tree, docs, signatures, git log) preloaded at session start. Measured to cut multi-question session cost ~42% on unfamiliar repos and ~68% per question on large doc archives. Use when the user asks to /loadcontext, "load project context", or wants a full-project overview loaded into the session. ALSO use when the user says "update the frames", "refresh/regenerate the context", "re-render the context", or similar — that means re-running the render step for the current project's .claude/snap-serializer/.
---

# loadcontext — condensed project context (text serializer)

Serializes a condensed snapshot of a project (file tree, docs, configs, code
signatures, git log) into `.claude/snap-serializer/context.txt` and loads it as the
session's project map. One Read call; the map pays for itself as soon as the
session consults it twice.

(Historical note: this skill previously rendered pixel-font PNG frames.
Paired testing showed the frames cost more end-to-end than the same content
as text in every regime and lose recall silently on archives — see
experiments/pretest/RESULTS.md. The serializer is now the whole tool; the
retired frame renderer lives in experiments/legacy-frames/ for reproducibility.)

## Steps

1. Run the renderer against the target project (defaults to cwd):

   python3 ~/.claude/skills/loadcontext/snap_serializer.py render [PROJECT_DIR]

   It prints the serialized size and the `context.txt` path.

2. Read `.claude/snap-serializer/context.txt` with the Read tool (in chunks if it is
   large). Use it as your project map for the session.

3. Tell the user what was loaded: sections, char count, approximate token
   cost. Then proceed normally.

## When to skip

For a single quick lookup ("where is function X?"), skip the preload —
plain grep is cheaper for one-shot questions. Preload when the session will
ask several questions of the project, or when working in a repo the model
has no strong priors on.

## Retrieving exact strings

The map is condensed; editing or quoting still means Reading the real file.
For hashes, tokens, and exact strings, grep the repo (or `context.txt`)
rather than trusting the map's rendering of them.

## Docs mode (prose projects and archives)

For projects whose value is documents rather than code (notes, journals,
research), serialize the files themselves, in full:

    python3 ~/.claude/skills/loadcontext/snap_serializer.py render DIR \
      --docs 'START-HERE.md,notes/*.md' --out DIR/.claude/snap-serializer/core \
      --max-chars 0

Separate `--out` subdirectories act as named context sets (a small `core`
set loaded by default, big reference files as their own on-demand sets).

Scope note (measured): for exhaustive multi-concept audits over very large
archives (~150+ documents), ask one concept per pass — single-pass recall
over any monolithic preload degrades at that scale, while per-file retrieval
reading stays exact. Cost still favors the preload ~3x per question.

## Updating the context

When the user says "update the frames", "refresh the context", "regenerate
context", or similar, they mean re-running step 1 for the current project so
`.claude/snap-serializer/` reflects the repo as it is now. Report the new stats
line. Only Read the regenerated context if the user also wants it loaded
into this session; a bare update is just the render. First-time setup is the
same command — mention adding `.claude/snap-serializer/` to .gitignore (derived
state).

## Notes

- No dependencies beyond Python 3.
- The map is for orientation — editing files still means Reading the real
  file first.
- `--max-chars` (default 60000, 0 = unlimited) bounds cost.
