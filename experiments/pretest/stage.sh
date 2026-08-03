#!/usr/bin/env bash
# Stage the pre-test onto the M5 and print next steps.
set -euo pipefail
HOST="${1:-m5}"
DEST="~/framed-context-pretest"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "==> rsyncing framed-context repo (incl. pretest) to $HOST:$DEST"
rsync -az --delete \
  --exclude '.git/' \
  --exclude '.env' \
  --exclude 'experiments/pretest/work*/' \
  --exclude '__pycache__/' \
  "$REPO_ROOT/" "$HOST:$DEST/"

# The runner clones task repos with git; local-path tasks need a git repo.
# NEVER -f here: .env (the API key) and work*/ must stay out of the snapshot,
# or every cloned workspace would hand the key to the agent under test.
# work*/ (not work/): round 2's raw records lived in work2/ and were wiped
# by the --delete above when this pattern only covered work/. Never again.
ssh "$HOST" "cd $DEST && git init -q 2>/dev/null; \
  grep -qx '.env' .gitignore 2>/dev/null || echo '.env' >> .gitignore; \
  grep -qx 'experiments/pretest/work*/' .gitignore 2>/dev/null || echo 'experiments/pretest/work*/' >> .gitignore; \
  git rm -r -q --cached .env 'experiments/pretest/work*' 2>/dev/null; \
  git add -A . 2>/dev/null; \
  git -c user.email=pretest@local -c user.name=pretest commit -qm snapshot -q 2>/dev/null; \
  git ls-files | grep -x '.env' && echo 'FATAL: .env is tracked in snapshot' && exit 1 || true"

# Generate the deterministic docs-mode corpora and make them clonable git repos.
for GEN in gen_corpus.py:corpus gen_corpus3.py:corpus3; do
  ssh "$HOST" "cd $DEST/experiments/pretest && python3 ${GEN%%:*} >/dev/null && \
    cd ${GEN##*:} && git init -q 2>/dev/null; git add -A . && \
    git -c user.email=pretest@local -c user.name=pretest commit -qm corpus 2>/dev/null; \
    echo '${GEN##*:} repo ready:' \$(git rev-parse --short HEAD)"
done

cat <<EOF

Staged. On the M5:

  ssh $HOST
  cd ${DEST}/experiments/pretest
  source ../../.env                         # dedicated capped pre-test key
  python3 runner.py --dry-run               # sanity-check the schedule
  python3 runner.py --only fc-q1 --replicates 1   # ~\$1 smoke test, all 3 arms
  python3 analyze.py

Full matrix (background, survives logout):
  nohup python3 runner.py --replicates 4 > run.log 2>&1 &
EOF
