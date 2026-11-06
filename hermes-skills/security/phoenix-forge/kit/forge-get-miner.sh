#!/bin/sh
# ============================================================
# PHOENIX-FORGE · 矿工获取（多源 fallback）
# 目标：拿到一个真实可用的 GPU 矿工二进制
#   - PRL/Pearl 系：PeakMiner（Kryptex 官方）
#   - 通用备份：XMRig（源码编译，任何机器都能出）
# 用法：sh forge-get-miner.sh [目标目录] [币种:prl|xmr]
# ============================================================
DEST="${1:-./miner}"; COIN="${2:-prl}"
mkdir -p "$DEST"
have() { command -v "$1" >/dev/null 2>&1; }

echo "[*] 矿工获取：dest=$DEST coin=$COIN"

# ---------- 通用：XMRig 源码编译（最稳，任何 Linux 都能出） ----------
get_xmrig() {
    have git || { echo "[!] 缺 git"; return 1; }
    have cmake || { echo "[!] 缺 cmake（apt install cmake）"; return 1; }
    have gcc || { echo "[!] 缺 gcc"; return 1; }
    TMP="/tmp/.xmrig.$$"
    echo "[*] 克隆 XMRig..."
    git clone --depth 1 https://github.com/xmrig/xmrig.git "$TMP" 2>/dev/null || return 1
    cd "$TMP" && mkdir -p build && cd build
    cmake .. -DCMAKE_BUILD_TYPE=Release -DWITH_HWLOC=OFF >/dev/null 2>&1 || return 1
    make -j"$(nproc 2>/dev/null || echo 2)" >/dev/null 2>&1 || return 1
    [ -f xmrig ] && { cp -f xmrig "$OLDPWD/$DEST/"; echo "[+] XMRig 编译完成: $DEST/xmrig"; cd "$OLDPWD"; rm -rf "$TMP"; return 0; }
    cd "$OLDPWD"; rm -rf "$TMP"; return 1
}

# ---------- PRL：PeakMiner（GitHub release 优先，失败 → 手动） ----------
get_pearl() {
    have curl || have wget || return 1
    for repo in "pearl-miner/peakminer" "KryptexGmbH/peakminer" "peakminer/peakminer"; do
        API="https://api.github.com/repos/$repo/releases/latest"
        JSON=$(curl -fsSL --connect-timeout 8 -m 25 "$API" 2>/dev/null)
        [ -z "$JSON" ] && continue
        URL=$(printf '%s' "$JSON" | grep -oE '"browser_download_url": *"[^"]+"' | head -1 | sed 's/.*: *"//; s/"$//')
        [ -z "$URL" ] && continue
        echo "[*] 发现: $URL"
        FN=$(basename "$URL")
        curl -fSL --connect-timeout 15 -m 300 "$URL" -o "$DEST/$FN" 2>/dev/null || continue
        case "$FN" in
            *.tar.gz|*.tgz) tar -xzf "$DEST/$FN" -C "$DEST" 2>/dev/null;;
            *.zip) have unzip && unzip -o "$DEST/$FN" -d "$DEST" >/dev/null 2>&1;;
        esac
        chmod +x "$DEST/"* 2>/dev/null
        echo "[+] 下载完成: $DEST/$FN"; return 0
    done
    return 1
}

case "$COIN" in
    prl) get_pearl && exit 0; echo "[!] PRL 自动获取失败，转 XMRig 备份"; get_xmrig && exit 0;;
    xmr) get_xmrig && exit 0;;
esac

echo ""
echo "[!] 自动获取未成功。手动方案："
echo "    ① XMRig 源码: https://github.com/xmrig/xmrig/releases"
echo "    ② 从已跑的机器 scp 二进制过来"
echo "    放入 $DEST/ 后运行: sh forge-deploy.sh --miner-bin $DEST/<二进制> ..."
exit 1
