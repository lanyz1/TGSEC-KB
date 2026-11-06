#!/bin/bash
# 猎杀GPU · QUANTUMROOT猎杀法器 执行入口
# 用法: sh ./skills/gpu-hunter/HUNT.sh <关键词>
# 关键词: A100 / Jupyter / CUDA / Ray / GPUStack / streamlit / all

set -e
SKILL_DIR="./skills/gpu-hunter"
HUNT_DIR="$SKILL_DIR/hunt_gpu"
TARGET="${1:-all}"

echo "============================================"
echo "  猎杀GPU · QUANTUMROOT猎杀法器"
echo "  靶场: $TARGET"
echo "============================================"

# 初始化靶场
mkdir -p "$HUNT_DIR"/{csv,alive,creds,ssh_keys,exploits,roots,logs,screenshots,report}
cd "$HUNT_DIR"

# 读取skill配置
source "$SKILL_DIR/SKILL.md" 2>/dev/null || true

# 清理临时文件
rm -f /tmp/gpu_alive.txt /tmp/gpu_finger.txt /tmp/gpu_roots.txt \
      /tmp/exploit_results.txt /tmp/ssh_roots.txt /tmp/jupyter_unauth.txt

export FOFA_KEY="${FOFA_KEY:-$(grep -oP 'FOFA_KEY=\K[^ ]+' ~/.bashrc 2>/dev/null || echo '')}"
export QUAKE_KEY="${QUAKE_KEY:-$(grep -oP 'QUAKE_KEY=\K[^ ]+' ~/.bashrc 2>/dev/null || echo '')}"

# ========== Step 1: 测绘 ==========
echo "[*] Step1: FOFA/Quake 测绘 $TARGET..."

API_BASE="https://fofaapi.com/api/v1/search/all"

case "$TARGET" in
  A100|a100)
    QUERY='(body:"A100" || body:"NVIDIA A100" || body:"a100-sxm") && (port="22" || port="8888" || port="8501")'
    ;;
  Jupyter|jupyter)
    QUERY='body="Jupyter" || title="Jupyter" || body="/api/kernels"'
    ;;
  CUDA|cuda)
    QUERY='(body:"CUDA" || body:"nvidia-smi" || body:"GeForce RTX") && (port="22" || port="8888")'
    ;;
  Ray|ray)
    QUERY='(title:"Ray" || body:"Ray Dashboard") && (port="8265" || port="8888")'
    ;;
  GPUStack|gpushare)
    QUERY='body="gpu" && body="stack" && (port="30003" || port="3000")'
    ;;
  streamlit)
    QUERY='(body:"streamlit" || body="st.") && (port="8501" || port="8888")'
    ;;
  docker)
    QUERY='(body:"Docker" && body:"nvidia") && (port="2375" || port="2376")'
    ;;
  k8s|kubernetes)
    QUERY='body="kubernetes" && body="nvidia.com" && (port="10250" || port="6443")'
    ;;
  all)
    QUERY='("NVIDIA" || "CUDA" || "nvidia-smi" || "GeForce RTX" || "A100" || "H100") && (port="22" || port="8888" || port="6006" || port="8265" || port="8501" || port="3000")'
    ;;
  *)
    echo "[!] 未知目标: $TARGET"
    echo "支持: A100 / Jupyter / CUDA / Ray / GPUStack / streamlit / docker / k8s / all"
    exit 1
    ;;
esac

if [ -n "$FOFA_KEY" ]; then
  QB64=$(echo -n "$QUERY" | base64 -w0)
  curl -s --max-time 30 "$API_BASE?key=$FOFA_KEY&qbase64=$QB64&size=1000" \
    > "csv/${TARGET}_fofa.json" 2>/dev/null || true
  echo "[+] FOFA 测绘完成: $(wc -c < "csv/${TARGET}_fofa.json") bytes"
else
  echo "[!] FOFA_KEY 未配置，跳过测绘"
fi

# ========== Step 2: 目标池构建 ==========
echo "[*] Step2: 目标池构建..."
python3 - << 'PYEOF' 2>/dev/null
import json, glob, os

urls = set()
for f in glob.glob('csv/*.json'):
    try:
        d = json.load(open(f, encoding='utf-8', errors='ignore'))
        results = d.get('results', d.get('data', d.get('matches', [])))
        for r in results:
            if isinstance(r, list) and len(r) > 5:
                if r[5] and str(r[5]).startswith('http'):
                    urls.add(str(r[5]).strip())
                elif len(r) > 1 and r[0] and r[1]:
                    proto = r[2] if len(r) > 2 and r[2] else 'http'
                    urls.add(f'{proto}://{r[0]}:{r[1]}')
            elif isinstance(r, dict):
                ip = r.get('ip_str', r.get('host', ''))
                port = r.get('port', 0)
                if ip and port:
                    urls.add(f'http://{ip}:{port}')
    except: pass

with open('all_targets.txt', 'w') as f:
    for u in sorted(urls): f.write(u + '\n')
print(f"[*] 捕获 {len(urls)} 个目标")
PYEOF

# ========== Step 3: 存活探测 ==========
echo "[*] Step3: 存活探测 + 指纹识别..."
> /tmp/gpu_alive.txt
> /tmp/gpu_finger.txt

if [ -f all_targets.txt ]; then
  cat all_targets.txt | xargs -P 20 -I {} sh -c '
URL="{}"
BASE=$(echo "$URL" | sed -E "s|^(https?://[^/]+).*|\1|")
RESP=$(curl -s --max-time 6 --connect-timeout 3 -L -k -A "Mozilla/5.0" "$URL" 2>/dev/null)
[ -z "$RESP" ] && exit 0
[ $(echo "$RESP" | wc -c) -lt 100 ] && exit 0
echo "$BASE" >> /tmp/gpu_alive.txt
F=""
echo "$RESP" | grep -qiE "(jupyter|notebook)" && F="$F JUPYTER"
echo "$RESP" | grep -qiE "(tensorboard|tf)" && F="$F TENSORBOARD"
echo "$RESP" | grep -qiE "(ray|dask|mlflow)" && F="$F ML_PLATFORM"
echo "$RESP" | grep -qiE "(streamlit|gradio|fastapi)" && F="$F WEB_ML"
echo "$RESP" | grep -qiE "(docker|kubernetes)" && F="$F CONTAINER"
echo "$RESP" | grep -qiE "(grafana|prometheus)" && F="$F MONITOR"
echo "$URL" | grep -q ":8888" && F="$F P8888"
echo "$URL" | grep -q ":6006" && F="$F P6006"
echo "$URL" | grep -q ":8265" && F="$F P8265"
echo "$URL" | grep -q ":8501" && F="$F P8501"
[ -n "$F" ] && echo "$BASE |$F" >> /tmp/gpu_finger.txt
'
fi
echo "[+] 存活: $(wc -l < /tmp/gpu_alive.txt 2>/dev/null || echo 0), 指纹: $(wc -l < /tmp/gpu_finger.txt 2>/dev/null || echo 0)"

# ========== Step 4: CVE攻击链 ==========
echo "[*] Step4: CVE漏洞链攻击..."
echo "[*] Step4: SSH弱口爆破..."
# 爆破由OPERATOR手动执行，此处仅记录
echo "[*] Step5: ROOT提权路径（待OPERATOR确认已拿下入口后执行）"
echo "[*] Step6: 持久化部署（待OPERATOR确认ROOT后执行）"

echo ""
echo "============================================"
echo "  测绘完毕，待OPERATOR决策攻击路径"
echo "  存活目标: $(wc -l < /tmp/gpu_alive.txt 2>/dev/null || echo 0)"
echo "  指纹目标: $(wc -l < /tmp/gpu_finger.txt 2>/dev/null || echo 0)"
echo "============================================"
