#!/usr/bin/env python3
"""Three-arm pre-test runner for framed-context.

Arms:
  baseline - stock headless Claude Code, no preloaded context
  text     - snapctx serialized context injected as plain context.txt
  frames   - snapctx pixel-font PNG frames (+ context.txt sidecar, as shipped)

Each run: fresh clone -> arm prep -> `claude -p` headless -> usage capture -> score.
Results append to results.jsonl (idempotent: completed run ids are skipped, so
the runner is resumable). Raw claude JSON is kept per-run for audit.

Usage:
  python3 runner.py --tasks tasks.json --replicates 4          # full matrix
  python3 runner.py --tasks tasks.json --dry-run               # print schedule
  python3 runner.py --tasks tasks.json --only fc-q1 --arms frames
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ["baseline", "text", "frames"]

FRAMES_PREFIX = (
    "First, load the condensed project context: use the Read tool on each PNG "
    "frame in .claude/snapctx/ (pixel-font renderings of the project map — file "
    "tree, docs, signatures, git log). The identical text exists in "
    ".claude/snapctx/context.txt for exact grep lookups. Then complete this "
    "task:\n\n"
)
TEXT_PREFIX = (
    "First, read the condensed project context in .claude/snapctx/context.txt "
    "(project map — file tree, docs, signatures, git log). Then complete this "
    "task:\n\n"
)


def sh(cmd, cwd=None, env=None, timeout=None, capture=True):
    return subprocess.run(
        cmd, cwd=cwd, env=env, timeout=timeout,
        capture_output=capture, text=True,
    )


def find_snapctx():
    for c in [HERE.parent.parent / "snapctx.py",
              Path.home() / ".claude/skills/loadcontext/snapctx.py"]:
        if c.exists():
            return c
    sys.exit("snapctx.py not found (looked in repo root and ~/.claude/skills/loadcontext)")


def build_schedule(tasks, arms, replicates):
    """Interleaved schedule: arm order rotates per (replicate, task) so no arm
    systematically runs earlier in the day than another."""
    sched = []
    for rep in range(replicates):
        for ti, task in enumerate(tasks):
            rot = (rep + ti) % len(arms)
            for arm in arms[rot:] + arms[:rot]:
                sched.append((task, arm, rep))
    return sched


def prepare_workspace(task, arm, run_dir, mirrors, snapctx):
    repo_src = task["repo"]
    if re.match(r"^(https?|git|ssh)://|^git@", repo_src):
        mirror = mirrors / re.sub(r"[^A-Za-z0-9._-]", "_", repo_src)
        if not mirror.exists():
            r = sh(["git", "clone", "--mirror", repo_src, str(mirror)])
            if r.returncode != 0:
                raise RuntimeError(f"mirror clone failed: {r.stderr[-500:]}")
        repo_src = str(mirror)
    elif not os.path.isabs(repo_src):
        repo_src = str((HERE / repo_src).resolve())
    workspace = run_dir / "repo"
    r = sh(["git", "clone", "--quiet", repo_src, str(workspace)])
    if r.returncode != 0:
        raise RuntimeError(f"clone failed: {r.stderr[-500:]}")
    if task.get("ref"):
        r = sh(["git", "checkout", "--quiet", task["ref"]], cwd=workspace)
        if r.returncode != 0:
            raise RuntimeError(f"checkout {task['ref']} failed: {r.stderr[-500:]}")

    if arm in ("text", "frames"):
        cmd = [sys.executable, str(snapctx), "render", str(workspace)]
        cmd += task.get("render_args", [])
        r = sh(cmd, timeout=300)
        if r.returncode != 0:
            raise RuntimeError(f"snapctx render failed: {r.stderr[-800:]}")
        snapdir = workspace / ".claude/snapctx"
        if not snapdir.exists():
            raise RuntimeError("render produced no .claude/snapctx")
        if arm == "text":
            for png in snapdir.glob("*.png"):
                png.unlink()
    return workspace


def isolated_config(workdir):
    """Pristine Claude Code config so the user's global CLAUDE.md / skills
    (which reference the frames!) can't contaminate any arm."""
    cfg = workdir / "claude-config"
    cfg.mkdir(parents=True, exist_ok=True)
    state = cfg / ".claude.json"
    if not state.exists():
        state.write_text(json.dumps({"hasCompletedOnboarding": True}))
    return cfg


def run_claude(prompt, workspace, cfg_dir, model, max_turns, timeout_s):
    env = dict(os.environ)
    env["CLAUDE_CONFIG_DIR"] = str(cfg_dir)
    env.pop("CLAUDECODE", None)
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "json",
        "--model", model,
        "--max-turns", str(max_turns),
        "--dangerously-skip-permissions",
    ]
    t0 = time.time()
    try:
        r = sh(cmd, cwd=workspace, env=env, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return None, time.time() - t0, "timeout"
    wall = time.time() - t0
    if r.returncode != 0 and not r.stdout.strip():
        return None, wall, f"exit {r.returncode}: {r.stderr[-500:]}"
    try:
        return json.loads(r.stdout), wall, None
    except json.JSONDecodeError:
        return None, wall, f"unparseable output: {r.stdout[-300:]}"


def score(task, workspace, result_text):
    """Returns (passed, detail) — detail is recorded so a scoring failure is
    always diagnosable from results.jsonl alone."""
    check = task["check"]
    if check["type"] == "regex":
        passed = bool(re.search(check["pattern"], result_text or "",
                                re.IGNORECASE | re.DOTALL))
        return passed, "regex"
    if check["type"] == "command":
        rf = workspace / ".pretest_result.txt"
        rf.write_text(result_text or "")
        env = dict(os.environ, RESULT_FILE=str(rf), PRETEST_DIR=str(HERE))
        r = sh(["bash", "-c", check["cmd"]], cwd=workspace, env=env, timeout=600)
        detail = (r.stdout + r.stderr).strip()[-300:]
        return r.returncode == 0, f"rc={r.returncode} {detail}"
    raise ValueError(f"unknown check type {check['type']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default=str(HERE / "tasks.json"))
    ap.add_argument("--replicates", type=int, default=4)
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--only", help="comma-separated task ids")
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--max-turns", type=int, default=40)
    ap.add_argument("--timeout", type=int, default=1500, help="seconds per run")
    ap.add_argument("--workdir", default=str(HERE / "work"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set — refusing to run (billing must "
                 "land on the dedicated pre-test key, not a login).")

    tasks = [t for t in json.loads(Path(args.tasks).read_text())
             if not t.get("disabled")]
    if args.only:
        keep = set(args.only.split(","))
        tasks = [t for t in tasks if t["id"] in keep]
    arms = args.arms.split(",")
    workdir = Path(args.workdir).resolve()
    (workdir / "runs").mkdir(parents=True, exist_ok=True)
    mirrors = workdir / "mirrors"
    mirrors.mkdir(exist_ok=True)
    snapctx = find_snapctx()
    results_path = workdir / "results.jsonl"

    done = set()
    if results_path.exists():
        for line in results_path.read_text().splitlines():
            try:
                done.add(json.loads(line)["run_id"])
            except (json.JSONDecodeError, KeyError):
                pass

    sched = build_schedule(tasks, arms, args.replicates)
    print(f"schedule: {len(sched)} runs ({len(tasks)} tasks x {len(arms)} arms "
          f"x {args.replicates} reps), {len(done)} already done, model={args.model}")
    if args.dry_run:
        for task, arm, rep in sched:
            rid = f"{task['id']}__{arm}__r{rep}"
            print(("SKIP " if rid in done else "RUN  ") + rid)
        return

    cfg_dir = isolated_config(workdir)
    for i, (task, arm, rep) in enumerate(sched):
        run_id = f"{task['id']}__{arm}__r{rep}"
        if run_id in done:
            continue
        print(f"[{i+1}/{len(sched)}] {run_id} ...", flush=True)
        run_dir = workdir / "runs" / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True)
        rec = {"run_id": run_id, "task": task["id"], "arm": arm, "rep": rep,
               "model": args.model, "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
        try:
            workspace = prepare_workspace(task, arm, run_dir, mirrors, snapctx)
            prefix = {"baseline": "", "text": TEXT_PREFIX,
                      "frames": FRAMES_PREFIX}[arm]
            prefix = task.get("prefix_override", {}).get(arm, prefix)
            out, wall, err = run_claude(prefix + task["prompt"], workspace,
                                        cfg_dir, args.model, args.max_turns,
                                        args.timeout)
            rec["wall_s"] = round(wall, 1)
            if err or out is None:
                rec.update(ok=False, error=err or "no output")
            else:
                (run_dir / "claude.json").write_text(json.dumps(out, indent=1))
                usage = out.get("usage") or {}
                if not usage and isinstance(out.get("modelUsage"), dict):
                    # older CLI shape: per-model camelCase usage — aggregate it
                    agg = {}
                    for mu in out["modelUsage"].values():
                        for k, v in (mu or {}).items():
                            if isinstance(v, (int, float)):
                                agg[k] = agg.get(k, 0) + v
                    usage = {
                        "input_tokens": agg.get("inputTokens"),
                        "output_tokens": agg.get("outputTokens"),
                        "cache_read_input_tokens": agg.get("cacheReadInputTokens"),
                        "cache_creation_input_tokens": agg.get("cacheCreationInputTokens"),
                    }
                rec.update(
                    ok=True,
                    cost_usd=out.get("total_cost_usd", out.get("cost_usd")),
                    num_turns=out.get("num_turns"),
                    duration_ms=out.get("duration_ms"),
                    input_tokens=usage.get("input_tokens"),
                    output_tokens=usage.get("output_tokens"),
                    cache_read_tokens=usage.get("cache_read_input_tokens"),
                    cache_write_tokens=usage.get("cache_creation_input_tokens"),
                    is_error=out.get("is_error", False),
                )
                passed, detail = score(task, workspace, out.get("result", ""))
                rec["success"] = passed
                rec["check_detail"] = detail
        except Exception as e:  # keep the matrix running; record the failure
            rec.update(ok=False, error=f"{type(e).__name__}: {e}")
        finally:
            shutil.rmtree(run_dir / "repo", ignore_errors=True)
        with results_path.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        status = "PASS" if rec.get("success") else ("FAIL" if rec.get("ok") else "ERR ")
        print(f"    {status} cost=${rec.get('cost_usd') or 0:.3f} "
              f"turns={rec.get('num_turns')} err={rec.get('error', '')}")

    print(f"\ndone. results: {results_path}\nanalyze: python3 analyze.py --results {results_path}")


if __name__ == "__main__":
    main()
