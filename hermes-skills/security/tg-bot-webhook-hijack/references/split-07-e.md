## E 面：客户端/源码/供应链

### 框架已知 CVE

| 框架 | 漏洞 | 影响 |
|------|------|------|
| aiogram < 3.22.0 | initData 校验用 `==` 非 `hmac.compare_digest` | 时序侧信道 |
| pyTelegramBotAPI | 链 aiohttp CVE-2024-23334 目录穿越 | 文件读 |
| aiogram | aiohttp CVE-2026-47265/54273-54278 DoS 家族 | 拒绝服务 |
| node-telegram-bot-api | 废弃依赖 request/form-data/tough-cookie | 多个已知洞 |

```bash
# 依赖审计（拿到 bot 源码时）
pip-audit -r requirements.txt
npm audit
osv-scanner --lockfile package-lock.json
```

### 供应链投毒检测

| 恶意包 | 手法 | 检测 |
|-------|------|------|
| pyronut | 冒牌 pyrogram，`Client.start()` 植入后门，`/e` = RCE | 检查 `__init__.py` 异常 import |
| gram-utilz / flashbot-sdk-eth | 同一 TG bot token 收赃 | 提取 token → getMe 反查 |
| 越南 TG 禁令后 Ruby gems | 替换 API base 指向攻击者 relay | 检查 API endpoint 是否标准 |
| dsfsdfds PyPI 系列 | `__init__.py` 藏发送逻辑 | grep `api.telegram.org` |

### YARA 规则（样本扫描）

```yara
rule HUNT_Telegram_Bot_API {
  strings:
    $api = "api.telegram.org" ascii wide
    $getMe = "getMe" ascii
    $getUpdates = "getUpdates" ascii
    $setWebhook = "setWebhook" ascii
    $deleteWebhook = "deleteWebhook" ascii
    $token = /[0-9]{10}:[A-Za-z0-9_-]{35}/ ascii
  condition:
    $api and ($token or 2 of ($getMe, $getUpdates, $setWebhook, $deleteWebhook))
}
```

---

