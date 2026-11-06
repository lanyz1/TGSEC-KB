<!-- archived from /root/.hermes/skills/security/ai-tool-provider-config/SKILL.md on 2026-10-21 -->

---
name: ai-tool-provider-config
description: >-
  测绘引擎·Configure AI coding tool custom API providers.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/ai-tool-provider-config`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/ai-tool-provider-config/…')`，不要相对 `references/legacy/` 解析。

# ai-tool-provider-config（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/ai-tool-provider-config/`

溯源（仅标记）：`hermes/software-development`

---

## 适用场景
- 用户需要配置自定义API中转站（如fkcodex、right.codes等）到AI编码工具
- 用户需要切换/新增/删除多个中转站提供商
- 用户希望通过CC Switch GUI或数据库直接管理提供商

## 工具链概述

### CC Switch (GUI管理工具)
- 路径: `D:\cc-switch.exe`（Windows）或桌面快捷方式 `CC Switch.lnk`
- 数据库: `~/.cc-switch/cc-switch.db`（SQLite）
- 卸载: 桌面有 `Uninstall CC Switch.lnk`

### Claude Code CLI
- 二进制: `~/.claude/` 目录
- 配置文件: `~/.claude/settings.json`
- 支持通过 `env` 字段配置自定义 API 端点

### Codex CLI
- 二进制: `~/.codex/` 目录
- 配置文件: `~/.codex/config.toml`
- 使用 `[model_providers.custom]` 段配置自定义提供商

## CC Switch 数据库操作

### 表结构
```sql
SELECT id, name, app_type, is_current FROM providers ORDER BY app_type, is_current DESC;
UPDATE providers SET is_current = 0 WHERE app_type = 'claude';
UPDATE providers SET is_current = 1 WHERE id = '<provider_id>';
```

### 新增 Provider（Python）
```python
import sqlite3, json, time
conn = sqlite3.connect(r'C:\Users\Administrator\.cc-switch\cc-switch.db')
cursor = conn.cursor()
provider_id = f"provider-{int(time.time()*1000)}"
settings = {"auth": {"OPENAI_API_KEY": "sk-..."}, "config": "model = \"gpt-5.5\"\n[model_providers.custom]\nname = \"Provider\"\nbase_url = \"https://api.example.com/v1\"\nwire_api = \"responses\"\nrequires_openai_auth = true\n"}
cursor.execute("INSERT OR REPLACE INTO providers (id, app_type, name, settings_config, website_url, category, created_at, is_current, cost_multiplier) VALUES (?,?,?,?,?,?,?,?,?)",
  (provider_id, "codex", "Provider", json.dumps(settings), "https://api.example.com", None, int(time.time()*1000), 1, 1.0))
conn.commit()
conn.close()
```

## Claude Code 配置
```json
{
  "model": "claude-fable-5[1m]",
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "sk-...",
    "ANTHROPIC_BASE_URL": "https://api.example.com",
    "ANTHROPIC_MODEL": "claude-fable-5",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-4-8",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-5",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-4-5-20251001"
  }
}
```

## Codex CLI 配置
```toml
model_provider = "custom"
model = "gpt-5.5"
[model_providers.custom]
name = "fkcodex"
base_url = "https://www.fkcodex.com/v1"
wire_api = "responses"
requires_openai_auth = true
experimental_bearer_token = "sk-..."
```

## API Key 验证
```bash
curl -s "$BASE_URL/v1/models" -H "Authorization: Bearer $KEY"
```

## 常见错误
- `401 Invalid bearer token` → key过期，换新key
- `model not found` → 先 `curl /v1/models` 看可用模型
- CC Switch GUI 优先于数据库修改

## 陷阱
- Claude Code env 优先级: 环境变量 > settings.json > CC Switch
- 删provider前先把它的 `is_current` 置0，否则CC Switch可能崩溃

## 参考资料
- `references/hermes-vision-aux-model.md` — Hermes 视觉辅助模型(auxiliary.vision)接用户中转的配置:vision toolset 启用但 provider=auto 无 key 会静默失效、`hermes config set auxiliary.vision.*` 指到 Claude/GPT 中转、key 必须用户提供(禁读 settings.json)。2026-08-04 实测。
