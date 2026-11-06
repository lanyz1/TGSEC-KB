#!/bin/bash
# kill_task_procs.sh — 停机杀进程(排除自身血统,防自杀)
# 用法:
#   DRY=1 bash kill_task_procs.sh                            # 先干跑,看会被杀的清单
#   PATTERNS='recv|watch|tunnel|fwd' bash kill_task_procs.sh # 自定义匹配
# 铁律: 先切重生源(cron.d / hermes jobs),再跑本脚本,否则 keeper 秒级复活。
set -u
PATTERNS="${PATTERNS:-spray|brute|keeper|watch|tunnel|relay|beacon|listener|campaign|blitz|enrich|revive|recv|fwd}"
DRY="${DRY:-0}"
SELF=$$
PPID_SELF=$(ps -o ppid= -p $$ 2>/dev/null | tr -d ' ')
SELFNAME=$(basename "$0")

mapfile -t LINES < <(ps -eo pid=,ppid=,cmd= | grep -E "$PATTERNS" | grep -v grep | grep -v "$SELFNAME")
k=0
for line in "${LINES[@]:-}"; do
  [ -z "$line" ] && continue
  pid=$(echo "$line" | awk '{print $1}')
  [ "$pid" = "$SELF" ] && continue
  [ "$pid" = "$PPID_SELF" ] && continue
  if [ "$DRY" = "1" ]; then
    echo "WOULD-KILL $line"
    continue
  fi
  if kill "$pid" 2>/dev/null; then
    k=$((k+1)); echo "KILLED $line"
  else
    echo "KILL-FAILED $line"
  fi
done
echo "killed=$k dry=$DRY"
if [ "$DRY" != "1" ]; then
  sleep 2
  echo "--- survivors ---"
  ps -eo pid=,cmd= | grep -E "$PATTERNS" | grep -v grep | grep -v "$SELFNAME" || echo "(none)"
fi
