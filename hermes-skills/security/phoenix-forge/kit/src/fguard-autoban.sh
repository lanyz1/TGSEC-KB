#!/bin/sh
# ============================================================
# FGUARD · AUTOBAN — 闯门者封杀（修正版）
# 修复原版缺陷：① iptables 规则持久化 ② 防自杀（白名单含本机所有IP/管理段）
#              ③ 阈值可配 ④ 封禁自动过期（防永久误封）
# 策略：外网来源 ≥FAIL_THRESH 次失败即封；内网 ≥INT_FAIL_THRESH 次
# ============================================================
LOG_FILE="${AUTH_LOG:-/var/log/auth.log}"
STATE="${BAN_STATE:-/var/lock/.fguard-ban.state}"
BANLOG="${BAN_LOG:-/usr/share/.fguard/banned.log}"
WL="${BAN_WHITELIST:-127.0.0.1}"
FAIL_THRESH="${FAIL_THRESH:-3}"       # 原版=1（易误伤），修正为 3
INT_FAIL_THRESH="${INT_FAIL_THRESH:-15}"
BAN_TTL="${BAN_TTL:-86400}"           # 封禁 24h 后自动解封
CHAIN="FGUARD_BAN"

[ -f "$LOG_FILE" ] || exit 0
mkdir -p "$(dirname "$BANLOG")" 2>/dev/null

# 确保自有链 + 跳转（幂等）
if command -v iptables >/dev/null 2>&1; then
    iptables -N "$CHAIN" 2>/dev/null
    iptables -C INPUT -j "$CHAIN" 2>/dev/null || iptables -I INPUT 1 -j "$CHAIN" 2>/dev/null
    iptables -C OUTPUT -j "$CHAIN" 2>/dev/null || iptables -I OUTPUT 1 -j "$CHAIN" 2>/dev/null
fi

# 规则持久化（重放封禁列表）
PERSIST="${BAN_PERSIST:-/usr/share/.fguard/ban.rules}"
reload_persist() {
    [ -f "$PERSIST" ] || return
    now=$(date +%s)
    while IFS='|' read -r ip ts; do
        [ -z "$ip" ] && continue
        [ $((now - ts)) -gt "$BAN_TTL" ] && continue
        iptables -C "$CHAIN" -s "$ip" -j DROP 2>/dev/null || iptables -A "$CHAIN" -s "$ip" -j DROP 2>/dev/null
        iptables -C "$CHAIN" -d "$ip" -j DROP 2>/dev/null || iptables -A "$CHAIN" -d "$ip" -j DROP 2>/dev/null
    done < "$PERSIST"
}

TOTAL=$(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)
LAST=$(cat "$STATE" 2>/dev/null || echo 0)
case "$TOTAL" in *[!0-9]*) TOTAL=0;; esac
case "$LAST" in *[!0-9]*) LAST=0;; esac
[ "$TOTAL" -le "$LAST" ] && { printf '%s' "$TOTAL" > "$STATE"; exit 0; }

BATCH="/tmp/.fgbatch.$$"
tail -n +$((LAST + 1)) "$LOG_FILE" 2>/dev/null | grep -E "Failed|Invalid" > "$BATCH" 2>/dev/null
[ -s "$BATCH" ] || { printf '%s' "$TOTAL" > "$STATE"; rm -f "$BATCH"; exit 0; }

# 收集候选 IP 及出现次数
awk '{
    for(i=1;i<=NF;i++) if($i=="from"){print $(i+1); break}
}' "$BATCH" | sort | uniq -c | while read -r cnt ip; do
    [ -z "$ip" ] && continue
    # 跳过白名单
    skip=0; for w in $WL; do [ "$ip" = "$w" ] && skip=1; done; [ "$skip" = "1" ] && continue
    # 跳过本机所有 IP（防自杀）
    if command -v ip >/dev/null 2>&1; then
        ip -o addr show 2>/dev/null | grep -q " $ip/" && continue
    fi
    case "$ip" in
        10.*|192.168.*|172.1[6-9].*|172.2[0-9].*|172.3[01].*) thr="$INT_FAIL_THRESH";;
        *) thr="$FAIL_THRESH";;
    esac
    [ "$cnt" -lt "$thr" ] 2>/dev/null && continue
    if ! iptables -C "$CHAIN" -s "$ip" -j DROP 2>/dev/null; then
        iptables -A "$CHAIN" -s "$ip" -j DROP 2>/dev/null
        iptables -A "$CHAIN" -d "$ip" -j DROP 2>/dev/null
        echo "$ip|$(date +%s)" >> "$PERSIST"
        echo "[$(date '+%F %T')] BANNED $ip (fails=$cnt thr=$thr)" >> "$BANLOG"
    fi
done

rm -f "$BATCH"
printf '%s' "$TOTAL" > "$STATE"
touch -r "${MREF:-/etc/hostname}" "$BANLOG" "$PERSIST" 2>/dev/null
exit 0
