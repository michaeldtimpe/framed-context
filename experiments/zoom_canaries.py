"""Crop each CANARY_* value from rendered frames and scale 4x for verification.

Usage: python3 zoom_canaries.py <tag> <prefix> <font> [--pack]

Locates targets via the corpus text but outputs ONLY images — no text is
printed, so the model still receives answers exclusively through pixels.
"""
import re
import sys

from PIL import Image

from render import CELLS, pack_text, wrap_text

tag, prefix, font_name = sys.argv[1], sys.argv[2], sys.argv[3]
pack = "--pack" in sys.argv
CW, CH = CELLS[font_name]
SIZE = 1568
COLS, ROWS = SIZE // CW, SIZE // CH

with open(f"context-{tag}.txt") as f:
    text = f.read()

if pack:
    stream = pack_text(text)
    lines = [stream[i : i + COLS] for i in range(0, len(stream), COLS)]
else:
    lines = wrap_text(text, COLS)

# find (frame, row, col_start, col_end) for every canary assignment
targets = []
joined = "\n".join(lines)
for row_i, line in enumerate(lines):
    for m in re.finditer(r"CANARY_\d\d=[^ ¶]*", line):
        targets.append((row_i // ROWS, row_i % ROWS, m.start(), m.end()))
        # packed values may spill onto the next rendered row
        if pack and m.end() == len(line) and row_i + 1 < len(lines):
            nxt = re.match(r"[A-Za-z0-9]+", lines[row_i + 1])
            if nxt and not line[m.start():].rstrip("¶").endswith("¶"):
                r2 = row_i + 1
                targets.append((r2 // ROWS, r2 % ROWS, 0, nxt.end()))

strips = []
for frame, row, c0, c1 in targets:
    img = Image.open(f"{prefix}-f{frame}.png")
    x0 = max(0, (c0 - 1) * CW)
    x1 = min(SIZE, (c1 + 1) * CW)
    crop = img.crop((x0, row * CH, x1, (row + 1) * CH))
    strips.append(crop.resize((crop.width * 4, crop.height * 4), Image.NEAREST))

total_h = sum(s.height + 8 for s in strips)
sheet = Image.new("L", (max(s.width for s in strips), total_h), 255)
y = 0
for s in strips:
    sheet.paste(s, (0, y))
    y += s.height + 8
out = f"canary_zoom-{tag}.png"
sheet.save(out)
print(f"wrote {out} ({sheet.width}x{sheet.height}, {len(strips)} strips)")
