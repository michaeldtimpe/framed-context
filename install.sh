#!/bin/sh
# Install the loadcontext skill (snap-serializer) into Claude Code's user
# skill directory. Pure Python, no dependencies.
set -e
DEST="$HOME/.claude/skills/loadcontext"
mkdir -p "$DEST"
cp snap_serializer.py SKILL.md "$DEST/"
echo "installed to $DEST — use /loadcontext in Claude Code (new sessions)"
