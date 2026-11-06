# Bot 面板侦察实战: 周氏PG → AYX 平台(2026-08)

## 目标链

`@zhoushipgbot`(周氏PG电子 bot)/ 频道 `@aipg` → 品牌反查 → **c7/爱游戏体育(AYX)平台**(门兴格拉德巴赫官方区域合作伙伴)。

## 反查链路(从 bot 到真实平台)

1. t.me 页面抓 `og:title/og:description` → 拿到客服 `@kefuzhou`、交流群链接、担保描述
2. 搜索品牌词 → 落地页 `wwgpr.com` / `zhou-shi.com` / `wlw-zgqjfww.com`(186.240.59.68-71,宝塔+nginx 多站点 Host 路由)
3. 抓 `/e/dongpo/tz/tz.js` → 泄露 iframe 落地页 `/ldy/index.html`
4. 抓落地页引用的 **`https://www.fenliwang.cn/static/js/xklink.js`** → **50+ 平台域名矩阵**(ky/ly/jy/hth/ayx/ml/xk/mk × 6 种入口,全是随机 `.vip` + 非标端口)
5. 周氏PG挂靠 **ayx 平台**: `www.n5j99k.vip:6508`(PC)/ `www.5o51d2.vip:9975`(H5)

## AYX 前端 → API 逆向(Next.js)

- 首页 35 个 webpack chunk;业务端点藏在 `user/[id]` chunk:`/site/api/v1/*`、`/fd/api/v1/*`、`/act/api/v1/*`、`/page/fd/api/v1/*`
- **请求头体系**(在 `_app` chunk 的 `v_:function` 里):
  ```
  X-API-CLIENT: web | X-API-VERSION: 2.0.0 | X-API-SITE: 1001 | X-API-UUID: uuid-v4
  X-API-XXX: WASM 签名(模块 2284 → static/wasm/2284/38464/729ede6e9048bb61.wasm, sign(路径,"prod"))
  X-API-TOKEN: 登录后
  ```
- **关键坑**: 缺 `X-API-SITE` 头 → 全部返回「平台类型错误 6008」;带齐头(preInfo/登录)即通。X-API-XXX 实测传 `test` 也通(可能不校验)
- 加解密密钥对: `GET /site/api/v1/sec/Hf6dtBdmHx` → `{k: base64(32B), v: base64(16B)}`
- 注册链: `defaultKaptcha`(取 x-code header)→ `validateGeeCheckV2`(极验,历史有任意值绕过先例)→ `/site/api/v1/user/register`(password=MD5)
- 业务端点(高价值): `page/fd/api/v1/payment/*`(充值/取款/速付)、`bankCard/insertMemberBanksV2`、`site/vipExclusiveDomain/getDomain`

## 面板验证流程

- 批量 HTTP 探测候选 IP: 标题含 bot/panel/telegram/管理 = 面板;登录框特征(password/login/username input)
- 登录表单分析: `<form action="index.php">` + 字段 `action/login/password`
- 弱口令 18 组全 303 → **303 无法区分成功/失败**(统一跳回 /),需带 cookie 跟随重定向或对比 Location 差异
- 发现 `89.232.188.12` = **paynet.zone 支付平台的 BOT Admin Panel**(Set-Cookie 域名泄露真实业务域)

## 教训

- Censys 搜 `zhoushi` 7 个 IP 全误命中(公司名/地址含"周氏",如乐鱼科技/福建工程站)→ 中文品牌词必须用 Fofa 或加 `bot/telegram/login` 组合
- Shodan API OSS plan 搜索不可用,网页版可用(见主 SKILL)
- 通用 bot+telegram 搜索全是无关项目 → 必须用专属指纹
