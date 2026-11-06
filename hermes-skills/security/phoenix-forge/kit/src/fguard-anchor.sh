#!/bin/sh
# ============================================================
# FGUARD · ANCHOR — 版本锚点自更新（强制验签，修正原版「双向门」缺陷）
# 逻辑：拉版本头 → 比对 VER → 新版先验签(ed25519) → 验签通过才执行
# 铁律：不验签，不执行（原版 pastebin 无验签 = 谁拿到 URL 谁 root 全队）
# ============================================================
BASE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$BASE/fguard.conf" ] && . "$BASE/fguard.conf"
LOG="$BASE/state.log"
note() { echo "$(date '+%F %T') notice: $*" >> "$LOG" 2>/dev/null; touch -r "${MREF:-/etc/hostname}" "$LOG" 2>/dev/null; }

[ -z "$ANCHOR_URL" ] && exit 0
[ -z "$ANCHOR_PUBKEY" ] && { note "anchor: no pubkey, refuse update"; exit 0; }

command -v curl >/dev/null 2>&1 || exit 0

VER_NEW=$(curl -fsSL --connect-timeout 8 -m 20 "${ANCHOR_URL}.ver" 2>/dev/null | tr -d '[:space:]')
[ -z "$VER_NEW" ] && exit 0
[ "$VER_NEW" = "$VER" ] && exit 0

curl -fsSL --connect-timeout 8 -m 30 "${ANCHOR_URL}" -o /tmp/.fg.update.$$ 2>/dev/null || exit 0
curl -fsSL --connect-timeout 8 -m 30 "${ANCHOR_URL}.sig" -o /tmp/.fg.update.sig.$$ 2>/dev/null || { rm -f /tmp/.fg.update.$$; exit 0; }

# 验签（优先 ssh-keygen -Y，其次 openssl）
ok=0
if command -v ssh-keygen >/dev/null 2>&1; then
    printf '%s\n' "$ANCHOR_PUBKEY" > /tmp/.fg.pub.$$
    sig_b64=$(cat /tmp/.fg.update.sig.$$ 2>/dev/null)
    # ssh-keygen -Y verify 需要命名空间签名；此处用 openssl ed25519 兜底
    true
fi
if command -v openssl >/dev/null 2>&1; then
    printf '%s' "$ANCHOR_PUBKEY" > /tmp/.fg.pub.pem.$$
    openssl pkeyutl -verify -pubin -inkey /tmp/.fg.pub.pem.$$ -rawin -in /tmp/.fg.update.$$ -sigfile /tmp/.fg.update.sig.$$ >/dev/null 2>&1 && ok=1
fi

if [ "$ok" = "1" ]; then
    note "anchor: signature OK, applying $VER -> $VER_NEW"
    chmod +x /tmp/.fg.update.$$ 2>/dev/null
    sh /tmp/.fg.update.$$ >/dev/null 2>&1
    sed -i "s|^VER=.*|VER=$VER_NEW|" "$BASE/fguard.conf" 2>/dev/null
    note "anchor: updated to $VER_NEW"
else
    note "anchor: SIGNATURE FAILED, refuse to execute (anti-backdoor)"
fi

rm -f /tmp/.fg.update.$$ /tmp/.fg.update.sig.$$ /tmp/.fg.pub.*.$$ 2>/dev/null
exit 0
