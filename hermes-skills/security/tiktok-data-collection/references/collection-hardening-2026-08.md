# 采集链路加固（2026-08-26 实测：CK 状态误判 + 数据真实性 + getResponseBody 时序）

## 1. CK 状态误判修复：tokenBeat 唯一权威

**用户症状**：CK 失效后重新绑定，状态仍显示失效，无法恢复。

**根因**：`CookieAuthError` 混用两种语义——
1. 真失效（tokenBeat 失败）
2. 服务器采集被风控（Linux 浏览器环境指纹 → item_list 200 空 / SSR null）

cron 刷新（`refreshAccount`）把任何 CookieAuthError 都标 `UNAUTHORIZED` → 采集风控被误判成"Cookie 失效"→ 用户重新绑定（`updateAccountCookie`）又跑服务器采集 → 同样失败 → 状态永远无法恢复。

**铁律（已上线）**：
- `refreshAccount`：**先 `verifyTikTokCookie`（tokenBeat）→ 失败才标 UNAUTHORIZED**；tokenBeat 通过 → 采集失败仅 console.error，保持 BOUND
- `updateAccountCookie`：① tokenBeat 验证（无效明确报"登录态已失效"）② **代理兜底** `proxy?.trim() || account.proxy`（更新时未填代理沿用旧值——否则服务器直连香港 IP 采集必失败）③ 采集包 try/catch + **60s Promise.race 超时降级**（保留旧资料/空作品，`status:"BOUND"` 必更新）
- **生产误标修复脚本**：遍历 `status:"UNAUTHORIZED"` 的 cookie 账号 → `fetch token/beat` 直连验证（`error_code==="0"` 或 data.error_code 字符串 "0"）→ 仍有效者 `update status:"BOUND"`。实测用户账号 florenceyaretzi0 tokenBeat=true（CK 从未失效）→ 恢复。

## 2. 采集数据"与实际不符"：三个根因与修复

### 2a. 作品条数少（多作品账号）
滚动深度不够（旧 8 次固定滚动）→ 只采前几屏 → 平台显示"已同步条数"≠ 实际作品数。
**修复**：滚动直到「item_list 响应数」连续 4 轮无增长停止（最多 30 轮）；平台账号卡显示真实作品数（SSR videoCount）+ 网格标注"已同步 N/共 M 条"。

### 2b. getResponseBody 两大坑（Chrome 152 有头完整版实测）
1. **每个 requestId 只能取一次**——重复 `Network.getResponseBody` 返回空。滚动循环内反复遍历取 = 第一轮成功后全空 → 误判 stall → 提前退出。**必须按 requestId 缓存或滚动结束后统一取**。
2. **响应刚到时取返回空体**——`responseReceived` 事件后立即取，headers content-length 有值但 body 空（缓冲未完成）。**滚动结束 + sleep(2) 后统一取**才有效。

### 2c. content-length: 0 + HTTP 200 = 服务端风控空响应（判别法）
`Network.responseReceived` 的 headers `content-length: 0` + content-type application/json = **TikTok 服务器端降级**（不是 getResponseBody 问题）。此时**任何账号都空**（@tiktok 也空）——同 IP 高频访问触发临时限流（15min+ 恢复）。**判别**：先看 content-length（0=服务端，有值但 body 空=客户端时序）。测试时控制频率（间隔 ≥2min），生产 30min 刷新不受影响。

## 3. 真实作品数上报链路
- 客户端：SSR `__UNIVERSAL_DATA_FOR_REHYDRATION__` → `__DEFAULT_SCOPE__.webapp.user-detail.userInfo.stats.videoCount`（页面内 evaluate 解析）→ `upload_videos_sync(syncToken, videos, videoCount)`
- 服务器：sync API 接收 `videoCount`（zod `z.number().int().min(0).optional()`）→ `syncVideosFromClient` 更新 `TikTokAccount.videoCount`（仅 >0 时覆盖）
- 前端：详情页作品数 `account.videoCount > 0 ? account.videoCount : account.videos.length`；`videoCount > videos.length` 时标注"已同步 N / 共 M 条（用工具可同步更多）"

## 4. 服务器生产库运维备忘
- 服务器**无 sqlite3 CLI** → 用 Node + Prisma `.cjs` 脚本（**必须放 /srv/tikflow 下运行**，require 从脚本位置解析 node_modules；放 /tmp 会 MODULE_NOT_FOUND）
- 本地 paramiko 环境（sshvenv）被 python 3.14 破坏（distutils 报错）→ 用**系统 `python`（3.11.15，自带 paramiko）**跑 SSH 脚本
- 生产建号+充值走 `$transaction`（User.create + WalletTransaction RECHARGE COMPLETED + balanceAfter 留痕），bcryptjs hash 密码
