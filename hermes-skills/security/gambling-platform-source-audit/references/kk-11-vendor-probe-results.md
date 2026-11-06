# 厂商 API 实测结果（2026-08 第1轮：IP 白名单探活 + JILI 深挖）

## 批量探活方法论

对每家厂商发一个**最简只读查询请求**（GetBalance/SearchMember/autologin 等，从 GameTo*.php 的 Select/Register 复刻签名），按响应区分防护等级：

| 响应特征 | 判定 |
|---|---|
| `Access denied: not in allow list` / `Invalid IP` / `IP not allowed: <ip>` / `not-whitelisted` | 🔴 有 IP 白名单，本地直调不可行（需服务器出口 IP / SSRF） |
| `{"ErrorCode":0,...}` / 200 正常业务响应 | 🟢 **无 IP 白名单**，可本地直调 — 立即深挖 |
| `invalid key` / 签名类错误 | 🟢 无白名单但签名未复刻对（修签名后重试） |
| 403 空 body / nginx HTML 403 | 🟡 疑似 nginx 层 IP 拦截 |
| 1010 (Cloudflare) | 🟡 浏览器签名拦截，带完整浏览器 UA+Referer 重试 |

注意：**打包者可能截断 config 里的密钥**（CQ9 token `eyJhbG...7JFI` 只剩头尾）→ 该厂商无法本地实测，在报告中标注凭证缺失。

## 实测结果表（11 家）

| 厂商 | 探活响应 | 白名单 | 结论 |
|---|---|---|---|
| **JILI** | `{"ErrorCode":0,"Data":[{"Account":"kkzonghe...","Balance":0,"Status":2}]}` | ❌ 无 | 🟢 **唯一可直调**，深挖见下 |
| PG | `Access denied: not in allow list` | ✅ | 需服务器 IP |
| EVO | `Invalid IP` | ✅ | 同上 |
| EEAI | `not-whitelisted` (408003) | ✅ | 同上 |
| JDB | `IP not allowed: <ip>` (9001) | ✅ | 同上 |
| XINGLI | `IP not allowed` (code 8) | ✅ | 同上 |
| IM | 403 nginx HTML | ✅ 疑似 | 同上 |
| FC | 403 空 body | ✅ 疑似 | 同上 |
| CQ9 | —（token 被截断） | 无法测 | 凭证缺失 |
| TCG / PP | 未测 | — | — |

## JILI 深挖（签名全复刻 + 跨平台信息泄露实锤）

**签名机制**：`key = 6位随机 + md5(参数串 + keyG) + 6位随机`，`keyG = md5(UTC4Time + AgentId + AgentKey)`，
`UTC4Time = yymd`（UTC-4 时区，**日去前导0**，如 `260731`/`26077` — 格式错了会返回 `invalid key`）。

接口清单与结果：

| 接口 | 参数（GetMemberInfo 例） | 实测 |
|---|---|---|
| `CreateMember?Account=<id>&AgentId=<aid>&Key=<key>` | key=6r+md5("Account="+id+"&AgentId="+aid+keyG)+6r | ✅ ErrorCode=0（重复=101） |
| `GetMemberInfo?Accounts=<id>&AgentId=<aid>&Key=<key>` | 同上（Accounts 复数） | ✅ **任意玩家余额可查** |
| `GetBetRecordByTime?StartTime=<ISO>&EndTime=<ISO>&Page=1&PageLimit=10000&AgentId=<aid>` | 时间窗口 **≤60 分钟**，ISO `Y-m-dTH:i:s`（UTC-4） | ✅ 742 条注单/小时 |
| `Transfer?Account=<id>&TransactionId=<txn>&Amount=<amt>&TransferType=2&AgentId=<aid>` | TransferType 2=转入 1=转出(Amount=0 全转) | ⚠️ `ErrorCode=4 service unavailable`（厂商侧限制转账） |
| `LoginWithoutRedirect?Account=..&GameId=..&Lang=..&AgentId=..` | — | 未测 |

**🔴 跨平台信息泄露（实锤）**：KK 的 JILI AgentId `KKOK_Anony_USD` 下挂了 3 个平台的玩家：
`yfzonghe*`（永发平台）639 条/时、`qdzonghe*`（QD综合）100 条、`mymy*` 3 条。
- 任意玩家余额可查（GetMemberInfo）
- 近 1 小时全平台注单可拉（BetAmount/PayoffAmount/GameId/Status/SettlementTime 全字段）
- 玩家 TG ID 全枚举、大户资金动向透明

**JILI Transfer 状态**：持续 `service unavailable` — 疑似厂商对该 AgentId 关闭转账（风控）。若恢复，`TransferIn → 平台转出 → 提现` 闭环即成立。

## 平台侧实测要点（同轮）

- 线上域名以小程序实际 `location.href` 为准（源码 config 可能是旧域）；`api.html` 与 `api.php` 常等价（nginx 重写）。
- Cloudflare 前置：默认 curl UA → 403 无 body；带浏览器 UA → 到达后端（400/真实响应）。先诊断 UA 再下"端点被拦"结论。
- 线上版本与打包源码差异大：`SIGN_ERROR`（KKPay）/ `签名验证失败`（Anony）= 已加固，P0 在线上不可用。
