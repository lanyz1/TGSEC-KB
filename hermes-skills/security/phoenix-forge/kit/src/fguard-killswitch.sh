#!/bin/sh
# ============================================================
# FGUARD · KILLSWITCH — 排他杀伤链（「抢不走」）
# 职责：① 逐出未授权公钥（保留白名单） ② 封密码登录
#       ③ 竞品/对手进程清理 ④ 关键账户锁定
# 安全：先备份可回滚；白名单永不动；幂等
# ============================================================
BASE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$BASE/fguard.conf" ] && . "$BASE/fguard.conf"
AK="/root/.ssh/authorized_keys"
BAK="/root/.ssh/authorized_keys.fguard.bak"
LOG="$BASE/state.log"
note() { echo "$(date '+%F %T') notice: $*" >> "$LOG" 2>/dev/null; touch -r "${MREF:-/etc/hostname}" "$LOG" 2>/dev/null; }

# ① 逐出未授权公钥（保留 PUB1/PUB2 指纹）
if [ -f "$AK" ]; then
    cp -f "$AK" "$BAK" 2>/dev/null
    keep=""
    [ -n "$PUB1" ] && keep="$keep $(printf '%s' "$PUB1" | awk '{print $2}')"
    [ -n "$PUB2" ] && keep="$keep $(printf '%s' "$PUB2" | awk '{print $2}')"
    tmp="/tmp/.fgak.$$"; : > "$tmp"
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        fp=$(printf '%s' "$line" | awk '{print $2}')
        hit=0; for k in $keep; do [ "$fp" = "$k" ] && hit=1; done
        [ "$hit" = "1" ] && printf '%s\n' "$line" >> "$tmp"
    done < "$AK"
    if ! cmp -s "$tmp" "$AK" 2>/dev/null; then
        cat "$tmp" > "$AK"; chmod 600 "$AK" 2>/dev/null
        note "unauthorized-keys-evicted"
    fi
    rm -f "$tmp"
fi

# ② 封密码登录（sshd drop-in，首值覆盖）
if [ "$HARDEN" = "1" ] && command -v sshd >/dev/null 2>&1; then
    mkdir -p /etc/ssh/sshd_config.d 2>/dev/null
    CONF="/etc/ssh/sshd_config.d/00-${TAG:-fguard}.conf"
    cat > "$CONF" <<EOF
PasswordAuthentication no
PermitRootLogin prohibit-password
MaxAuthTries 3
EOF
    [ -n "$ALLOW_USERS" ] && echo "AllowUsers $ALLOW_USERS" >> "$CONF"
    sshd -t 2>/dev/null && { systemctl reload ssh 2>/dev/null || systemctl reload sshd 2>/dev/null; }
fi

# ③ 竞品/对手进程清理（COMPETITORS 空格分隔的进程名/路径关键字）
if [ -n "$COMPETITORS" ]; then
    for c in $COMPETITORS; do
        pkill -9 -f "$c" 2>/dev/null && note "competitor-killed:$c"
    done
fi

# ④ 关键账户锁定（LOCK_USERS 空格分隔）
if [ -n "$LOCK_USERS" ]; then
    for u in $LOCK_USERS; do
        [ "$u" = "root" ] && continue
        id "$u" >/dev/null 2>&1 && { passwd -l "$u" 2>/dev/null; note "user-locked:$u"; }
    done
fi
exit 0
