#!/usr/bin/env python3
"""Score a docs-mode synthesis answer: exact set match on note IDs.

Usage: check_docs.py <concept>   (concept: overrun | corrosion)
Reads the agent's final text from $RESULT_FILE. Looks for the last line
matching 'ANSWER...:' whose label mentions the concept (or a bare 'ANSWER:'),
extracts note-### IDs, and requires exact set equality with ground truth.
Exit 0 = pass.
"""
import os
import re
import sys

GROUND_TRUTH = {
    # baked from gen_corpus.py output (deterministic seed)
    "overrun": set("note-007,note-010,note-029,note-030,note-031,note-039,note-040".split(",")),
    "corrosion": set("note-008,note-013,note-022,note-024,note-025".split(",")),
    # baked from gen_corpus3.py output (round 3, 160-note archive)
    "overrun3": set("note-008,note-030,note-053,note-054,note-072,note-099,note-129".split(",")),
    "corrosion3": set("note-015,note-041,note-063,note-064,note-078".split(",")),
    "wildlife3": set("note-007,note-034,note-060,note-095,note-143,note-146".split(",")),
}

def main():
    concept = sys.argv[1]
    text = open(os.environ["RESULT_FILE"]).read()
    lines = [l for l in text.splitlines() if re.match(r"^\s*ANSWER[^:]*:", l, re.I)]
    base = re.sub(r"\d+$", "", concept.lower())  # overrun3 -> overrun
    labeled = [l for l in lines if base in l.lower()]
    bare = [l for l in lines if re.match(r"^\s*ANSWER\s*:", l, re.I)]
    pick = (labeled or bare)
    if not pick:
        print(f"no ANSWER line for {concept}")
        sys.exit(1)
    got = set(re.findall(r"note-\d{3}", pick[-1]))
    want = GROUND_TRUTH[concept]
    if got == want:
        print(f"{concept}: exact match ({len(want)} ids)")
        sys.exit(0)
    print(f"{concept}: MISMATCH missing={sorted(want - got)} extra={sorted(got - want)}")
    sys.exit(1)

if __name__ == "__main__":
    main()
