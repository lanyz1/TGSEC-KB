---
name: white-label-h5-player-api
description: Use when pentesting an apeiro8-style gambling H5 player.
---

# 白标博彩 H5 玩家端攻击手册（apeiro8 系）

## 1. 玩家端入口不在主站
主域往往只是**下载落地页**（零 input）。真正的 H5 注册/登录在「简化H5域名」：
从免签的 `/site/api/v1/configuration/preInfo` 或 localStorage `customUrl` 拿 `h5DomainUrl`，
注册路由 `/entry/register`（字段 用户名/密码/确定密码 + 勾协议），提交前调
`POST /site/api/v1/user/member/kaptchcate {"kType":4}` → 6022 = 触发 botion 点选。

## 2. 每个模块一个固定 X-API-XXX 常量
```javascript
const t0 = await TC( path.match(/\/\w+\/\w+/)[0] );   // 路径前两段做哈希 → 常量
headers = { "X-API-CLIENT":"h5", "X-API-XXX":t0, "X-API-VERSION":"1.0.0",
            "X-API-SITE":"4002", "X-API-TYPE":"h5",
            "X-API-TOKEN":cookie, "X-API-UUID":cookie }
```
抓一次就能调该模块**所有**接口。实测（开云 4号店）：
- `/site/api` → `047dc7e2a504dc908e2d91faa8a152a23c413390aac299f8a6b7303a26041428`
- `/page/fd` → `99dc2daa5b3d7361babdcec11750ccfe92b215121024c56be581ce0b6f2f64f6`
- `/game/api` → `98d2aa91538c60754664d74bb7690fca24897ff409d02e51aa03425ab2efe0ee`
- `/act/api` → `693b9c351d9a823698f43a00beb98018084cd925f80662204c8b964c2dafe47b`

**纯 Python/curl 会被阿里云 WAF 挡（HTTP 416 安全阻断页）**，必须在浏览器内用
WebCrypto + fetch 调用（AES-256-CBC，密钥取自 `/site/api/v1/sec/Hf6dtBdmHx`，body 形如 `{"x":cipher}`）。

## 3. localStorage 明文口令（高危）
```javascript
var m="Z=EO`(h$/?23adze";   // 硬编码密钥=IV，明文写在公开 JS 里
localStorage['s_f'] = AES.encrypt(JSON.stringify({name,password,checked}), m, {iv:m})
```
解密即得用户**明文密码**。利用点：任意 XSS、共用设备、本地文件读取。
平台「登录失效自动登录」本身依赖存明文，属设计缺陷。

## 4. 取款面（fd 模块）
```
GET  /page/fd/api/v1/bankCard/queryMemberBanksInfoList   (headers X-USER-ENCY)
GET  /page/fd/api/v1/speedDraw/getSpeedDrawInfo
POST /page/fd/api/v1/vCurrency/checkSupportUsdt | usdtWithdrawInfo | getUsdtRate
POST /page/fd/api/v1/withdraw/withdrawInfoV2 | baseCfg/listV3 | drawRule/list
POST /page/fd/api/v1/speedDraw/getDrawTypeInfoV4      kyc 门 + hint 文案
POST /page/fd/api/v1/withdraw/newV2                   提交
     {amount, bankCardId, version:5, withdrawMethod, twoPassword, bonusRuleId, category, preVersion}
```
**kyc 门**：`getDrawTypeInfoV4.kyc.hasRealName/hasPhone/hasVirtualWithdraw`。
虚拟币/USDT 取款需「真实姓名 + 手机号」，人民币取款还要银行卡。
**绑定路**：`bindFromDepositVe2 {realName,phone,code}`（存款绑定，疑似免短信）、
`bindPhoneVe2` / `bindEmailVe2` / `bindCardId` / `sendCode/{one,two}Ve2`。

## 5. 不要误报的点（已证伪）
- `X-USER-ENCY`（= **md5(用户名)**）是可疑的客户端身份头，**但服务端忽略它**，身份绑在 token 上。
  判据陷阱：重复请求会返回 `6011 请勿重复操作`，**不存在的账号也一样** ⇒ 别把它当账号状态 oracle。
- `member/info` 带他人 ency 仍返回自己的记录 ⇒ 隔离正确。

## 6. 第三方引擎
场馆启动 `/game/api/v1/venue/launch` 会下发引擎 token 与 MemberCode（IM体育形如 `p02<用户名>`）。
引擎源站多为 Spring Boot（`api.<xxx>.com/yewuNN/api/user/*`，从 Python 可直连、无 CORS），但需引擎会话；
`/yewuNN/actuator` 可能暴露（也可能只开 health/info）。
引擎 H5 常年按 IP 封锁（`ACCESS RESTRICTED` + CaseID）。
