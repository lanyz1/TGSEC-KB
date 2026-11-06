---
name: admin-panel-login-triage
description: "Use when attacking an admin/login panel or lockout."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [admin-panel, login, lockout, aspnet, webback, cloudflare, cpanel, triage]
    related_skills: [aspnet-viewstate-hunt, laravel-pentest, recon-discriminators, cdn-origin-tracing]
---

# Admin/Login Panel Triage

后台登录面的第一原则:**先证明面板是真的、按钮是真的,再花锁定次数。** 很多「打不进去」不是密码错,而是面板根本不在、或 POST 按钮名不对、或锁定计数已悄悄耗尽。

## When to Use

- 发现 `/admin`、`/login`、`/admin/core/login.aspx`、WHM/cPanel、CMS 后台
- 准备试默认口令/字典之前
- 登录返回 200 但页面没变化、或锁定计数不动
- 面板挂在 Cloudflare 后面,端口「全开」但响应 521/526

## 0. 先证面板真实存在

### CF 代理端口 521/526 ≠ 源站有 cPanel

`2082/2083/2086/2087/2095/2096/8443/2052/2053/8080/8880` 全有响应,不等于源站跑 cPanel/WHM。这组是 **Cloudflare 默认代理端口**:CF 接受连接后回源,源站拒绝回 **521**,源站 TLS 坏回 **526**。

- `2087 → 521` 只说明「CF 愿意代理 2087」。
- 判据:直连候选源站 IP + `Host`/`--resolve`;只有直连拿到 WHM 登录页/证书才算。
- FOFA/DNS/crt.sh 都拿不到非 CF 的 A 记录 → 源站未暴露,记为 blocked;不要拿 521 当「cPanel 在,只差密码」。
- 详见 `references/cf-proxied-panel-ports.md`。

### 诱饵/兜底页

- 先请求一个保证不存在的路径,记长度基线;后台页若与基线同长,是 catch-all。
- POST 一次明显错误的凭据,看响应/Set-Cookie/锁定文案是否真的变化;完全不变 = 可能不是真登录口。

## 1. 解析真正的提交控件

### ASP.NET WebForms

- 必带:`__VIEWSTATE`、`__VIEWSTATEGENERATOR`、`__EVENTVALIDATION`(从 GET 页面解析)。
- 提交控件可能是普通 `<input type="submit" name="...">`,也可能是 **LinkButton**:`__doPostBack('ctl$BtnLoginLink','')`。
- **坑**:POST 一个不存在的按钮名,服务端照常 200,登录逻辑不触发,锁定计数也不加。每次 POST 后读锁定文案;数字没变 = 按钮名错了,立刻重新解析表单,不要继续猜密码。
- WebBack CMS 实测细节:`references/webback-cms.md`。

### Laravel / PHP

- 看 `laravel_session`/`XSRF-TOKEN`;POST 需带 `_token` + cookie。
- `/admin` 的 **403 = 已登录但角色不足**,**302 → /login = 未登录**。403 时别再试路径绕过,差的是角色。
- 注册/资料接口的角色字段与判据:`references/laravel-role-boundary.md`。

## 2. 锁定计数纪律

- 先找页面上的计数文案(如 `You are on attempt N of 6`),确认上限。
- **到 N-1 就封存**,最后一次留给「有明确依据的唯一候选」,不做字典。
- 没有可见计数时,先发 1 次已知错误凭据,对比响应差异;假定有锁,按 5 次上限规划。
- 默认口令/弱口令只试少量高概率组合;无公开默认值的冷门 CMS 不浪费次数。

## 3. 替代面

- **forgotpass**:常见 `TxtUser` + `TxtEmail`,两者匹配才发新密码。响应文案固定 = 无枚举 oracle;单引号导致的长度差可能只是回显,先抓 alert/错误文案再判 SQLi。
- **trial/contact 表单**:常是 EF/ORM 参数化;单引号与 `WAITFOR DELAY` 都无差异就停。
- **前端 JS**:可能是 44 字节 stub,不要指望从中找未授权 handler。

## 4. 停手与换面

- 登录面全是参数化 + 锁定将满 → 转同运营方兄弟子域/服务器/其他端口,不在 6 次锁上硬耗。
- 记录已用次数与封存状态,写进案卷,避免下一轮重复消耗。

## Pitfalls

- 200 不代表登录逻辑触发;只有锁定计数/错误文案/Session 变化才算。
- `forgotpass` 三次响应长度不同,可能只是单引号回显,不是注入。
- CF 521/526 是边缘回源错误,不是源站应用错误。
- 403 与 302 混淆会让你把「角色不足」误判成「未登录」,反复做无效登录。
- 冷门 CMS 没有公开默认口令,别把 6 次锁当字典额度。

## Verification

- [ ] 面板真实性已用直连 IP/Host 或指纹确认
- [ ] 提交控件名/`__doPostBack` 目标已从页面解析
- [ ] 每次 POST 后锁定计数已核对
- [ ] 替代面(forgotpass/trial)已判参数化
- [ ] 已用次数/封存状态写入案卷

## References

- `references/webback-cms.md` — WebBack CMS 指纹、LinkButton 登录、6 次锁定实测
- `references/cf-proxied-panel-ports.md` — CF 代理端口 521/526 判读与源站验证
- `references/laravel-role-boundary.md` — 批量赋值字段与 403/302 角色判据
