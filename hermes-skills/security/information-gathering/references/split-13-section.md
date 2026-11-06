## 十二、泄露数据库与暗网情报

### 12.1 2025-2026 泄露态势（情报背景）
- 2025-06 Cybernews 披露 **160 亿条凭证** 暴露于未加密存储，92% 来自 2024-2025 活跃攻击，61% 密码仍有效，34% 附带会话令牌
- 2025 年 Infostealer（窃密木马）新增 **15.6 亿条凭证**，平均每台感染设备 547 条密码，86% 为明文
- AI 工具凭证进入黑市：2025 年超 102 万条 OpenAI 账号凭证、HuggingFace 凭证 +18%
- 凭证从感染到上架 <48 小时，勒索部署通常 <4 天——时效性决定数据价值
- 54% 的勒索受害者在攻击前其企业凭证已出现在 stealer 日志中（Hudson Rock 等研究）

### 12.2 查询数据源分层
| 层级 | 数据源 | 覆盖范围 | 成本 |
|------|--------|---------|------|
| 免费公开 | HIBP、IntelX、LeakCheck 免费档、Pastebin | 已公开披露泄露 | 免费 |
| 聚合商业 | Dehashed、Snusbase、LeakCheck、Scylla | 多来源聚合+明文密码 | 付费 |
| 威胁情报 | SOCRadar、Recorded Future、CloudSEK XVigil、MicroCTI | stealer log、暗网论坛、IAB 情报 | 企业级 |
| 暗网监控 | 自有爬虫 + Telegram 频道监控 | 实时一手数据 | 高成本 |

### 12.3 暗网/Telegram 监控方法论
```bash
# 原则：监控 ≠ 主动购买/交互。仅收集公开可访问的泄露数据用于安全评估

# Telegram 频道（Telethon 只读抓取公开频道中目标关键词）
# 关键词：目标域名/公司名/邮箱后缀/系统名

# 暗网索引（Tor 环境，仅访问合法可索引站点）
# DarkSearch / Ahmia / 已索引的泄露数据库镜像
torsocks curl -s "http://darksearch.io/api/search?query=target.com"

# Stealer log 平台（Hudson Rock 免费查询接口）
curl -s "https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-email?email=@target.com"
# → 返回受感染设备、窃取凭证 → 直接关联企业泄露面

# 评估命中数据价值（见 12.1）：新鲜度/明文性/会话令牌/访问级别（VPN、邮件、云控制台）
```

