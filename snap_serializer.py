#!/usr/bin/env python3
"""snap-serializer — condense a project or document set into one compact text
map that a coding agent reads once at session start.

  render [dir]   serialize a code project (tree, docs, configs, signatures,
                 git log) -> <dir>/.claude/snap-serializer/context.txt
  render [dir] --docs 'globs'   serialize the named documents in full (prose
                 mode), for archives whose value is text rather than code

Pure standard library, no dependencies. Measured to cut multi-question
session cost ~42% on unfamiliar repos and ~68% per question on large document
archives; see experiments/pretest/RESULTS.md for the full method and the
negative result for the pixel-frame encoding this tool used to ship.
"""
import argparse
import os
import re
import subprocess
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "dist", "build", "target", ".venv", "venv",
             "__pycache__", ".next", ".cache", "coverage", "vendor", ".claude"}
SIG_PATTERNS = {
    ".py": r"^\s*(def |class |[A-Z_]+ = )",
    ".js": r"^\s*(export |function |class |const [A-Za-z_]+ = (async )?\()",
    ".ts": r"^\s*(export |function |class |interface |type |enum )",
    ".tsx": r"^\s*(export |function |class |interface |type )",
    ".go": r"^(func |type |var |const )",
    ".rs": r"^\s*(pub |fn |struct |enum |trait |impl )",
    ".rb": r"^\s*(def |class |module )",
    ".java": r"^\s*(public |private |protected |class |interface )",
    ".swift": r"^\s*(func |class |struct |enum |protocol |extension )",
}
DOC_NAMES = {"readme.md", "claude.md", "architecture.md", "contributing.md"}
CONFIG_NAMES = {"package.json", "pyproject.toml", "cargo.toml", "go.mod",
                "makefile", "docker-compose.yml", "requirements.txt"}


def head(text, n):
    return text if len(text) <= n else text[:n] + " [truncated]"


def list_files(root):
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files"], capture_output=True,
                             text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return [root / p for p in out.stdout.splitlines()]
    except Exception:
        pass
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for f in filenames:
            if not f.startswith("."):
                files.append(Path(dirpath) / f)
    return files


def serialize(root, budget):
    root = Path(root).resolve()
    files = sorted(list_files(root))
    sections = [f"# Context snapshot: {root.name} ({len(files)} files)"]

    # compact tree: one line per directory
    bydir = {}
    for f in files:
        bydir.setdefault(str(f.parent.relative_to(root)), []).append(f.name)
    tree = ["## tree"]
    for d in sorted(bydir):
        tree.append(f"{d}/: " + " ".join(sorted(bydir[d])[:40]))
    sections.append(head("\n".join(tree), 6000))

    # docs
    for f in files:
        if f.name.lower() in DOC_NAMES and f.is_file():
            try:
                sections.append(f"## {f.relative_to(root)}\n"
                                + head(f.read_text(errors="replace"), 2500))
            except Exception:
                pass

    # configs
    for f in files:
        if f.name.lower() in CONFIG_NAMES and f.is_file():
            try:
                sections.append(f"## {f.relative_to(root)}\n"
                                + head(f.read_text(errors="replace"), 900))
            except Exception:
                pass

    # signatures
    sig = ["## signatures"]
    for f in files:
        pat = SIG_PATTERNS.get(f.suffix.lower())
        if not pat or not f.is_file():
            continue
        try:
            lines = f.read_text(errors="replace").splitlines()
        except Exception:
            continue
        hits = [ln.strip() for ln in lines if re.match(pat, ln)][:15]
        if hits:
            sig.append(f"@ {f.relative_to(root)}")
            sig.extend("  " + h for h in hits)
    sections.append("\n".join(sig))

    # git log
    try:
        log = subprocess.run(["git", "-C", str(root), "log", "--oneline", "-25"],
                             capture_output=True, text=True, timeout=10)
        if log.returncode == 0 and log.stdout.strip():
            sections.append("## git log (recent)\n" + log.stdout.strip())
    except Exception:
        pass

    text, used = [], 0
    for s in sections:
        if used + len(s) > budget:
            text.append(f"[context budget reached; {len(sections) - len(text)} "
                        f"sections dropped]")
            break
        text.append(s)
        used += len(s) + 2
    return "\n\n".join(text)


def serialize_docs(root, patterns, budget):
    """Docs mode: include the named files themselves in full, for prose
    projects where the code-shaped serializer would miss the content."""
    root = Path(root).resolve()
    files = []
    for pat in patterns:
        hits = sorted(root.glob(pat.strip()))
        if not hits:
            print(f"warning: --docs pattern {pat.strip()!r} matched nothing")
        files.extend(h for h in hits if h.is_file() and h not in files)
    sections = [f"# Documents: {root.name} ({len(files)} files)"]
    for f in files:
        try:
            sections.append(f"#### {f.relative_to(root)}\n"
                            + f.read_text(errors="replace"))
        except Exception as e:
            sections.append(f"#### {f.relative_to(root)} [unreadable: {e}]")
    text = "\n\n".join(sections)
    if budget and len(text) > budget:
        text = text[:budget] + "\n[--max-chars budget reached; content truncated]"
    return text


def cmd_render(args):
    root = Path(args.dir).resolve()
    outdir = Path(args.out) if args.out else root / ".claude" / "snap-serializer"
    outdir.mkdir(parents=True, exist_ok=True)
    if args.docs:
        text = serialize_docs(root, args.docs.split(","), args.max_chars)
    else:
        text = serialize(root, args.max_chars)
    ctx = outdir / "context.txt"
    ctx.write_text(text)
    print(f"serialized {len(text)} chars -> {ctx} (~{len(text) // 4} tokens)")
    print(f"LOAD: Read {ctx} at session start")


def main():
    ap = argparse.ArgumentParser(prog="snap-serializer")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render", help="serialize a project into context.txt")
    r.add_argument("dir", nargs="?", default=".")
    r.add_argument("--out", default=None,
                   help="output dir (default DIR/.claude/snap-serializer)")
    r.add_argument("--docs", default=None,
                   help="comma-separated globs: serialize these files in full "
                        "(prose mode) instead of the code-map serializer")
    r.add_argument("--max-chars", type=int, default=60000,
                   help="serializer budget; 0 = unlimited (use for docs mode)")
    r.set_defaults(func=cmd_render)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
