"""Score answers: python3 check.py <answers.json> <my_answers.json>"""
import difflib
import json
import sys

with open(sys.argv[1]) as f:
    truth = json.load(f)
with open(sys.argv[2]) as f:
    mine = json.load(f)

exact = total = 0
for key, want in truth.items():
    got = str(mine.get(key, "<missing>")).strip()
    want = str(want).strip()
    total += 1
    if key.startswith("VERBATIM"):
        ratio = difflib.SequenceMatcher(None, want, got).ratio()
        ok = ratio == 1.0
        exact += ok
        print(f"{'PASS' if ok else 'PART'} {key}: similarity {ratio:.3f}")
        if not ok:
            print(f"   want: {want}")
            print(f"   got : {got}")
    else:
        ok = got == want
        exact += ok
        print(f"{'PASS' if ok else 'FAIL'} {key}: want={want!r} got={got!r}")

print(f"\nscore: {exact}/{total} exact")
