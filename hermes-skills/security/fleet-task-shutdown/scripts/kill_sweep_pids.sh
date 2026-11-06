#!/bin/bash
# kill_sweep_pids.sh — 子孙树杀进程(停机收网用)
#
# 为什么不直接 pkill -f:
#   1) pkill -f 会命中自己的 exec shell(命令串里有目标字面量)= 自杀;
#   2) 只杀顶层进程,watch/sleep/curl 孩子会挂到 init 下继续跑。
#
# 本脚本三件事:
#   a) 先把自身 ancestry(本 shell -> ... -> 1) 收进白名单,永不杀;
#   b) 显式 PID + 族名正则 双路收目标,再递归展开全部子孙;
#   c) TERM -> 3s 复查 -> 幸存者 SIGKILL -> 再复查,全过程落日志。
#
# 用法(改 BODY 顶部两个变量即可):
#   EXPLICIT="583445 813818"                       # 摸底盘过的 PID
#   FAMILY_RE='watch631|vgld|govmn-clone|ipv4_addrconf'  # 族名正则
#   bash kill_sweep_pids.sh [DRY=1]
#
# 注意: kill 前该摘的 systemd 单元/keeper 目录已先摘(否则杀了会复活)。
set -u

EXPLICIT="__EXPLICIT_PIDS__"
FAMILY_RE='__FAMILY_REGEX__'
LOG="${LOG:-/root/stop_sweep/kill_sweep.log}"
mkdir -p "$(dirname "$LOG")"
: > "$LOG"
say(){ echo "$@" | tee -a "$LOG"; }

# ---- 自身血统白名单 ----
PROTECT=""
pid=$PPID
while [ "${pid:-0}" != "1" ] && [ -n "${pid:-}" ]; do
  PROTECT="$PROTECT $pid"
  pid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
  [ -z "$pid" ] && break
done
say "PROTECT(ancestry):$PROTECT $$"
PROTECT="$PROTECT $$"

all_children(){
  local parent=$1 c
  for c in $(ps -eo pid,ppid --no-headers | awk -v p="$parent" '$2==p{print $1}'); do
    echo "$c"; all_children "$c"
  done
}

# ---- 收目标 ----
TARGETS=""
for p in $EXPLICIT; do kill -0 "$p" 2>/dev/null && TARGETS="$TARGETS $p"; done
for p in $(ps -eo pid,cmd --no-headers | grep -E "$FAMILY_RE" | grep -v grep | awk '{print $1}'); do
  skip=0
  for k in $PROTECT; do [ "$p" = "$k" ] && skip=1; done
  case " $TARGETS " in *" $p "*) skip=1;; esac
  [ $skip -eq 0 ] && TARGETS="$TARGETS $p"
done

EXPANDED=""
for p in $TARGETS; do EXPANDED="$EXPANDED $p $(all_children "$p")"; done
TARGETS=$(echo $EXPANDED | tr ' ' '\n' | sort -un | tr '\n' ' ')

say "--- TARGETS:"
for p in $TARGETS; do
  ps -o pid,ppid,etime,cmd -p "$p" --no-headers 2>/dev/null | cut -c1-160 | tee -a "$LOG"
done

if [ "${1:-}" = "DRY=1" ]; then say "DRY run — 未杀"; exit 0; fi

# ---- TERM -> SIGKILL ----
say "--- SIGTERM"
for p in $TARGETS; do kill -TERM "$p" 2>/dev/null; done
sleep 3
LEFT=""
for p in $TARGETS; do kill -0 "$p" 2>/dev/null && LEFT="$LEFT $p"; done
say "survivors after TERM:$LEFT"
say "--- SIGKILL survivors"
for p in $LEFT; do kill -KILL "$p" 2>/dev/null; done
sleep 2
LEFT2=""
for p in $TARGETS; do kill -0 "$p" 2>/dev/null && LEFT2="$LEFT2 $p"; done
say "survivors after KILL:$LEFT2"
[ -z "$LEFT2" ] && say "OK: survivor=0" || say "WARN: 仍有存活,回 Phase 2 查新生源"
