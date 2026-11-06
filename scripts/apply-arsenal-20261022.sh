#!/usr/bin/env bash
# 2026-10-22 技能库升级：2178 卡 → 2146 卡（去模板卡/停死卡/搬胖 refs/清缓存），并重建索引 + 过门禁。
# 幂等：重复跑不会删错东西；每一步都先判存在。
# 用法：bash scripts/apply-arsenal-20261022.sh [--no-purge]
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SK="${HERMES_SKILLS:-$HOME/.hermes/skills}"
AR="${ARSENAL_DIR:-$HOME/.hermes/arsenal}"
ARCHIVE="${ARCHIVE_DIR:-/root/archive}"
export ARSENAL_SKILLS="$SK" ARSENAL_DIR="$AR" ARSENAL_DB="$AR/arsenal.db"
STAMP="$(date +%Y%m%d-%H%M)"
BK="$AR/trim_$STAMP"
PURGE=1
[ "${1:-}" = "--no-purge" ] && PURGE=0

say() { printf '\n== %s\n' "$*"; }
# 新机器 bootstrap：安装位不存在或一张卡都没有时，先用仓里的伞形卡把库立起来，
# 否则后面的每一步都没得跑（2026-10-22 实测：干净机器直接 FATAL: 技能树不存在）。
mkdir -p "$HOME/.hermes"
if [ ! -d "$SK" ] || [ "$(find "$SK" -name SKILL.md 2>/dev/null | wc -l)" -eq 0 ]; then
  echo "[i] 安装位为空（$SK），先用仓库伞形卡 bootstrap"
  bash "$REPO/scripts/sync-hermes-skills.sh" || { echo "FATAL: bootstrap 失败"; exit 1; }
fi
[ -d "$SK" ] || { echo "FATAL: 技能树不存在：$SK"; exit 1; }
mkdir -p "$AR" "$BK"

say "0/6 安装检索栈到 $AR（仓库版覆盖本机版）"
for f in "$REPO"/tools/arsenal/*.py "$REPO"/tools/arsenal/*.json; do
  cp "$f" "$AR/$(basename "$f")"
  echo "  -> $AR/$(basename "$f")"
done
# 拷完自检：逐个比 md5。少一个文件后面验收命令就会 File not found（2026-10-22 案卷机就踩过：
# 只装了 build/gate/selftest，full_reachability_audit.py 一直没到位，说明里的验收藏了半个月）。
miss=0
for f in "$REPO"/tools/arsenal/*.py "$REPO"/tools/arsenal/*.json; do
  b="$(basename "$f")"
  if [ "$(md5sum "$f" | cut -d' ' -f1)" != "$(md5sum "$AR/$b" 2>/dev/null | cut -d' ' -f1)" ]; then
    echo "  !! 拷贝不一致：$b"; miss=$((miss+1))
  fi
done
[ "$miss" -eq 0 ] && echo "  校验：工具栈 $(ls "$REPO"/tools/arsenal/*.py "$REPO"/tools/arsenal/*.json | wc -l) 个文件全部到位（md5 一致）"
mkdir -p "$HOME/.hermes/scripts"
cp "$REPO/tools/arsenal/arsenal_keeper.py" "$HOME/.hermes/scripts/arsenal_keeper.py" 2>/dev/null || true

say "1/6 备份将被删除的卡到 $BK"
cd "$SK/security" || { echo "FATAL: $SK/security 不存在"; exit 1; }
mapfile -t DEL < <(ls -d redteam-*-detail-pack laravel-app-pentest 2>/dev/null)
if [ "${#DEL[@]}" -gt 0 ]; then
  tar czf "$BK/cards_backup_$STAMP.tar.gz" -C "$SK/security" "${DEL[@]}"
  printf '  %s\n' "${DEL[@]}" > "$BK/removed_cards.txt"
  echo "  待删 ${#DEL[@]} 张，备份 $(du -h "$BK/cards_backup_$STAMP.tar.gz" | cut -f1)"
else
  echo "  无待删卡（已升级过）"
fi

say "2/6 删除模板卡 + 重复卡"
[ "${#DEL[@]}" -gt 0 ] && { printf '%s\0' "${DEL[@]}" | xargs -0 rm -rf; echo "  已删 ${#DEL[@]} 张"; }
echo "  剩余 detail-pack: $(ls -d redteam-*-detail-pack 2>/dev/null | wc -l)"

say "3/6 胖卡 refs 搬出技能树：72stack-sec/references/h1-reports (46MB)"
if [ -d "$SK/security/72stack-sec/references/h1-reports" ]; then
  mkdir -p "$ARCHIVE"
  mv "$SK/security/72stack-sec/references/h1-reports" "$ARCHIVE/72stack-h1-reports"
  echo "  -> $ARCHIVE/72stack-h1-reports ($(find "$ARCHIVE/72stack-h1-reports" -type f | wc -l) 文件)"
else
  echo "  已搬过，跳过"
fi

say "4/6 停用 6 张本机跑不了的 bundled 卡（写入 skills.disabled）"
python3 - "$SK" <<'PY'
import sys, os, json, subprocess
add = ['apple-notes','apple-reminders','findmy','imessage','sdlc-review','teams-meeting-pipeline']
try:
    sys.path.insert(0, '/usr/local/lib/hermes-agent')
    from hermes_cli.config import load_config
    d = list(load_config().get('skills', {}).get('disabled') or [])
except Exception as e:
    print('  [跳过] 读不到 Hermes 配置（非 Hermes 环境属正常）：%s' % e); raise SystemExit(0)
miss = [x for x in add if x not in d]
if not miss:
    print('  已在 disabled 列表里，跳过'); raise SystemExit(0)
new = miss + d
p = subprocess.run(['hermes','config','set','skills.disabled', json.dumps(new)],
                   capture_output=True, text=True)
ok = p.returncode == 0
print('  %s %d 张 -> skills.disabled 共 %d' % ('已加' if ok else '失败', len(miss), len(new)))
if not ok:
    print('  请手工把这几个名字加进 ~/.hermes/config.yaml 的 skills.disabled：' + ' '.join(miss))
PY

if [ "$PURGE" = 1 ]; then
  say "5/6 清可再生的磁盘垃圾"
  if [ -d "$SK/.curator_backups" ]; then
    mapfile -t SNAP < <(ls -1d "$SK/.curator_backups"/2* 2>/dev/null)
    if [ "${#SNAP[@]}" -gt 1 ]; then
      printf '%s\0' "${SNAP[@]:0:$((${#SNAP[@]}-1))}" | xargs -0 rm -rf
      echo "  删旧周快照 $(( ${#SNAP[@]} - 1 )) 份，留最新 $(basename "${SNAP[-1]}")"
    fi
  fi
  rm -f "$AR"/arsenal.db.bak-* "$AR"/arsenal.findcache.pkl && echo "  删 db 迁移备份 + findcache"
else
  say "5/6 跳过磁盘清理（--no-purge）"
fi

say "6/6 重建索引 + 门禁"
DISK_N=$(find "$SK" -name SKILL.md | wc -l | tr -d ' ')
echo "  预检：本机 SKILL.md $DISK_N 张"
if [ "$DISK_N" -lt 1000 ]; then
  echo "  [i] 精简库/新克隆机。门禁会输出 portable 层级：基线按「本机有卡才计分」，"
  echo "      不适用条目逐条列在 facts 里，不再把缺卡误判成检索退化。"
  echo "      要 full 基线（案卷机 2146 卡）请先在案卷机跑 scripts/export-arsenal-library.sh 搬库。"
fi
[ -f "$AR/arsenal_build.py" ] || { echo "FATAL: $AR/arsenal_build.py 不存在"; exit 1; }
time python3 "$AR/arsenal_build.py"
python3 "$AR/post_rebuild_gate.py"
RC=$?
echo
python3 - "$AR/gate_last.json" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    print("  门禁状态文件读不到：%s" % sys.argv[1]); raise SystemExit(0)
tier, ok = d.get("tier", "?"), d.get("ok")
print("  索引 %s 卡 / 磁盘 %s 张 · tier=%s · 不适用基线 %s 条"
      % (d.get("total"), d.get("disk"), tier, d.get("skipped", 0)))
if ok and tier == "full":
    print("升级完成：全量库基线全绿（selftest / core96 / 三 phase 全量计分）。")
elif ok:
    print("升级完成（portable）：本机库不全，基线只按「本机有卡」的条目计分；full 基线需搬全量库。")
else:
    print("门禁未过（判的不是缺卡，是真问题）：看上面 ✗ 行；回滚见 docs/UPGRADE-20261022-ARSENAL.md §回滚")
PY
exit $RC
