#!/usr/bin/env python3
"""snapctx — render condensed project context into pixel-font PNGs that a
vision-capable model reads as cheap, dense context.

Subcommands:
  render [dir]              serialize project -> packed 6x12 frames in <dir>/.claude/snapctx/
  verify <code> [--out DIR] check a SELFTEST reading against the stored value
  zoom <pattern> [--out DIR] crop rows matching regex from frames, 4x, -> zoom.png

Empirically validated (2026-07): Spleen 6x12 at 1568px reads near-perfectly;
errors concentrate in random strings on confusable pairs (S/5, U/V, l/1, O/0),
so the SELFTEST code and zoom escape hatch exist for exactly those cases.
"""
import argparse
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SKILL_DIR = Path(__file__).resolve().parent
CELLS = {"6x12": (6, 12), "8x16": (8, 16)}
FRAME = 1568
# no confusable glyphs: excludes s/5, u/v/w, o/0, l/1/i, g/q/9-alikes, and all
# uppercase (case pairs like K/k are themselves confusable at 6x12)
SELFTEST_ALPHABET = "acdefhkmnrt34679"

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


def pack_text(text):
    out = []
    for ln in text.split("\n"):
        ln = " ".join(ln.split())
        if ln:
            out.append(ln)
    return "¶".join(out)


def render_frames(text, outdir, font_name="6x12", max_frames=4):
    cw, ch = CELLS[font_name]
    font = ImageFont.load(str(SKILL_DIR / "fonts" / f"spleen-{font_name}.pil"))
    cols, rows = FRAME // cw, FRAME // ch

    code = "".join(random.SystemRandom().choice(SELFTEST_ALPHABET) for _ in range(8))
    stream = f"SELFTEST:{code} ¶" + pack_text(text)
    # bitmap font is latin-1 only; degrade anything else to '?'
    stream = stream.encode("latin-1", "replace").decode("latin-1")
    cap = cols * rows * max_frames
    if len(stream) > cap:
        stream = stream[:cap - 60] + "¶[frame budget reached; content truncated]"

    lines = [stream[i:i + cols] for i in range(0, len(stream), cols)]
    paths = []
    for n in range(0, len(lines), rows):
        chunk = lines[n:n + rows]
        img = Image.new("L", (FRAME, FRAME), 255)
        draw = ImageDraw.Draw(img)
        draw.fontmode = "1"
        for row, line in enumerate(chunk):
            draw.text((0, row * ch), line, font=font, fill=0)
        p = outdir / f"ctx-f{n // rows}.png"
        img.save(p, optimize=True)
        paths.append(p)

    (outdir / "selftest.json").write_text(json.dumps({"code": code}))
    (outdir / "context.txt").write_text(text)
    (outdir / "packed.txt").write_text(stream)
    return paths, stream


def cmd_render(args):
    root = Path(args.dir).resolve()
    outdir = Path(args.out) if args.out else root / ".claude" / "snapctx"
    outdir.mkdir(parents=True, exist_ok=True)
    text = serialize(root, args.max_chars)
    paths, stream = render_frames(text, outdir, args.font, args.max_frames)
    cw, ch = CELLS[args.font]
    img_tokens = len(paths) * (FRAME * FRAME) // 750
    print(f"serialized {len(text)} chars -> packed {len(stream)} chars "
          f"-> {len(paths)} frame(s), ~{img_tokens} image tokens "
          f"(vs ~{len(text) // 4} as text)")
    for p in paths:
        print(f"FRAME: {p}")
    print(f"sidecars: {outdir}/context.txt (grep for exact strings), selftest.json")
    print("Read each FRAME above, then run: snapctx.py verify <code-you-read> "
          f"--out {outdir}")


def cmd_verify(args):
    outdir = Path(args.out)
    want = json.loads((outdir / "selftest.json").read_text())["code"]
    if args.code == want:
        print("PASS — pixel text is legible on this model/pipeline")
    else:
        print(f"FAIL — you read {args.code!r}, actual differs. Frames may be "
              "downscaled or illegible; fall back to reading files as text.")


def cmd_zoom(args):
    outdir = Path(args.out)
    stream = (outdir / "packed.txt").read_text()
    font_name = args.font
    cw, ch = CELLS[font_name]
    cols, rows = FRAME // cw, FRAME // ch
    hits = [m.start() // cols for m in re.finditer(args.pattern, stream)]
    if not hits:
        print(f"no match for {args.pattern!r}")
        return
    want_rows = sorted({r + d for r in hits for d in (0, 1)})[:24]
    strips = []
    for row in want_rows:
        frame, fr = row // rows, row % rows
        p = outdir / f"ctx-f{frame}.png"
        if not p.exists():
            continue
        img = Image.open(p)
        crop = img.crop((0, fr * ch, FRAME, (fr + 1) * ch))
        strips.append(crop.resize((crop.width * 4, crop.height * 4), Image.NEAREST))
    sheet = Image.new("L", (strips[0].width, sum(s.height + 8 for s in strips)), 255)
    y = 0
    for s in strips:
        sheet.paste(s, (0, y))
        y += s.height + 8
    out = outdir / "zoom.png"
    sheet.save(out)
    print(f"ZOOM: {out} ({len(strips)} rows at 4x)")


def main():
    ap = argparse.ArgumentParser(prog="snapctx")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render")
    r.add_argument("dir", nargs="?", default=".")
    r.add_argument("--out", default=None)
    r.add_argument("--font", default="6x12", choices=CELLS)
    r.add_argument("--max-chars", type=int, default=60000)
    r.add_argument("--max-frames", type=int, default=4)
    r.set_defaults(func=cmd_render)

    v = sub.add_parser("verify")
    v.add_argument("code")
    v.add_argument("--out", required=True)
    v.set_defaults(func=cmd_verify)

    z = sub.add_parser("zoom")
    z.add_argument("pattern")
    z.add_argument("--out", required=True)
    z.add_argument("--font", default="6x12", choices=CELLS)
    z.set_defaults(func=cmd_zoom)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
