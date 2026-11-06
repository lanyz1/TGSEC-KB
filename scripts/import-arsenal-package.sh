#!/usr/bin/env bash
# 一条命令把加密分享包灌成可用技能库（含归档分层 seed），然后重建索引 + 过门禁。
# 用法：
#   bash scripts/import-arsenal-package.sh <hermes-skills-*.tar.gz.gpg> <PASSPHRASE.txt>
# 环境变量：
#   HERMES_SKILLS=/root/.hermes/skills   目标安装位（默认 $HOME/.hermes/skills）
#   BACKUP_DIR=/root                    旧库备份到 $BACKUP_DIR/skills.bak-<时间>
set -uo pipefail

PKG=${1:?用法: import-arsenal-package.sh <pkg.gpg> <passphrase_file>}
PASSFILE=${2:?缺少口令文件}
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SK="${HERMES_SKILLS:-$HOME/.hermes/skills}"
PARENT="$(dirname "$SK")"
BACKUP_DIR="${BACKUP_DIR:-$(dirname "$SK")}"
STAMP=$(date +%Y%m%d-%H%M%S)

[ -f "$PKG" ] || { echo "FATAL: 包不存在 $PKG"; exit 1; }
[ -f "$PASSFILE" ] || { echo "FATAL: 口令文件不存在 $PASSFILE"; exit 1; }
mkdir -p "$PARENT"

echo "== 0/4 校验包"
EXPECT_TMP=$(mktemp -d); trap 'rm -rf "$EXPECT_TMP"' EXIT
gpg -q --batch --passphrase-file "$PASSFILE" -d "$PKG" 2>/dev/null | tar xzf - -C "$EXPECT_TMP" || {
  echo "FATAL: 解密/解包失败（口令错或包损坏）"; exit 1; }
EXPECT=$(find "$EXPECT_TMP" -name SKILL.md | wc -l | tr -d ' ')
SEED=$(python3 -c "import json,sys;print(len(json.load(open('$EXPECT_TMP/skills/.disabled.json'))))" 2>/dev/null || echo 0)
echo "  包内 $EXPECT 张卡，归档分层 $SEED 条"
[ "$EXPECT" -gt 0 ] || { echo "FATAL: 包内没有 SKILL.md"; exit 1; }
if [ "$SEED" -eq 0 ]; then
  echo "  WARN: 包里没有 skills/.disabled.json —— 新机会把全库算 enabled，core96 会从 94/96 掉到 88/96"
fi

echo "== 1/4 备份现有安装位"
if [ -d "$SK" ] && [ "$(find "$SK" -name SKILL.md 2>/dev/null | wc -l)" -gt 0 ]; then
  BK="$BACKUP_DIR/skills.bak-$STAMP"
  mv "$SK" "$BK" && echo "  旧库 -> $BK（$(du -sh "$BK" | cut -f1)）"
else
  echo "  安装位为空，跳过备份"
fi

echo "== 2/4 解包到 $SK"
gpg -q --batch --passphrase-file "$PASSFILE" -d "$PKG" 2>/dev/null | tar xzf - -C "$PARENT" || {
  echo "FATAL: 解包失败"; exit 1; }
echo "  解出 $(find "$SK" -name SKILL.md | wc -l | tr -d ' ') 张卡"

echo "== 3/4 装检索栈 + 重建索引 + 门禁"
bash "$REPO/scripts/apply-arsenal-20261022.sh"
RC=$?

echo "== 4/4 结果"
python3 - "$HOME/.hermes/arsenal/gate_last.json" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    print("  读不到 gate_last.json"); raise SystemExit(0)
print("  total=%s disk=%s tier=%s skipped=%s ok=%s"
      % (d.get("total"), d.get("disk"), d.get("tier"), d.get("skipped"), d.get("ok")))
PY
exit $RC
