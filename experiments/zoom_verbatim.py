"""Crop the rendered rows spanning each VERBATIM marker + its line, scale 3x.

Usage: python3 zoom_verbatim.py <tag> <prefix> <font> [--pack]
Outputs only images — no text printed.
"""
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

# rows from first VERBATIM marker through 3 rows past the last marker row
marker_rows = [i for i, ln in enumerate(lines) if "VERBATIM" in ln]
r0, r1 = min(marker_rows), min(max(marker_rows) + 4, len(lines))

strips = []
for row in range(r0, r1):
    frame = row // ROWS
    img = Image.open(f"{prefix}-f{frame}.png")
    crop = img.crop((0, (row % ROWS) * CH, SIZE, (row % ROWS + 1) * CH))
    strips.append(crop.resize((crop.width * 3, crop.height * 3), Image.NEAREST))

total_h = sum(s.height + 6 for s in strips)
sheet = Image.new("L", (strips[0].width, total_h), 255)
y = 0
for s in strips:
    sheet.paste(s, (0, y))
    y += s.height + 6
out = f"verbatim_zoom-{tag}.png"
sheet.save(out)
print(f"wrote {out} ({sheet.width}x{sheet.height}, rows {r0}-{r1})")
