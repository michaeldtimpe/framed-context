"""Generate synthetic project-context text seeded with random canaries.

Usage: python3 gen_testdata.py <tag>

Writes:
  context-<tag>.txt     - the corpus (DO NOT show to the model as text)
  answers-<tag>.json    - ground truth (read only by check.py)
  questions-<tag>.json  - answer-free question list (safe for the model to read)

Nothing secret is printed to stdout.
"""
import json
import random
import string
import sys

tag = sys.argv[1]
CANARY_ALPHABET = sys.argv[2] if len(sys.argv) > 2 else string.ascii_letters + string.digits

rng = random.SystemRandom()

SYL = ["ka", "zor", "mel", "tri", "vex", "lun", "dro", "fi", "gas", "pol",
       "qui", "rup", "sen", "tav", "ulm", "wex", "yar", "bin", "cor", "dux"]


def name(n=3):
    return "".join(rng.choice(SYL) for _ in range(n))


def code(n=8):
    return "".join(rng.choice(CANARY_ALPHABET) for _ in range(n))


def sentence():
    verbs = ["retries", "flushes", "compacts", "shards", "validates", "mirrors"]
    nouns = ["the ledger", "stale sessions", "orphaned blobs", "the write-ahead log",
             "expired leases", "the manifest cache"]
    tails = ["every {} seconds".format(rng.randint(3, 900)),
             "after {} failed attempts".format(rng.randint(2, 9)),
             "unless the {} flag is set".format(name(2)),
             "when disk usage exceeds {} percent".format(rng.randint(50, 99))]
    return "The {} worker {} {} {}.".format(
        name(2), rng.choice(verbs), rng.choice(nouns), rng.choice(tails))


answers, questions, chunks = {}, [], []

project = name(2) + "-" + name(2)
chunks.append(f"# Project: {project}\n")
chunks.append("Auto-generated context snapshot. Sections: modules, config, services, git log.\n\n")

# --- modules with signatures ---
canary_i = 0
fact_i = 0
services = []
for m in range(14):
    mod = name(2)
    chunks.append(f"## module src/{mod}.py\n")
    for f in range(rng.randint(3, 6)):
        fn = name(2) + "_" + name(1)
        args = ", ".join(f"{name(1)}: {rng.choice(['int', 'str', 'bool', 'float'])}"
                         for _ in range(rng.randint(1, 4)))
        ret = rng.choice(["None", "int", "str", "dict", "list"])
        chunks.append(f"def {fn}({args}) -> {ret}")
        chunks.append(f"    # {sentence()}")
    # sprinkle canaries between modules
    if canary_i < 12 and m % 1 == 0 and rng.random() < 0.95:
        canary_i += 1
        val = code(8)
        cid = f"CANARY_{canary_i:02d}"
        chunks.append(f"{cid}={val}")
        answers[cid] = val
        questions.append({"id": cid, "q": f"What is the exact value of {cid}?"})
    chunks.append("")

# --- config ---
chunks.append("## config (resolved)\n")
for _ in range(25):
    chunks.append(f"{name(2)}.{name(1)}.{rng.choice(['timeout', 'limit', 'ttl', 'depth'])} = "
                  f"{rng.randint(1, 50000)}")
chunks.append("")

# --- services with fact QAs ---
chunks.append("## services\n")
for s in range(6):
    fact_i += 1
    svc = name(2)
    port = rng.randint(1024, 65535)
    path = "/" + name(1) + "/" + name(1)
    chunks.append(f"service {svc}: listens on port {port}, health endpoint {path}, "
                  f"replicas={rng.randint(1, 12)}")
    chunks.append(f"  # {sentence()}")
    fid = f"FACT_{fact_i}"
    answers[fid] = str(port)
    questions.append({"id": fid, "q": f"What port does service '{svc}' listen on?"})
chunks.append("")

# --- verbatim blocks ---
for v in (1, 2):
    line = sentence() + " " + sentence()
    chunks.append(f"### VERBATIM {v} ###")
    chunks.append(line)
    chunks.append("")
    vid = f"VERBATIM_{v}"
    answers[vid] = line
    questions.append({"id": vid,
                      "q": f"Transcribe verbatim the single line that appears "
                           f"immediately after the marker line '### VERBATIM {v} ###'."})

# --- git log filler to reach target size ---
chunks.append("## git log\n")
target = 18000
while sum(len(c) + 1 for c in chunks) < target:
    chunks.append(f"{code(10).lower()} {rng.choice(['fix', 'feat', 'chore', 'refactor'])}: "
                  f"{sentence()}")

text = "\n".join(chunks)
with open(f"context-{tag}.txt", "w") as f:
    f.write(text)
with open(f"answers-{tag}.json", "w") as f:
    json.dump(answers, f, indent=2)
with open(f"questions-{tag}.json", "w") as f:
    json.dump(questions, f, indent=2)

print(f"corpus: {len(text)} chars, {text.count(chr(10)) + 1} lines, "
      f"{len(questions)} questions ({canary_i} canaries, {fact_i} facts, 2 verbatim)")
