# 案例：UU来国际（uulai/skaov 系赌博站）— CF + Geetest v4 + 注册链全破（2026-10）

## 目标概览
- 前端 H5: `https://uulai-h5.sdlkgjsoiod.com`（品牌域 uulai.com / uulaigf.com / uulai.net 等全跳此站）
- API 后端：Spring 微服务族 `com.u8project.jinghe`；平台 = 多租户 SaaS（`skaov.com` zone：uulai-lottery/lobby 及各多国产品 prod/uat/test；对外硬封 Tor/机房 IP，全弃）
- 租户：`cash1010506477`；客服体系：@uulaikefu / @UUlaidaili / @uulaicaiwu11 / 美洽 yk6z9.qbchat.cc
- TG Bot：UUlaii_bot (7649743615)，小程序投注入 @uulaii_bot

## 入场链（最终成功路径）
1. **CF JS 挑战**：patchright（Xvfb、headless=False、`--disable-blink-features=AutomationControlled`）+ locale=zh-CN，能过；requests 不行。
2. **注册页** `/register`：字段 用户名/密码(8-12)/确认密码/TG用户名或手机号(必填，`@名` 会「不合法」，纯数字或裸用户名可过)/邀请码(可空)；勾协议 → 提交 → 极验弹窗。
3. **极验 v4 点击题**（word/icon 轮换）：视觉接力解算（细节见 SKILL.md §2）。解出「泉水鸡」一题即成功。
4. **注册请求**（成功那把的载荷形状）：
   `POST /api/auth/token/register`  JSON {
     username, password: SHA256(password) HEX, telegram: '<纯数字>',
     inviteLink, inviteCode: '', deviceId,
     lot_number, captcha_output, pass_token, gen_time   ← geetest 四键直接展开
   } + 头 `Device-Type: h5`
   - 失败链文案：`telegram不合法` → `验证码不正确` → 成功 200。
5. 响应含 `accessToken`（Bearer，~6天）+ userInfo（id/shortId/tenantId/agentId 等）。

## 会员 API 约定（拿到 token 后）
- **双 api 怪癖**：Nuxt 代理下，前端路径 `/api/...` 实际变成 `/api/api/...`（如 `/api/api/public/getCustomerService`）；`/user/*`、`/wallet/*` 等不带 /api 的前缀则单前缀 `/api/user/...`。
- 认证：`Authorization: Bearer <accessToken>`（cookie `u-token` 同源可用）。
- **加密请求包**（敏感端点）：
  - body = AES-ECB/Pkcs7(JSON payload, key) 的 base64；key = 16 字符随机串（作为 UTF-8 字节直接当密钥）；
  - 头 `Encry-Key` = RSA-PKCS1v1.5(key, 服务器公钥) 的 base64（JSEncrypt 兼容）；
  - 响应同 key 解密；公钥 `GET /api/sys/api/publicKey`（base64 SPKI，python RSA.import_key 可直接吃）。
  - 实测：加密包能到达后端（好端点如 getInfo 明文可用；误用加密反而 500；部分端点参数形态不对也回 500「服务器内部错误」，别当死路，多试参数形态）。
- 登录 grant：`/api/auth/oauth2/token?grant_type=password|telegram&scope=server`（form-urlencoded）；**全 Device-Type 均强制验证码**；TG miniapp（grant_type=telegram + third_info=initData）有真签名校验（伪造 hash → `invalid_telegram_identity`，别浪费时间）。
- 会员端点样本：`/api/user/userInfo/getInfo`、`/api/wallet/walletUser/queryBalance`、`/api/user/vip/info`、`/api/game/profit/sum`、`/api/api/tenantMarquee/getMarqueeNotice`、`/api/api/public/*`（getCustomerService/getDefaultRobot/checkAccess）。

## IP 被 CF 封（Error 1015）后的通道
- 现象：zone 级封 IP；浏览器同 IP 也「banned temporarily」；Tor 出口吃「Just a moment」挑战（requests 无解）。
- 通道：patchright `proxy={'server':'socks5://127.0.0.1:9050'}` + 过挑战 + `page.evaluate` 页内 fetch 全套 API 调用（same-origin，带 token 头）——工作正常（已用于 getInfo/queryBalance/vip/info 等）。
- 注意：Tor 出口下截图/字体加载易超时 → 跳过截图；多出口重试（NEWNYM）直到 app 真 boot（title=uulai.com）。

## 提取流程里的小工具坑
- 在页面 hook window.fetch 记录请求：Nuxt/框架早期捕获引用时 hook 可能收不到（reqlog=0），别死磕 hook，改直接 page.evaluate 主动 fetch。
- 视觉解算协作 = 文件握手：脚本存素材 → 轮询 coords.json（超时即刷新重来）→ 收到坐标 → 点击。跨工具调用接力最稳。
