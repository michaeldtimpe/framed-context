# Pre-test results: do the frames actually save money?

Three rounds of paired A/B/C testing (baseline vs plain-text context preload
vs pixel-font frames), run 2026-07-28 on Claude Sonnet 5 through headless
Claude Code with exact billed usage capture. Protocol in README.md; raw
per-run records in the workdirs on the runner host. All CIs are 10k-resample
paired bootstraps.

## Round 1 — single lookups, famous repos (54 runs)

Tasks: 9 symbol-localization questions on click/requests/httpx (pinned SHAs,
exact-line-number answers to defeat pretraining memorization).

| arm | mean $/run | success | out tokens | turns |
|---|---|---|---|---|
| baseline | **$0.069** | 18/18 | 294 | 2.9 |
| text | $0.097 | 18/18 | 484 | 3.8 |
| frames | $0.131 | 18/18 | 955 | 6.3 |

Every paired difference significant. **Preloading anything lost; frames lost
worst.** Frames cost +90% vs baseline, +34% vs the same bytes as text, with
3.2x the output tokens — the "mental OCR" reasoning tax.

## Round 2 — no-priors repos, amortization, docs synthesis (81 runs)

Post-training-cutoff repos (agentlint, agora) kill memorized layouts;
1-vs-6-question sessions test load amortization; a 188k-char grep-resistant
corpus tests exhaustive semantic identification (exact-set scoring).

$/successful task:

| regime | baseline | text | frames |
|---|---|---|---|
| no-priors, 1 question | **$0.099** | $0.107 | $0.128 |
| no-priors, 6 questions | $0.233 | **$0.134** | $0.201 |
| docs synthesis, 1 question | $0.488 | **$0.431** | $0.709 (4/6 pass) |
| docs synthesis, 2 questions | $0.527 | **$0.412** | $1.633 (1/3 pass) |

**The serializer won; the pixels lost.** Text-map preload cut multi-question
session cost 42% and docs-synthesis cost ~22% at 100% success. Frames lost to
text in every regime and dropped recall on the corpus — every failure was a
silent omission (note-010's overrun phrasing missed in 4 of 4 failures),
never a false positive. The worst failure mode for an archive tool: output
that looks complete and isn't.

## Round 3 — archive scale, 160 notes / ~750k chars / 23 frames (27 runs)

The claimed docs-mode niche: an archive at the "24-frame" scale. Three
concepts (7 overrun, 5 corrosion, 6 wildlife notes) hidden in 160 notes with
decoys; exhaustive exact-set answers.

| arm | mean $/run | success | out tokens | turns | $/success |
|---|---|---|---|---|---|
| baseline (retrieval) | $1.582 | 9/9 | 6,406 | 11.7 | $1.582 |
| text preload | **$0.511** | 8/9 | 7,525 | 16.0 | **$0.574** |
| frames | $1.264 | 6/9 | 9,916 | 29.9 | $1.896 |

**Text preload cut archive-question cost 68%** (paired CI [-$1.50, -$0.60])
and went 6/6 on single-concept questions. Frames were strictly dominated:
+$0.75/run over text (significant), 2.6x the turns, and 0/3 on the
three-concept batch — every failure the same silent recall omission
(note-008/note-030's overrun phrasings), never a false positive.

**The honest twist:** at this scale the text arm dropped one batch run too
(2/3, same two notes). Exhaustive multi-concept synthesis over *any*
single-pass preload degrades recall at 160-note scale; only per-file
retrieval reading stayed 9/9. So the text preload's cost win comes with a
scope note — for exhaustive audits, ask one concept per pass (6/6 in text
arm) or pay for retrieval-grounded reading.

## Conclusions

1. **The pixels are dead in every tested regime.** Round 1: +90% cost on
   ordinary lookups. Round 2: +34-50% over text with recall failures. Round
   3: dominated on cost by text and on accuracy by both other arms, in the
   archive niche the frames were built for. The ~2.6x input-token density is
   real and irrelevant — output tokens (5x price) and turn count dominate,
   and pixel-reading inflates both.
2. **The serializer is the product.** `snapctx render`'s compact text
   preloaded into sessions: -42% on multi-question sessions in unfamiliar
   repos, -68% per archive question at 160-note scale, at parity accuracy
   (with the multi-concept scope note above).
3. Pixel reading fails silently — omissions, not errors — and a glyph
   selftest cannot catch attention-level misses. Disqualifying for archives.

Total spend, all three rounds: ~$62 in API credits. Rounds: 54 + 81 + 27 =
162 scored runs, zero harness errors.
