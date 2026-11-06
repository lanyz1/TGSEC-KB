#!/usr/bin/env bash
# TGSEC-Qtzuu publish self-check: case file count, index head, dirty tree, local vs remote, pre-push guard.
# Usage: bash verify_publish.sh [/root/TGSEC-Qtzuu]
set -u
REPO="${1:-/root/TGSEC-Qtzuu}"
cd "$REPO" || { echo "no repo: $REPO"; exit 1; }

echo "== repo: $REPO"
echo "== actual case files: $(ls domains/*/case-lessons/*.md 2>/dev/null | wc -l)"
echo "== CASE-INDEX head:"
sed -n '1,14p' domains/CASE-INDEX.md
echo "== domain counts (heading vs files):"
for d in domains/*/case-lessons; do
  [ -d "$d" ] || continue
  name=$(basename "$(dirname "$d")")
  printf '   %-20s files=%s\n' "$name" "$(ls "$d"/*.md 2>/dev/null | wc -l)"
done
echo "== dirty files: $(git status --porcelain | wc -l)"
git status --porcelain | head -20

echo "== local  : $(git rev-parse --short HEAD)"
if git fetch -q origin 2>/dev/null; then
  echo "== remote : $(git rev-parse --short origin/master 2>/dev/null || echo 'n/a')"
else
  echo "== remote : fetch failed (offline?)"
fi

echo "== guard:"
if [ -f /root/tgsec-guard/scan_push.py ]; then
  python3 /root/tgsec-guard/scan_push.py "$REPO"
  echo "== guard exit=$?"
else
  echo "== guard script missing: /root/tgsec-guard/scan_push.py"
fi
