# llama.cpp on Windows + NVIDIA (Blackwell/CUDA 13.x)

## 版本选择 (关键)

RTX 50xx (Blackwell, sm_120) 必须用 **CUDA 13.x 编译版** llama.cpp:
- ✅ `llama-b10233-bin-win-cuda-13.3-x64.zip` + `cudart-llama-bin-win-cuda-13.3-x64.zip`
- ❌ `...-win-cuda-12.4-x64.zip` — 能识别 GPU(`--list-devices` 显示正常),但推理输出是乱码/混合垃圾

GitHub releases 资产命名: `llama-b<build>-bin-win-cuda-<ver>-x64.zip` 和 `cudart-llama-bin-win-cuda-<ver>-x64.zip`。

## 解压顺序 (致命坑)

cudart zip 里**也含 `ggml.dll` 等引擎 DLL**。如果直接解压到主程序目录,会**覆盖**主包的正确 DLL → 之后所有模型输出随机 ASCII 乱码。

正确做法:
1. 解压引擎主包到新目录 (如 `bin\v13\`)
2. 从 cudart zip 只拷贝 3 个文件进同一目录: `cublas64_13.dll`、`cublasLt64_13.dll`、`cudart64_13.dll`

## Qwen3 思考模式 (空回复坑)

Qwen3 默认开思考模式:API 返回 `content: ""`,思考草稿在 `reasoning_content` 里,`finish_reason: "length"`。

**正确修复** — 每个请求里传:
```json
{"chat_template_kwargs": {"enable_thinking": false}}
```

试过无效的方式:
- 启动参数 `--chat-template-kwargs '{"enable_thinking":false}'` (git-bash 引号转义损坏)
- 环境变量 `LLAMA_ARG_CHAT_TEMPLATE_KWARGS` (未生效)
- 只有**请求级**参数稳定生效

## 启动命令 (已验证)

```bash
llama-server.exe -m D:\models\Qwen3-14B-Q4_K_M.gguf \
  --host 127.0.0.1 --port 8081 -ngl 99 -c 16384 --jinja
```

- `-ngl 99` = 全量进 GPU。验证: `nvidia-smi` 显存应涨到 ~8-12GB
- `--jinja` 用模型内置模板(比手动 `--chat-template chatml` 稳)
- 健康检查: `curl http://127.0.0.1:8081/health` → `{"status":"ok"}`
- 速度基线: 5080 + 14B Q4 = 120 t/s,首 token ~1s

## 显存预算 (16GB 卡)

| 模型 | 权重+上下文显存 |
|---|---|
| Qwen3-14B Q4 (8.4GB) | ~12.4GB |
| Qwen3-8B Q4 (~5GB) | ~7GB |
| GLM-4-9B Q4 (6.2GB) | ~8.4GB |

两个同时驻留 = 超 16GB → **一次只跑一个**,切换约 10s。

## 进程管理 (Windows)

- 每次新起 `llama-server` 不会自动清旧的 → 多个实例挤爆显存 (3个=15.5GB)
- 检查: `powershell "Get-Process llama-server"` 
- 按 PID 杀: `powershell "Stop-Process -Id <pid> -Force"`
- git-bash 里 `taskkill //F //PID` 参数会转义坏,别用

## 下载源 (中国网络)

- ModelScope 直连 ~39MB/s: `https://modelscope.cn/models/<org>/<repo>/resolve/master/<file>`
- hf-mirror ~2MB/s (慢但可用): `https://hf-mirror.com/<org>/<repo>/resolve/main/<file>`
- GitHub release 需走代理 (127.0.0.1:10808)
- GLM-4.5-Air 是 110B MoE,16GB 卡跑不动 — 甜点档实际是 GLM-4-9B-chat (9B)

## 老模型 GGUF 兼容警告

2024 年的旧转换 GGUF (如 bartowski/glm-4-9b-chat-GGUF) 在新版 llama.cpp 上会报:
`W load: special_eot_id is not in special_eog_ids - the tokenizer config may be incorrect`
→ 输出满屏 ASCII 标点乱码。优先用同代模型 (Qwen3 系列) 或新转换版本。
