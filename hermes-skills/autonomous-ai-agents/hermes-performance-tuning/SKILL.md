---
name: hermes-performance-tuning
description: "压缩慢时用: Hermes压缩/辅助模型性能调优, 摘要模型换非推理快模型。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, compression, performance, tuning, aux-model, configuration]
---

# Hermes 上下文压缩与辅助模型性能调优

## 触发场景
- 用户抱怨 Hermes 压缩上下文"每次都特别慢"、`/compress` 卡很久
- 大上下文会话频繁压缩卡顿
- 想给辅助 LLM(压缩 / web_extract / 标题生成)指定更快模型

## 根因(99% 的情况)
Hermes 压缩 = 调**辅助 LLM** 生成历史摘要。`auxiliary.compression` 默认:

```yaml
provider: auto   # ← 继承主模型
model: ''
```

当主模型是 thinking/reasoning 模型(deepseek-reasoner、deepseek-v4-flash 等),摘要生成要跑完整思考链,且压缩输入通常是几万 token → 一次压缩几分钟。换非推理快模型立竿见影。

## 修复步骤(本次已验证)
```bash
hermes config set auxiliary.compression.provider <主模型同provider>   # 如 deepseek
hermes config set auxiliary.compression.model <非推理快模型>          # 如 deepseek-chat,同一把 key 零额外成本
hermes config set auxiliary.compression.context_length 128000
hermes config set auxiliary.compression.timeout 180
```
- **context_length 必须显式设**: 压缩可行性检查硬下限 64K(`MINIMUM_CONTEXT_LENGTH`,见 agent/conversation_compression.py),检测不到或低于下限会报错/自动降阈值
- timeout 默认 120s: 大输入单次调用可能超时 → 触发重试反而更慢,提到 180

## 生效时机
- **provider/model**: 每次压缩调用实时读 config → 下一次压缩立即生效
- **context_length**: 会话启动时读(agent/agent_init.py)→ 新会话生效

## 验证
```bash
hermes config get auxiliary.compression
# 应显示 provider: deepseek, model: deepseek-chat, timeout: 180
```

## 配置旋钮速查
| 键 | 默认 | 说明 |
|---|---|---|
| compression.threshold | 0.50 | <512K 窗口模型被 floor 到 0.75(raise-only),别指望小窗口模型 0.5 早触发 |
| compression.target_ratio | 0.20 | 提高→保留更多、总结更少→压缩更快,但上下文占用更多 |
| compression.protect_last_n | 20 | 尾部不压缩消息数 |
| compression.tail_mode | legacy | lean = 保留 token 少 3 倍,但多几次 summarizer 调用 |
| compression.proactive_prune_tokens | 0 | 确定性无 LLM 工具结果修剪(大窗口模型省 token) |
| compression.micro_compact | false | 每轮小压缩摊薄卡顿,但每轮 break prompt cache,费用涨,默认别开 |
| auxiliary.<task>.reasoning_effort | '' | 可给压缩设 none/low 进一步压速度(provider 支持时) |

## 坑
1. **profile 配置 ≠ 根配置**: `hermes config get/set` 解析的是**活跃 profile** 的 config.yaml(`profiles/<name>/config.yaml`),不是根目录 config.yaml。诊断前先确认在哪个 profile 下跑,读文件要看对路径。
2. **context_length 提示 "not a recognized key"**: `hermes config set` 会警告但照存;代码 `agent/agent_init.py` 用 `cfg_get("auxiliary","compression").get("context_length")` 真实读取,保留即可。
3. **凭据**: 压缩模型与主模型同 provider 时自动用同一凭据池。若根 .env 的 key 已失效但会话仍正常,说明 profile 有自己的 .env / 凭据池,以 profile 为准。
4. 压缩模型上下文 < 主模型阈值时,代码会自动把会话 threshold 降到 aux 上下文(保证压缩可用),触发点突然变化是正常行为,不是配置坏了。

## 代码地图(排查用)
- `agent/conversation_compression.py`: `compress_context()`、`check_compression_model_feasibility()`(64K 下限)
- `agent/auxiliary_client.py`: `get_text_auxiliary_client()`、`_resolve_task_provider_model()`(auto → 继承主模型的关键路径)
- `hermes_cli/config_defaults.py`: compression / auxiliary 全部默认值
- `agent/agent_init.py`: `_aux_compression_context_length_config` 读取
