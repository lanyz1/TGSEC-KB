#!/usr/bin/env bash
# Verify git remote WRITE access over SSH.
# Usage: bash git_push_access_check.sh [git@github.com:OWNER/REPO.git]
set -u

REMOTE="${1:-}"

echo "===== [1] remote SSH auth ====="
out=$(ssh -o StrictHostKeyChecking=accept-new -o BatchMode=yes -T <EMAIL-REDACTED> 2>&1 | head -3)
echo "$out"
case "$out" in
  *"successfully authenticated"*) echo "  -> key IS registered upstream" ;;
  *"Permission denied (publickey)"*) echo "  -> key NOT registered upstream (or wrong key offered); hand the .pub to the owner" ;;
  *"Host key verification failed"*)  echo "  -> known_hosts missing: ssh-keyscan github.com >> ~/.ssh/known_hosts" ;;
  *) echo "  -> inconclusive output above" ;;
esac
echo
echo "===== [2] local material ====="
ls -1 "$HOME/.ssh" 2>/dev/null || echo "  (no dot-ssh dir)"
command -v gh >/dev/null 2>&1 && { echo "-- gh auth --"; gh auth status 2>&1 | head -5; } || echo "  gh not installed (irrelevant for the SSH path)"
echo
if [ -z "$REMOTE" ]; then
  echo "===== [3] remote checks skipped (no remote arg) ====="
  echo "    re-run as: bash $0 git@github.com:OWNER/REPO.git"
  exit 0
fi

echo "===== [3] ls-remote $REMOTE ====="
git ls-remote "$REMOTE" HEAD 2>&1 | head -3

echo
echo "===== [4] dry-run push (writes nothing) ====="
if git rev-parse --git-dir >/dev/null 2>&1; then
  res=$(git push --dry-run "$REMOTE" HEAD:refs/heads/__access_probe 2>&1 | tail -5)
  echo "$res"
  case "$res" in
    *read-only*|*403*|*denied*) echo "  -> WRITE ACCESS MISSING: enable 'Allow write access' on the deploy key" ;;
    *up-to-date*|*"would be pushed"*|*"new branch"*) echo "  -> write access looks OK" ;;
  esac
else
  echo "  (cwd is not a git repo; run from the repo or skip)"
fi
