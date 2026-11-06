# 白标博彩 H5（apeiro8 系）玩家/代理端 —— 实测手册

案例：开云 4 号店（`wabizhuanqianruanjian.lol` → 开云/熊猫/IM体育），`X-API-SITE: 4002`，
前端 Next.js，API 网关 apeiro8（报错页 `<center>apeiro8</center>`）。

---

## 1. 类级识别

- 主域打开是**纯下载落地页**（零 input、只有「立即下载/扫码」）
- 报错页/边缘回包含 `apeiro8`；`X-API-SITE: <四位数>`；多品牌并存（开云/熊猫/IM体育）
- 域名矩阵极多（一会话实测 6+ 个活域，端口各异），且**互相是同一个后端**
- SEO 隐蔽漏斗入口：博彩壳页 → `ad.js` → 跳板域 → `atob` 跳转 → 真 H5 的 `entry/register`

## 2. 入口发现（先找“真正的 H5 域”，别在落地页上耗）

免签接口（不需要任何 token）：
```
POST /site/api/v1/configuration/preInfo   → SiteBaseConfigVo:
  pcDomainUrl / siteDomainUrl / sportAppDomainUrl / h5DomainUrl / simplifyDomainUrl …
POST /site/api/v1/sec/Hf6dtBdmHx          → {"k":"<b64>","v":"<b64>"}   每域一套 AES 密钥
```
也可从 `localStorage.customUrl` / `/act/api/v1/invite/baseConfig`（`h5_code`）拿。

**哪些域名是“完整 H5”**：打开后能看到 `/mine/*`、底部导航的才是；只看得到「立即下载/扫码/赛事介绍」
的是**落地页**（注册/登录/反馈页全部 404 或渲染成 landing）。实测：`h5DomainUrl`（如 `:6004`）是完整 H5，
`siteDomainUrl`/`sportAppDomainUrl` 可能是落地页。

注册路由：`https://<h5域>/entry/register`（用户名/密码/确定密码 + 勾协议）。
提交前前端会 `POST /site/api/v1/user/member/kaptchcate {"kType":4}` → `6022` = 拉起 botion 点选（见技能 `botion-captcha-solver`）。

## 3. 鉴权模型（踩过的坑）

```javascript
// 每模块一个【公开常量】做 X-API-XXX，不是签名
const t0 = await TC(path.match(/\/\w+\/\w+/)[0]);   // 路径前两段
headers = { "X-API-CLIENT":"h5", "X-API-XXX":t0, "X-API-VERSION":"1.0.0",
            "X-API-SITE":"4002", "X-API-TYPE":"h5",
            "X-API-TOKEN":cookie, "X-API-UUID":cookie }
```
抓一次就能调该命名空间下**所有**接口。实测常量（案例）：`/site/api`、`/page/fd`、`/game/api`、`/act/api` 各一个 64-hex。

坑：
- **不能写成本字面量**（`X-API-XXX: /site/api` ⇒ `6003 非法请求`），必须用抓到的哈希值
- **明文 vs AES 混用**：同一命名空间里，有的接口吃 `{"x":cipher}`（AES-256-CBC），
  有的直接吃明文 JSON（如 `loginFlow`、`getSecurityQuestionNoLogin`、`addFeedBackV2`）。两种各试一次
- 有的接口用**明文但必须带会话 cookie**；有的完全免鉴权

错误码：`6000` 成功 / `6001` 会话过期(30 分钟无操作自动下线) / `6003` 非法请求 / `6008` 参数错 / `6022` 需极验 /
`6010` 上传类 / `6011` 重复操作频控 / `6012` 需谷歌验证码 / `6005` 业务错

## 4. 免鉴权接口矩阵（本类平台真实的高危面）

| 接口 | 用途 | 备注 |
|---|---|---|
| `POST /site/api/v1/configuration/preInfo` | 全域名矩阵 + 站点配置 | 免签 |
| `POST /site/api/v1/sec/Hf6dtBdmHx` | AES k/v | 免签 |
| `POST /site/api/v1/configuration/vvPretty` | **隐藏服务端点表** | 免签；用公开 AES 钥直接解开（引擎镜像/WSS/新域名） |
| `POST /site/api/v1/user/member/registerFlow` | 注册代理（返 token） | 字段组：`{name,password,confirmPassword,userPassword,confirmUserPassword}` + 图形码；**可直接批量造号** |
| `POST /agent/api/v1/security/getRsaPrivateKey` | **RSA-2048 私钥整对** | 免鉴权 ⇒ 可解密任意用户下发的密文 |
| `POST /agent/api/v1/security/getSecurityQuestionNoLogin {userName}` | 任意用户**密保问题**（密文） | 免鉴权；配上面的私钥即得明文问题 |
| `POST /agent/api/v1/security/verifyInformationLoginUnverified {name}` | 账号存在性 oracle | **`{"isExists":false}`=存在；“代理不存在”=不存在（是反的）** |
| `POST /site/api/v1/user/member/validateCode` | 图形码 PNG | `x-code` 响应头 = XCodeId |
| `POST /act/api/v1/invite/getMarquee` | **真实用户邀请滚动榜**（50 条，含金额） | 免登录可读；用户名已打码 `fp****57` |

判据：私钥是客户端用来**解密/签名**服务端下发数据的（`PKCS1_v1_5(privateKey).encrypt("足球")` → 公钥回解）；
拿它只能解出**密保问题**，拿不到**答案**，且密保登录是「口令之后的第二步」⇒ **不能据此接管**。

## 5. 写入面与防御（不要空耗）

### 5.1 反馈提交（吃明文 JSON）
```
POST /site/api/v1/user/feedback/addFeedBackV2   ← 明文 body
  { content, description, category, images:[...], orderNo }
  · description 必填且 **20~200 字**（太短报 6008「请求参数错误」）
  · 图片字段名是 **images**（不是 picUrls）
  · 服务端回存后才生成 picUrls/picUrl1..3（会丢弃非自家 CDN 的 URL）
成功文案：「反馈提交成功」；列表：getFeedBackList → {id,memberId,memberName,content,description,status,isRead,replyContent}
配套：queryFeedBackType（合法 category：1存款/2取款/3游戏/4优惠）、getFeedbackInfoV2、delFeedback、unreadNum
审核流：POST /page/fd/api/v1/resource/uploadV2 + recordsV3 → {djValidate,djAuditInfo,depositValidate,normalValidate}
```

### 5.2 文件上传（真的可用）
```
POST /component/front/api/v1/upload/uploadImage      multipart，字段名 file
  → {"data":{"contentType":"image/png","fileName":"x.png",
              "fileUri":"/images/new_public/h5/others/<rand>.png",
              "fileUrl":"https://<cdn>/images/new_public/h5/others/<rand>.png"}}
```
`uploadMultiImage` 字段名不同（空字段回 `上传图片不能为空` 6010）；无 `/component` 前缀的版本 404。

### 5.3 实测被拦死的绕过
| 尝试 | 回包 | 拦截层 |
|---|---|---|
| `.svg` / `.html` / `.xml` | `请上传正确格式的图片` 6010 | 类型白名单 |
| `.svg` 改名 `.png`（内容仍是 SVG） | `上传内容不合法，请稍后重试` | ★ **魔数/内容校验** |
| `x.php.png` | WAF 安全阻断页 | WAF |
| 伪造 JPEG 头 + SVG 体 | 403 tengine | 边缘 |
| 反馈 content 里 `<img onerror>` / `<svg onload>` / `<script>` | WAF「您的访问请求可能对网站造成安全威胁」 | WAF |
| 反馈 content 里 `<iframe>` / `<img src>` | `反馈内容中包含敏感信息` | 服务端内容过滤 |
| 反馈 images 塞任意远程 URL | 入库后 `picUrls:""` | 服务端 URL 校验 |
正常 PNG 上传成功，回包 `content-type: image/png`（不嗅探）。⇒ **上传/自由文本→自家 CDN XSS 被四层防死。**

## 6. 越权接管：本类平台**打不通**（省时间用）

| 面 | 实测 |
|---|---|
| 改密/敏感接口 | **无「目标」入参**，一律以会话身份为准（回包文案「该代理…」）；且需 2FA/短信码/原密码 |
| 数据接口（玩家~50 个 + 代理端） | 全部会话隔离；带 `agentId/userName/name/inviteCode` 仍只回自己 |
| 伪造头 `X-USER-ENCY` / `X-AGENT-ID` / `X-USER-ID` / `X-API-AGENTID` | 服务端**忽略** |
| `X-USER-ENCY` 到底是啥 | **= md5(用户名)**；看着像身份牌，实测不生效（务必用不存在账号做对照，详下） |
| 多租户头 `X-API-SITE` / 跨命名空间 | 无效 |
| 密保链 | 密保=口令后的第二步（`密码不能为空`） |
| 源站 DB / shell | 端口多是 CDN 边缘伪装；Z-Blog 类模板洞需管理员权限 |

## 7. 判据纪律（踩过的真实假阳性）

**规矩：测「客户端可控身份头是否被信任」必须跑对照组 —— 存在账号 / 不存在的账号 / 全 0 / 全 f。**
四组行为一致 ⇒ 该头**未被信任**，立刻作废结论。

反面教材：`bindEmailVe2` 对 `admin` 回 `6011 请勿重复操作`，当时当成「admin 已绑邮箱」并报了「账号状态 oracle」；
拿**不存在的账号**一试回包一模一样 ⇒ 那只是**重复请求频控**（同类目标常见的保护），结论当场推翻。

同理：自己账号数据为空时，「换他人标识后仍返回空」**既可能是隔离，也可能是对方本来就没数据** ⇒ **不可区分就不下结论**。

## 8. 探测模板（省时间）

- **空 body 探针**（字段名第一利器）：POST `{}` → 服务端错误文案直接报缺什么
  （`请输入持卡人姓名` / `手机号码必填` / `请输入验证码` / `查询时间范围不能为空`）
- **长度门槛**：字段都给了还报参数错 ⇒ 先怀疑长度（如反馈描述 20~200 字）
- **抓应用自己的请求**：浏览器内挂 fetch/XHR 钩子后**用 SPA 内点击触发**；整页导航会把钩子冲掉（本会话踩过多次）
- **每域独立密钥**：换域先重取 `sec/Hf6dtBdmHx`，否则 `Incorrect IV length` / 乱码
- **封禁按域**：某域 416/`chrome-error://` 就换别的域（token 跨域通用），别急着上浏览器、更别换 IP
- **会话保活**：本类平台 30 分钟无操作自动下线（`6001`）；长时间作业要预留重登（登录图形码可用 ddddocr 4x 放大）

## 9. 第三方引擎面

`POST /game/api/v1/venue/launch` 会下发引擎 token 与 MemberCode（IM体育形如 `p02<用户名>`）。
引擎源站多 Spring Boot：`https://api.<xxx>.com/yewuNN/api/user/*`（`getUserInfo/info/balance/getBalance/money/betList/transferRecord`
路径真实存在，未带引擎会话回 `0401013 账户信息已过期`；从 Python 可直连、无 CORS），
`/yewuNN/actuator` 有时暴露（本案例只开 health/info）。引擎 H5 常按 IP 封锁（`ACCESS RESTRICTED` + CaseID）。
