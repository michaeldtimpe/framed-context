#!/usr/bin/env python3
"""Analyze pre-test results: per-arm summaries + paired bootstrap CIs.

Pairing: runs sharing (task, rep) across two arms form a pair; we report the
mean per-run difference with a 95% bootstrap CI (10k resamples, stdlib only).
A CI excluding zero is the "statistically real" bar for this pre-test.
"""
import argparse
import json
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

ARMS = ["baseline", "text", "frames"]
METRICS = ["cost_usd", "output_tokens", "input_tokens", "num_turns", "wall_s"]


def load(path):
    rows = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    ok = [r for r in rows if r.get("ok")]
    err = [r for r in rows if not r.get("ok")]
    return ok, err


def summarize(rows):
    by_arm = defaultdict(list)
    for r in rows:
        by_arm[r["arm"]].append(r)
    print(f"{'arm':<9} {'n':>3} {'success':>8} {'mean $':>8} {'med $':>8} "
          f"{'$/success':>10} {'out tok':>9} {'turns':>6} {'wall s':>7}")
    for arm in ARMS:
        rs = by_arm.get(arm, [])
        if not rs:
            continue
        n = len(rs)
        succ = sum(1 for r in rs if r.get("success"))
        costs = [r["cost_usd"] for r in rs if r.get("cost_usd") is not None]
        total_cost = sum(costs)
        print(f"{arm:<9} {n:>3} {succ}/{n:>5} "
              f"{st.mean(costs):>8.3f} {st.median(costs):>8.3f} "
              f"{(total_cost / succ if succ else float('inf')):>10.3f} "
              f"{st.mean([r.get('output_tokens') or 0 for r in rs]):>9.0f} "
              f"{st.mean([r.get('num_turns') or 0 for r in rs]):>6.1f} "
              f"{st.mean([r.get('wall_s') or 0 for r in rs]):>7.0f}")
    return by_arm


def paired_diffs(rows, arm_a, arm_b, metric):
    idx = {(r["task"], r["rep"], r["arm"]): r for r in rows}
    diffs = []
    for (task, rep, arm), r in idx.items():
        if arm != arm_a:
            continue
        other = idx.get((task, rep, arm_b))
        if other and r.get(metric) is not None and other.get(metric) is not None:
            diffs.append(r[metric] - other[metric])
    return diffs


def bootstrap_ci(diffs, n_boot=10000, seed=7):
    rng = random.Random(seed)
    means = sorted(
        st.mean(rng.choices(diffs, k=len(diffs))) for _ in range(n_boot)
    )
    return means[int(0.025 * n_boot)], means[int(0.975 * n_boot)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(Path(__file__).parent / "work/results.jsonl"))
    args = ap.parse_args()
    ok, err = load(args.results)
    print(f"loaded {len(ok)} completed runs, {len(err)} errored\n")
    if err:
        for r in err[:10]:
            print(f"  ERR {r['run_id']}: {r.get('error', '?')[:100]}")
        print()
    if not ok:
        return
    summarize(ok)

    print("\npaired differences (mean, 95% bootstrap CI; negative = first arm cheaper/lower):")
    for a, b in [("frames", "baseline"), ("text", "baseline"), ("frames", "text")]:
        for metric in METRICS:
            diffs = paired_diffs(ok, a, b, metric)
            if len(diffs) < 3:
                continue
            lo, hi = bootstrap_ci(diffs)
            sig = " *" if (lo > 0 or hi < 0) else ""
            print(f"  {a} - {b:<9} {metric:<14} n={len(diffs):>3} "
                  f"mean={st.mean(diffs):>+9.3f}  CI=[{lo:>+9.3f}, {hi:>+9.3f}]{sig}")
        print()

    print("per-task success rates:")
    by_task = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for r in ok:
        cell = by_task[r["task"]][r["arm"]]
        cell[1] += 1
        cell[0] += 1 if r.get("success") else 0
    for task, arms in sorted(by_task.items()):
        cells = "  ".join(f"{a}={arms[a][0]}/{arms[a][1]}" for a in ARMS if a in arms)
        print(f"  {task:<28} {cells}")


if __name__ == "__main__":
    main()
