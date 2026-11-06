#!/usr/bin/env bash
# Shrink a git repo for real: backup -> N filter-repo passes -> gc -> assertions -> (optional) force push + read-back.
#
# WHY: `git rm` + commit frees NOTHING. GitHub's size == the local pack, and every "deleted" blob is still
# reachable from history. Only a history rewrite moves the number. Measured on a 25.8k-file / 291 MiB repo:
# pass 1 = 24.9 s, pass 2 = 1.9 s, 291.08 -> 88.67 -> 52.17 MiB.
#
# DRY RUN (default) - works on the live repo, leaves a timestamped backup:
#   REPO=/root/MyRepo \
#   LISTS="/root/cases/delete_t1.txt /root/cases/delete_t2.txt" \
#   KEEP_GREPS='vuln-wiki.*\.pdf$|payloader|panda-dex-dumper' \
#   bash git_history_rewrite.sh
#
# On a THROWAWAY COPY first if the repo is precious (doubles as a validated, push-ready artifact):
#   cp -a /root/MyRepo /tmp/MyRepo-test   # then REPO=/tmp/MyRepo-test
#
# PUSH only after the numbers above look right AND the owner has said yes (rewrites every commit SHA):
#   PUSH=1 REMOTE=<EMAIL-REDACTED>:owner/repo.git BRANCH=master REPO=/root/MyRepo bash git_history_rewrite.sh
set -euo pipefail

REPO=${REPO:?set REPO=/path/to/repo}
LISTS=${LISTS:-}                 # space-separated paths-from-file lists; may be several (one per tier)
KEEP_GREPS=${KEEP_GREPS:-.}      # regex of paths you promised to spare - echoed after the rewrite
REMOTE=${REMOTE:-}
BRANCH=${BRANCH:-master}
PUSH=${PUSH:-0}
export PATH="$PATH:$HOME/.local/bin"   # uv tool install git-filter-repo lands here

command -v git-filter-repo >/dev/null 2>&1 || { echo "MISSING: uv tool install git-filter-repo"; exit 1; }
cd "$REPO"

if [ "$(git status --porcelain | wc -l)" != "0" ]; then
  echo "WORKTREE DIRTY - commit or stash first (filter-repo refuses otherwise):"
  git status --short | head
  exit 1
fi

if [ "$PUSH" = "1" ]; then
  # ---- push half: assumes the rewrite already ran and looked right ----
  [ -n "$REMOTE" ] || { echo "set REMOTE=<git url>"; exit 1; }
  git remote remove origin 2>/dev/null || true    # filter-repo strips origin; re-add is idempotent
  git remote add origin "$REMOTE"
  git push --force origin "$BRANCH"

  echo "=== read-back (the ONLY receipt that counts) ==="
  git ls-remote "$REMOTE" "$BRANCH"
  tmp=$(mktemp -d)
  git clone --quiet --depth 1 "$REMOTE" "$tmp/rc"
  ( cd "$tmp/rc"
    echo "remote HEAD   = $(git rev-parse HEAD)"
    echo "files         = $(git ls-files | wc -l)"
    echo "residual media= $(git -c core.quotePath=false ls-files | grep -cE '\.(png|jpg|jpeg|gif|mp4|mov|avi|webp|bmp)$' || true)"
    echo "kept by grep  = $(git -c core.quotePath=false ls-files | grep -cE "$KEEP_GREPS" || true)"
    du -sh .git )
  rm -rf "$tmp"
  echo
  echo "NOTE: api.github.com 'size' lags by minutes-hours - do NOT read the old value as failure."
  echo "NOTE: old commit SHAs stay dangling a while; every clone/CI/other profile must RE-CLONE (pull conflicts)."
  exit 0
fi

# ---- rewrite half ----
# validate the lists BEFORE copying hundreds of MB
[ -n "$LISTS" ] || { echo "set LISTS=<paths-from-file> [more...]"; exit 1; }
for f in $LISTS; do
  [ -f "$f" ] || { echo "list not found: $f"; exit 1; }
done

BAK="$REPO.bak-$(date +%Y%m%d-%H%M%S)"
echo "=== backup -> $BAK ==="
cp -a "$REPO" "$BAK"

BEFORE=$(git count-objects -vH | awk '/size-pack/{print $2" "$3}')
echo "=== BEFORE: size-pack $BEFORE ==="
git count-objects -vH | grep -E 'in-pack|size-pack'

for f in $LISTS; do
  echo "=== filter-repo pass: $f ($(wc -l < "$f") entries) ==="
  # --paths-from-file takes LITERAL paths (glob:/regex: prefixes optional); exact beats fighting --path-glob **/ semantics
  git filter-repo --force --invert-paths --paths-from-file "$f" 2>&1 | tail -3
done

# gc only after the LAST pass
git reflog expire --expire=now --all
git gc --prune=now --quiet

echo "=== AFTER ==="
git count-objects -vH | grep -E 'in-pack|size-pack'
echo "BEFORE size-pack $BEFORE"
du -sh "$REPO" "$REPO/.git"
echo "files=$(git ls-files | wc -l)"

echo "--- keep-list survival (every one of these must still be present) ---"
git -c core.quotePath=false ls-files | grep -E "$KEEP_GREPS" | sed 's/^/  KEEP /' | head -30
echo "--- biggest survivors (Tier-2 candidates) ---"
git -c core.quotePath=false ls-tree -r -l HEAD | sort -k4 -nr | head -8 | awk '{printf "  %10d  %s\n",$4,$5}'
echo
echo "NEXT: confirm the numbers + keep-list, then re-run with PUSH=1 REMOTE=<url>"
echo "ROLLBACK: rm -rf \"$REPO\" && mv \"$BAK\" \"$REPO\""
