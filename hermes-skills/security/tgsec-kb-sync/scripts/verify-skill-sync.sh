#!/usr/bin/env bash
# 校验本地技能与仓库技能的一致性 —— 关键是方向:
#   仓库独有 > 0  => 没灌进来(真失败)
#   本地独有 > 0  => 私有增量(正常, 保留)
# 用法: bash verify-skill-sync.sh [仓库路径=/root/security-suite]
set -uo pipefail

REPO="${1:-/root/security-suite}"
SRC="$REPO/.claude/skills"
DST="${HERMES_SKILLS_DIR:-$HOME/.hermes/skills}/security"

if [ ! -d "$SRC" ]; then
  echo "[!] $SRC 不存在 —— 上游可能又搬了目录。先跑:"
  echo "    git -C $REPO ls-tree --name-only origin/master"
  exit 1
fi
[ -d "$DST" ] || { echo "[!] $DST 不存在"; exit 1; }

fail=0
for s in $(ls "$SRC"); do
  if [ ! -d "$DST/$s" ]; then
    printf '  %-34s [缺] 仓库有、本地无\n' "$s"; fail=$((fail+1)); continue
  fi
  d=$(diff -rq "$DST/$s" "$SRC/$s" 2>/dev/null)
  ro=$(printf '%s\n' "$d" | grep -c "^Only in $SRC")
  lo=$(printf '%s\n' "$d" | grep -c "^Only in $DST")
  printf '  %-34s 仓库独有=%-3s 本地独有=%-3s\n' "$s" "$ro" "$lo"
  [ "$ro" != "0" ] && fail=$((fail+1))
done

echo "------------------------------------------------"
echo "仓库技能 $(ls "$SRC" | wc -l) 张 | 本地技能 $(ls "$DST" | wc -l) 张"
if [ "$fail" = "0" ]; then
  echo "[✓] 同步完整（本地独有 = 私有增量，正常）"
else
  echo "[✗] $fail 张未同步进来 —— 检查同步脚本的 SRC= 是否指向 $SRC"
  exit 1
fi
