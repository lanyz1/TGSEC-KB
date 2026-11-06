<!-- archived from /root/.hermes/skills/security/hermes-config-tuning/SKILL.md on 2026-10-21 -->

---
name: hermes-config-tuning
description: >-
  测绘引擎·Use when tuning Hermes config behavior (compression pauses).
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/hermes-config-tuning`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/hermes-config-tuning/…')`，不要相对 `references/legacy/` 解析。

# hermes-config-tuning（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/hermes-config-tuning/`

溯源（仅标记）：`hermes/autonomous-ai-agents`

---

# Hermes 配置级诊断与调优（本机实测）

## When to Use

用户抱怨 Hermes 行为问题（"Summarizing thread 卡好久"、压缩慢、aux 模型失效等），需要配置级诊断时使用。通用文档/CLI 帮助见 bundled 的 `hermes-agent` 技能（不可改）；本技能记录本机实测的调优知识与排障路径。

配置文件：`$LOCALAPPDATA/hermes/profiles/<profile>/config.yaml`（本机 profile=sdsd）。改配置一律用 `hermes config set key value`，禁止手改 yaml。

## 症状 1：桌面端 "Summarizing thread..." 卡 1.5~3.5 分钟

**根因**：`compression.threshold`（默认 0.5）= 上下文百分比触发阈值。deepseek-v4-flash ctx=1,000,000 → 触发点 = **50 万 tokens**。压缩要把整个 ~50 万 token 对话发给辅助模型重总结，单次实测 84~204 秒（telemetry `total_duration_ms`: 112562~204609）。超长会话（1000+ 条消息）一天能触发多次。

**压缩用什么模型**：`auxiliary.compression.provider/model` 未配置时 → `auto` = 主模型。本机只有 `DEEPSEEK_API_KEY`，所以压缩 = deepseek-v4-flash 本身，无更快备用。

### 诊断步骤
1. `grep -A6 "^compression:" config.yaml` 看当前阈值
2. `grep -iE "compress|summariz" logs/agent.log | tail -25`：
   - `Preflight compression: ~N tokens >= threshold` = 触发点
   - `context compression done: ... total_duration_ms` = 单次耗时
   - `Auxiliary compression: using auto (主模型)` = 没配独立压缩模型
3. `.env` 只列键名判断可用模型：`grep -oE "^[A-Z_]+" .env | sort -u`

### 配置键（源码 agent_init.py / context_compressor.py 确认）
- `compression.enabled` (bool)
- `compression.threshold` (0~1 浮点，默认 0.5，乘 ctx = 触发 tokens)
- `compression.target_ratio` (默认 0.2，决定压缩后保留量/tail budget)
- `compression.threshold_tokens` (绝对 token 上限，与 threshold 取小)
- `compression.model_thresholds` (dict: 模型名子串→触发比例，最长匹配胜)
- `compression.protect_first_n` (默认3) / `protect_last_n` (默认20)
- 独立压缩模型：`auxiliary.compression.provider` / `auxiliary.compression.model`

### 调优杠杆（2026-08-12 本机实测落地）
- 1M ctx 模型阈值 0.5→0.3：触发点 50 万→30 万，**单次卡顿约减半**，但触发更频繁
- 落地/还原：`hermes config set compression.threshold 0.3` / `0.5`（一条命令可逆）
- **生效时机：新会话才读取**，已在跑的会话保持旧值 → 改完让用户开"新会话"验证
- 彻底不卡：`compression.enabled: false`（风险：超长会话 >1M ctx 会顶爆，工作流不推荐）
- 工作流建议：长任务（>1000 条消息）拆新会话，从根上避免涨到阈值

## 症状 2：会话标题生成失败（DeepSeek 400）

`errors.log`: `title_generator: Title generation failed: Error code: 400 - 'This response_format type is unavailable now'`。DeepSeek API 不支持该调用用的 response_format（json_schema）→ 标题生成失败，**不影响对话/压缩**。独立小问题，别当卡顿根因。

## 症状 3：hermes update 中断 → 每次 CLI 命令先弹恢复流程且失败（Windows）

**原因**：上次 `hermes update` 中途被打断（关窗口/断电）留下半成品。下次跑任何 `hermes` 命令自动触发补装恢复，但桌面端/CLI 正运行时 venv 文件被锁（`cryptography\...\_rust.pyd: Access is denied (os error 5)`）→ 恢复失败，报 "Could not auto-recover the interrupted install"。

**注意**：恢复失败**不影响命令本身**（如 `hermes config set` 照常写入配置，别被吓到，继续验证值）；反复跑命令会反复弹恢复流程（噪音，非新故障）。

**修复**：完全退出 Hermes 桌面端/CLI 后从独立终端执行：
```bash
cd /d "C:\Users\Administrator\AppData\Local\hermes\hermes-agent"
"C:\Users\Administrator\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" -m pip install -e ".[all]"
```
然后重启 Hermes。（安装期 stash 恢复提示选 `n`，见 hermes-windows-cn-install 症状 4。）

## 症状 4：vision_analyze 报 400 "unknown variant `image_url`, expected `text`"

**含义**：当前 `auxiliary.vision` 配置的模型是纯文本模型(或不支持多模态 content 数组)。本机实测:曾配 aisz.mom 中转的 `gpt-5.5`,vision_analyze 每张图都 400;模型支持图片消息才能用。

**诊断/配置路径**:
1. 配置位置:`profiles/sdsd/config.yaml` 的 `auxiliary.vision.{provider,model,base_url,api_key}`(用 `hermes config set auxiliary.vision.X ...`,勿手改)
2. 改完**立即生效**(vision_analyze 每次调用实时读配置),无需重启;实测可用 `vision_analyze` 传一张小图验证
3. 视觉通道建议 = **SiliconFlow(硅基流动)**:
   - 查账号可用模型:`curl https://api.siliconflow.cn/v1/models -H "Authorization: Bearer sk-..."`,筛选 id 含 `VL`/`vision`/`glm-4v` 的
   - 本机已启用:`Qwen/Qwen3-VL-32B-Instruct`(base `https://api.siliconflow.cn/v1`),读图/描述截图质量好、~2-3s 响应
   - 同账号备选:`Qwen/Qwen3-VL-30B-A3B-Instruct`(性价比)、`Qwen/Qwen3-VL-8B-Instruct`(最轻)、32B/8B-Thinking(带推理)
4. 离线验证某模型能吃图(不经过 Hermes):`chat/completions` 的 content 用数组 `[{"type":"image_url","image_url":{"url":"data:image/png;base64,..."}},{"type":"text","text":"..."}]`,能返回内容 = 该模型可用
5. key 管理:`auxiliary.vision.api_key` 直接内联存 profile config(与 custom provider 格式一致)

## 症状 5：Windows 下 ssh 弹 GUI 密码框 → 终端命令挂起(超时/中断)

git-bash 的 ssh 未配免密时,**Windows 会弹"Git for Windows"密码对话框**(不是终端内提示),命令挂起等输入,表现为超时/中断/exit 130。对策:脚本化 SSH 一律加 `-o BatchMode=yes`(免密失败立即报错,不弹框);需要密码时走 sshpass 或先配好 key。

## 已知坑
- 压缩 telemetry 里 `chunking: false` 属正常，非配置项
