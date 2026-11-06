# AYX/c7 平台 API 逆向细节(2026-08-09, 周氏PG电子背后平台)

## 目标链

@zhoushipgbot(周氏PG电子下注 bot)→ 品牌周氏 → c7/爱游戏体育(AYX)平台
- 落地页域名: zhou-shi.com / wwgpr.com / wlw-zgqjfww.com(186.240.59.68-71 同服务器群,宝塔+Nginx Host 路由)
- xklink.js(www.fenliwang.cn/static/js/xklink.js)挖出 8 平台 × 6 入口 = 50+ 随机 .vip 域名:
  ky/ly/jy/hth/ayx/ml/xk/mk; 每平台 Web/H5/App/TyApp/FljWeb/FljH5
- AYX 主站: www.n5j99k.vip:6508(PC Next.js) / www.5o51d2.vip:9975(H5, API 同域)
- preInfo 泄露更多域名: pcDomainUrl/siteDomainUrl 轮换机制

## API 端点体系

```
/site/api/v1/...       站点配置/用户/安全(注册登录)
/fd/api/v1/...         财务(支付/取款)
/act/api/v1/...        活动/广告
/page/fd/api/v1/...    支付子路径(H5)
```

实测可用端点:
- POST /site/api/v1/configuration/preInfo → 200 站点配置(需 X-API-SITE 头)
- POST /site/api/v1/user/login → 200 "用户名或密码错误"(参数被接受)
- POST /site/api/v1/user/register → 200 "注册失败"(校验未过,缺验证码)
- POST /site/api/v1/sec/Hf6dtBdmHx → 200 返回 AES 密钥对!
  - k = base64(xpMCdmAS1gPC0ctqbRppnTqvFbtZB6Ar)  32字节 AES-256 候选
  - v = base64(chei7caishou8aiF)  16字节 AES-128 key 候选
- POST /site/api/v1/user/member/validateGeeCheckV2 → 极验校验("验证码错误")
- GET /site/api/v1/user/register/defaultKaptcha → 图形验证码 + x-code header(该域名 404, PC 域名提供)
- POST /site/api/v1/user/member/kaptchcate {"kType":4} → 200 空数据

## 请求头体系(硬门槛)

从 webpack chunk(_app-2322f845390c9065.js)逆向:
```js
headers = {
  "X-API-CLIENT": "web",          // 固定
  "X-API-XXX": sign(路径, "prod"), // WASM 签名(模块 2284 → static/wasm/2284/38464/729ede6e9048bb61.wasm)
  "X-API-VERSION": "2.0.0",       // 固定
  "X-API-SITE": "1001",           // 站点 ID(关键!)
  "X-API-TOKEN": token,           // 登录后
  "X-API-UUID": uuid-v4,          // localStorage._uuid 或随机
}
```
WASM 模块有静态密钥: `v="ZFRYCMdFYGf0i5HgO0oWvFV0terUABU0"`, `g="CbE3P3t1lY34Ns8F"`(模块 87802)
路径前缀归一: /component → /site/api ; /page/fd → /fd/api

**关键坑**: 缺 X-API-SITE 头 → 所有接口报 "平台类型错误"(status_code 6008),不是 401!
带齐头(即使 X-API-XXX 用 test) → 接口正常返回。实测 X-API-XXX 不校验或宽松。

## 注册链路

```
defaultKaptcha(图形验证码, 拿 x-code header)
  → validateGeeCheckV2(极验, body {validate_way, geetest_*})
  → register({name, password: MD5(pwd), confirmPassword, i_code, x_code})
```
- 用户名规则: 4-11位, 首位字母, 字母+数字组合
- 密码: MD5 明文传输
- platformType 默认 6(JS: n=void 0===t?6:t),但实测 1-20 全报平台类型错误 → 平台类型在 header 的 X-API-SITE,不在 body

## 网络层要点

- 服务器 186.240.59.68-71: 80(200)/443 真实开放,其余端口全是 TUN 假象
- API 无 IP 限制(前端页面有 restrictionIp 拦截,API socket 直连不受影响)
- RateLimit: X-RateLimit-Limit-minute: 30,CORS Allow-Origin: *

## 未完成(下次继续)

- X-API-XXX WASM 签名未复刻(实测 test 值可通,可能服务端不校验)
- 注册未打通(卡在极验 validateGeeCheckV2,历史经验极验可任意值绕过但需正确参数结构)
- 登录后 X-API-TOKEN 未拿到 → 资金面(/page/fd/api/v1/payment/* 充值/取款/速付/银行卡)未测
