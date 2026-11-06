---
name: auth-surface-exhaustion
description: Use when an admin login resists every bypass.
---

# 认证面穷尽（打不动时怎么量化并撤出）

前门被彻底堵住时的固定流程。目标不是「再试一次爆破」，而是在一两个小时内把**还有没有门、门有多硬、哪条线值得挂长期**全部量化，写成交付级结论，而不是凭感觉说打不动。

触发词：后台进不去 / 只有 401 / 账号被锁 / 换 IP 还锁 / 打不动了 / 继续深挖 / 要不要放弃。

## 0. 先分诊：这是「单点硬」还是「整面硬」

- 逐层判：边缘（CDN/WAF）→ 反代 → 应用拦截器 → 业务守卫。每层用一个不存在路径和一个存在路径对照。
- 全站唯一 401 + 全站统一 JSON 错误体 → 拦截器在 servlet/filter 层，路径绕过基本无望（但仍要跑完 §4 矩阵再下结论）。
- 同一台机挂多个 vhost 很常见：管理端可能直连源站、业务 API 走 CDN。**每个域名都 `dig`，逐个带 `Host`/SNI 打源站 IP 对比**，常能发现「边缘只保护了一个域」。
- 源站对未知路径一律回 SPA fallback 时，`/actuator`、`/swagger-ui`、`/druid`、`/.env` 全 200 是假象——看 `content-type` 和首字节，别直接写「发现泄露」。

## 1. 从 bundle 反推鉴权语义（不试就知道几道门）

管理端错误码语义就写在前端响应拦截器里，先读它再决定打什么：

```
grep -oE '.{200}t\.code===[0-9]{4}.{200}' index.js
grep -rhoE 'is[A-Z][A-Za-z]+Required|loginType|accessToken|captcha|googleCode' ch/ | sort -u
```

真实命中过的收获：

- `code===4001` + `isGoogleAuthRequired` → 密码之后**还有 Google 2FA**。口令线最多算半程。
- `code===10014` + 「IP 不在后台访问白名单内」→ 口令命中后**还有 IP 白名单**，提前想好下一步。
- 每个数值分支都抄下来（冲突确认/风控/锁定/验证码），后面全靠它判响应。
- 同时提全部 `url:"..."` 模板形成端点全集；SPA 的 chunk 目录就是 admin API 地图，一次提完比逐个猜快一个数量级。
- 登录响应字段名决定伪造令牌的 claims 形状。**先解一次真 token**：`jti/uid/sess/typ/iat/exp`。`sess` 内嵌 JSON（deviceId/kycStatus/tokenVersion）= 令牌绑会话+设备、有版本号可吊销。

## 2. 令牌伪造矩阵（一次跑完，别反复试）

对每个服务各跑一遍：`alg:none`（三种大小写）/ 空签名 / `kid` 注入（路径穿越+SQLi）/ `HS256` 弱密钥 / 真 token 改 `uid`/`tokenVersion`。全 401 就判死并写进报告。

两个关键判读：

- 三个服务（app/admin/IM）对**同一个 token** 全 401 → 互不共享密钥，别幻想「拿 App 的票进后台」。
- 令牌可能绑会话：存盘后新进程/新握手复用会回「登录状态已过期」。不是 token 坏，是绑了登录时的 handshake session/deviceId。修法：handshake → login → 立刻 set_token → 继续扫，**全程同一个客户端对象**，别反复重登浪费时间。

## 3. 注入/逻辑先证伪，再宣称

- **基线优先**：列表/排序端点先发空参。空参就 500 = 接口本身坏的（NPE），后面带 payload 的 500 不算注入信号。
- 排序白名单看**回显**：`sortField:"<注入串>"` 而响应 `sort.field` 仍是 `CREATED_AT` 且零延时 → 白名单化，收手。
- 验证码：测复用（同码两次）、过期、空值、类型混淆。一次性 token 复用回错误码 = 封死。
- 越权用**两个活对象**：建 A/B 两会话各造一条记录交叉互读。`10007 会话不存在` 这类模糊串区分不了「不存在」和「不是你的」，双活对象交叉读才能定性。访客型系统（客服 IM/工单/购物车）一律这么测，见 `references/visitor-widget-and-two-object-idor.md`。

## 4. 路径/头绕过矩阵（一次跑完）

`//admin`、`/admin/..;/`、`%2e`、`%61dmin`、`;.js`、`/./admin`、大小写、`X-Forwarded-For`/`X-Real-IP`/`True-Client-IP`/`Forwarded`、`X-Original-URL`/`X-Rewrite-URL`。全返回同一个 401 体 → 拦截器在 servlet 层，判死。

## 5. 锁阈值实测 + 长跑节奏

- 顺序 6 发错口令，第几次转 `430` 就是阈值（实测过 **2 次失败 / 30 分钟**）。
- 换出口（Tor/代理）复测：仍锁 = **账号锁**，换 IP 无用，别再买代理。
- 节奏 = `1440 / (锁时长 + 余量)` 每账号每天；1000 条定制字典 × 3 账号 ≈ 一周。
- 430 当轮作废不重试；429 退避 10 分钟，别把 IP 层也打爆。
- 定制字典 > 通用字典：品牌/域名/运营方人名/年份/`@123` 组合。被 rockyou 打空过的目标别重跑同一本。

工具：`scripts/lock_threshold_probe.py`（测阈值）、`scripts/lock_safe_slow_brute.py`（可续跑长跑器），数学与字典构造见 `references/lock-threshold-and-pacing.md`。

## 6. 交付：把「打不动」写成结论

报告只写实测，每个结论带证据形态（状态码/错误串/端点计数）：

- 端点全图：`N 个 JSON 端点，未授权 0（全部 401）` 这种数字比「鉴权严格」有用。
- 封死清单逐条：alg=none 全拒 / 路径矩阵全拒 / 排序白名单 / 验证码一次性 / 双活对象越权全拒。
- 正在挂的动作 + 节奏 + 命中后会怎样。
- 剩余可打面（新版 wgt/CVE、上游支付供应商、源码泄露），而不是「已挖到极限」。

## Pitfalls

- 别用 `nohup ... &` 起长跑（前台包装会被拦），用 `terminal(background=true)`；状态落盘以便续跑。
- 命中判据是**响应里出现 token 字段**，不是 `code==200`（很多站 200 也带错误包裹）。
- 大量脚本输出被折叠/截断时别重复猜：结果一律落盘 JSON/日志，再单独读文件统计。
- 用户说「继续」= 加深不是收尾；挂着长跑时不回来问「要不要继续」。阶段性结论落 `REPORT_R<n>_<date>.md` 并以 `MEDIA:` 发文件。
- 别把「失败」当结论：两条 500 基线、三次 401 不是穷尽，先跑完矩阵再写「无」。
