#!/usr/bin/env bash
# 验收分享包是否干净：卡数 / 自有 IP / 密钥字面量 / 归档 seed
# 用法：
#   bash scripts/verify_package_clean.sh <pkg.gpg> <passphrase_file> <expect_cards> <ip_regex> <literals_file>
# 例：
#   bash scripts/verify_package_clean.sh /root/arsenal-share/hermes-skills-*.tar.gz.gpg \
#        /root/arsenal-share/PASSPHRASE.txt 2204 '154\.219\.127\.' /root/audit/secret_literals.txt
# 输出末行：PKG_CLEAN 或 PKG_FAIL；退出码 0/1
set -uo pipefail

PKG=${1:?pkg.gpg}
PASSFILE=${2:?passphrase file}
EXPECT=${3:?expect card count}
IPRE=${4:-}
LITFILE=${5:-}

[ -f "$PKG" ] || { echo "FAIL: 包不存在 $PKG"; exit 1; }
[ -f "$PASSFILE" ] || { echo "FAIL: 口令文件不存在 $PASSFILE"; exit 1; }

T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
gpg -q --batch --passphrase-file "$PASSFILE" -d "$PKG" 2>/dev/null | tar xzf - -C "$T" || {
  echo "FAIL: 解密/解包失败"; exit 1; }

CARDS=$(find "$T" -name SKILL.md | wc -l | tr -d ' ')
IP_HITS=0
[ -n "$IPRE" ] && IP_HITS=$(grep -rlE "$IPRE" "$T" 2>/dev/null | wc -l | tr -d ' ')
LIT_HITS=0
if [ -n "$LITFILE" ] && [ -f "$LITFILE" ]; then
  LIT_HITS=$(grep -rlF -f "$LITFILE" "$T" 2>/dev/null | wc -l | tr -d ' ')
fi
SEED=$(python3 - "$T" <<'PY'
import json, sys, os
p = os.path.join(sys.argv[1], 'skills', '.disabled.json')
try:
    print(len(json.load(open(p))))
except Exception:
    print(0)
PY
)
BYTES=$(stat -c%s "$PKG")
SHA=$(sha256sum "$PKG" | cut -d' ' -f1)

echo "cards=$CARDS expect=$EXPECT ip_hits=$IP_HITS literal_hits=$LIT_HITS seed=$SEED"
echo "pkg=$PKG bytes=$BYTES"
echo "sha256=$SHA"

RC=0
[ "$CARDS" = "$EXPECT" ] || { echo "FAIL: 卡数 $CARDS != $EXPECT"; RC=1; }
[ "$IP_HITS" -eq 0 ] || { echo "FAIL: 自有 IP 命中 $IP_HITS 个文件"; RC=1; }
[ "$LIT_HITS" -eq 0 ] || { echo "FAIL: 密钥字面量命中 $LIT_HITS 个文件"; RC=1; }
[ "$SEED" -gt 0 ] || { echo "WARN: 包内无 .disabled.json（新机全 enabled，core96 会掉到 88/96）"; }
[ "$RC" -eq 0 ] && echo "PKG_CLEAN" || echo "PKG_FAIL"
exit $RC
