# 源码泄露链式挖掘 — 方法论笔记（原 source-code-exposure 技能全文）

> 已并入 webapp-blackbox-audit 第 9 节；本文件保留完整原文供深入参考。

# 源码泄露链式挖掘

## 触发条件
当目标 Web 应用返回 `package.json` 或 `.js` 源码文件 200 时，必须加载本技能。

## 核心原则

### 链式挖掘路径
```
package.json (入口) → scripts/*.js (测试脚本) → server/*.js (服务端) → config/*.js (配置) → data/*.json (数据)
```

### 从 package.json 提取的关键信息
| 字段 | 用途 |
|------|------|
| `scripts.start` / `main` | 入口文件路径 |
| `scripts.*` | 所有脚本名（直接访问对应路径） |
| `dependencies` | 技术栈判断（pg=PostgreSQL, express=Node.js） |
| `type: "module"` | ESM 模块系统（import 语法） |

### 脚本文件优先排查
| 脚本 | 高风险内容 |
|------|-----------|
| `api-smoke-test.js` | 测试 API key、bot token、配置文件 |
| `preprod-check.js` | 所需环境变量列表 |
| `set-telegram-bot-profile.js` | Telegram bot token 使用方式 |
| `self-optimize.js` | 内部测试逻辑 |

### 服务端源码关键文件
| 文件 | 价值 |
|------|------|
| `server/config.js` | 环境变量映射（apiKey, databaseUrl, telegramBotToken） |
| `server/lib/http.js` | 认证函数实现（requireApiKey, verifyTelegramInitData） |
| `server/routes/api.js` | 全部 API 端点 + 认证要求 |
| `server/storage/jsonStore.js` | 数据文件名列表（直接枚举） |
| `server/storage/postgresStore.js` | 数据库 schema |
| `server/telegram/bot.js` | Telegram bot 处理逻辑 |

### 数据文件枚举
从 `jsonStore.js` 的 `files` 对象提取文件名，批量访问 `data/` 目录：
- `users.json` / `tradingUsers.json` — 用户账号、Telegram ID
- `trades.json` — 交易记录、金额、TXID
- `paymentAccounts.json` / `counterparties.json` — 银行账户
- `cryptoAddresses.json` — 加密货币地址
- `auditLogs.json` — 全量审计日志
- `otcGroups.json` / `otcGroupMembers.json` — 群组配置和成员角色

### 认证逻辑分析
- `requireApiKey`: 检查 `x-api-key` 头；若 key 为 "change-me" 或空则绕过
- `requireApiKeyOrTelegram`: 先检查 x-api-key，再验证 Telegram init data HMAC
- Joypay 双认证: `x-joypay-api-key` 或 `x-api-key` 均接受

### 响应头指纹
- nginx 响应: `Server: nginx/1.18.0 (Ubuntu)`
- Node.js 静态: `x-content-type-options: nosniff` + `referrer-policy: no-referrer`
- 404 区分: nginx=HTML, Node=text/plain "not found", API=JSON `{"error":"not_found"}`

## 相关路由
- 源码审计阶段: 加载 `insecure-source-code-management`
- 认证绕过: 加载 `auth-agent` → `auth-sec`
- API 利用: 加载 `api-agent` → `api-sec`
- 数据利用: 加载 `webapp-blackbox-audit`
