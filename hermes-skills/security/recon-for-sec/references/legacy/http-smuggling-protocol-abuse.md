<!-- archived from /root/.hermes/skills/security/http-smuggling-protocol-abuse/SKILL.md on 2026-10-21 -->

---
name: http-smuggling-protocol-abuse
description: "HTTP走私/协议滥用时使用。触发: CL.TE, TE.CL, h2c走私, CRLF注入, Host头攻击。"
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, smuggling, clte, tecl, h2c, crlf, host-header, surveyengine-absorbed]
    related_skills: [web-ssrf, cdn-origin-tracing-v51, spring-security-csrf-bypass, surveyengine-knowledge-pack]
---

> 归档卡：原目录 `/root/.hermes/skills/security/http-smuggling-protocol-abuse`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/http-smuggling-protocol-abuse/…')`，不要相对 `references/legacy/` 解析。

# HTTP 请求走私与协议滥用家族

## When to Use

遇到正文顶部触发指纹/关键词时使用本技能(吸收自测绘引擎知识包)。完整卡全文: 镜像 `D:\博彩通杀\技能库\测绘引擎知识包\.cursor\skills\<原名>\SKILL.md`。


来源: 测绘引擎知识包吸收。镜像卡:
- `...\http-request-smuggling\SKILL.md`(255 行)
- `...\http2-specific-attacks\SKILL.md`(366 行)
- `...\crlf-injection\SKILL.md`(199 行)
- `...\http-host-header-attacks\SKILL.md`(337 行)
- `...\http-method-webdav\SKILL.md`(31 行)

## 1. HTTP 请求走私

### 原理与分类
| 类型 | 前端/后端解析差异 |
|---|---|
| CL.TE | 前端用 Content-Length, 后端用 Transfer-Encoding |
| TE.CL | 前端用 TE, 后端用 CL |
| TE.TE | 两端 TE 变体混淆 |
| H2.CL / H2.TE | HTTP/2 降级走私 |

### CL.TE 基础 payload
```http
POST / HTTP/1.1
Host: target
Content-Type: application/x-www-form-urlencoded
Content-Length: 6
Transfer-Encoding: chunked

0

G
```
验证: 连发两次,第二次响应异常(400/慢响应)= 走私成立。
```bash
curl -s -o /dev/null -w "%{http_code} %{time_total}" --http1.1 \
 -H "Content-Length: 6" -H "Transfer-Encoding: chunked" \
 -d $'0\r\n\r\nG' https://target/
# 精确字节控制: Turbo Intruder 或 Python socket
```

### 利用
- **绕过前端访问控制**: 走私请求直达后端未授权路径(/admin)
- **捕获其他用户请求**(L3): 走私带 Content-Length 的挂起请求,吸附下一个用户的请求头
- **SSRF-via-smuggling**: 走私打到内网

## 2. HTTP/2 专项
- **h2c 走私**: `Upgrade: h2c` 头被反代盲转发 → 后端讲 H2,前端盲 → 绕过前端 ACL
```http
GET / HTTP/1.1
Host: target.com
Upgrade: h2c
HTTP2-Settings: <base64 H2 settings>
Connection: Upgrade, HTTP2-Settings
```
工具: h2csmuggler
- **伪头注入**: 前后端对 :path/:authority 解析差异;重复伪头;scheme 操纵

## 3. CRLF 注入
- 探测: 参数值带 `%0d%0a` 看响应是否出现新行/新头
- 利用: `Set-Cookie` 会话固定、响应体注入 XSS、缓存投毒、日志注入
- 双 CRLF(`\r\n\r\n`)→ 注入响应体
- **过滤器绕过**: URL 编码双写 `%250d%250a`、unicode `%u000d`、空白混淆

## 4. Host 头攻击
| 攻击 | 手法 |
|---|---|
| 密码重置投毒 | Host 改攻击域 → 重置链接指向攻击者 |
| 缓存投毒 | Host 注入 → CDN 缓存恶意页 |
| SSRF | Host 指向内网 → 后端路由到内网 |
| vhost 绕过 | 直接 Host: 隐藏vhost |

**Host 校验绕过**: 覆盖头 `X-Forwarded-Host`/`X-Host`/`Forwarded`;请求行绝对 URL;双 Host 头。

## 5. HTTP 方法/WebDAV
- OPTIONS 看 Allow;`PUT webshell`、`DELETE`、`PATCH`、`TRACE`(反射头)、`PROPFIND`
- WebDAV: `MOVE`/`COPY` 改名绕过上传过滤
- 403 规避: X-HTTP-Method-Override / X-Method-Override 头

## 成功口径
| 档 | 条件 |
|---|---|
| L1 | 走私/Host头/CRLF 确认存在(timing diff/响应异常) |
| L2 | 走私绕过 ACL 访问未授权页,或 Host 投毒成立 |
| L3 | 捕获他人请求/SSRF 内网/缓存投毒影响用户 |

## Pitfalls
- smuggling 影响共享连接所有用户 → 授权内谨慎,PoV 用最小请求
- 检测走私必须 timing+diff 双证据,单次 400 不算
- 纯 CDN 前(无回源代理)走私面小;先确认架构再打
- CRLF 需看响应是否真回显注入(有些框架过滤)
