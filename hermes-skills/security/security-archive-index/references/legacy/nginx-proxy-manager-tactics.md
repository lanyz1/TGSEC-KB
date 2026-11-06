<!-- archived from /root/.hermes/skills/security/nginx-proxy-manager-tactics/SKILL.md on 2026-10-21 -->

---
name: nginx-proxy-manager-tactics
description: Use when 目标为 Nginx Proxy Manager(:81/openresty)——NPM 渗透速查。
version: 1.0
author: yingying
license: MIT
---

> 归档卡：原目录 `/root/.hermes/skills/security/nginx-proxy-manager-tactics`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/nginx-proxy-manager-tactics/…')`，不要相对 `references/legacy/` 解析。

# Nginx Proxy Manager (NPM) 渗透速查

## When to Use
- 端口扫描命中 :81 管理台（或任意端口出现 `<title>Nginx Proxy Manager</title>` / "In The Office Planner" / openresty 默认站）
- 同主机伴生面排查：NPM 常与后端微服务（uvicorn/容器服务）同机部署，NPM 是外围入口而非数据面

## 指纹
- :81 管理台 SPA：`<title>Nginx Proxy Manager</title>`、meta description "In The Office Planner"
- :80 openresty「Default Site」；:443 openresty 且 **SNI 严格**——无 SNI/未知域名直接 TLS alert 112 unrecognized name，无默认证书，vhost 枚举对严格 SNI 部署无效
- server: openresty（NPM 镜像内置 openresty）

## 匿名 oracle（先打这两发）
- `GET :81/api/` → 200 `{"status":"OK","setup":true,"version":{"major":2,"minor":13,"revision":6}}`——**未授权拿精确版本**；`setup:false` = 初始向导未完成（直接走向导建管理员即接管）
- 管理台根页面 Last-Modified 可旁证部署时间

## 默认凭据（登录面默认凭据 ≤3 发纪律内）
- 工厂默认 <EMAIL-REDACTED> / adminchangeme：`POST /api/tokens {"identity":"<EMAIL-REDACTED>","secret":"adminchangeme"}`
- 400 `{"error":{"code":400,"message":"Invalid email or password"}}` = 已改密，此面记死

## 未授权 CVE（2.0–2.15.1 全系受影响，截至 2026-09 无官方修复版）
### CVE-2026-93964 未授权证书校验 oracle
- 端点：`POST /api/nginx/certificates/validate`（**无需登录**）
- 请求体必须是 **multipart 文件上传**（file part 名 `certificate` + `certificate_key`）；JSON body → 400 "No files were uploaded"
- 自签证书对 → 200 回显解析结果（cn/issuer/有效期）；junk → 400 且 **debug 泄露**：内部 cmd 串 `openssl pkey -in /tmp/<uuid>/tmp -check -noout 2>&1`、JS 堆栈、/app/ 容器内路径
- **注入死因（勿重复烧弹）**：临时路径全服务端 UUID、上传文件被重命名为固定名，文件名不进命令行——文件名/内容注入金丝雀（; ` $() sleep）均无时间差；openssl stderr 不回填响应。CVSS C:L/I:N 与实测吻合，止步于 oracle + 信息泄露
- 畸形证书可触发 500 应用 bug（如 ReferenceError），同样走 debug 泄露

### CVE-2026-40519 已认证 RCE（2.9.14–2.15.1）
- 需登录 + certificates:manage 权限——拿到 NPM 凭据后的首选升级链；无凭据时不可达

## 判定纪律
- 2.13.x 线无已知未授权 RCE；/api/* 其余端点全需 JWT
- NPM 反代面（:80/:443）与后端服务直连口（uvicorn 等非常规端口）是**不同的脸**——NPM 只代理它配置过的 host；后端直连口常比 NPM 面软，全端口扫描时逐口指纹
