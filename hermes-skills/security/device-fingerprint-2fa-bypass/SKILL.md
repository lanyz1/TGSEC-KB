---
name: device-fingerprint-2fa-bypass
description: "Use when login is gated by device fingerprint OTP."
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
---
# 设备指纹 2FA 绕过（hasFp / 新设备验证族）

## 触发条件
- 登录响应带 `hasFp:false` / `deviceBound:false` / `trustedDevice:false` / `newDevice:true`
- 前端代码分叉：绑定过就走 password grant 直发 token，没绑过就弹 OTP 表单
- OTP 发往目标真实邮箱/手机，我方收不到
- 目标同时存在「完整注册」「快速注册」两个入口

凭据本身正确但进不去 —— **这不是密码问题，是设备信任状态问题。别再爆破密码。**

## 核心模型
```
登录第一跳（ver-fp / check-login / pre-login）:
  {usrnm, pw, fp}  →  {suc:true, hasFp:false, eml:"a*****@x.com"}
                         ↑ 密码已验过    ↑ 设备未绑 → 强制 OTP
绑定过的情况:
  {suc:true, hasFp:true}  →  前端直接调 OAuth2 password grant
                          →  {access_token: JWT}   无 OTP
```
指纹字段通常成对：`fp`（主）+ `fpPlus`（增强/环境指纹）。**两者必须全程一致**，
服务端多半只存 `fp` 但会比对 `fpPlus` 的稳定性。

## 绕过阶梯（成本从低到高，逐级试）

### 0 级：先确认凭据真伪（开口就问清，别瞎爆）
`ver-fp` 类登录第一跳本身就是**完美 oracle**：
- 错密码 → 专用错误码（如 `30039`）
- 对密码 → `suc:true` + 掩码邮箱
一句话分清「密码错」还是「被 2FA 挡」。**任何登录卡住，先做这个对照实验。**

### 1 级：注册即绑定指纹 —— 最高成功率
找**快速注册 / 免验注册**入口，提交里带 `fp`、`fpPlus`：
```
POST /.../qck-reg
{ctryCode, curCode, usrnm, pw, refCode, fp, fpPlus}      ← 无 otpCode、无 eml
→ {suc:true, data:{id:..., usrnm:...}}
```
注册动作把指纹写进设备表，于是**新号天然 `hasFp:true`**：
```
ver-fp  → {hasFp: true}
OAuth2  → {access_token, refresh_token, expires_in:299}
```
**整条链闭合，2FA 被整个跳过。** 建号成本 = 一次拼图验证码 + 一个推荐码。

### 2 级：找免鉴权的「预绑定」端点
从端点表里捞这类名字，用新号 token 试：
`crt-pin` / `bind-fp` / `enroll-device` / `trust-device` / `ver-fp` / `upd-fp`
有的站允许「先绑后验」，绑完再登录就不弹 OTP。

### 3 级：参数缺席 / 空值 / 类型混淆矩阵
对 `ver-fp` 和 `ver-otp-fp` 各跑一遍：
`fp` 缺失 / `fp:""` / `fp:null` / `fp:0` / `fpPlus` 缺失 / `fpPlus=fp` / `fpPlus:""` / 两者互换
部分后端把「缺 fp」当成「已是信任设备」直接放行；部分回落到纯密码校验。

### 4 级：OTP 发/验端点分流 + 软 oracle
- **send 和 verify 经常不在同一服务前缀**（如 send 在 `prv`、前端 import 看着在 `ply`）→ 一轮 170002/404 立刻换前缀重扫
- 有的 `verify` 端点前端标 `secure:!1`（明文）却仍要加密 body → 明文回 `999984`/解密失败码，不是格式错
- **`otpCode` 省略 vs 空串语义不同**：省略 → `Otp Not Found`（按账号+用途查不到）；空串 → `Invalid OTP`（记录找到了，按值匹配不过滤）→ 说明后端按 otpCode 值查表，记录是活的
- 类型混淆（int vs str、`"001234"` vs `1234`）跑一轮，偶有弱类型后端放行

### 5 级：爆破 —— 先算数学再动手
- 位数从 JS 抠：`grep -o 'length([0-9])'`
- **4 位 = 1 万**，5 分钟窗口 @240 req/s ≈ 2.4 万 → 覆盖得下，值得打
- **6 位 = 100 万**，@240 req/s 需 ~70 分钟不间断 → 撞限额+WAF，实际不可行，别投时间
- **限额按 IP 不按账号**：`170009 reached maximum` 是出口 IP 的滚动窗口。
  先测「本机 IP vs 跳板 IP」额度是否独立 —— 独立的话换出口就是换满额
- WAF 红线（实测 CF）：`~240 req/s` 安全；`496 req/s` 立即全空响应；`16 线程 × 240` 触发 Human Verification。控 ≤10 线程

## 侦察：grep bundle，别猜
```bash
# 登录/注册真正的提交对象
grep -o 'quickRegister[A-Za-z]*\|registerPlayer\|ver-fp\|verFp\|lgt\b' *.js
# 路径变量定义（服务分区前缀）
grep -o '="/gtw/[a-z]*"\|="/api/[a-z]*"' *.js
```
**最关键的一行判断：注册函数参数里有没有 `otpCode` / `eml`。**
没有 = 这个入口不需要验证码，直接省掉整个 OTP 难题。
再从 JS 还原「路径变量 → {method, secure}」契约表，比黑盒猜快 10 倍。

## 客户端加密场景的性能纪律
- 加密（AES-GCM + RSA-OAEP + HMAC 之类）必须本地算，别指望网关明文放行
- **把客户端搬到跳板机本地跑 `requests`，不要用 SSH 转发 curl**：实测 7s/req → 0.3s/req，20 倍差距，直接决定爆破可行性
- **先做对照实验**：拿一个已知能通的端点（如 `get-profile`）验证加密/签名正确，**再去扫**。
  否则 240 req/s 跑的全是无效请求，白烧一小时还以为「端点不存在」

## 别浪费时间的地方
- **RS256 + 公开 JWKS ≠ 可伪造**。`alg=none`、HS256+PEM(SPKI)、HS256+PEM(PKCS#1)、HS256+n 原始字节、HS256+b64(n) 五种变体在成熟网关**一律 401**。确认一次就收手
- **强制自作用域 ≠ IDOR**：传 `plyId=1`/`usrnm=别人` 被静默忽略、恒返回自己的数据，是授权做对了，别报成漏洞
- **SPA fallback 假阳性**：`GET /api`、`GET /gtw/xxx` 根路径返回 HTML 是前端壳，不是端点存在
- 同一路径在多个前缀下都要试：在 A 前缀 404/999999，在 B 前缀可能直接通

## 参考
- `references/wtlb-gateway-family.md` —— WTLB 网关族（`wtlb-prtl-app`，hengongbet.cc / merCode wlm）完整现场：
  六分区前缀、加密头、可用端点契约、错误码全表、注册→token 全链、mer 无鉴权泄露、已试死路清单
