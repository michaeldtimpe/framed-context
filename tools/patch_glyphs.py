"""Patch confusable glyphs in Spleen BDFs and rebuild the PIL bitmap fonts.

Empirical basis (canary experiments, 2026-07-21): raw-read errors at 6x12/8x16
concentrate in S/5, U/V, and G/6. Patches make S round everywhere 5 is
angular, V converge to a point where U has a flat bowl, and 6 open with a
diagonal where G has a flat top and full left wall.
"""
import re
import sys
from pathlib import Path

from PIL import BdfFontFile

SRC = Path("fonts/spleen-2.1.0")

PATCHES = {
    "6x12": {
        "S": "00 70 88 80 70 08 08 88 70 00 00 00",
        "V": "00 88 88 88 88 88 50 50 20 00 00 00",
        "6": "00 30 40 80 F0 88 88 88 70 00 00 00",
    },
    "8x16": {
        "S": "00 00 3C 66 60 60 3C 06 06 06 66 3C 00 00 00 00",
        "6": "00 00 1C 30 60 C0 FC C6 C6 C6 C6 7C 00 00 00 00",
    },
}


def patch(name, targets):
    src = (SRC / f"spleen-{name}.bdf").read_text()
    for ch, hexrows in targets.items():
        rows = hexrows.split()
        pat = rf"(STARTCHAR [^\n]*\nENCODING {ord(ch)}\n(?:[^\n]*\n)*?BITMAP\n)(?:[0-9A-Fa-f]+\n)+(ENDCHAR)"
        new = None
        def repl(m):
            nonlocal new
            new = m.group(1) + "\n".join(rows) + "\n" + m.group(2)
            return new
        src, n = re.subn(pat, repl, src, count=1)
        if n != 1:
            sys.exit(f"failed to patch {ch!r} in {name}")
        print(f"patched {ch!r} in {name}")
    out = Path(f"fonts/spleen-{name}-patched.bdf")
    out.write_text(src)
    with open(out, "rb") as fp:
        font = BdfFontFile.BdfFontFile(fp)
    for dest in [Path("fonts"), Path.home() / ".claude/skills/loadcontext/fonts"]:
        font.save(str(dest / f"spleen-{name}"))
        print(f"rebuilt {dest}/spleen-{name}.pil")


for name, targets in PATCHES.items():
    patch(name, targets)
