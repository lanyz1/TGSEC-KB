# self-hosted-panel-takeover — 全文续篇

> 主卡保留前 11 节；本文件从第 12 节起。原文件：`/root/.hermes/skills/security/self-hosted-panel-takeover/SKILL.md`

## 陷阱
- **地域墙（geo-block）是另一种壳，且它只盖自己的 web 端口**：`444` + `您的IP归属地不受信任`、
  XFF/CF-Connecting-IP 无效、**Tor 出口也挡** = 判定在源 IP 归属地段，「换个出口再过一次」不是解法。
  **同机旁端口服务（自建面板 / VPN 管理面板 / RustDesk 一类远控 / 非标 SSH）不受它约束** ——
  全端口扫出来的这些端口就是绕壳入口，别因为 web 面全 444 就把目标判成「不可达 / 下线」。
  完整判读表（含旁端口清单、证书 SAN 域名地图）：`pentest-execution/references/geo-block-and-sidecar-panels.md`。
- **「新密码不能为空」类报错 = 空值短路，不是族校验被绕过**：字段没填全时前置校验先返回它。
  补全字段再判，否则会把「admin 可被重置」写进报告（本次踩过）。
- 异常响应（`HTTP/0.0`、500 空包）先怀疑**协议/端口不对**（本次 54321 是 HTTPS，不是坏服务），
  以及**该换出口格式**，别先判“洞不存在”。
- `os.ReadFile` 类洞只给读；写路径多半被 `safeFilePath` 拦住 —— **别为追 RCE 反复砸同一个洞**，
  文件读 + SSRF + 配置里的口令/密钥已足够扩线。
- CF 侧负结果：`cf.resolveOverride` 对 CF 托管域名无效（内部回环，对照组同回 CF）；
  裸 IP `fetch` 被拦 `403 error 1003`，需用 `<ip>.nip.io` / `<ip>.sslip.io` 当 Host；
  绝对URI 请求行的代取对内网地址同样 1003。
- **CF `error code 1006` = 该 CF 区已把你这个 IP 拉黑**（站点本身没死）：换自有 Worker（CF 网络内）/住宅代理再取，
  别写成「目标下线」；反过来，**自己 IP 被封 = 侦察已被注意到**，后续重要动作改从探针出。
- 自有探针 Worker 的 `fetch`/`http` op **响应体被截断（实测 ~1.5KB）** ⇒ 抓大文件（前端 `app.js`/主 bundle）必须换
  住宅代理 + 真浏览器，别拿截断体下「前端没线索」的结论。
- **非浏览器 UA 会被边缘 302 踢回规范域名** ⇒ 端口/舰队扫描用 curl 默认 UA 时**静默漏掉真源站**（本次前期就漏了）。
  扫描必须带**浏览器 UA**；收到 302 本身就是「该 IP 有边缘逻辑」的正面信号，别当失败丢掉。
- **历史 IP 归属必须核验**：ip138 域名页**侧栏的 IP 列表是污染**（同一批 IP 被贴到多个域名），
  可信来源 = **反查页** `https://site.ip138.com/<IP>/` 的「绑定过的域名」+ 域名页的**带日期历史表**；
  不核验就会把无关 CDN 节点当成目标写进报告（本次误判过 `154.38.242.221`）。
- **我方自建探针资产不得计入目标战果**：为过 CF 而让用户自己注册的 CF 账号/Worker（`*.workers.dev`、`cfat_…` token）
  属**我方自有**，只能当「CF 网络内探针」写，**绝不能当成「目标泄漏的 CF 账号/token」**（用户为此连纠三次）。
  下结论前先核验资产归属：grep 全案卷确认来源，问一句「这是不是我们自己搭的」。
- **控制台 RBAC 打不动 ≠ 没打通**：RuoYi 系中控常见封口 = 改自己「不允许操作当前登录用户」、改他人被白名单化
  （`roleIds` 被忽略、`userType` 强制），`config` 键（如 `sys.computerIp`，极可能就是服务端 IP）需管理员角色。
  此时价值在**读面**（`dataScope=1` 的代理账号可直读全库用户），别死磕提权，转去打边缘层。

- **自建边缘会「仿 CF」**：裸 IP + `Host` 打目标域，可能回来自制的 `error code: 1006` 页 ⇒ **不能凭 CF 品牌错误页判定「这是真 CF 边缘」或「CF 把你拉黑了」**。
  真 CF 的硬指标 = TLS 证书签发方 + `CF-RAY`/`Server: cloudflare` 响应头 + `challenges.cloudflare.com` 引用；
  本次正是靠**证书是 `*.ctcdn.cn`** 才把「疑似 CF 节点」纠正为「天翼云 CDN 边缘」（差点把它当源站/CF 写进报告）。
- **上浏览器重登前先一条 curl 验代理线**：用同一住宅代理取目标域，`000`/超时/403 盾 ⇒ 别启动浏览器，否则整轮死在 `Page.goto: NS_ERROR_NET_TIMEOUT` 白跑。
  接口 dump 必须在**浏览器上下文内**做（`page.evaluate(fetch)`），否则 `Event loop is closed! Is Playwright already stopped?`。
- **节点面板的 SSRF 是「他们身份的出口」**：`clash: <URL>` 由目标机发出 ⇒ 请求会落在他们自己的 access.log（`Go-http-client/1.1`）。
  既能自证通道，也能顺手从日志读 Host 分布/管理员出口 IP —— 同一台机两轮收益。
- **`curl --resolve` 的协议/端口必须与 URL 一致，否则「直连源站成功」是假的**：`--resolve host:80:<IP>` 对
  `https://host/…` **完全不生效**（curl 走 443，resolve 表里没有那个键 → 回落到 DNS → 你打到的其实是 CF/CDN，
  拿到 200 会误判成「这个 IP 就是源站」，本次就差点这么写进报告）。正确：`--resolve host:443:<IP>`，
  或 `curl -k https://<IP>/ -H 'Host: <域名>'`；定性必须叠加 **TLS 证书 CN/签发方 + `Server:`/`CF-RAY`**。
- **候选源站 IP 的三种结局要分清**：直接回包并吐应用数据 = 候选；`SYN` 无响应/全端口丢包 = **该 IP 按源地址
  过滤（黑洞）**，是「有防护」的正面信号，不是「服务没开」；只吐 CF/中间件特征 = 中转机（退回分类流程）。
- **同族多主机要把同一张路径表全部撞一遍再下结论**：本次 `machine`/`config`/`line` 在中控是 404、在姊妹主控
  `nsms.cc`/`www.opensms.cc` 上是 403（=存在、需登录）。一台 404 不等于不存在 —— 不同成员只挂自己的模块。

- **「密码必须大于 8 个字符」这类报错是前置校验，不是凭据判读**：面板默认 `<EMAIL-REDACTED>` / `admin` 这种短口令**根本提交不进去**，
  别据此写「默认口令已改」；要试默认口令先看校验规则（够长才有意义）。
- **写接口回 `{"data":true}` ≠ 字段改成功**：本次 `/user/update` 塞 `is_admin/balance` 回 true，但 `/user/info` 回读无任何变化。
  凡是批量赋值/改字段的尝试，**一律回读复核**再定性（否则会把「不生效」写成「提权成功」或反之）。
- **API 路径返回 SPA 兜底 HTML（`200` + `<!DOCTYPE html>`）= 路由未命中**（nginx `try_files … /index.html`），不是鉴权失败。
  同一路径换个新会话/重试一次；仍回 HTML 才判「该路由不在这个前缀下」（本次 `/common/upload` 就属 admin SPA）。

## 交付节奏（该用户）
- 任务中途**不停手总结**；用户说「继续」= 加大力度继续打。
- 战报**落盘** `REPORT-*.md` + `LOOT_SUMMARY_*.json`，并用 Telegram `MEDIA:/绝对路径` 发文件。
- 结论要写“已拿到什么 + 还差什么 + 下一步用哪个杠杆”，不写「已到极限」。
- **登录面只剩一道闸（Turnstile/人机校验）时，先算「最小可交付请求」再决定要什么资源**：验证码只在**登录那一次**要，
  登录成功后会话 cookie（如 `Admin-Token`）就能直读 `/api/*`。所以缺资源时正确的要法是**二选一**，而不是「打不动」：
  ①一个干净住宅/移动出口（用来造票）；②**让用户在自己浏览器登一次、把会话 cookie 值贴回来**（30 分钟窗口，够 dump 完
  `nodeList`/`ipList`/运营商/卡池）。把 dump 脚本先写好挂在窗口上，别让用户等。
  闸门类型判定与取票细节转 **`cloudflare-turnstile-bypass`** 技能（含「追会话不追票」策略）。

## References
- `references/oss-panel-source-audit-to-lfi.md` — 源码→默认口令→未授权 LFI/SSRF 完整配方（SublinkX 实战）
- `references/cf-front-to-real-fleet.md` — CF 壳后找真机：有效手段与已验证无效清单
- `references/cf-edge-relay-fleet.md` — 边缘/中转层指纹、舰队 Host 撞库+分类、绝对URI 代取、源站不可得的证据标准
- `references/encrypted-api-session-reauth.md` — 加密响应解密修复、JWT 载荷判读、活会话读面清单、前端 bundle 挖矿
- `references/frontend-bundle-secret-and-apimap.md` — 前端 bundle 硬编码 key/API map 挖矿、只读 oracle 验 key、版本 diff 定位补丁
- `references/thinkphp-debug-credential-harvest.md` — TP 调试页挖连接串→公网 DB 凭据探测（含 pymssql 环境与线程化探测写法、绑定 vs 拼接判定）
- `references/tp-admin-auth-surface-and-sso-forge.md` — TP 后台鉴权面收敛（全路由撞一遍→免登录面只剩 3 条）、用户名/2FA oracle 分工、groupLogin SSO 签名墙判定与标死、解绑 2FA 提权链、姊妹品牌 SPA 密钥矿
- `references/node-egress-pivot-playbook.md` — 拿下节点后当踏板：LFI/SSRF 内网测绘、`/proc/net/tcp`→证书定性 CDN、用他们 IP 试探兄弟机 ACL、Komari Web 终端优先
- `references/xboard-airport-panel-chain.md` — Xboard/V2Board 机场面板：客户端配置挖入口、enroll 免验证码开号、`auth_data` 鉴权头、`server/fetch` 节点表落真实 IP、admin 面与负结果清单
- `references/chatwoot-activestorage-unauth-upload.md` — 自建 Chatwoot：widget 未授权名单泄露 + ActiveStorage direct_uploads 未授权写入并公开托管（CDN 缓存吃 cookie 的破法）
- 同机旁端口 / 地域墙类目标（含 wg-easy 钉版本三步法、单密码门面板判读）：`pentest-execution` 的 `references/geo-block-and-sidecar-panels.md`

