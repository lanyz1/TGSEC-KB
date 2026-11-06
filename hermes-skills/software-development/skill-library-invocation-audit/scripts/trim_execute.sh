#!/usr/bin/env bash
# 技能库裁卡执行器：解析 → 备份 → 删 → 清单 → 重建 → 门禁
# 用法: trim_execute.sh cards.txt [outdir]
#   cards.txt 每行一个卡名（如 redteam-ssrf-detail-pack）或相对路径（security/foo）
#   outdir 默认 /root/.hermes/arsenal/trim_YYYYmmdd_HHMM
# 前置：cards.txt 必须来自 trim_scan.py 的人工判定 + 操作员点名，不要拿 use_count=0 直接喂。
set -u
LIST=${1:?usage: trim_execute.sh cards.txt [outdir]}
SKILLS=${SKILLS_ROOT:-/root/.hermes/skills}
ARS=${ARSENAL:-/root/.hermes/arsenal}
OUT=${2:-$ARS/trim_$(date +%Y%m%d_%H%M)}
mkdir -p "$OUT"

: > "$OUT/resolved.txt"
: > "$OUT/missing.txt"
while IFS= read -r line; do
  line=$(printf '%s' "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  [ -z "$line" ] && continue
  case "$line" in \#*) continue;; esac
  if [ -d "$SKILLS/$line" ]; then
    echo "$SKILLS/$line" >> "$OUT/resolved.txt"
  else
    hit=$(find "$SKILLS" -maxdepth 3 -type d -name "$line" -not -path '*/.curator_backups/*' 2>/dev/null | head -1)
    if [ -n "$hit" ]; then echo "$hit" >> "$OUT/resolved.txt"; else echo "MISS $line" >> "$OUT/missing.txt"; fi
  fi
done < "$LIST"
N=$(wc -l < "$OUT/resolved.txt" | tr -d ' ')
echo "resolved=$N missing=$(wc -l < "$OUT/missing.txt" | tr -d ' ') out=$OUT"
[ "$N" -eq 0 ] && { echo 'no card to remove'; exit 1; }

# 1) 备份（保留 skills 下相对路径，还原时就地 tar xzf）
tar czf "$OUT/cards_backup.tar.gz" -C "$SKILLS" $(sed "s#^$SKILLS/##" "$OUT/resolved.txt") || { echo 'backup FAILED, abort'; exit 1; }
ls -lh "$OUT/cards_backup.tar.gz"

# 2) 删
while IFS= read -r d; do rm -rf "$d" && echo "rm $d"; done < "$OUT/resolved.txt"

# 3) 清单：每张卡的 legacy 原件位置（删后仍在磁盘但不再进索引）
{
  echo "# 裁卡执行清单 $(date '+%F %T')"
  echo
  echo "- 删除 **$N** 张，备份 \`$OUT/cards_backup.tar.gz\`"
  echo "- 还原：\`tar xzf cards_backup.tar.gz -C $SKILLS\` 然后重跑 arsenal_build.py + post_rebuild_gate.py"
  echo "- 注意：\`skills.disabled\` 里仍留有已删卡名（无害；同名包重装会被自动停用）"
  echo
  echo '| 卡 | legacy 原件（纸面追溯，不进索引） |'
  echo '|---|---|'
  while IFS= read -r d; do
    n=$(basename "$d")
    l=$(find "$SKILLS" -path "*/references/legacy/$n.md" 2>/dev/null | head -1)
    echo "| \`$n\` | ${l:-—} |"
  done < "$OUT/resolved.txt"
} > "$OUT/TRIM-MANIFEST.md"
echo "manifest: $OUT/TRIM-MANIFEST.md"

# 4) 重建 + 门禁（绿时静默，红时退出码非 0）
python3 "$ARS/arsenal_build.py" | tail -2
python3 "$ARS/post_rebuild_gate.py"
