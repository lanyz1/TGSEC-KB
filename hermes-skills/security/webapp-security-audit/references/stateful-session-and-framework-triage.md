# 有状态会话攻坚 + 框架版本三连(实测)

## A. 整页缓存 → 全站 CSRF 419(最高频拦路虎)

**症状**:任何 POST(登录 / 注册 / 加购 / 结算)恒定 **419 Page Expired**,反复重取页面、重建会话都无效。

**根因**:公开页被整页响应缓存(`X_CACHE_KEY` 这类按访客轮换的 cookie)。
**缓存 HTML 里的 `_token` 属于另一个访客的 session** → 必然校验失败。

**判别**(一眼确诊):
`Set-Cookie` 只给到 `X_CACHE_KEY`,**既没有 session cookie 也没有 `XSRF-TOKEN`**
= 该响应来自缓存,**根本没建立会话**。

**修复(Laravel,实测有效,顺序别换)**:
1. `GET /sanctum/csrf-cookie` → 204,必设 session + `XSRF-TOKEN`(该端点不缓存)。
2. 把 `XSRF-TOKEN` cookie **URL-decode 后**放进 `X-XSRF-TOKEN` 请求头
   (Laravel 原生支持,按 session 签发,与页面缓存无关)。
3. **body 里绝对不要带 `_token`** —— body 的 `_token` 优先级**高于** header,
   带上就还是用那张过期票 → 依旧 419。只发 header。
4. 客户端必须用真 `requests.Session()`。手写 cookie jar 处理 `Set-Cookie` 不稳,
   表现为**随机 419 / 静默丢登录态**,极难归因(本次踩过)。

**排错顺序**:连续 419 时,先看 `Set-Cookie` 里有没有 session cookie,再怀疑 token 本身。
不要把 419 当成「token 抓错了」去反复重取 —— 缓存场景下重取多少次都一样。

## B. 框架版本三连:落在区间 ≠ 可利用

1. **bundle 里的版本串可能是别的库**
   实测抓到 `3.15.12` 差点当 Livewire 版本用,取上下文一看是
   `Alpine.reactive / effect / raw / startObservingMutations` → **是 Alpine.js,证伪**。
   **先看上下文再下结论。** JS bundle 里常常**没有** Livewire 版本串,别硬找。

2. **用官方检测工具做指纹,并知道它的假阴性条件**
   Livewire 用 Synacktiv `Livepyre.py -c`(哈希指纹,**-c 是纯检测不利用**)。
   坑:它的存活判据是页面里是否出现字面量 `livewire` → 走 CDN / 回源改写就会**假阴性**
   ("Target does not seem to be running Livewire")。
   → 用 `/etc/hosts` 指向源站再跑(工具自带 `verify=False`,证书不匹配无妨)。
   依赖缺 `pycryptodome` 时装上即可(镜像超时换清华源)。

3. **必须看 CVSS 影响向量对不对得上目标**
   | CVE | 版本 | 影响 | 结论 |
   |---|---|---|---|
   | CVE-2025-54068 | Livewire ≤ 3.6.3 未授权 RCE | 真实 RCE | 目标 Livewire **3.8.0 → 已修** |
   | CVE-2026-48500 | Filament 3.0.0–3.3.51 登录页未授权上传 | `C:N/I:L/A:L` | **只影响可用性(磁盘耗尽),读不到任何数据** |

   目标 Filament 3.3.50 **落在区间内**,但 CVE-2026-48500 对「拿数据」目标**零价值**。
   → **先算清影响面再决定投不投时间。**「版本命中」不是结论。

4. **Filament 登录必须走 Livewire 协议**:`POST /livewire/update` + `wire:snapshot` 重放
   (`snapshot.data.data[0]={email,password,remember}`, `calls[].method="authenticate"`,
   需 `X-XSRF-TOKEN`)。直接表单 POST `/admin/login` 会 **405**。

## C. 附带:后台资源存在性 oracle

用 **302 vs 404** 判 Filament / 后台路由是否存在(未认证时会 302 到 login):
`/admin/users`→302 存在、`/admin/withdrawals`→302 存在、`/admin/password-reset/request`→404 不存在。
比瞎猜路径高效,且能直接圈出「有数据价值」的页面(用户表 / 提现 / 充值)。
注意 `/admin/`(带斜杠)可能 403 而 `/admin/login` 200 —— 那是 web 服务器的目录拒绝,不是鉴权。
