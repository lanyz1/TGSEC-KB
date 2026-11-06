#!/bin/bash
# cve_scan.sh v2 — CVE 判型矩阵（只读无痕）
# 改进(v2): 精确版本 map / 编译链检测 / 容器能力 / sudo|docker 组 / 更多 AI 端口
echo "===== CVE 判型矩阵 v2 ====="
echo "--- 指纹 ---"
UNAME=$(uname -r); echo "kernel: $UNAME"
grep -E "^(NAME|VERSION)=" /etc/os-release 2>/dev/null
ID=$(grep -oP '^ID=\K.*' /etc/os-release 2>/dev/null || echo unknown)
echo "distro: $ID"
echo "--- 身份/权限 ---"
id
echo "groups: $(id -ng)"
echo "cap_eff: $(grep CapEff /proc/self/status 2>/dev/null | awk '{print $2}')"
echo "sudo version: $(sudo -V 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo none)"
echo "--- 编译链（决定能否本地搓 EXP） ---"
for C in cc gcc clang tcc; do command -v $C >/dev/null 2>&1 && echo "  [OK] $C -> $(command -v $C)"; done
command -v make >/dev/null 2>&1 && echo "  [OK] make"
echo "--- 内核提权候选 ---"
K="${UNAME%%.*}"; KP="${UNAME#*.}"; KM="${KP%%.*}"
KV=$((K*100+KM))
# CVE-2024-1086: nf_tables 5.14 ≤ K < 6.6.patch(2)
if [ $KV -ge 514 ] && [ $KV -lt 606 ]; then echo "[!] CVE-2024-1086 (nf_tables) 候选  ($UNAME in 5.14-6.5)"; fi
# CVE-2024-0582: io_uring 5.10-6.6
if [ $KV -ge 510 ] && [ $KV -le 606 ]; then echo "[!] CVE-2024-0582 (io_uring) 候选"; fi
# CVE-2022-0847 DirtyPipe: 5.8 ≤ K < 5.16.11 / 5.15.<26
if [ $KV -ge 508 ] && [ $KV -le 515 ]; then echo "[!] CVE-2022-0847 (DirtyPipe 任意写) 候选"; fi
# nf_tables 老将 CVE-2023-32233: 5.14-6.3
if [ $KV -ge 514 ] && [ $KV -le 603 ]; then echo "[!] CVE-2023-32233 (nf_tables) 候选"; fi
# CVE-2023-0386 overlayfs-FUSE: 所有 <6.2(不含后期patch)
if [ $KV -ge 500 ] && [ $KV -lt 602 ]; then echo "[!] CVE-2023-0386 (overlayfs FUSE) 候选"; fi
echo "--- 发行版专属 ---"
case "$ID" in
  ubuntu)
    case "$UNAME" in
      *5.4.* ) echo "[!] CVE-2021-3493 (overlayfs, Ubuntu 20.04) 候选";;
      *5.15.*) echo "[!] CVE-2023-2640/32629 (overlayfs, Ubuntu 22.04) 候选";;
      *6.2.*|*6.5.*) echo "[!] CVE-2023-32629 (overlayfs, Ubuntu 23.04) 候选";;
    esac
    ;;
esac
echo "--- 用户态 ---"
GLIBC=$(ldd --version 2>/dev/null | head -1 | awk '{print $NF}')
echo "glibc: ${GLIBC:-none}"
case "$GLIBC" in
  2.3[4567]) echo "[!] CVE-2023-4911 (Looney Tunables) 候选";;
  2.2[0-9]|2.3[0-3]) echo "[!] CVE-2022-37706 或老 LD_PRELOAD 类候选";;
esac
SUDO=$(sudo -V 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
case "$SUDO" in
  1.8.*) echo "[!] CVE-2021-3156 (Baron Samedit) 候选";;
esac
[ -x /usr/bin/pkexec ] && echo "[?] pkexec 在 → 试 CVE-2021-4034 (PwnKit, 通杀大部分老机)"
echo "--- 容器/逃逸面 ---"
[ -S /var/run/docker.sock ] && echo "[!] docker.sock 挂载 → 一键宿主 root (docker run -v /:/host)"
id -nG 2>/dev/null | grep -qw docker && echo "[!] 在 docker 组 → docker run -v /:/host 免密码宿主 root"
id -nG 2>/dev/null | grep -qw sudo  && echo "[!] 在 sudo 组 → sudo -l 看白名单"
grep -qE "SYS_ADMIN" /proc/self/status 2>/dev/null && echo "[!] CapEff 含 SYS_ADMIN → cgroup/release_agent 逃逸"
for P in "8188:ComfyUI" "30003:GPUStack" "8265:Ray" "11434:Ollama" "8888:Jupyter" "2375:DockerAPI" "8080:GPUSTack-web"; do
  PORT=${P%%:*}; NAME=${P##*:}
  timeout 2 bash -c "echo > /dev/tcp/127.0.0.1/$PORT" 2>/dev/null && echo "[!] $NAME on :$PORT"
done
echo "===== 扫完 → kernel_lpe.sh run 打主武器 ====="
