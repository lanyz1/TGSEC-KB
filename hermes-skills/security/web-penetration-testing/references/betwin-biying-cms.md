# BetWin (biying) 博彩/代理 CMS 渗透要点

实战来源：ag.61995q.com / 9581kk.com / ag.5911x.com 同代码多站部署（2026-07 会话）。

## 架构指纹
- 模板目录 `tpl/biying/`，favicon `/cl/tpl/biying/favicon.ico?=1174`
- 三级权限：`bg_super_*`(超管) / `gs_bg_*`(公司) / `daili_bg_*`(代理) —— 从 login.css 引用的背景图路径可确认层级
- 部署：注册站(如 9581kk.com 会员站) 与 代理登录站(ag.61995q.com) 分离；管理口常见 `:7777`
- 管理路由：`/cl/index.php?module=X&method=Y`（System/Member/Admin/Agent/Manage/Super 等）
- 代理登录：`POST /app/daili/login.php`，字段 `username, password, uid, langx, active, Submit`（active 默认 "1"，服务端忽略其变异）
- 前端 SPA（React）：`/m/login` `/m/signup`(会员) `/m/regagent`(代理)，静态资源走 CDN，`/cdn.php` 动态选 CDN

## API 架构（关键！）
```
POST /api/Public/main/index.php?service=Module.Method
已知 service：Server.GetCompany, User.Login, User.Register, User.RegAgent, User.isRegister, Uc.*, Member.*, Game.*, Bank.*
```

### ⚠️ GetCompany 需要 Referer + Origin 头
裸 POST `website=xxx` 一律返回 `{"ret":416,"msg":"请求的website不存在！"}`。
**加 `Referer: https://<host>/m/regagent` + `Origin: https://<host>` 后返回完整公司数据**：
```json
{"ret":200,"data":{"id":"125771","account":"2Zy9PFAF","code":"b8","client_id":"2e00195a7eff0cfb5ee4c2a8ebbe070200518814","client_ip":"207.168.55.31","ver":202107101859,...}}
```
- `client_id` 是 32+ 位字符串，**User.Login/Register/RegAgent 的必需参数**
- `client_ip`、`ver` 也要带上
- 实测 `9581kk.com` 认 `website=9581kk.com`（带 Referer 时）；试过的其它域名全 416

### 注册/登录参数
- `User.Register`（会员）：必需 `username, password, uname, ip, code, client_id, website`；报错逐条补参即可
- `User.RegAgent`（代理）：`agentid, username, password, uname, code, client_id, mobile, email, qq, wx, dy, password2, bankid, account, website, ip` + `safe_pwd`（取款密码，JS 里没有该字段但服务端校验，报 407 "取款密码格式错误"）
- 反自动化：`uid = md5(password + username + client_id + website + ip)` —— 缺它报 "请更新最新版本！ERROR:2"
- 验证码：`/api/Public/main/authCode.php?entry=1&client_id=<id>` 返回 41x20 GIF；**session 绑定**，过期极快（约 10-30 秒），必须 取码→立即提交

### 验证码协作流程（用户偏好，重要）
不要浪费时间 OCR 验证码。正确做法：
1. 新 session：`curl -c sess.txt <host>/` 拿 Example_Session
2. 同 session 拉验证码存盘
3. 用 `MEDIA:` 绝对路径把图发给用户，等用户回数字
4. 立刻用同一 session 提交注册（一个 session 一次尝试，失败就重开 session 再来）

## WAF 特征（Chinese WAF，Apache 前置）
| 行为 | 触发 |
|---|---|
| 406 统一页 (157B) | SQL 关键词：`OR 1=1`、`SLEEP`、`UNION`、`EXTRACTVALUE/CONCAT`、`%bf%27` 宽字节 |
| nginx 404 | 路径遍历 `../`（443 前置 nginx） |
| TLS 连接直接掐断 (000/0B) | 敏感文件名黑名单：`phpinfo.php`、`config.php`、备份/zip/.git/.env（所有编码绕过都无效） |

### WAF 绕过
- **`OR/**/1=1` 注释注入可过 SQL 关键词检测**（`admin' OR 1=1-- ` 被 406，`admin' OR/**/1=1-- ` 200）
- 单引号本身不触发 406，只有关键词组合触发
- 双重 URL 编码 `%256f%2552` 可绕过（WAF 解码一次，PHP 再解一次）——但登录点实测无时间差分，注入不成立

## 登录/会话
- `main_index.php` 直接访问报 `Template Error: filename: file ../../template//main_index.html does not exist.`——**必须带 `?uid=<临时UID>&langx=zh-tw`**（uid 是 8 位随机串，由外层 `/app/daili/index.php` iframe 生成）；空 uid 可渲染但无登录表单
- 443 上 `/app/admin/`、`/admin/`、`/manage/` 等全 404，**管理入口只在 7777**（`/cl/` 和 `/m/` SPA）；443 只暴露 `/app/daili/` 登录与会员站 `/m/`
- 任意 PHPSESSID/Example_Session + page_site cookie 就能让公开模板显示 `var is_login='1'` —— **纯前端假象**
- 受保护路由（Member/Admin/Game 等 module）全部返回 `<script>alert('您尚未登录，请登录！')...</script>`，做真实服务端会话校验 → 会话操纵越权走不通
- 弱口令（admin/123456、daili/daili 等）全失败

## 其它入口
- `:7777/api/` → 403（存在但受限）
- `:7777/cl/upupFlash.php`、`/refresh.php` → 200 空壳（无权限校验，但无内容）
- `crossdomain.xml` 通配（Flash/AIR 任意域+任意头）—— 旧客户端攻击面
- CDN（kfc.jfwdpc.com 等）只服务应用引用文件，无目录列表/遍历/配置泄露
- 多站同代码：一个站的注册/API 发现可反哺其它站；`GetCompany` 的 Referer 技巧同理
