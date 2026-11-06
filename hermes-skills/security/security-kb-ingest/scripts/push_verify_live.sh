#!/bin/bash
# TGSEC push 验收一键脚本 — 用法: bash push_verify_live.sh [repo_dir]（默认 /root/TGSEC-Qtzuu）
# 判据: 本地 HEAD == 远端 refs/heads/master == 远端 HEAD，且工作树 0 残留
REPO="${1:-/root/TGSEC-Qtzuu}"
cd "$REPO" || { echo "REPO_MISSING: $REPO"; exit 9; }
echo "== LOCAL HEAD =="
git rev-parse HEAD
git log --oneline -2
echo "== WORKTREE STATUS =="
git status -sb
echo "== REMOTE REFS (live ls-remote) =="
git ls-remote origin
echo "== EXIT_CODE=$? =="
