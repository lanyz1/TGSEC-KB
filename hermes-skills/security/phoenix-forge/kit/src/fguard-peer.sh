#!/bin/sh
# ============================================================
# FGUARD · PEER — 跨机互保（终极形态：A 看 B / B 看 A）
# 配置：PEER='user@host2:/usr/lib/.sysnode'
# 逻辑：心跳新鲜度检测（对端 state.log 时间戳）→ 异常则 SSH 远程拉起
# ============================================================
BASE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$BASE/fguard.conf" ] && . "$BASE/fguard.conf"
LOG="$BASE/state.log"
note() { echo "$(date '+%F %T') notice: $*" >> "$LOG" 2>/dev/null; touch -r "${MREF:-/etc/hostname}" "$LOG" 2>/dev/null; }

[ -z "$PEER" ] && exit 0
PHOST="${PEER%%:*}"
PDIR="${PEER##*:}"
[ "$PHOST" = "$PDIR" ] && PDIR="/usr/lib/.${TAG}"

# 取对端 state.log 最后修改时间（心跳新鲜度）
remote_ts=$(ssh -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=no "$PHOST" \
    "stat -c %Y '$PDIR/state.log' 2>/dev/null" 2>/dev/null)
[ -z "$remote_ts" ] && { note "peer: unreachable $PHOST → remote revive"; \
    ssh -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=no "$PHOST" \
        "setsid nohup '$PDIR/fguard-reviver' --loop >/dev/null 2>&1 & nohup /bin/sh '$PDIR/fguard-heal.sh' >/dev/null 2>&1 &" 2>/dev/null; exit 0; }

now=$(date +%s)
age=$((now - remote_ts))
# 心跳超过 15 分钟视为异常 → 远程拉起（带抖动）
if [ "$age" -gt 900 ]; then
    note "peer: stale heartbeat ${age}s → remote heal"
    ssh -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=no "$PHOST" \
        "nohup /bin/sh '$PDIR/fguard-heal.sh' >/dev/null 2>&1 &" 2>/dev/null
fi
exit 0
