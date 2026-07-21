"""Render text into pixel-font PNG frames for vision-model consumption.

Usage: python3 render.py <input.txt> <output_prefix> [--font 8x16] [--size 1568]
"""
import argparse
import os
from PIL import Image, ImageDraw, ImageFont

CELLS = {"5x8": (5, 8), "6x12": (6, 12), "8x16": (8, 16)}


def pack_text(text):
    """Fold the corpus into one continuous stream: newline runs become a
    single pilcrow, runs of spaces collapse, so every rendered row is full."""
    lines = [ln.rstrip() for ln in text.split("\n")]
    out = []
    for ln in lines:
        if ln:
            out.append(" ".join(ln.split()))
    return "¶".join(out)


def wrap_text(text, cols):
    lines = []
    for raw in text.split("\n"):
        if not raw:
            lines.append("")
            continue
        while len(raw) > cols:
            lines.append(raw[:cols])
            raw = raw[cols:]
        lines.append(raw)
    return lines


def render(text, prefix, font_name="8x16", size=1568, pack=False):
    cw, ch = CELLS[font_name]
    font = ImageFont.load(f"fonts/spleen-{font_name}.pil")
    cols, rows = size // cw, size // ch
    if pack:
        stream = pack_text(text)
        lines = [stream[i : i + cols] for i in range(0, len(stream), cols)]
    else:
        lines = wrap_text(text, cols)
    frames = [lines[i : i + rows] for i in range(0, len(lines), rows)]
    paths = []
    for n, frame_lines in enumerate(frames):
        img = Image.new("L", (size, size), 255)
        draw = ImageDraw.Draw(img)
        draw.fontmode = "1"
        for row, line in enumerate(frame_lines):
            draw.text((0, row * ch), line, font=font, fill=0)
        path = f"{prefix}-{font_name}-f{n}.png"
        img.save(path, optimize=True)
        paths.append(path)
        kb = os.path.getsize(path) / 1024
        print(f"{path}: {size}x{size}, {len(frame_lines)} rows x {cols} cols "
              f"(capacity {rows * cols} chars/frame), {kb:.0f} KB")
    return paths


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("prefix")
    ap.add_argument("--font", default="8x16", choices=CELLS)
    ap.add_argument("--size", type=int, default=1568)
    ap.add_argument("--pack", action="store_true")
    args = ap.parse_args()
    with open(args.input) as f:
        text = f.read()
    print(f"input: {len(text)} chars")
    render(text, args.prefix, args.font, args.size, args.pack)
