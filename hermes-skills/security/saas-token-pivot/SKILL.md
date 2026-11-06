---
name: saas-token-pivot
description: "Use when SaaS tokens harvested. Validate, mine, pivot."
version: 0.1.0
tags: [slack, clickup, resend, openai, tokens, pivot, docs-mining]
---

# SaaS 令牌落地后：验证 → 挖掘 → 横向

应用被拿下后，其配置/数据库里的第三方集成密钥（Slack / ClickUp / Notion / 邮件 / LLM…）往往比应用本身更值钱。这是从「一个应用」扩到「整个生态」的标准打法。

## 1. 只读验证（每条先验活再有底气写报告）

- **Slack**：`POST https://slack.com/api/auth.test`（`Authorization: Bearer xoxb-...`）→ `ok:true, team, user, team_id`。bot scope 常 `missing_scope`（读不了 channels/users）——**别浪费轮次猛试读接口**，auth.test + webhook URL 就够定性。
- **ClickUp**：`GET https://api.clickup.com/api/v2/user`（`Authorization: <token>`）→ 账号名/邮箱。
- **Resend（邮件）**：`GET https://api.resend.com/domains` → 域名验证状态。
- **OpenAI**：`GET https://api.openai.com/v1/models`。其余各家都有 /me 类只读端点。
- 铁律：**只读，绝不发送/改动/删挡任何内容**；写操作能力（webhook）记入报告即可。

## 2. ClickUp 深度挖掘（文档库常藏明文凭据——本链最高价值处）

- 团队/成员：`GET /api/v2/team` → teams[].members（邮箱域名常暴露关联公司，如 @torrero.com/@betmaster.com 双域）。
- 空间/文件夹/列表：`GET /api/v2/team/{id}/space` → `/space/{sid}/folder`、`/space/{sid}/list`、`/folder/{fid}/list`。
- 任务：`GET /api/v2/list/{lid}/task?include_closed=true&subtasks=true`（运营任务描述=情报）。
- **文档（只在 v3！v2 的 /docs 是 404）**：
  - 列表：`GET https://api.clickup.com/api/v3/workspaces/{team}/docs`
  - 全文：`GET /api/v3/workspaces/{team}/docs/{doc}/pages?max_page_depth=3&content_format=text/md` ← **doc 详情接口的 pages 常为空，正文要用 pages 端点拿**
- 重点搜页面名：Accounts / Credentials / Onboarding / Important links / New employee —— 实拍案例：一页 `Accounts` = 明文密码本（20+ 系统账密 + Basic 认证 + 测试号统一 OTP + 全部管理后台 URL）。

## 3. 从文档反哺主线（别停在“读到了”）

- 后台清单（Main admin / Malta admin / preprod…）→ 回灌渗透目标列表。
- 供应商后台凭据（Evolution/Pragmatic/Playtech…）和测试账号 → 报告素材 + 横向面。
- Slack 工作区、Notion 空间等 → 记为「可写/可读面」并附验证证据（auth.test 结果等）。

## Pitfalls

- 令牌类型有别：OAuth client_secret vs personal token，调用头不同（`Authorization: token` vs `Bearer`）。
- Slack bot 读不了频道 ≠ 令牌无效——missing_scope 是常态，别误判。
- 文档站（如 Notion）大多需登录，浏览器渲染也拿不到正文——别恋战，优先有 API 的（ClickUp v3）。
- 把验证结果（谁/哪队/有效期）写进报告用「已实控」口径，未使用的写「可用未动用」。
