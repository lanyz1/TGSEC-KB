# WebBack CMS (ASP.NET) — 指纹、后台登录与锁定计数

2026-10 实测：`www.saturney.com`（Azure IIS 10 / ASP.NET，`cmv=4.2.9`）。冷门国产 .NET CMS，无公开默认口令；真正价值是**别浪费锁定次数**。

## 1. 指纹

- 首页 meta：`cms:record:controller=home`、`cms:record:type=homemanager`、`cms:record:id=22`
- 后台入口：`/admin/core/login.aspx`，标题 `WebBack - Login`
- 版本参数：`/cms/assets/js/base.min.js?cmv=4.2.9`（实测仅 44 字节，无前端逻辑可挖）
- 同家族容易误判成 SiteServer；`cms:record:*` + `/admin/core/login.aspx` 才是 WebBack。不要只凭 meta 定性。

## 2. 登录表单（关键坑）

- 字段：`mp$PageContent$TxtUser`、`mp$PageContent$TxtPass`
- 按钮是 **LinkButton** `mp$PageContent$BtnLoginLink`，必须走 `__doPostBack('mp$PageContent$BtnLoginLink','')`
- 必须带：`__VIEWSTATE`、`__VIEWSTATEGENERATOR`、`__EVENTVALIDATION`（从 GET 页面解析）
- **坑**：提交 `mp$PageContent$BtnLogin=...` 不会触发登录逻辑，页面照常 200，且**不消耗锁定次数**。每次 POST 后读页面里的 `attempt N of 6`；数字没变 = 按钮名错了，立刻停手重新解析表单，不要继续猜密码。

## 3. 锁定计数

- 文案：`You are on attempt N of 6`，N 随失败递增
- 硬上限 6 次，到顶封禁；**5/6 即封存**，不再试默认口令/字典。
- 默认口令无公开来源；`admin/admin888`、`admin/123456`、`admin`、`Saturney@2026`、`admin' OR '1'='1' --` 实测全失败（EF 参数化，SQLi 不成立）。

## 4. 其他面

- `forgotpass.aspx`：字段 `TxtUser` + `TxtEmail`，用户名+邮箱匹配才发新密码；实测参数化，无 SQLi，响应文案固定、无枚举 oracle。
- `/Trial/Submit`：`Firstname/Lastname/Company/Email/Phone`，EF 参数化，`WAITFOR DELAY` 无反应。
- 结论：登录面打不动时，转同运营方其他子域/服务器，不要在 6 次锁上硬耗。
