---
name: ai-api-relay-configuration
description: >-
  测绘引擎·配置AI中转站到CC Switch/Claude Code/Codex CLI/Cursor等工具。
owned: true
tier: general
pack: survey-skill
---

# ai-api-relay-configuration（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/ai-api-relay-configuration/`

溯源（仅标记）：`hermes/mlops`

---

# AI API Relay 配置指南

## 适用场景
通过中转站（API relay/proxy）访问 OpenAI/Claude/Grok 等大模型 API，常见于中国大陆用户。

## 核心工具链

### 1. CC Switch（推荐，GUI 管理）
位置: Windows GUI 应用
数据库: `~/.cc-switch/cc-switch.db` (SQLite)

#### Provider 管理（直接操作 SQLite）
```python
import sqlite3, json

db = sqlite3.connect(r'~/.cc-switch/cc-switch.db')
cursor = db.cursor()

# 查看所有 providers
cursor.execute("SELECT id, name, app_type, is_current FROM providers ORDER BY app_type")

# 添加新 provider
provider_id = f"relay-{int(time.time()*1000)}"
settings = {
    "auth": {"OPENAI_API_KEY": "sk-***"},
    "config": 'model = "gpt-5.5"\n[model_providers.custom]\nname = "relay"\nbase_url = "https://relay.com/v1"\nwire_api = "responses"\nrequires_openai_auth = true\n'
}

# 切换默认 provider
cursor.execute("UPDATE providers SET is_current = 0 WHERE app_type = 'codex'")
cursor.execute("UPDATE providers SET is_current = 1 WHERE id = ?", (new_id,))
db.commit()
```

#### Claude provider 的 settings_config 格式（env 注入）

⚠️ **claude 与 codex 的 settings_config 结构完全不同** — claude 用 `env` 键注入环境变量（Anthropic SDK 读环境变量），不是 `auth`+`config`：

```python
settings = {
    "env": {
        "ANTHROPIC_AUTH_TOKEN": "sk-***",
        "ANTHROPIC_BASE_URL": "http://relay:8080",          # 注意不带 /v1
        "ANTHROPIC_MODEL": "claude-fable-5",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-4-8",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-5",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-4-5-20251001"
    }
}
# INSERT INTO providers (app_type='claude', settings_config=json.dumps(settings))
```

要点：
- `ANTHROPIC_BASE_URL` 是裸域名/裸IP（如 `http://70.39.179.245:8080`），**不带** `/v1`
- 模型名必须与中转站 `/v1/models` 返回的 id 完全一致
- 登录返回的 token 即 `ANTHROPIC_AUTH_TOKEN`（Bearer 直用）

#### 余额自动查询（meta.usage_script）

CC Switch 的 provider 可在 `meta` 里挂 JS 余额查询脚本，GUI 面板每 30s 自动拉一次：

```python
meta = {"usage_script": {
    "enabled": True,
    "language": "javascript",
    "code": """({
  request: { url: '{{baseUrl}}/api/usage/balance', method: 'GET',
             headers: { Authorization: 'Bearer {{apiKey}}' } },
  extractor: function (r) {
    if (!r || r.success === false) throw new Error((r && r.message) || 'failed')
    var d = r.data || r, disp = d.display || {}
    return { planName: d.token_name || 'Account',
             total: Number(disp.total || 0), used: Number(disp.used || 0),
             remaining: Number(disp.remaining || 0), unit: disp.unit || '',
             isValid: true }
  }
})""",
    "timeout": 10, "baseUrl": "https://relay.com", "autoQueryInterval": 30
}}
```

`{{baseUrl}}` / `{{apiKey}}` 是占位符，CC Switch 自动替换为 provider 的 website_url 和 key。**注意：`/api/usage/balance` 是 CC Switch 的通用猜测，不保证所有中转站都支持——必须实测**（见下）。

#### ⚠️ 余额查询实测结论（2026-08，fkcodex + 裸IP中转）

**API key 只能用于 `/v1/*` 推理接口，余额是账户级信息，绝大多数中转站不支持用 API key 查余额**。实测：

- **fkcodex.com**（new-api 框架）：`/api/user/self` 返回 `{"message":"Unauthorized, invalid access token"}` —— 需要**网页登录 session token**，API key 无效；`/dashboard/billing/credit_grants` 返回前端 HTML 而非 JSON（WAF 会拦 python urllib 的 403 error 1010，需带浏览器 UA）
- **裸 IP 中转**（如 70.39.179.245:8080）：`/api/user/self`、`/api/balance`、`/dashboard/billing/credit_grants` 全部 404
- **结论**：余额只能**网页登录中转站控制台**看。CC-Panes 无余额功能（全代码零匹配），CC Switch 的 usage_daily_rollups 也只是本地用量统计不是中转站实时余额

识别 new-api 框架的方法：抓首页 JS（`curl 首页 | grep -oE 'src="[^"]+\.js"'`），grep API 路径特征——出现 `/api/model-pricing`、`/api/deployments`、`/api/user/self` 即 new-api 系。

#### 清空重建 Codex 配置的注意

直接重写 `~/.codex/config.toml` 时（如换 provider），**必须保留**：`[mcp_servers.node_repl]` 段（Codex GUI 依赖）、`[marketplaces.*]`、`[windows] sandbox`。只改 `model_provider`/`model`/`[model_providers.*]` 段即可，否则 Codex 桌面版启动即崩。

### 2. Claude Code CLI 配置
配置文件: `~/.claude/settings.json`

```json
{
  "model": "claude-fable-5[1m]",
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "sk-***",
    "ANTHROPIC_BASE_URL": "https://relay.com",
    "ANTHROPIC_MODEL": "claude-fable-5"
  }
}
```

### 3. Codex CLI 配置
配置文件: `~/.codex/config.toml`

```toml
model_provider = "custom"
model = "gpt-5.5"
[model_providers.custom]
name = "relay"
base_url = "https://relay.com/v1"
wire_api = "responses"
requires_openai_auth = true
experimental_bearer_token = "sk-***"
```

### 4. Cursor IDE 配置
Settings → Models → OpenAI API Key → Custom
- Base URL: `https://relay.com/v1`
- Model: 根据 relay 支持的模型名称填写
- ⚠️ Cursor **Free 版不能切自定义端点**，只有 Pro 可以

### 5. 多中转并行（同机同时挂两个 Claude 中转，命令名区分）

需求：终端输入 `claude1` 走中转1、`claude2` 走中转2（如 fkcodex 与裸 IP 各挂一个）。方案：**包装命令**（.cmd 批处理）——各自 set 对应环境变量后调用真实 claude CLI，不覆盖原 `claude` 命令：

```bat
@echo off
REM D:\claude-bin\claude1.cmd — 中转1 (fkcodex)
set ANTHROPIC_AUTH_TOKEN=sk-xxx
set ANTHROPIC_BASE_URL=https://www.fkcodex.com
set ANTHROPIC_MODEL=claude-opus-4-8
set ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-8
set ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-5
set ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-haiku-4-5-20251001
call "%APPDATA%\npm\claude.cmd" %*
```

claude2.cmd 同样结构，换成中转2 的 token/base_url/model。`D:\claude-bin` 加入用户 PATH 即可在任意终端（含 CC-Panes 内置终端）用。完整环境变量可从 CC Switch 数据库直读（`providers.settings_config` 的 `env` 键，claude 类型），写进 .cmd 不显示明文。

⚠️ 注意：
- 包装命令需透传/设置 `CC_PANES_CLI_TOOL=claude` 等变量，否则 CC-Panes 的 SessionStart hook 可能把 claude1 识别为未知 CLI，会话恢复/launch history 失效
- 中转1/中转2 默认模型可能不同（如 opus-4-8 vs fable-5），实施前和用户确认是否统一
- .cmd 含明文 token，只放本机目录，勿进仓库


## Grok (xAI) 接入

### 云端 API（推荐）
- Base URL: `https://api.x.ai/v1`（OpenAI 兼容 chat/completions）
- API Key: 去 https://console.x.ai 注册
- 模型: `grok-2`, `grok-2-vision`

```bash
curl https://api.x.ai/v1/models -H "Authorization: Bearer sk-***"
```

### 本地 GGUF（离线）
- 完整 Grok-2 GGUF: `unsloth/grok-2-GGUF`（HuggingFace）— 极大，Q2_K ~120GB+，需服务器级内存
- 可跑小模型: `mradermacher/grok-oss-Apollyon-8B-i1-GGUF`（~5GB，Q4_K_M，普通电脑可跑）
- 运行工具: Ollama / llama.cpp

### Cursor 调用 Grok
- Settings → Models → OpenAI API Key → Custom: base=`https://api.x.ai/v1`, model=`grok-2`
- 前提: Cursor Pro（Free 不能切自定义端点）

## Codex 报 503 Unknown error @ 127.0.0.1:port 的诊断链

链路：**Codex → 本地代理（CC Switch 内置代理 / 破甲工具，常见端口 15721）→ 上游中转站**。端口能回 503（而非"连接拒绝"）= 本地代理活着，问题在上游；代理把上游故障包成 `503 Unknown error` 丢给 Codex（详细判定与 200/401/403/503 对照见下方 auxiliary.vision 节的"实测坑"条目）。

完整排查顺序：
1. `netstat -ano | findstr <port>` 确认监听者。若是绫波丽系（proxy_relay.py），看源码里 `TARGET =` 变量即转发目标——可能套二级链（如 `127.0.0.1:57321` → 真正中转），每层都要查
2. 看 CC Switch / 破甲面板的连通性自检，典型报错：`Connection failed: error sending request for url (https://www.fkcodex.com/v1) 无法建立连接（DNS / 连接 / TLS / 超时）`
3. curl 直连上游 `/v1/models` 带 key 定位（见 auxiliary.vision 节映射表）
4. ⚠️ **上游连不通先查本机系统代理**：系统代理指向死端口（`127.0.0.1:10808` 但 v2rayN/Clash 没开）会让原生应用（CC Switch/uv/irm）报连接失败或 `os error 10061`，而浏览器（插件代理或直连）正常——容易误判成中转挂了。修复见 windows-cli-deployment 的"Hermes Agent 安装（Windows + 中国网络）"节

## 验证方法论

### 测试 API 连通性
```bash
# 查看可用模型
curl https://relay.com/v1/models -H "Authorization: Bearer sk-***"

# 测试基础对话
curl https://relay.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-***" \
  -d '{"model":"gpt-5.5","messages":[{"role":"user","content":"hi"}]}'
```

### ⚠️ 配置前先查模型清单（关键 pitfall）

**任何中转站配置前，先 `curl /v1/models` 看实际支持的模型**，不要凭中转站网站宣传或猜测填模型名：

- fkcodex.com → GPT 系（gpt-5.5/5.6-sol 等，**无 grok**）
- 裸IP中转（如 70.39.179.245:8080）→ Claude 系（fable-5/opus-5/sonnet-5 等，**无 grok**）
- **Grok 在中转站上很稀有** — 想要 grok 一般只能直连 `api.x.ai/v1` 或找专门支持的中转
- 模型名不匹配时请求报 `model not found`，查清单 5 秒解决

### 中转站登录/注册限速（rate limiting）

大多数中文中转站对登录接口有失败锁定（如 fkcodex 连续错密码 → `尝试次数过多,请 15 分钟后再试`）。批量测试弱口令前先确认，否则会把自己锁在外面。

## 支持的 app_type

| app_type | 对应工具 | API 格式 |
|----------|---------|---------|
| claude | Claude Code CLI | Anthropic Messages |
| codex | Codex CLI | OpenAI Responses |
| claude-desktop | Claude Desktop App | Anthropic Messages |
| gemini | Google Gemini | Gemini API |

## Hermes Agent 视觉工具接入（auxiliary.vision）

Hermes 的看图能力（vision_analyze / 工具集 vision）走 `auxiliary.vision` 配置，**默认 `provider: auto` 需要 OPENROUTER_API_KEY 或 GOOGLE_API_KEY 才能找到后端**——两者都没有时 vision 工具静默不加载（不报错，就是没有）。可把 CC Switch 里现成的中转 key 指过去，无需新注册：

```bash
# 从 CC Switch DB 提取 key（不打印明文）
hermes config set auxiliary.vision.provider custom:mycodex
hermes config set auxiliary.vision.model gpt-5.5
hermes config set auxiliary.vision.base_url https://api.aisz.mom/v1
hermes config set auxiliary.vision.api_key sk-***   # 从 DB 提取，勿硬编码进命令历史
```

⚠️ **实测坑（2026-08）**：
- **fkcodex.com 的 key 对 `/v1/chat/completions` 和 `/v1/responses` 都是 403 Forbidden**（wire_api=responses 专用，仅限 Codex CLI 直连；vision/通用 HTTP 调用不可用）。403 = 端点/权限限制，401 才是 key 无效——别把 403 当 key 错去换 key。
- **api.aisz.mom（My Codex222，gpt-5.4/5.5/5.6-sol 全系）可用**，chat/completions 带 `data:image/png;base64` 的 image_url 实测通过。
- 裸 IP 中转（70.39.179.245:8080）曾 503，不稳定。
- **Codex 报 `503 Service Unavailable: Unknown error @ http://127.0.0.1:15721/v1/responses` = 本地代理（CC Switch 内置代理 / 破甲工具）活着，但上游中转连接失败**——代理把上游故障包成 503 "Unknown error"。判断链：① 端口能回 503（而不是"连接拒绝"）= 代理进程在跑；② CC Switch 同时弹「无法建立连接（DNS/连接/TLS/超时）」即证实是上游问题；③ 2026-08 实测 fkcodex.com 就是这种连接级故障（此前是 403，注意同一中转可能 403→连接失败演进）。定位：直连 curl 上游 `/v1/models` → 200=代理配置/模型名问题（重启代理+完全重开 Codex）；401=key 失效/欠费（换 key 或查余额）；403=端点限制（换接入方式）；503/超时=中转挂了（换中转）。
- **配置后需 `/reset` 新会话才生效**（Hermes 工具变更 mid-conversation 不生效）。没 reset 也能用：直接从 CC Switch 取 key 拼 urllib 请求中转 `/v1/chat/completions` 带 base64 图，等效看图。
- **用户已定持久工作流（2026-08-04）**：看图统一走 API 脚本，**不依赖 Hermes 内置 vision 工具**。现成脚本 = `scripts/vision-api.py`（本技能目录）：自动从 CC Switch DB 读 My Codex222 key、base64 发图给 api.aisz.mom gpt-5.5、打印中文回答。MSYS 下注意路径：脚本在中文目录时先 `cd` 进目录再 `python vision-api.py <win路径> <问题>`，别用 `/d/...` 绝对路径（会被吞成 `d\...`）。
- 验证视觉通路的固定手法：发 1×1 base64 PNG + "这张图什么颜色？"，答出颜色名即链路通。
- **403 vs 401 判定**：403 = 端点/权限限制（如 fkcodex 的 key 只给 Codex CLI responses wire 用，通用 chat/completions 全 403）；401 = key 无效。403 别去换 key，换端点/换 provider 才对。测试多个候选 key 时循环遍历 CC Switch 所有 provider 的 auth.OPENAI_API_KEY 逐个打，能快速找出可用者。

## 支持文件

- `references/lingboli-0.2-portable-build.md` — 绫波丽0.2 便携版（NERV-BREAK-5.6 NSIS 打包）拆解：安装位置、panel 菜单、101 vs 28 技能核对方法、故障排查（"Proxy starting..." 启动流程、破甲失败=换中转或清环境）
