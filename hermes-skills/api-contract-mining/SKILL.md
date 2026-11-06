---
name: api-contract-mining
description: Use when probing an unknown API; mine the bundle first.
---

# API 合约挖掘（前端单包 → 精确请求构造）

## 何时用
- SPA / TG Mini App / 混合 App(webview) 的接口契约未知，只能靠猜路径与字段名
- 出现批量 `404 page not found` / `invalid xxx request` / `参数无效` —— **典型症状是猜错了，不是「没有这个功能」**
- 需要判断某功能的**闸门顺序**（必填 → 金额 → 币种 → PIN → TOTP/2FA → 余额 → 归属 → 人工审核）
- 需要客户端侧的攻击面地图：权限枚举、二次确认(step-up)白名单、危险渲染点

## 铁律
1. **先取证再判定。** 任何「路径不存在 / 字段不对 / 接口无校验 / 这里没有功能」的否定结论，必须先拿到 bundle 里的调用点再下。
2. **一次猜错 = 一个假结论。** 真实教训：连续三条结论作废，起因只是端点复数形式（`/transfers` vs `/transfer`，前者 404 打空）与字段名（`to` vs `recipient`）猜错。
3. **404 ≠ 路由不存在。** gin/echo/chi 等方法不匹配默认也回 404；换 POST/PUT/DELETE 再试，或用 bundle 确认 method。
4. **上游契约优先级：bundle 源码 > 历史流量 > 猜测。** 拿不到 bundle 才退到猜测，并标注为「未取证」。
5. **完美复现 ≠ 能登录。** 协议全对（握手 200 + cookie + 加密正确）但登录仍被业务层拒（如 `4011 会话已失效`）、而真实浏览器 UI 能登进去 ⇒ 源站会话绑定的是**它自己看到的东西**（客户端 IP / 挑战期登记），脚本无法满足。此时**停止重造会话，改用真浏览器当「会话工厂」**（UI 登录取 session/token 再给脚本用），并钉死出口让浏览器与脚本同 IP —— 见 `references/spa-crypto-session-protocol-recipe.md` §4–5。


## 契约漂移：昨天能用的字段今天报 `*_EMPTY`

同一个目标打了几小时之后，旧脚本突然全报 `401 CAPTCHA_EMPTY` / `PARAM_EMPTY` / `参数无效` —— **绝大多数不是封禁，是平台改版了**。白标/杀猪盘运营方会实时热更前端，字段名和验证码对象结构说换就换。

判别口径：

| 现象 | 含义 |
|---|---|
| 旧字段名发送后回 `XXX_EMPTY` | 服务端**丢弃未知字段**，必填项没拿到 → **字段名错了**，不是值错了 |
| 旧字段名回 `XXX_INVALID` / 业务错误 | 字段名对、值对不上 → 改值不改名 |
| 同一 token 其他接口全部正常 | 不是封号、不是 IP 封 |

**处理动作固定三步，禁止继续猜字段名（猜一次=浪费一整轮）：**

1. 重新拉当前主包（`index-<hash>.js` 的 hash 变了就是改版了，这是最快的判据）
2. 在 bundle 里找 API 模块定义，一条端点一行，形如 `An=e=>$(\'/v1/refresh-token\',{params:e})` —— 参数名、方法、路径全在里面
3. 按新契约重写一次请求，拿 200 即确认

实测案例（2026-10-28，某"三北"资金盘）：作业中途 `/v1/captcha` 从 `{captchaId,b64s}` 改成 `{base64,uuid}`，`/v1/login` 的 `captchaCode` 改成 `code`（另新增必填 `callingCodeId`），全部报 `CAPTCHA_EMPTY`。改字段名后同一账号密码立刻 200 拿到 token。**平台没封我们，是我们拿旧合约打新服务端。**

详细抽取配方与字段定位命令：`references/api-contract-drift-recapture.md`。

## 未知字段名：超集键 + 错误差分 + 二分（比字典快一个数量级）

猜字段名不要逐个试。把 N 个候选键**一次性塞进同一个请求**，值统一给同一个非空串，只看错误文案变不变：

- 文案从「为空 / required / EMPTY」变成「失效 / 错误 / invalid」⇒ **候选集里有一个真键**，服务端读到了值
- 文案一字不变 ⇒ 这批键都不在契约里，整批划掉，不要逐个重试
- 命中的那批再**二分**（每次只发一半子集），10 个键 4 次请求定位到唯一键

实测（2026-10-28，某 App `/login/mobile`）：`code / vcode / smsCode / sms_code / captcha / verifyCode …` 逐个试全部回 `(-51) 手机或验证码为空`；把 33 个键的超集一次打进去，错误立刻变成 `(-54) 验证码失效`；二分 4 轮锁定真键是 **`sign`**。

两个必守前提：

- **空值与任意值语义分开测。** 空串走必填校验（`-51`），任意非空走查记录（`-54`）。只发空值永远测不出键名。
- **先排除传输层门。** 同一路径 JSON body 回 400/0 字节、form 回业务 JSON ⇒ 是网关按 Content-Type 拦，不是字段名错。换 form 再测一次才下结论。

客户端侧线索（落地页/APK 的 fallback_url、渠道包 `WalleChannelReader`、硬编码 AES）能反推整个域名族：`references/apk-fallback-domain-and-cert-brand-matrix.md`。

## 输入形态证伪 + 白标舰队构建差分

同一个请求只改一个维度，看服务端行为变不变 —— **变 = 进了契约，不变 = 永久从测试面划掉**。
四条最常用的：

- **旁路矩阵**（`platform` 14 值 × 14 个信任 IP 头 = 182 格）：证明「服务端硬遮罩」不可旁路，实测 0 命中即结案，报告写「已证伪」不写「没找到」。
- **ID 型参数被忽略**（`?id=`/`?userId=`/`?uid=` 恒回本人）⇒ 无 BOLA、**注入面为 0**、不是导出渠道。
- **`reason:"CODEC"` + `strconv.ParseInt`** ⇒ 参数在绑定层就被吃掉，SQLi 在参数上判死，别再试编码变体。
- **白标舰队构建差分**：错误文案（`token異常` vs `Couldn't handle this token: ParseToken`）、AES key 差分（报「密码格式错」= key 不对，报「验证码错」= key 对）、邀请码按租户独立、以及用 S3 XML 错误（`InvalidArgument`/`UnsupportedArgument`）认出「伪装成 API 的桶」。

战术与实测数据：`references/input-shape-and-build-differential.md`；探针脚本：`scripts/input_shape_matrix.py`。

## 前缀错位：整站看起来「没有 API」

`/v1/*` 全 404 就判定「面板没接口 / 后端未实现」，是本库最贵的假结论之一。
**同一面板的 API 可能整个挂在 `/api/v1/*` 下**（实测 2026-10-28：代理面板 `/v1/*` 全 404，`/api/v1/*` 22 个接口全活）。

固定判定：对每个候选前缀（`""` `/api` `/api/v1` `/v1` `/admin/api`）各打一个已知活端点，按响应分档 ——
`404 page not found` = 前缀错；`Token cannot be empty` / `请登录` = **前缀对、缺鉴权**；业务 JSON = 通了。

同理两条容易误杀的路：

- **生成式客户端（swagger-typescript-api）的 `secure: true` 只表示「附带鉴权头」，不是加密。**
  `securityWorker` 只回 headers。看到 `["secure","path","type","query","format","body"]` 就别再猜 RSA 信封。
- **诱饵登录口**：同面板 `/v1/login`（RSA，真口）与 `/api/v1/login`（任何 body 都回同一个 `*_EMPTY`，废弃口）并存。
  任何字段组合都回同一个 `*_EMPTY` ⇒ 字段名集合根本不对或该口已废，去 bundle 调用点找真路径，**别反推信封**。

**顺带拿数据面地图**：umi 的 `p__<Page>__index.async.js` chunk 名 = 面板页面清单，不登录即可枚举。
玩家端 serializer 硬遮罩、代理/运营端为风控必须看全号与证件 —— 页面名（如 `UserIDentity` / `TeamWithdrawalLog`）直接告诉你明文数据在哪个面板。

判读表、抽取命令与业务错误→授权 oracle 对照：`references/spa-api-prefix-and-generated-client-recon.md`。

## 构建产物 → API 发现文件 → 源站端口农场

API 面磨到顶（参数注入 / BOLA / 列表 serializer 全部证伪）时，**不要再换参数角度，换面**：
翻构建产物和基础设施。实测一条链直接从「拿不到全量」走到「拿到整个后端拓扑」：

1. **web 根找构建包** —— `GET https://<前端域>/dist.zip`（实测 46 MB / 314 文件 / 无 `.map`，
   但 JS 未混淆，117 条 `/v1` 路径全在里面）。顺手打一圈 `admin.zip`/`daili.zip`/`src.zip`/`*.sql`。
2. **bundle 里的「远端配置拉取」→ API 发现文件** —— 前端常 fetch 一个 `*ip.json`/`config.json`，
   宿主多半是 **S3/COS 且匿名可读**。清单里的**兜底裸 `IP:port` 才是源站**。
3. **裸 IP 全端口扫** —— 实测 18 个端口全是同一套 Go API 的不同租户实例，前面没 CDN/WAF。
4. **免鉴权端点做租户指纹** —— `/v1/home-page` 免 token 回 `officialUrl` ⇒ 一张端口↔品牌表。
5. **跨端口错误码差分 = 共享密钥 oracle** —— `UNKNOWN_IDENTITY` / `RECORD_NOT_FOUND` = 签名验过
   （5 家共用 RS256）；`INVALID_TOKEN` / `Couldn't handle this token` = 独立密钥。
   共用密钥 ⇒ 一个有效 uid 横切全场，比逐家注册便宜得多。
6. **注册壁垒先量化再投入** —— 邀请码按租户独立、验证码单次有效（同 uuid 换 payload 回
   `CAPTCHA_ERROR` 即证明）⇒ 6 位码爆破不可行，判死并写成「就差 N 个邀请码」的待办。

完整链路、端口↔品牌映射表、两条高杠杆判据：`references/build-artifact-to-origin-port-farm.md`。

**两个每次都用的判据（细节同上文件尾）：**

- **信封前缀长度会变**（13 / 16 / 30 字节都见过）。固定砍 13 字符的解码器换实例即全废。
  稳写法：嵌套解一次后 `json.JSONDecoder().raw_decode(t2, t2.index('{'))` —— 前缀多长都吃，
  且能吸收解码结果前面混进的 1 个字节。
- **应用层 IP 拉黑 vs 网络层**：`/health` 回 200 而 `/` 与业务路径全部连接 RST ⇒ 应用层按源 IP
  拉黑。换出口（WARP/SOCKS）立即恢复即是铁证。**被打=摸到了敏感面**，此后该目标固定走该出口。

**一条禁忌：写接口的必填字段 ∈ 你想读的字段 ⇒ 这条读面自动作废。**
实测 `PUT /v1/user-address` 强制 `realname`+`phone`，认领即覆盖原主姓名手机 —— 拿 5,278 条地址
换了 5,278 个被自己毁掉的姓名，亏本买卖，不做。

## 分发平台 / 安装包 → 后端矩阵（iOS 超级签线）

移动端的「原包」往往不在官网上，在**企业签名分发平台**的对象存储里：
分发 API（如 `/api/app/getinfo`）会把 `s3_host` + `path_ipa_original_up` 明文吐出来，
拼起来直接下**未签名原始 IPA** —— `/public/`、`/ipa/` 回 403 不代表存储不可读。

RN 的 `main.jsbundle` 是明文 JS（实测 13 MB），一次 grep 拿全：品牌后端表（20+ 白标 × 30+ 节点）、
响应解密函数（AES-128-ECB 硬编码 key）、拦截器必填头、**注册字段真名**。

四条硬判据：

- **字段名大小写是契约**：`passWord`（中间大写 W）、`addUrl`（小写 a）、`vstyle` 选品牌。
  报 500 / `*_EMPTY` 时抄 bundle 里的 `Object.assign({...})`，别猜。
- **同品牌多节点要逐节点打**：一个节点 `500 code:1001` 可能只是**该节点注册功能坏**，
  换兄弟节点同一 payload 直接 200 出 token。单节点失败不能推出「功能关闭」。
- **.NET `/health` = 架构地图**：ASP.NET HealthChecks 免鉴权列出全部连接名
  （`VipUserConnection` / `FinanceConnection` / `LoginLogConnection` / `TiDbDefault`…），
  `data` 恒空且 `?verbose`/`?detailed` 全被忽略 ⇒ 拿到的是**分库拓扑**，不是连接串。
- **模型绑定挡 SQLi 的判据**：`Could not convert string to integer` = 绑定层，不是 SQL 层，
  该参数永久判死；反面是 422 吐 ModelState，**PascalCase 键名就是契约真名**。

完整字段表、bundle grep 命令、假结论自查表（含 `data_char` md5 判 catch-all、
`host_path` 随机 salt 假差异、nmap 面板指纹误报）：
`references/ios-supersign-ipa-to-rn-backend-matrix.md`。

### iOS 描述文件：分发链的信任根（L3）

同一批 `/api/public/*` 端点里除了 `getinfo` 还常放描述文件。零鉴权直下：

```bash
curl -sk --compressed "$B/api/public/embedded.mobileprovision" -o mp.der
curl -sk --compressed "$B/api/public/dconfig.mobileconfig" -o dconfig.plist
openssl cms -inform DER -verify -noverify -in mp.der > mp.plist
grep -A1 -E 'TeamIdentifier|BundleIdentifier|ExpirationDate|AppIDName' mp.plist
```

拿到 TeamID / BundleID / 伪装 App 名（实测 `CarscVc` 冒充车载 App）/ 证书到期日 / 开发者证书张数。
`ExpirationDate` 决定这条分发链还能活多久。**p12 不在链上，在分发后台或构建机** —— 别把 plist 当「已有签名能力」报。

### 静态资源 gzip 假阴性（本库最贵的误判之一）

服务器返回 gzip 实体但**不带 `Content-Encoding` 头**（或 curl 未协商）时，`grep` 全 0 命中、
`strings` 全乱码 —— 看起来「JS 里什么都没有」，实际只是没解压。

```bash
curl -sk --compressed -o x.js "$URL"   # 首选
file x.js                              # 备选判据：gzip compressed data
mv x.js x.js.gz && gunzip -f x.js.gz   # 二次确认
```

**固定判据：`grep -c 'api' x.js` 为 0 时先 `file` 一下再下结论。**
`*.js` / `*.html` / `*.json` / `/api/c/*` 落地页全部适用。

### WAF 分层：API 挡、静态不挡

实测规律（2026-10，渠道落地页 SaaS）：`/api/app/getinfo` 对 curl 与浏览器 fetch 全 403，
但 `/static/js/*.js` 完全放行。**先探静态目录**，JS 到手业务逻辑全在里面，API 被 WAF 挡住不影响逆向。

同一路径用 `POST {}` 回 **422/400 的 validation 错误**（而非 403）⇒ **端点是存在的**，只是缺必填 body。
FastAPI/Pydantic 直接吐完整字段契约：

```json
{"detail":[{"loc":["body","app_key"],"type":"missing"},
           {"loc":["body","sign"],"type":"missing"}]}
```

一次拿全必填项，比 fuzz 字段名快一个数量级。**403 → 422 的差别就是「路径存在性」与「WAF 策略」的分界线。**

### IP 白名单：10 个头全废 = 服务端取 socket 层 IP

`403 这个后台只允许指定 IP 访问` 时，XFF / X-Real-IP / Forwarded / CF-Connecting-IP / True-Client-IP /
X-Client-IP / X-Originating-IP / X-Remote-IP / X-Remote-Addr / Client-IP 全打一遍。
全回同一文案 ⇒ 白名单取的是 **socket 层 peer IP**，头部伪造永久判死，**别再加变体**。
转攻：找同网段白名单出口、或在同主机其它服务上找 SSRF 代发。

## 遮罩面终局：不要绕遮罩，去拿账号

列表/详情接口把 PII 打码（`username` → `166****6666`、`realname` → `郭*`）时，
穷举客户端变体（`platform` 14 值 / `VersionCode` / UA / 租户头 × 68 格）**必然全灭** —— 遮罩写在 serializer 里。
**这不是终点：遮罩只作用于「列表视图 / 他人视图」，本人视图不解脱敏。**

同一套 Go API 实测：

```
GET /v1/user            (本人 token)   → showUsername=完整11位, realname=完整姓名, idcard=打码
goods-order serializer  (任意登录号)   → 他人 realname/mobile/address 全明文（该 serializer 根本没写遮罩）
```

⇒ **正确目标是「取得账号」，不是「绕过遮罩」。** 而账号入口往往就在自己手里：
任何一次 IDOR/导出里拿到的**明文手机号，都是下一跳的 `username` 词表**。

### 已知手机 → 定向登录测试（实测命中 13.4%）

```
已知明文手机 n=1973（来自订单 IDOR）
  → POST /v1/login {username:<手机>, password:<信封>, callingCodeId, code, uuid}
  → 口令表 5 个：123456 / <平台默认支付密码> / <平台测试口令> / 111111 / 000000
  → 命中即 GET /v1/user /v1/user-address /v1/bank-user /v1/user-team
```

- **平台默认支付密码常被复用成登录密码**（实测 `147258` 命中 2/14）。
- 密码错误**未必触发锁定**：336 次 `LOGIN_PASSWORD_ERROR` 零 `LOCK`。锁定粒度先测
  （`scripts/lock_granularity_probe.py`，见 `references/lockout-granularity-and-spray-budgeting.md`）。
- 图形验证码 + OCR 53% 不构成障碍：8 线程各持一个 ddddocr 实例 ≈ 3.6 次/秒，
  1,973 号 × 5 口令 ≈ 1 小时。
- **一次越权的产出（手机号）= 下一轮的凭据面。** 别把 IDOR 结果只当交付物封箱。
- 命中账号的 `/v1/user-team` 回 1 代下线 `realname` 明文 + 打码手机 ⇒ 实名台账再扩一层
  （`tier`/`parentId`/`userId` 参数全被忽略，只能读 1 代，别反复试下钻）。

### 两个会产出「假否定」的测试错误

1. **JSON 类型是维度，不是细节。** `?friendUserId=4966`（数字）→ `[]`；
   `"4966"`（字符串）→ 200 带目标数据。**BOLA 只发 int 就会写出「无越权」的假结论**（本库真实踩坑）。
   每个 ID 型参数至少发 `int` / `str` 两形态——这是「输入形态证伪」的第五个维度。
2. **`*_EMPTY` 报的字段名不一定是缺的那个。** 注册漏 `payPassword` 却回
   `REGISTER_PASSWORD_EMPTY`（`password` 明明有值）。见 `*_EMPTY` 先补齐**上一次成功请求的全部字段**，
   再判断是字段名错还是值错。

### 读不出来的表 → 存在性 oracle 给出精确行数

路径参数资源对「不存在」与「存在但不属于你」回不同错误码时：

```
/resource/0      → 400 RECORD_NOT_FOUND    (不存在)
/resource/1..N   → 500 UNKNOWN_IDENTITY    (存在；归属校验挂在身份解析上)
/resource/N+1    → 400 RECORD_NOT_FOUND
```

二分即得 **N = 5278**，精确到行 —— 即使一行都读不出来，也能把「表有多大」写进报告。
身份来源只认 token：query/header/body 注入 `userId`/`uid`/`friendUserId` 全部无效，别浪费轮次。

### bundle 端点正则的一个引号差别（117 → 0）

打包后的 bundle 用**模板字符串**写路径：`grep -rhoE '"/v1/[^"]+"'` 返回 **0 条**。
用 `` '`/v1/[a-zA-Z0-9_/{}:.-]+`' `` 才出 117 条；再用 `. {190}`/v1/<ep>`. {120}` 取调用点原文，
方法 + 入参名一次到手（本项目 117 端点就是这样拿全的）。

完整配方、错误码对照与实测数据：`references/self-view-unmask-and-account-takeover-chain.md`。

## 鉴权墙分层：框架指纹 → 白名单家族 → 桩函数

`401/403` 不是终点，也不是「整站有鉴权」的结论。先按响应体判层：

- **go-zero**：`{"code":403,"reason":"Forbidden","message":"Authentication required","metadata":{}}`；裸 `404 page not found` = 没进路由（路径或 method 错）
- **Sa-Token**：`未能读取到有效 token`，默认头名 `satoken`；「无 token」与「token 无效」文案不同 = 头名 oracle

三条纪律（实测 2026-10-28，go-zero IM + Sa-Token 管理面）：

1. **白名单按精确路径注册，单点成功不可外推。** `/user_attachment/*` 10 个端点只有 `get_info_by_id` 放行，分页/按哈希/上传/改状态全 403。命中一个点后把整组端点 × `GET`/`POST` 打一遍再定口径。
2. **路径变量解析失败是第二存在性 oracle。** `GET /x/{id}` 传 `r` 回 500 `strconv.ParseInt`、传数字回 403 ⇒ 路由存在且需登录；同路径 POST 回 404 ⇒ 只注册了 GET。客户端字符串表里的路径 ≠ 服务端注册过。
3. **错误文案带未填充格式符 = 桩函数。** `登录失败(%d)` 这种原样回显的，handler 没写完，任意参数文案不变即弃线，别穷举 deviceId/imei/oaid。

4. **路径规范化决定白名单能否被「借道」。** `..%2f` 会被 Tomcat 规范化，Sa-Token 看到的就是 `/api/admin/...` ⇒ 401；`.;%2f` 不被规范化，白名单 `/api/common/**` 放行但 Spring 也不折叠 `.;` ⇒ 回 `非法请求：<原始路径>`。**`非法请求：<path>` = 白名单命中的 oracle，`401 未能读取到有效 token` = 未命中** —— 用这一对文案判断「前缀在白名单里但路由不存在」，别把 401 和路由兜底混为一谈。

JWT 伪造电池先在**确认存在且需鉴权**的路由取 403 基线 —— 拿 404 路由做基线会把 404 误判成「绕过成功」。alg=none + 30 余个弱密钥全灭属常态，价值在分钟级判死。

完整指纹表、白名单矩阵、IDOR 元数据与文件本体分离的交付口径：`references/auth-wall-whitelist-and-framework-fingerprints.md`。

## 边缘 400 空体 ≠ 端点不存在

同一主机一半路径 200、另一半 **400 + 0 字节 + `server: cloudflare`** ⇒ 是**边缘路径规则**，不是源站拒绝，更不是「端点没开」。三件套判据：`server: cloudflare`、`content-length: 0`、同 Host 兄弟路径正常。

绕规则先试静态后缀 `;.js`（`/api/actuator/env;.js`）。过后端回什么决定结论：

- `非法请求：/actuator/env;.js` = Spring 静态资源兜底 ⇒ **端点确实没暴露**（后缀破坏路由匹配，只能证「没开」）
- 业务 JSON / 200 = 到达目标，再换不带后缀的其它变形复测

2026 年 Spring Boot 默认只暴露 `health`：`GET /api/actuator` 的 `_links` 就是暴露清单，**只有 `health` 就别再爆 env/heapdump/loggers**；`health/db`、`health/redis` 回 404 = 组件没注册，到此为止。

判层细节：`references/waf-fronted-target-recon.md`；源站/备案层：`references/hidden-origin-recon.md`。

## .NET 422 ModelState：既是字段真名，也是类型 oracle

`422` 的 `errors` 有两种形态，价值差一个数量级：

- **完整 diagnostics**：`The JSON value could not be converted to ActiveSystem.Core.Default.VipPromotion.EnumPeriodValues`
  —— **CLR 类型全名直接吐出来**。`Enum*` ⇒ 标量枚举，发单值 `0..N` 遍历即解；`Guid`/`List<T>` 同理。
- **只有 DisplayName**：`detail:["活动标识 是必须的"]` —— `活动标识` 是 `[DisplayName]`，**不是字段名**。
  拿它当字段名撞必填校验是纯浪费（实测 57 候选 × 11 值 = 594 次全 Required）。
  此时回 bundle 抄调用点，或对候选字段**发错类型**（标量发数组 / Guid 发字符串）把响应逼回完整形态。

错误码三档定去留：`401/403` 需凭据 → `422` 参数可解 → **业务错误（`5024 没有找到下级会员…`）= 已进业务层**。
动钱/发奖接口回业务错误而不是 401，就是 handler 里没有 `[Authorize]` 的铁证。

**参数即身份 IDOR**（body 里只有 `uid`、无任何鉴权头）验证三件套：零凭据 + 无参对照组（回 `5003 登录过期`）
+ **非自造第三方 uid**。服务端只校验 uid 存在性、从不校验调用者归属 ⇒ 别人业绩/下级/邀请码 + 可代领。

响应加密与路由地图：AES-ECB 的 body 常是 **JSON 字符串字面量**（先 `json.loads` 去引号再 b64decode，否则
`Incorrect padding`）；`/metrics` 的 `route="…{uid}"` 标签 + controller/action 名 = 完整路由表，比 fuzz 精确且零噪音；
`adapt.js` 里的 endpoint 常是「十进制字符码 → base64」双层，只解一层拿不到真源站。

完整配方（`openssl` 判 IP 白名单 vs 主机死、注册免验证码的 bundle 判据、视觉点选三坑）：
`references/dotnet-modelstate-oracle-and-uid-identity-idor.md`。

## 热更新包 > 安装包：CodePush 是更快的契约源

IPA/APK 里的 `main.jsbundle` 常常是压过/混淆过的一版，`postLogin(`、`grep '"api/Cash/'` 这类正则直接 **0 命中** ——
不是没有，是**手上的包旧了**。RN 应用的真实生产代码走 CodePush 热更，通常比商店包新几个版本、混淆更轻，
**一次下载就能把 API 合约全拿到**。

四步取包（全程零鉴权，实测 2026-10-29 某 48.VIP 白标）：

1. **配置不在包里，走 DNS TXT 下发。** bundle 里搜 `codepush`/`TXT`，形如
   `https://dns.alidns.com/resolve?name=test-codepush-txt.<品牌域>&type=TXT`；
   TXT 值 base64 解出服务器数组 `["http://<ip>:<port>", ...]`。
2. **deploymentKey 在 iOS `Info.plist`**（`CodePushDeploymentKey`），不在 bundle —— `plistlib` 一次读出。
3. **`GET /v0.1/public/codepush/update_check?deployment_key=<key>&app_version=1.0.0`** 零鉴权回当前发布：
   `{"update_info":{"version":"v238","size":4194304,"download_url":"https://..."}}`。
   参数名不对会回 `please input deploymentKey and appVersion`（Gin 实现特征）—— 照这句改下划线/驼峰再打。
4. 下 zip → `unzip` → `CodePush/main.jsbundle`（实测 13 MB，比 IPA 里的大一倍）。

管理面：Gin 版 CodePush 只暴露 `/v0.1/public/codepush/*`，`/v0.1/apps`、`/v0.1/auth/login`、`/v0.1/accessKeys` 全 404；
bundle 落 S3 时 `GET /` 回 `AccessDenied`，**匿名 PUT 覆盖没成功过 —— 别把「能读」当成「能推」**。
推送需要 accessKey，那是另一条线（管理端/数据库）。**读通道 ≠ 供应链控制，报告里必须分开写。**

**这一招解决过的问题**：`LoginV2` 回 `422 detail:["登录地址 是必须的"]`，照 DisplayName 试了 57 个候选字段 × 11 个值全灭；
从 v238 热更包抄出真实构造 `loginUrl: Platform.OS`（值就是 `"ios"`/`"android"`，所以候选里传 URL 永远不中）。
—— DisplayName ≠ 字段名，**旧包 grep 0 命中时先去拿新包，不要开始穷举**。

配方与本例完整数据：`references/codepush-hotupdate-bundle-harvest.md`；探针：`scripts/codepush_update_check.py`。

### 验证顺序 oracle：故意送错密码

登录类接口的 factor 往往不止一个，**卡在哪一层决定你要攻什么**。用「正确用户名 + 明显错误密码 + 姓名变体」
三组对照，按返回码阶梯定位真正的门：

```
姓名缺失 → statusCode:2 请输入真实姓名
姓名不符 → statusCode:3 验证真实姓名错误      ← 只有姓名在比对
姓名匹配 → statusCode:1 验证码未通过 + verifyMode  ← 密码这一层根本还没判
```

实测该接口**密码在任何阶段都不参与判定**（`wrongpass123` 与正确密码返回完全一致）⇒ 硬门是
「用户名 + 真实姓名 + 极验票」，同时构成**姓名枚举 oracle**（3020/1029 可区分）。
反向的坑：`SearchUserPwd?userName=` 对存在与不存在**恒回 true** ⇒ 不是 oracle，立刻停手别浪费轮次。

### minified JS 里的 `Get[A-Z]` action 表

.NET/网关型前端把 action 名写成字符串常量，`.post(`/`axios` 常被 webpack 抹掉。稳写法是直接数标识符：

```python
collections.Counter(re.findall(r'\b(Get[A-Z][A-Za-z0-9]{2,40})\b', js))
```

一次拿全（实测 13 个 `Get*` = 推广站全部 action，含 `GetInfiniteSubordinate` 这种页面上没出现的）。
配套判据：**时间参数格式错会回「查询时间不正确」而不是 400** —— 依次试 `YYYY-MM-DD` / `YYYY-MM-DD HH:MM:SS` / ISO，
别把这当成接口不可用。

## 支付网关 → 收银台 → 链上：一条链打通

白标/灰产支付链的固定形状：商户页 `/mPG/`（或 `/mU2/`）带参数 → **302 到收银台**，
`Location` 里带 `?payInfo=<AES-base64>`（或 `/pay/<token>`）。三步顺下去：

1. **payInfo 直接解**：同一套前后端的 KEY 常在已抓到的 bundle 里，AES-CBC + PKCS7 一次成功
   （判据：cipher 长度 mod 16 == 0）。比逆 JS 快得多。
2. **收银台 SPA 只做一件事**：`fetch("/api/v1/pay/" + token)` —— 直接打这个 API，
   拿订单**全字段**（金额 / 收款地址 / `client_ip` / `client_region`），常无鉴权。
3. **收款地址 → 链上**：从订单里的 `address` 起手拉 TRC20 全量流水（分页 + decimals 坑 + 归集拓扑，见 reference）。

token 若为 32 位 hex，先算 `md5(client_order_id / pf_order_id / id)` 候选再判是否可枚举 ——
全灭就写「不可枚举」，别浪费轮次。

完整链路与实测数据：`references/pay-gateway-cashier-and-onchain-flow.md`。

## 全文导航（已拆分）

主卡保留前 2 节；其余 5 节在 `references/full.md`：

- 步骤
- 探针纪律（避免自伤、避免假结论、避免伤第三方）
- 工程纪律（长批次探针）
- 支持文件
- 报告落点

加载：`skill_view(name='api-contract-mining', file_path='references/full.md')`
