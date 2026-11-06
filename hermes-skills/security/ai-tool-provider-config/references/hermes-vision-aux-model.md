# Hermes 视觉辅助模型(auxiliary.vision)接中转

> 场景:用户想让 Hermes 的 vision 工具(看图)走自己的 Claude/GPT 中转,而不是注册 OpenRouter/Google。
> 2026-08-04 实测:用户桌面 Hermes 配置文件在 `C:\Users\Administrator\AppData\Local\hermes\profiles\sdsd\`。

## 症状:vision 工具"不存在"/看不了图
- `vision` toolset 显示 `✓ enabled`,但会话里 vision_analyze 工具不出现、`tool_search` 搜不到。
- 根因:`auxiliary.vision.provider: auto` — auto 模式需要 `OPENROUTER_API_KEY` 或 `GOOGLE_API_KEY` 才能找到后端,两者都没有 → **vision 静默失效,工具不加载**(不报错)。
- 排查命令:
  - `hermes tools list | grep -i vision` → 看 toolset 是否启用
  - `hermes config get auxiliary` → 看 vision.provider 是否 auto、model/base_url/api_key 是否空
  - 查 `.env` 是否有 `OPENROUTER_API_KEY`/`GOOGLE_API_KEY`(只有键名,别回显值)

## 修复:指到用户已有中转(OpenAI 兼容接口)
用户两个现成中转(都是 OpenAI 兼容 `/v1` 风格,支持多模态模型):
- **Claude 中转**: `70.39.179.245:8080`(fable-5/opus-4.5~5/sonnet-5/haiku-4.5 带视觉)
- **GPT 中转**: `fkcodex.com`(gpt-5.x 带视觉)

配置命令(以 Claude 中转为例):
```bash
hermes config set auxiliary.vision.provider custom:claude-vision
hermes config set auxiliary.vision.model fable-5
hermes config set auxiliary.vision.base_url http://70.39.179.245:8080/v1
hermes config set auxiliary.vision.api_key <key>
```

## 关键注意
- **key 必须用户提供** — 项目红线禁读 `~/.claude/settings.json` 的 ANTHROPIC_AUTH_TOKEN 明文来配其它工具(禁 echo/禁写文件/禁入 memory)。用户可"直接贴 key"(配完不回显)或"出命令自己填"。
- 两个中转 `/v1/models` 不带 key 都返回 `API_KEY_REQUIRED` / `Invalid token` — 探测模型列表必须带 key。
- 配好后 `/reset` 新会话生效(vision 工具加载),无需重启 gateway。
- 主模型 provider 无关(当前主模型是 deepseek),auxiliary 是独立配置段。
