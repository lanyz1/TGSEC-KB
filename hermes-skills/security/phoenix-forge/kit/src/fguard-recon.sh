#!/bin/sh
# ============================================================
# FGUARD · RECON — 四维差分雷达（进程/网络/文件/登录）
# 职责：仅变化时落案（静默期零噪音）；PID-无感命名
# ============================================================
BASE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$BASE/fguard.conf" ] && . "$BASE/fguard.conf"
SNAP="$BASE/.snap"
LOG="$BASE/recon.log"
TS=$(date '+%F %T')
mkdir -p "$SNAP"

FILTER="^$|kworker|kthread|rcu_|idle_|migration|cpuhp|ksoftirqd|sleep |cron|run-parts|systemd|dbus|grep|ps -eo|awk |sed |cat |touch |find |sh -c|/bin/sh "

# ① 进程差分
ps -eo pid,ppid,args --no-headers 2>/dev/null | awk '{print $2,$3,$4,$5}' | sort -u > "$SNAP/ps.cur"
if [ -f "$SNAP/ps.bak" ]; then
    NEW=$(comm -13 "$SNAP/ps.bak" "$SNAP/ps.cur" 2>/dev/null | grep -vE "$FILTER" | head -5)
    [ -n "$NEW" ] && echo "[$TS][proc] $NEW" >> "$LOG"
fi
cp -f "$SNAP/ps.cur" "$SNAP/ps.bak" 2>/dev/null

# ② 网络差分（新监听 + 新外连）
{ ss -tlnp 2>/dev/null | awk 'NR>1{print "L:"$4}'; ss -tn state established 2>/dev/null | awk 'NR>1{print "E:"$4"->"$5}'; } | grep -v "127.0.0.1" | sort -u > "$SNAP/net.cur"
if [ -f "$SNAP/net.bak" ]; then
    NEWNET=$(comm -13 "$SNAP/net.bak" "$SNAP/net.cur" 2>/dev/null | head -8)
    [ -n "$NEWNET" ] && echo "[$TS][net] $NEWNET" >> "$LOG"
fi
cp -f "$SNAP/net.cur" "$SNAP/net.bak" 2>/dev/null

# ③ 关键文件 hash
FILES="${WATCH_FILES:-/root/.ssh/authorized_keys /etc/passwd /etc/shadow /etc/sudoers /etc/crontab /etc/ssh/sshd_config}"
for f in $FILES; do [ -f "$f" ] && sha256sum "$f" 2>/dev/null; done > "$SNAP/files.cur"
if [ -f "$SNAP/files.bak" ]; then
    DIFF=$(diff "$SNAP/files.bak" "$SNAP/files.cur" 2>/dev/null | grep -E "^[<>]" | head -4)
    [ -n "$DIFF" ] && echo "[$TS][file] $DIFF" >> "$LOG"
fi
cp -f "$SNAP/files.cur" "$SNAP/files.bak" 2>/dev/null

# ④ 登录差分
tail -50 "$AUTH_LOG" 2>/dev/null | grep -E "Failed|Accepted" | tail -3 > "$SNAP/auth.cur" 2>/dev/null
: > "$SNAP/auth.cur" 2>/dev/null
tail -50 /var/log/auth.log 2>/dev/null | grep -E "Failed|Accepted" | tail -3 > "$SNAP/auth.cur" 2>/dev/null
if [ -f "$SNAP/auth.bak" ]; then
    NEWAUTH=$(comm -13 "$SNAP/auth.bak" "$SNAP/auth.cur" 2>/dev/null | head -3)
    [ -n "$NEWAUTH" ] && echo "[$TS][auth] $NEWAUTH" >> "$LOG"
fi
cp -f "$SNAP/auth.cur" "$SNAP/auth.bak" 2>/dev/null

touch -r "${MREF:-/etc/hostname}" "$LOG" "$SNAP"/* 2>/dev/null
exit 0
