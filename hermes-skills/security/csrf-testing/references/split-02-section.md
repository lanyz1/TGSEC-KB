## 概述

CSRF（Cross-Site Request Forgery）利用浏览器自动携带Cookie的机制，诱导已登录用户执行非预期状态改变操作。现代防护体系包含 CSRF Token（Synchronizer Token / Double Submit / HMAC Cookie）、SameSite Cookie、Referer/Origin校验、自定义Header、CORS限制与新兴的 Fetch Metadata（Sec-Fetch-Site）与 CHIPS 分区Cookie。

本技能（v3.0.0）站在资深攻防专家视角，在保留 v2.0 全部核心内容（GET/POST/JSON/Flash/SOAP、Token绕过矩阵、SameSite绕过、CORS+CSRF链、Service Worker劫持）的基础上，新增：**登录CSRF与OAuth授权码CSRF（账户劫持级）、状态改变类API CSRF（WebSocket/GraphQL/REST PATCH/DELETE）、双提交Cookie绕过深化、Token位于Header但可通过CORS/JSONP泄露场景、Chrome/Firefox/Safari新SameSite语义差异、Service Worker/Cache poisoning实现的CSRF、CSPT2CSRF、CSRF→账户接管→业务影响完整攻击链、多步表单CSRF与Token传递、AI大模型辅助攻防**。全篇中文，Payload/PoC 可直接复制使用。

### 核心概念
- **CSRF三前提**：①受害者在目标站有活动会话（Cookie自动携带）②目标仅凭Cookie认证且CSRF防护缺失/可绕过 ③受害者访问攻击者可控页面
- **Site vs Origin**：SameSite 判定基于"site"（scheme+eTLD+1），CORS/SOP 基于"origin"（scheme+host+port）；子域之间是 same-site 但 cross-origin——这是大量链式攻击的根基
- **Synchronizer Token（同步令牌）**：Token存Session，表单/Header携带，服务端比对（有状态）
- **Double Submit（双提交）**：Token同时放Cookie与表单/Header，服务端只比对两者一致（无状态），存在Cookie注入/子域覆盖绕过面
- **SameSite**：`Strict`（跨站一律不携带）、`Lax`（跨站顶级导航GET携带，其余不携带）、`None`（必须配合Secure，全部携带）；无属性时现代浏览器默认视为Lax
- **Fetch Metadata（Sec-Fetch-Site/Dest/Mode/User）**：2023年起全部主流浏览器可用、JS不可伪造的请求上下文头，`.NET 11`、`Rails 8.2`、`Laravel 13`等框架已作为自动CSRF防护信号
- **第三方Cookie淘汰（2024-2026）**：Chrome逐步淘汰、Safari ITP强限制；`Partitioned`（CHIPS）Cookie把存储按顶级站点分区，改变CSRF的Cookie携带前提

### 2026防御现状速览（测试前提判断）
| 防御层 | 现状 | 对攻击者意义 |
|-------|------|-------------|
| SameSite默认Lax | Chrome 80+（2020）、Firefox 87+（2021）、Safari 16.4+ | 跨站POST默认不携带Cookie，但GET导航/2分钟窗口/方法覆盖可绕过 |
| Fetch Metadata | 2023起基线广泛可用，.NET 11已集成 | 服务端可拒绝`Sec-Fetch-Site: cross-site`，需寻找Header缺失/代理剥离场景 |
| 第三方Cookie淘汰 | Chrome 2025起逐步执行、Safari ITP | 依赖第三方Cookie的站点要么迁移，要么开SameSite=None（放大CSRF面） |
| CSRF Token | 仍是主流且有效 | 核心攻击目标：绕过校验或泄露Token |
| 双层防护 | Token+SameSite+CORS收敛 | 需组合链（XSS/CORS/子域/OAuth）逐个拆解 |

