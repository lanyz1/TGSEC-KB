#!/bin/bash
# 验分享包：卡数对不对 + 自有 IP / 已知密钥有没有漏出去。
# 用法: verify_package_clean.sh <pkg.tar.gz.gpg> <PASSPHRASE.txt> <期望卡数> [ip正则] [字面量表]
set -uo pipefail
PKG=${1:?pkg}
PF=${2:?passphrase file}
EXPECT=${3:?expected card count}
IPRE=${4:-'154\.219\.127\.'}
LITF=${5:-}
[ -f "$PKG" ] || { echo "NO_PKG $PKG"; exit 1; }
P=$(cat "$PF")
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
gpg -q --batch --passphrase "$P" -d "$PKG" 2>/dev/null | tar xzf - -C "$T" || { echo DEC_FAIL; exit 1; }

CARDS=$(find "$T" -name SKILL.md -type f | wc -l | tr -d ' ')
IP_HITS=$(grep -rlE "$IPRE" "$T" 2>/dev/null | wc -l | tr -d ' ')
LIT_HITS=0
if [ -n "$LITF" ] && [ -f "$LITF" ]; then
  LIT_HITS=$(grep -rlF -f <(grep -v '^#' "$LITF" | grep -v '^$') "$T" 2>/dev/null | wc -l | tr -d ' ')
fi
SEED=$(python3 -c "import json;print(len(json.load(open('$T/skills/.disabled.json'))))" 2>/dev/null || echo NA)

OK=1
[ "$CARDS" = "$EXPECT" ] || OK=0
[ "$IP_HITS" = "0" ] || OK=0
[ "$LIT_HITS" = "0" ] || OK=0

echo "cards=$CARDS expect=$EXPECT ip_hits=$IP_HITS literal_hits=$LIT_HITS seed=$SEED"
sha256sum "$PKG"
if [ "$OK" = "1" ]; then echo "PKG_CLEAN"; exit 0; else echo "PKG_DIRTY"; exit 2; fi
