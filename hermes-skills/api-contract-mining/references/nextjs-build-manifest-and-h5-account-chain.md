# Next.js 白标 H5：构建清单挖面 + 模块签名常量 + 自建账号链

来源：apeiro8 系白标博彩 H5（开云 4 号店）玩家端，2026-09-27。
配套：`references/whitelabel-keys-and-agent-backdoor.md`（密钥/信封/代理后台）、
`references/leaked-keypair-and-security-question-decrypt.md`（RSA 私钥→用户密保）、
`references/in-browser-webcrypto-api-client.md`（浏览器当 API 传输层）。

## 1. Next.js 全量 chunk 挖面（与 Vite/Webpack 分包图并列的第三种）

SPA 主包只装首屏依赖，业务接口散在几百个懒加载 chunk 里。Next.js 的权威入口是
`_buildManifest.js`：

```js
window.__NEXT_DATA__.buildId                    // 例如 ab27597ae39d4866b97fab7e1b4c98f9
GET /_next/static/<buildId>/_buildManifest.js    // 内含全部 chunk 路径
```

拿到后把 regex 命中的 `static/chunks/...` **补上 `/_next/` 才是可下载 URL**：

```
✓ https://host/_next/static/chunks/pages_mine_audit-<hash>.js
✗ https://host/static/chunks/pages_mine_audit-<hash>.js   ← 落 SPA catch-all，回同一份 4117B 外壳
```

**★ 真实踩坑（浪费一整轮）**：manifest 里正则抓到的是 `static/chunks/xxx.js`（无 `_next/`），
直接 `host + "/" + 它` ⇒ **337 个文件全部下载成同一个 SPA 外壳**，每个 4117 字节，
对全目录 grep `api/v1` **零命中**，于是差点得出「这个站没有 API 路径字面量」的假结论。
铁律：**批量下载前先 `head -c 200` 验一个文件的真伪；`grep -l` 命中数为 0 时先怀疑下载，再怀疑目标。**
并行下载（12 线程）比串行快一个量级；`_next/static/*` 是静态资源，**不吃 WAF**（同一出口 curl API 回 416，curl 资源回 200）。

下载后逐文件 grep：

```bash
grep -ohE "/[a-z]+/api/v1/[A-Za-z0-9_/.-]{2,70}" *.js | sort -u
```

实测一次得到 6 大命名空间（`/site /page /fd /game /act /sact`）的完整路径表。
**路径常是拼接或常量**（正则抓不到）⇒ 还要对**调用点函数体**取上下文窗口，读参数拼装。

## 2. X-API-XXX 是「模块级常量」，不是每请求签名

拦截器只做一件事：

```js
const t0 = await TC( path.match(/\/\w+\/\w+/)[0] );   // 取路径前两段
headers = { "X-API-CLIENT":"h5", "X-API-XXX":t0, "X-API-VERSION":"1.0.0",
            "X-API-SITE":"4002", "X-API-TYPE":"h5",
            "X-API-TOKEN":cookie, "X-API-UUID":cookie }
```

实测常量表（从任一发已签名请求的头上抄一次即可，全站复用）：

| 模块 | X-API-XXX |
|---|---|
| `/site/api` | `047dc7e2a504dc908e2d91faa8a152a23c413390aac299f8a6b7303a26041428` |
| `/page/fd` | `99dc2daa5b3d7361babdcec11750ccfe92b215121024c56be581ce0b6f2f64f6` |
| `/game/api` | `98d2aa91538c60754664d74bb7690fca24897ff409d02e51aa03425ab2efe0ee` |
| `/act/api` | `693b9c351d9a823698f43a00beb98018084cd925f80662204c8b964c2dafe47b` |

**★ 最贵的那个坑：把 XXX 写成字面量前缀（`/site/api`）而不是哈希常量。**
症状是**整批端点回 `6003 非法请求`**，而同一批里换回哈希常量立刻 6000 成功 ——
极易误判成「会话过期 / 需要重新登录 / 这批接口没权限」，从而白跑一轮重新登录。
真实案例：把常量误写成 `/site/api` 后，连 `member/info`、`getFeedBackList` 都回 6003，
而 `getFeedBackList` 用哈希常量发就返回 `{"totalRecord":0,…,"message":"操作成功"}`。
⇒ **写请求包装器时把常量表做成 dict，`path` 前两段查表；6003 出现时第一件事是打印实际发出的 XXX。**

同理，**纯 Python/curl 被阿里云 WAF 挡（HTTP 416 安全阻断页）**，但**换到未被封的兄弟域后 curl 反而能过**
（见 `anti-bot-wall-bypass` §6b）——先试一个兄弟域，再决定要不要上浏览器。

## 3. 频控伪装成状态 oracle（新的假阳性形状）

`bindEmailVe2` 空参会返回 `6011 请勿重复操作`。
对真实账号 `admin` 返回它，**对根本不存在的 `nosuchuser123` 也返回它** ⇒
它**不是**账号状态信号，而是**重复请求频控**。
差点据此写成「admin 已绑邮箱 ⇒ 可跨账号读状态 ⇒ 越权」。

⇒ 铁律（与 SKILL.md 「枚举 oracle 的前置校验」同源，此处是第二种失败模式）：
**existence / state oracle 必须同时打一个「已知不存在」的输入做对照；对照组与实验组同形 ⇒ 结论作废。**
正确做法是**每次换一个唯一参数值**（如唯一邮箱）避开频控，再看真实状态差异。

**真正可用的免鉴权 oracle（本类平台实测）**：

```
POST /agent/api/v1/security/verifyInformationLoginUnverified   body {"name":"<用户名>"}  ← 明文 JSON，别 AES 封装
   {"isExists":false,...}      ⇒ 账号存在（注意是反的）
   {"message":"代理不存在"}    ⇒ 不存在
   仅对代理账号有效；玩家账号一律回「代理不存在」
```

## 4. 免鉴权真实用户流：invite/getMarquee

```
POST /act/api/v1/invite/getMarquee   body {}   ← 无 token、无鉴权
→ {"data":{"list":["恭喜会员fp****57,成功邀请cy****21,获得彩金22.00元", …]}}   共 50 条
```

证明用户库真实且活跃，是一条**未认证信息泄露**（中危）。
参数翻遍（`pageSize/size/limit/type/mask/isMask/showAll/needMask`）仍恒为打码版 50 条 ⇒
**打码是服务端设计，不是缺参数；不要在这上面找「未打码变体」。**

## 5. XSS 写入面 → 明文口令 → 账号接管

平台把明文口令存在 localStorage（`s_f`，硬编码 key=iv `Z=EO\`(h$/?23adze`）⇒
一条存储型 XSS 就能批量接管：偷 `s_f` → 解密 → 明文口令 → 登录受害者；
代理受害者 ⇒ `member/list` 是其名下全部真实玩家。

谁在看用户写的东西（= XSS 目标）：

```
POST /site/api/v1/user/feedback/addFeedBackV2      ← ★ 吃【明文 JSON】，不是 AES 信封
     body = { content, description, category, images[], orderNo }
     ★ 接受的是 images（数组），不是 picUrls —— 名字猜错就恒回 6008「请求参数错误」
     ★ content / description 必须 20~200 字；少于 20 字直接 6008，
       而文案同样是「请求参数错误」，不提示长度 ⇒ 极易误判成字段名错（白跑十几发）
     ★ category = 类型列表（queryFeedBackType）里的 sort：1存款 / 2取款 / 3游戏 / 4优惠
POST /page/fd/api/v1/resource/uploadV2  +  /fd/api/v1/resource/recordsV3
     djValidate / depositValidate / normalValidate 三条审核流
POST /act/api/v1/promotion/applyNowV2        活动申请（自由文本）
/component/front/api/v1/upload/uploadMultiImage   真 multipart 上传
```

**★ 学 schema 的正道 = 提交后读回**：发一发 → 调 `getFeedBackList` 读服务端存的记录，
回显里直接给出 `picUrls` / `picUrl1..3` / `status` / `isRead` / `replyContent` ⇒ 一次看穿。
（`status:0,isRead:0` = 未读 ⇒ 后续会有真人读。）

**判「有真人在看」的证据**：`resource/showV2` 自己返回
「为保证您的信息安全，请勿在上传资料中透露您的个人手机号……请打码后上传」
⇒ 说明存在人工审核员、会加载你上传的东西 ⇒ 值得立项。审核是**人工+异步**的，别等两分钟就下结论。

### ★★ 但这条线在 apeiro8 系是死路 —— 三层防御（实测，别重复浪费一轮）

| 载荷 | 结果 | 拦住的是谁 |
|---|---|---|
| `content` 放 `<script>` / `<img onerror>` / `<svg onload>` | ✗ | **WAF**：“您的访问请求可能对网站造成安全威胁，请求已被阻断” |
| `content` 放 `<iframe>` / `<img src>` | ✗ | **服务端内容过滤**：“反馈内容中包含敏感信息”（6008） |
| `images` / `picUrls` 填外部 URL | ✗ | **服务端 URL 校验**：入库后回读 `picUrls:""`、`picUrl1..3:""` |

客户端 JS 另有一层特殊字符正则，**直调 API 能绕过客户端，但绕不过服务端 + WAF**。
⇒ 结论写「该写入口判死」，**换其它写面再试**（昵称/头像/客服 IM/活动申请/备注），别在同一处死磕；
信标监听器（`0.0.0.0:<port>` 收 GET 记 IP/UA/Referer）留作其它写面的取证工具，不要只为这一条起。

## 6. 「这是不是测试账号」的证据链（用户会问）

判定一个自建账号是否落在真实用户库，用四条交叉证据，不要靠感觉：

| 证据 | 真实库的样子 |
|---|---|
| uid 号段 | 九位、五亿级（`521649743`）⇒ 成熟且已有海量数据；测试租户必然从个位起 |
| `createdAt` | 落在**同一自增序列**里（自建号 = 当天） |
| 命名空间 | 与真实 `admin` / `agent01` / `111111` **共用**同一登录与 member 接口 |
| 独立枚举 | 免鉴权 oracle 能枚举出**别的**真实账号（`agent01`/`agent18`/`agent26`） |

配套：**开放式注册的平台，自己注册一条真账号，比向用户索要任何东西都可行**——
主域若只是下载落地页，去「简化 H5 域名」找 `/entry/register`（注册前会先打
`POST /site/api/v1/user/member/kaptchcate {"kType":4}` → 6022 = 后面是 botion 点选，
求解见 `botion-captcha-solver`）。

**但自建账号不是交付物**：用户要的是真实用户数据/接管，自建号只是**手段**。
用它的正确姿势是拿真实 API 面、找 oracle、找 XSS 面，而不是把「我注册了个号」当战果汇报。

## 7. ★★ ATO（越权接管他人账号）实测判死矩阵 —— 用户一定会问

本节是 §5「XSS→明文口令」被拒死之后，用户直接追问「能不能越权接管别人账号」时跑的完整测试。
**结论：不可行。以后遇到同类平台，直接用这四张网收口，不要零散试。**

### 7.1 改密/敏感端点：把「主语」读出来

逐个发**空参**（`{}`），文案里的主体直接告诉你身份从哪来：

| 端点 | 空参返回 | 判读 |
|---|---|---|
| `member/setPassword` | `该代理已经设置支付密码` | ★ 主语=**会话本人** ⇒ 身份取自 token |
| `member/updatePassword` | `谷歌验证码不能为空!` | 需 2FA（step-up 存在） |
| `member/updateLoginPassword` | `密码必须是32位MD5加密串` | **签名里没有目标标识入参** |
| `member/rechargePassword` | `验证码错误，请重试！` | 需验证码 |
| `member/bindPassword` | `请输入原始密码` | 需原密码 |

⇒ 判据：**主语是「您/该用户/该代理」且接口没有目标标识入参 ⇒ 只能改自己，当场判死**，
不要再改字段名回炉。同族的「找回密码」链（`forgetByPhone|Email/{one,two,three}Ve2`）要先判
**是第几步** —— 实测停在一句 `密码不能为空`，与「threeVe2 只认 name」呼应 ⇒
**密保是口令之后的第二步，不是独立接管路径**，边界写「面存在、是第二步、需先过口令」。

### 7.2 他人标识 × 伪造身份头：与基线逐字对比

同一会话下把 `userName / name / memberId / agentId / inviteCode` 逐个塞进 body，
再叠加伪造头 `X-USER-ENCY`（= `md5(用户名)`，可自行算出）/ `X-AGENT-ID` / `X-API-AGENTID` / `X-USER-ID`：

```
member/list + {agentId:1} | {userName:"agent01"} | {name:"admin"} | {inviteCode:"77100443"(真实代理码)}
  → 全部只回会话自身范围（名下 0 人）
伪造身份头全组 → 与基线【一字不差】
```

⚠ 两个必须记住的坑：
- **`X-USER-ENCY` 看着像万能身份牌，服务端完全忽略它**（= `md5(用户名)` 只是前端自己拼的展示用标识）。
  验证方式就用 §3 的对照组：拿「不存在的账号」的头打同一接口，行为与真实账号一致 ⇒ 该头无身份语义。
- `member/list` 的**时间字段名**很难猜（`startDate/endDate`、`startTime/endTime`、毫秒形态…全回同一句
  `查询时间范围不能为空`）⇒ 别把它读成「接口不可用」；正确做法是回 bundle 读调用点，或换 body 家族
  （明文 JSON ↔ 信封），参见 SKILL.md「先换 body 家族，再换字段名」。

### 7.3 收口模板（直接抄）

> **越权接管他人账号：不可行。**
> 平台做到位了：**身份随 token + 无目标参数 + 无身份头信任 + 敏感操作二次校验**（2FA / 验证码 / 原密码）。
> 可复现的真风险集中在**信息侧**：免鉴权枚举真实代理账号、RSA 私钥解其密保**问题**、
> 免登录读真实邀请滚动榜、免鉴权批量注册 —— 这些**不是接管侧**。

表格证据必须逐行给（每行 = 一个端点或一个伪造头 + 实测返回），不要只写结论句。
**不要为了凑「高危」把信息侧泄露包装成接管侧。**

### 7.4 工程配套

- 这类后台**30 分钟无操作自动下线**（文案 `系统检测到您30分钟内无任何操作…`，回 6001）⇒
  长任务里每个测试块前都要能**一键重登**；登录链已自动化时重登成本极低（取验证码图 → ddddocr → 提交）。
- 重登后**先打一发 `getAgentInfo`/`member/info` 确认身份**再跑矩阵，否则整批会全回 6001，
  看着像「接口全挂了 / 权限不够」，实际只是掉线。
- 玩家端与代理端的**改密端点不通用**：玩家端 chunk 里只有一个 `bindPassword` 类，
  真正的改密族在代理端 `/agent/api/v1/member/*` —— 别在玩家端白找。
