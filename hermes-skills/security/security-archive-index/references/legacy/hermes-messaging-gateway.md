<!-- archived from /root/.hermes/skills/security/hermes-messaging-gateway/SKILL.md on 2026-10-21 -->

---
name: hermes-messaging-gateway
description: >-
  测绘引擎·Use when linking Hermes to phone via messaging gateway.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/hermes-messaging-gateway`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/hermes-messaging-gateway/…')`，不要相对 `references/legacy/` 解析。

# hermes-messaging-gateway（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/hermes-messaging-gateway/`

溯源（仅标记）：`hermes/autonomous-ai-agents`

---

# Hermes 手机联动(消息网关 Messaging Gateway)

用户需求模式:"我在手机 app 发消息能同步到桌面 Hermes,桌面的任务进度也能推到手机" → 答案是**消息网关**:`hermes gateway` 进程把聊天平台 bot 挂到**同一个 profile**(技能/记忆/工具全共享),手机和 bot 对话 = 远程指挥这台 Windows 机(能跑终端/浏览器/渗透,不止聊天)。**这台电脑开机 + gateway 进程在跑**是唯一前提。

## 快速配置(Telegram,本用户推荐路径)

1. 用户手机操作(约2分钟,无需我代劳):
   - `@BotFather` → `/newbot` → 显示名 + 用户名(必须以 `bot` 结尾) → 得到 **API token**(形如 `123456789:ABC...`,保密,泄露用 `/revoke` 重置)
   - `@userinfobot` 发条消息 → 得到**数字 user ID**(不是用户名)
2. 配置(推荐交互向导):`hermes gateway setup` → 选 Telegram → 填 token + allowed user IDs,自动写配置
   - 手动方式:.env 加 `TELEGRAM_BOT_TOKEN=...` 和 `TELEGRAM_ALLOWED_USERS=...`(多个用逗号分隔)
3. 启动:`hermes gateway`,几秒内上线,手机发条消息验证
4. 可选:config.yaml `gateway.platforms.telegram.extra.status_indicator: true`(bot 简介显示 🟢 Online/🔴 Offline);`/setcommands` 配命令菜单;Windows 开机自启 gateway 保证随时可连

## 关键语义(先讲清楚,防期望落差)

- **桌面会话内容不会自动镜像到手机**:网关会话是独立聊天线程。手机发任务 → 结果回手机;但桌面端跑的活不会自己"同步"过去。
- 想要桌面任务进度上手机:agent 主动推送到 Telegram home channel,或 **cron 任务** 配 `deliver` 到 Telegram(`deliver: all` 或 `telegram:<chat_id>:<thread_id>`;`attach_to_session: true` 可开可回复线程)。
- 手机端会话有完整工具权限(terminal/browser 等),与桌面同 profile 同权限。

## 本机现状快照(2026-08-08,配之前先复查)

- `config.yaml`:**无 `gateway:` 段**;`browser.use_gateway: false`;但 `platform_toolsets.telegram: [hermes-telegram]` 已就位(工具集就绪,只差配置)
- `.env`:TELEGRAM_* 键只作为模板注释存在,无真实值 → **网关未配置**
- 用户已询问过手机联动(2026-08-08),当时选择"先不配,就问问" → 再次主动提出时才动手配
- 其他已列 toolsets:discord/whatsapp/slack/signal/homeassistant/qqbot/yuanbao/teams/google_chat

## 平台选型(大陆用户)

- **Telegram(默认推荐)**:配置最顺。需走 v2rayN TUN(系统全局,gateway 自动走,**勿手动给软件设 10808 代理**——环路风险见 memory)。用户已有 Telegram 账号(运营两个付费社群)
- 国内免翻墙备选:飞书/钉钉/企业微信/QQ bot(`hermes-qqbot` toolset 已列)/元宝(yuanbao)
- WhatsApp 亦可,绑号稍繁琐;Signal/SMS(Twilio)/Email 也可
- 官方平台清单见文档:Telegram, Discord, Slack, WhatsApp(+Business Cloud API), Signal, Email, SMS, Teams, 钉钉, 飞书, 企业微信, Weixin, QQ Bot, Yuanbao, Matrix, Mattermost, Google Chat, Home Assistant 等 20+

## 文档导航坑(Next.js 文档站)

- `/docs/messaging/`、`/docs/messaging-gateway/` → **404**;`/llms.txt` 返回的是 HTML 不是纯文本
- 正确路径:docs 首页侧栏 **Messaging Platforms → Popular → Telegram**(或对应平台),内容含 bot 创建/隐私模式/命令菜单/status_indicator 等完整细节
- Telegram 群聊注意:bot 默认隐私模式只收 `/` 命令、@提及、回复;要观察群聊需 BotFather 关隐私模式或设为群管理员(改后必须移除重加才生效)

## 验证

- 启动后手机给 bot 发消息,能收到回复即通
- `hermes gateway` 前台日志无报错;`status_indicator` 开启时 bot 简介显示 Online
