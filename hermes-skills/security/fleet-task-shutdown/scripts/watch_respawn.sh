#!/bin/bash
# watch_respawn.sh — 杀完盯盘:判"本地自愈"还是"远程重投递"
#
# 用法: watch_respawn.sh <client路径> [unit名] [采样秒数] [间隔秒]
#   例: watch_respawn.sh /usr/bin/ipv4_addrconf vgld-48aae1dc 180 10
# 输出: 每次采样一行  ts bin=... unit=... dir=... proc=...
# 判读: 180s(覆盖一次远程补件周期)全 NO/none/inactive/none
#       = 本地无自愈源、窗口内也没被远程重投
# 注意: 进程匹配用 ps+awk(显式排除自身),不用 pgrep -f —— 会命中自己的命令行造成假阳
set -u

CLIENT=${1:?用法: watch_respawn.sh <client路径> [unit名] [秒数] [间隔]}
UNIT=${2:-}
SECS=${3:-180}
IV=${4:-10}
LOG=${LOG:-/root/stop_sweep/watch_respawn.log}
BASE=$(basename "$CLIENT")
END=$((SECONDS+SECS))
mkdir -p "$(dirname "$LOG")" 2>/dev/null
: > "$LOG"

snap(){
  ts=$(date -u +%H:%M:%S)
  if [ -e "$CLIENT" ]; then
    bin="YES($(stat -c %s "$CLIENT")B,$(stat -c %y "$CLIENT" | cut -c1-19))"
  else
    bin=NO
  fi
  if [ -n "$UNIT" ]; then
    unit=$(systemctl is-active "$UNIT" 2>/dev/null || echo unknown)
  else
    unit=n/a
  fi
  dir=$(ls -d /root/.cache/.*/ 2>/dev/null | tr '\n' ',')
  dir=${dir:-none}
  proc=$(ps -eo pid,cmd --no-headers 2>/dev/null \
         | grep -F "$BASE" | grep -v grep | grep -v 'awk -v b=' \
         | awk -v me="$$" '$1!=me {print $1}' | tr '\n' ',')
  echo "$ts bin=$bin unit=$unit dir=$dir proc=${proc:-none}" | tee -a "$LOG"
}

while [ $SECONDS -lt $END ]; do snap; sleep "$IV"; done
echo "=== 盯盘结束 (${SECS}s) ===" | tee -a "$LOG"
