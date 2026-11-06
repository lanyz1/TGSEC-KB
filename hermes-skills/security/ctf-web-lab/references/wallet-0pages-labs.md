# 实战记录：Digital Wallet Lab + Vue 0Pages Lab（2026-08）

两个相邻端口靶场（38.60.125.120:30017 / :30018），各自独立，60 分钟计时，目标 `CTF{...}` flag。

## Digital Wallet Lab (:30017)

Vue3 + Vuetify 钱包应用。前端 JS chunk：`index-Cq7aS2Y4.js`（主）+ `Login-C3jUqX1E.js` + 页面组件（Dashboard/Profile/Transactions/Transfer）。

**API 面**：`/api/login` POST {username,password} → {token,user}；`/api/me`、`/api/balance`、`/api/transfer`、`/api/transactions`、`/api/users`（Bearer token）。已知账号 alice/bob/charlie。

**攻击链**：
1. 弱口令全灭 → SQLi：`username=admin' OR '1'='1` → **直接登录 admin**（token 含 `role:admin`，余额 999,999.99）
2. UNION 确定 6 列：`UNION SELECT 1,2,3,4,5,6` → 回显映射 id/username/name/balance/role/email
3. `database()` 报错 + `FROM users` 可用 → **SQLite**；`information_schema` 报错 → 换 `sqlite_master`
4. 枚举出表：`users`、`transactions`、**`flags`**
5. `SELECT flag_value FROM flags` → `CTF{w4llet_1dor_sqli_bu51ness_l0g1c}`

**附带发现**：负数转账 `amount=-100` → 余额反增（无限刷钱）；`amount="1e2"` 字符串类型混淆绕过校验；users 表密码全明文；JWT HS256 常见密钥未中（SQLi 已足够，无需伪造）。

## Vue 0Pages Lab (:30018)

静态托管平台：注册 → 登录（cookie 会话）→ 上传 ZIP → 部署站点 → `/preview/{site_id}/` 访问。Express 后端（X-Powered-By）。

**API 面**：`/api/auth/register` POST {username,password,confirm_password}、`/api/auth/login`、`/api/sites` GET/POST(multipart archive)、`/api/sites/{id}`、`/api/sites/template`。

**关键观察**：
- 注册字段需 confirm_password（缺字段报 "Please fill all fields"）
- **SPA fallback**：所有未知路径返回 200+index.html；真实静态文件有 Last-Modified/ETag；`/preview/{site_id}/xxx` 文件不存在返回 "Site not found."（区别于 fallback）
- ZIP 必须含 `webroot/` 目录才有内容可服务
- 路径穿越条目（`webroot/../../pwned.txt`）部署成功但预览隔离（返回 Site not found）——文件解压到了沙箱外的站点目录，预览服务只服务 webroot
- symlink 条目被保留但**预览不跟随解析**（访问返回链接目标字符串本身）
- admin 用户名存在（注册冲突验证）；登录 SQLi 参数化防御（除双引号 500 泄露）

**限流**：批量 curl 后连接被重置（`curl: (52) Empty reply from server`）→ IP 被临时封禁；等 2-5 分钟恢复。对策：低频（≥2-3s/请求）、先小样本、核心验证优先。

## 通用教训
- SPA 靶场先抓 JS chunk 还原 API，别靠目录枚举（全 200 假阳性）
- SQLi 登录绕过是最快入口；SQLite 指纹 = information_schema 报错 + FROM 可注入
- 计时制：flag 到手立即提交，别沉迷附加分
