# 白标博彩平台：免鉴权密钥下发 + 租户域名总泄漏 + 代理口开号

**案例**：t4 = `wabizhuanqianruanjian.lol`（SEO 壳）→ 开云 KAIYUN 白标博彩平台（`www.2mxswj.vip:6004` 等 14 个域名）
**结论**：协议 100% 逆向 + 拿到有效代理后台登录态；玩家侧因**平台级关闭注册**未能开号。

---

## 1. 攻击链入口：SEO 壳的 UA 分流（cloaking）

静态 SEO 落地页（`last-modified` 数个月前、Bootstrap、无 API）在 `ad.js` 里做分流：

```javascript
if (UA 匹配 /spider|bot/) { /* 什么都不做 → 给搜索引擎看无害页 */ }
else { var url = "https://<真站>"; 注入全屏 iframe }
```

⇒ **静态壳不等于没目标。** 必查：①每个 `<script src>`（尤其 `ad.js`/`tj.js`/`g.js` 这类小文件）；②外壳页里的 `atob('…')` 混淆串（本案解出下一跳 `https://lb.<域>/jump.js`）；③统计 ID（百度统计 32 位 hash）当运营方指纹跨站关联。

同一台机器（`103.80.19.182`）还挂着 Z-BlogPHP + 中文导航站，是**真实服务器**（非 CDN），可作为独立落脚点。

---

## 2. 免鉴权下发信封密钥（本类平台的核心特征）

```http
POST /site/api/v1/sec/<8位随机名>          # 无任何认证
→ {"data":{"k":"eHBNQ2Rt…","v":"Y2hlaTdj…"},"message":"操作成功","status_code":6000}
```

`atob` 之后：

| | 值 | 长度 | 用途 |
|---|---|---|---|
| `k` | `xpNCdmAS1gPC0ctqbRppnTQvFbtZB6Ar` | 32B | AES-256 **key** |
| `v` | `chei7caishou8aiF` | 16B | **IV** |

同一个 `/sec/<随机名>` 端点**换任意 `X-API-XXX` 都回同一对密钥** ⇒ 全局密钥。

**兜底常量密钥**（前端模块 756127，key 与 iv 同一串）：

```javascript
var l = "ZFRYCMdFYGf0i5HgO0oWvFV0terUABU0";
function HI(t, e){ return encrypt(t, Utf8.parse(e.key ?? l), {iv: Utf8.parse(e.iv ?? l)}).toString(b64) }
function pe(t, e){ return decrypt(t, Utf8.parse(e.key ?? l), {iv: Utf8.parse(e.iv ?? l)}).toString(Utf8) }
```

---

## 3. 信封格式与三段头

```
请求: POST https://<host>/<服务>/api/v1/<方法>
体  : {"x": "<base64(AES-256-CBC-Pkcs7(明文JSON))>"}
响应: {"data":…,"message":…,"status_code":…}    （部分接口响应体同样加密）
```

**必需头**（来自 axios 请求拦截器，逐请求拼装）：

| 头 | 值来源 |
|---|---|
| `X-API-XXX` | **URL 前两段**：`e.match(/\/\w+\/\w+/i).shift()`（如 `/site/api`、`/act/api`、`/page/fd/api`） |
| `X-API-SITE` | 租户站点 ID，硬编码（本案 `4002`） |
| `X-API-VERSION` / `X-API-CLIENT` / `X-API-TYPE` | `1.0.0` / `h5` / `h5` |
| `X-API-UUID` | 客户端 UUID（cookie/localStorage 持久化，服务端可能与令牌绑定） |
| `X-API-TOKEN` | 服务端下发的不透明串（`DL_<32hex>`），**不是自加密可伪造的** |
| `X-API-FINGER` / `X-API-ORIGIN-SITE` / `X-API-APPTYPE` | 设备指纹 / 来源站点 |

### 状态码语义（判读表）

| 码 | 含义 | 读法 |
|---|---|---|
| `6000` | 成功 | |
| `6001` | 请重新登录 | **缺票** → 需要账号 |
| **`6003`** | **非法请求** | **缺头/形状不对** → 别改 body，去补 `X-API-*` |
| `6005` | 请求失败 | 服务端内部 |
| `6008` | 参数/校验错 | 看 message 是否**指向具体字段** |
| `6021` / `6022` / `6023` | 图形码 / 极验 / 验证关闭 | TS 枚举 `{verifyImage:6021, verifyGee:6022, verifyClose:6023}` |
| `6022`（登录时） | **极验前置** | 口令根本不校验，必须过 GeeTest |

**关键判据**：两个「都要登录」的端点回了**不同**的码（`6003` vs `6001`）⇒ 其中一个多一道请求形状层。

---

## 4. 验证码类型枚举 ↔ 码值分属两个字段

```javascript
$I = { verifyImage: 6021, verifyGee: 6022, verifyClose: 6023 };  // 状态码
Gr = { [verifyGee]: 0, [verifyImage]: 1, [verifyClose]: 2 };      // 提交时传的值

// 注册提交（图形码场景）
o = { name, password: md5(明文), Kaptchcate: ee.Gr[v], codeId: sessionStorage.getItem("xCode") };
if (v === ee.$I.verifyImage) { o.code = x; }   // ← 码值走独立字段
```

- `codeId` = 验证码接口的 **`x-code` 响应头**（sessionStorage 键名 `xCode`）
- 图形码 = **5 位混合大小写 + 偶然夹汉字** ⇒ `ddddocr` 失效，需视觉识别
- 密码字段传 **32 位 MD5**（`密码必须是32位MD5加密串`）

---

## 5. 租户配置端点 = 一次泄漏全部角色域名（最高价值单点）

```http
POST /site/api/v1/configuration/preInfo   # 无鉴权
→ {"data":{"SiteBaseConfigVo":{
     "id":1, "name":"4号店", "title":"开云体育官网-皇家马德里足球俱乐部官方区域合作伙伴",
     "h5DomainUrl":"https://www.2mxswj.vip:6004",
     "pcDomainUrl":"https://www.x1bjjy.vip:9961",
     "siteDomainUrl":"https://www.pebhy1.vip:6504",
     "sportAppDomainUrl":"https://www.cj1dyg.vip:6001",
     "h5StreamlineDomainUrl":"https://www.vbsm9k.vip:9053",
     "agentPcDomainUrl":"https://www.7htxsb.vip:6506",     // ★ 代理 PC 后台
     "agentH5DomainUrl":"https://www.71j8yy.vip:9023",     // ★ 代理 H5 后台
     "customerService":"[{...chatweb...}]",
     "whiteDomain":"https://chatweb.…,*.n3c94unw.com,…"      // 80+ 白标/客服域
}}}
```

⇒ **一个免鉴权请求拿到全部后台地址。** 同类字段名优先级：`*Domain*` / `*Url` / `domain` / `whiteDomain` / `categories`。
配套：`/configuration/appConfig`、`/site/venue/sort`、`/video/getAnchorShowSetting`（后者的 DB 审计字段 `updateBy` 会泄漏**内部管理员账号名**）。

---

## 6. 代理后台：与玩家侧「同平台不同闸」

- 代理后台 = 独立 Next.js 站点（`agentPcDomainUrl` / `agentH5DomainUrl`），**注册表单只有图片码，无 GeeTest** ⇒ 直接开号成功。
- 开号后 `localStorage['login_agent_info']` 明文回吐：`id` / `inviteCode` / **`password`（MD5）+ `salt`（每用户独立盐）** / 各脱敏字段。
- 认证态可用接口：`member/getAgentInfo`、`finance/draw/initMoney`（代理钱包 + 提现额度）、`finance/excel/venue`（分场馆财务）、`member/list`（**需 `startDate`+`endDate`，宽区间回「数据量过大请缩小查询范围」**）、`front/queryMonthOverview`、`game/getAllGameVenue`。
- **`/promote` 页泄漏 5 条官方拉新链**（`…/register<n>/?i_code=<编码>`），带出新域名 + 代理自己的子码。

### 判死项（别再回炉）

| 尝试 | 结果 |
|---|---|
| `member/list`、`member/detail`、`getAgentInfo` 改 `agentId`/`memberId`/`uid`/`parentId`/`inviteCode` | 参数被**忽略**，一律回自己会话范围的数据 ⇒ 会话范围过滤正确 |
| `member/updateAgentConfig` 传 `agentModel`/`agentLevel`/`isCaptain`/`teamId`/`sysType` | 全部回「成功」但**值不落库**（白名单更新）⇒ 无 mass assignment |
| 代理 token 打玩家 API | `6003`（跨系统隔离） |
| `member/joinUs` 代理自助注册 | `参数错误`（需完整参数+安全校验） |

---

## 7. 用户存在性 oracle（免登录、精确）

```http
POST /site/api/v1/user/forgetByPhone/twoVe2   {"name":"<用户名>","phone":"<PHONE-REDACTED>","code":"123456"}
→ 不存在的账号 : {"message":"用户不存在","status_code":6004}
→ 存在的账号   : {"message":"账号和手机不匹配","status_code":6008}   ← 6004 vs 6008 即判据
```

字段名陷阱：玩家端**只认 `name`**（传 `username`/`userName` 回 `用户名格式不对`）；代理端 `getSecurityQuestionNoLogin` 认 `userName`/`username`（传 `name` 回 `请求参数错误`）。**同一平台两套命名，逐端点校准，别跨端点套用。**

---

## 8. 假开放端口：CDN 边缘 vs 真源站

广扫 `www.2mxswj.vip` 得到「21/22/80/443/6000-6012/8000-8005/8443/9090/27017 …全开」⇒ 实为 **Cloudflare 边缘自身支持的端口列表**，所有端口回同一个应用。

同理 `138.113.x.x` / `118.107.x.x`（Zenlayer 系）上「3306/6379/27017/9200/11211 全开」但**连接后立即 `RST`** ⇒ **CDN 边缘接管，不是源站裸奔**。

判据：①「开放」端口集合与某 CDN 的文档端口表高度重合；②connect 成功但首个数据包即被重置；③所有端口回同一响应体。**别把这种分布写成「数据库裸奔」。**

---

## 9. 本案例的墙（写清形状证据，防下轮重复）

| 面 | 形状证据 |
|---|---|
| 玩家注册 | 6 域名 + 5 条官方代理链，全部**同一句** `注册失败`（无字段指向） |
| 玩家登录 | `6022`（极验前置）；过闸后回 `用户名或密码错误`（证明**验证码可过**，缺的是凭证） |
| 代理/玩家跨系统 | 代理 token 打玩家 API 恒 `6003` |
| IDOR / 提权 | 见 §6 判死表（会话范围过滤 + 白名单更新） |
