#!/bin/sh
# Install the loadcontext skill into Claude Code's user skill directory.
set -e
DEST="$HOME/.claude/skills/loadcontext"
mkdir -p "$DEST/fonts"
cp snapctx.py SKILL.md "$DEST/"
cp fonts/spleen-6x12.pil fonts/spleen-6x12.pbm \
   fonts/spleen-8x16.pil fonts/spleen-8x16.pbm \
   fonts/SPLEEN-LICENSE "$DEST/fonts/"
python3 -c "import PIL" 2>/dev/null || echo "warning: Pillow not found — pip install pillow"
echo "installed to $DEST — use /loadcontext in Claude Code (new sessions)"
