<!-- archived from /root/.hermes/skills/security/tiktok-account-binding/SKILL.md on 2026-10-21 -->

---
name: tiktok-account-binding
description: >-
  测绘引擎·用 when 排查 TikFlow 绑定账号卡"绑定中"或改代理必填/采集超时。
owned: true
tier: ops
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/tiktok-account-binding`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/tiktok-account-binding/…')`，不要相对 `references/legacy/` 解析。

# tiktok-account-binding（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/tiktok-account-binding/`

溯源（仅标记）：`hermes/software-development`

---

# TikTok 账号绑定链路运维（TikFlow 平台侧）

## 触发条件
- 用户问"绑定账号一直显示绑定中 / 卡住"
- 修改绑定接口校验（代理必填等）
- 评估服务器能挂多少账号 / 采集并发

## 绑定架构（关键认知）

绑定 = **tokenBeat 官方验证（最终裁决） + 浏览器采集（尽力而为）**：

```
POST /api/tiktok/bind {handle, cookie?, proxy}
→ bindAccount() → bindSchema.parse（proxy 必填）
  → verifyTikTokCookie(cookie, proxy)  # ★官方 tokenBeatWeb 快验证（秒级、精准、免浏览器）
      ├─ 失败 → 400 明确报错（proxy 失败→"代理连接失败"；否则"登录态已失效"）
      └─ 通过 → CDP 采集（尽力而为，失败不误判 Cookie 无效）
  → fetchProfileByCookie()   # 游客模式 goto 账号页，SSR 解析资料（含 secUid/昵称/头像/粉丝/视频数）
  → fetchVideosByCookie()    # ★游客模式采集作品（2026-08-19 起：不注入 cookie + stealth + 滚动监听 item_list 响应）
  → prisma.tikTokAccount.create({status: BOUND})
```

- **★tokenBeat = 唯一裁决（2026-08-16 上线，wukong 参考）**：绑定成败由 `passport/token/beat/web/` 官方接口 error_code===0 决定；CDP 采集（profile/videos）失败只回退空数据，**不再误判"Cookie 无效"**（解决 headless 指纹导致有效 CK 被误判的根因）
- **★fetchVideosByCookie 游客模式（2026-08-19 上线）**：登录态模式账号页不触发作品请求（TikTok 2026 架构）+ CDP 自动化被检测降级 → 改为**不注入 cookie** + stealth（webdriver/时区伪装）+ 滚动触发页面原生懒加载 + `page.on('response')`+`resp.buffer()` 监听 `/api/post/item_list/`。实测 @tiktok 79 条/17.8s。详见 tiktok-data-collection"游客模式 vs 登录态模式"节
- 无代理账号 → 共用 9223 常驻 headless 实例；有代理账号 → 动态 launch 独立实例（--proxy-server），用完关闭（代理必填后无代理账号已基本不存在）
- 定时刷新（instrumentation.ts `__ttRefresh`，默认 30 分钟）：只刷 **ACTIVE 投放中** 的账号，**并发 3 信号量池**（2026-08-17）；30 分钟频率远低于 TikTok 账号页降级触发线（同 IP 高频 10+ 次/短时才会触发，15min+ 恢复）
- **★多账号刷新并发(2026-08-17 上线)**:refreshActiveAccounts 串行 for 循环 → **并发 3 信号量池**(worker 数组 + Promise.all;12核/8GB 每实例 250-300MB,3 并发内存安全);100+ 账号 30 分钟窗口才刷得完
- **★代理地区标签 proxyTag(2026-08-17 上线)**:`stripSensitive` 剥离 cookie/proxy 时提取 `#备注`(如 #美国)返回 `proxyTag` 字段;账号卡片渲染地区徽章(多账号直观区分出口 IP);完整代理地址/凭据仍不外泄

## "一直绑定中"的修复模式（2026-08 实测有效）

根因：串行两次采集最坏 ~3.5 分钟 + 前端 loading 无超时 → 用户以为卡死。

三层修复（已上线生产）：
1. **后端并行**：`Promise.race([Promise.all([fetchProfileByCookie, fetchVideosByCookie]), 90s 超时 reject CookieAuthError])` —— 耗时减半 + 90s 必出结果
2. **前端超时**：fetch 加 `AbortController` 90s → 超时 setError(t("bindTimeout"))
3. **翻译键**：zh `绑定超时（90秒），请检查 Cookie 和代理后重试` / en 对应

后续遇到"绑定中"：先查 `pm2 logs tikflow --nostream`（bind 相关）、`curl 127.0.0.1:9223/json`（CDP 存活）、数据库无残留（卡在采集阶段不会建账号）。

## 绑定报 cookie_invalid 的两个失败面（2026-08-16 实测；★2026-08-19 已被 tokenBeat 裁决重构）

- 旧逻辑：profile 失败（代理不可达 ERR_PROXY / 90s 超时 / CK 真失效）与 videos 失败（Orca 拦 post/item_list 返回 200 空包）都会抛 CookieAuthError → route 统一映射 `{error:"cookie_invalid"}` → 前端误导"Cookie无效或已失效"
- **★现状（tokenBeat 上线后）**：`verifyTikTokCookie`（官方 passport 接口）先行——**CK 是否有效由官方裁决**，失败 400 明确报错（proxy_error / cookie_invalid 二选一）；通过后 CDP 采集失败只回退空数据，**不再产生 cookie_invalid 误报**。Orca 拦 item_list / 游客模式采不到作品 → 空作品列表 + 前端可见（不再伪装成 Cookie 失效）
- 排查顺序：先看绑定请求有没有建库（无残留 = 卡在采集期）；再跑复现探针判别三接口；tokenBeat 通过 = CK 有效，问题在采集层（IP 降级/Orca），不是 Cookie
- 探针：`scripts/repro-bind-flow.js`（见 tiktok-data-collection：profile/recommend/post 三接口 + tt_orcas_res 响应头）

## 代理必填（业务铁律，2026-08 定案）

"全部的账号都要有独立的ip，没有提交独立的ip的直接不能在官网绑定"：

```ts
proxy: z.string().min(7, "proxy_required").max(200)
  .regex(/^(https?|socks5h?):\/\/[^\s]+$|^[^\s:@/]+:[^\s@/]+@[^\s/]+:\d+$/, "proxy_format"),
```

- 正则允许：`socks5://u:p@host:port#美国`（#备注剥离在采集层）、`http://u:p@h:port`、`socks5://h:port`；**拒绝裸 `host:port`**（必须带 scheme）
- 前端：`if (!isUpdate && !proxy.trim()) setError(proxyRequired)` —— **刷新已有账号允许不填（沿用 account.proxy）**；新绑定必须填
- i18n：`proxyOptional` → `proxyRequired`（"必填 · 每账号独立 IP"）；placeholder 注明"需与登录 TikTok 的网络 IP 一致"
- 存量迁移：绑定前查库（cookie 账号数），无历史数据则无需迁移

## 服务器容量模型（12 核 / 8GB EPYC 实测）

| 维度 | 数值 |
|---|---|
| 内存 | 8GB（可用 ~6.9GB），headless shell 每实例 ~250-300MB |
| 有代理并发 | 同时 ~15-20 独立实例 |
| 无代理并发 | 共享 9223 实例，20-40 page 没问题 |
| 刷新上限 | 30 分钟窗口 ÷ 每账号 15-30s ≈ **60-100 账号/轮**（串行瓶颈） |
| 风控上限 | **无代理 ≤3 个**（共用服务器香港 IP，关联风控）；有代理（独立 IP）50-100 安全 |

超 100 账号 → 刷新改并发 3-5（内存够）；无代理多挂 → 需购买多出口 IP。

## 生产验证路径

- SSH 通道（本机无 sshpass，用 plink）：`/d/ClaudeCode/bin/plink -ssh -P 14003 -pw '<密码见memory>' -hostkey 'SHA256:GG74T6a+eiafXIVTI12orcHMqEFlAHS/OR8tlQe3y5s' -batch root@118.107.3.134 "cmd"` —— 首次连接必须 `-hostkey` 显式带指纹，batch 模式才不中断；传文件：`plink ... "cat > /tmp/x" < 本地文件`；坑：git-bash 的 /tmp 与 Windows Python 的 /tmp 不是同一个（后者在 C:\tmp），跨工具传文件用显式路径
- DB：`cd /srv/tikflow/prisma && python3 -c "import sqlite3; ..."`（prod.db；node -e 的 prisma 输出会炸，用 sqlite3 更稳）
- 接口强制逻辑验证：本地 `node -e` 用 zod 直接跑 schema 断言（路由层先验 session 会 401，测不到 schema）
- pm2 环境快照坑：改 .env 后必须 `export VAR=值 && pm2 restart --update-env`

## 关联

- 客户端抓 CK 工具（GUI exe/内置代理/云端更新）：见 `tiktok-ck-tool-dist`（user-owned，需 `hermes curator adopt` 后才能改）
- 采集数据通道：见 `tiktok-data-collection`（user-owned）
