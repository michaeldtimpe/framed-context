# framed-context pre-test

A private, rigorous A/B/C test of whether the pixel-font context frames
actually lower end-to-end billed cost without hurting task success — run
*before* submitting anything to a public benchmark (Tura or otherwise).

## Design

Three arms, same task, fresh clone every run:

| Arm | Context provided | What it isolates |
|---|---|---|
| `baseline` | none — agent explores organically | the status quo |
| `text` | snapctx's `context.txt` as plain text | the value of the *serializer* |
| `frames` | snapctx PNG frames + `context.txt` sidecar (as shipped) | the value of the *pixel encoding* on top |

The `text` arm is the control that keeps this honest: if `text` matches or
beats `frames` on cost, the win is the curated context load, not the pixels.

**Predictions written down in advance** (what makes this a test, not a demo):

1. `frames` wins first-turn uncached input tokens by construction (~2.6x).
2. Open question A: does the agent re-read real files anyway, making frames
   additive cost? (the rtk failure mode — frames are "a map, not an editing
   source")
3. Open question B: does mental-OCR reasoning inflate output tokens (billed at
   5x the input rate) past the input savings?
4. Kill criterion: if `frames` does not beat `text` on $/successful-task with
   a CI excluding zero, the pixel encoding is overhead and the serializer is
   the product.

## Metrics (priority order)

1. Task success rate (a saving that costs correctness is negative)
2. Billed $ per successful task (`total_cost_usd` from `claude -p`, which
   prices uncached/cached/write/output correctly — no estimation)
3. Output tokens (the mental-OCR tax lives here)
4. Turns, wall clock

Analysis is paired per (task, replicate) with 10k-resample bootstrap CIs.
Arm order is interleaved per task/replicate so time-of-day drift can't bias
one arm.

## Hygiene

- Fresh clone per run; workspace deleted afterwards (raw `claude.json` kept).
- `CLAUDE_CONFIG_DIR` points at a pristine config so the operator's global
  CLAUDE.md and the loadcontext skill (which reference the frames!) cannot
  contaminate any arm.
- Runner refuses to start without `ANTHROPIC_API_KEY` set, so spend lands on
  the dedicated capped key, never a subscription login.
- Results are append-only JSONL; the runner is resumable (reruns skip
  completed run ids).

## Model choice

Default `claude-sonnet-5`: high-res vision tier (frames are 1568px squares ≈
2.46 MP — models below the 2576px/3.75MP tier downscale and destroy the
font), and cheapest to test on ($3/$15/MTok, intro $2/$10 through 2026-08-31).

Caveat: the repo's 19/20-20/20 glyph accuracy was measured on Fable 5.
Before the full matrix, smoke-test that Sonnet 5 passes `snapctx.py verify`
on a rendered frame; if its raw read is materially worse, run the matrix on
`--model claude-opus-5` and accept the higher unit cost. If results will be
quoted for Claude Code usage specifically, replicate the headline comparison
on the model you actually run (`claude-fable-5`, $10/$50).

## Tasks

`tasks.json`. The three `fc-*` entries are smoke tasks against this repo —
good for validating plumbing, too shallow to decide anything. Real signal
needs 5-8 tasks on 2-3 repos where the frames are deployed, mixing:

- cross-file "where/how is X done" Q&A with regex-checkable answers
- bug localization ("which function causes Y") pinned to a commit
- small fixes verified by `{"type": "command", "cmd": "pytest ..."}`

Pin `ref` to a commit SHA so every replicate sees identical code.

## Budget

~90 runs (7 tasks x 3 arms x 4+ reps) at $0.50-2/run on Sonnet 5 intro
pricing ≈ **$50-150**. Fund $150 with a $200 hard spend limit.

## Run it

```sh
./stage.sh                    # rsync to the M5 + print instructions
# on the M5:
export ANTHROPIC_API_KEY=sk-ant-...
python3 runner.py --dry-run
python3 runner.py --only fc-q1 --replicates 1    # ~$1 plumbing check
python3 runner.py --replicates 4                 # full matrix
python3 analyze.py
```
