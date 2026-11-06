---
name: mobile-api-crypto-reversing
description: "Use when app API payloads are AES-encrypted."
version: 1.0.0
tags: [pentest, mobile, reverse, aes, gcm, flutter, api]
---

# Mobile API Crypto Reversing

你拿到的是一个 APP 的后端，不是 HTML 站点：TLS 解完后 body 还是 `{"data":"<base64>"}`。
这层加密的 key 硬编码在客户端二进制里，**它不是防护，只是延迟**。目标不是「解出一次密文」，
而是**用客户端那把 key 把整条 API 当明文接口来打**：看懂报错 → 走出 schema → 找到免鉴权/逻辑洞。

## 铁律

1. **先抠 key，再谈方案。** Flutter AOT（`libapp.so`）保留类名与字符串常量：
   `strings -n 6 lib/arm64-v8a/libapp.so | grep -iE 'encrypt|decrypt|aes|gcm|cbc|interceptor|secret|nonce'`
   典型线索是 `XxxEncryptionInterceptor` 类名紧邻一个 32 字符 ASCII 常量（AES-256）。
2. **用密文长度推模式，不要瞎试。** `L = 12 + n + 16` → AES-GCM（12B nonce + 密文 + 16B tag）；
   `L % 16 == 0` 且无独立 nonce → CBC/ECB。**明文一定是 JSON**，解出 `{"errCode":...}` 即一次命中。
   完整判定表与代码见 `references/aes-gcm-reversal-recipe.md`。
3. **请求侧通常比响应侧弱。** 先明文发；回 `encrypted data is required` 再把 body 包成
   `{"data": base64(nonce||ct||tag)}`（同 key，随机 12B nonce）。记下哪些接口强制加密——那往往是资金/管理面。
   **编码不要猜：拿一个已知能通的接口（登录）做对照**，同一份明文分别以「明文 / 标准 base64 / URL-safe base64」三发，
   哪一种回业务错误（而不是「格式错/空参」）就锁定哪种。本类服务请求侧实测是**标准 base64**，不是 URL-safe。
4. **字段位置比字段名更要命。** 同名放错位置会被静默忽略（Go/gin 不报错）。依次试
   **顶层 body → 嵌套对象（`user.*`）→ query → header**。填了没反应，十有八九在 header（`deviceID`、`X-Device-Id`、`token`）。
5. **`errCode:0` + token ≠ 账号可用。** 注册类接口可能发签名 token 却不落库。必须用第二条独立通道验证：
   同凭证 `login`、`findByPhone`/`exists`、一个受 token 保护的接口。**同一身份重复注册返回一个全新的 id 而不是「已注册」，
   就是写库 no-op 的直接证据**——有唯一约束的表不可能第二次还成功。
   更不要从 token 报错的文案反推签名状态：`TokenUnknown`/`1505`/`token is empty` 这类通用码在「签名错」和
   「签名对但服务端 token 表无记录」时**是同一个码**；能证明签名错的是另一集群明确的 `signature is invalid`，
   能证明签名对的是离线 HMAC 验签（见铁律 7）。
6. **写原语必须回读验证。** 上传/注册/配置写入返回成功只是声明：拿到 `object_name` 后直接 GET，
   验 200 + Content-Type + magic bytes。存储桶 `?acl` 回 200 也要读内容——`AllUsers: READ` 只代表可读。
7. **JWT secret 先离线验签，再谈在线 oracle。** 手上有服务端签发的真 token 时，直接离线比对 HS256 签名
   （`b64url(hmac(secret, h+"."+p))` 与第三段比较），一次证伪所有候选 secret，零请求、零风控、零封号。
   只用在线报错码判 secret 会把结论建在沙上（铁律 5 的通用码问题）。离线命中后再铸 token 打面板/提权接口验证 reach。
   rockyou 级（14M）打空就停，换面。
8. **502 / 404 / 403 / 200 是路由预言机。** 文档路径整段 502 不等于服务挂了：`502` = location 存在但上游此刻没起，
   `404` = 没这个 location，`403` = 边缘锁死。若兄弟前缀（`/openChat/account/*`）存活而 `/account/*` 502，
   说明 nginx 在做**剥前缀反代**。APK 里 `strings libapp.so | grep -E '^/[a-zA-Z]'` 收真实前缀，别靠猜。
   `/debug/pprof/`、`/debug/vars`、`/metrics` 回 502 = 位置配好了、后端平时是活的——挂轮询，它一回来就是堆里的 DB DSN 和服务密钥。
   **`200` + 空 body 单独看没有信息量**：加密校验中间件常先于路由匹配执行，未知路由也回 200 空；
   只有带文案的 `{"errMsg":"encrypted data is required"}` 才证明该路由真的注册了。没有文案的空 200 既不能当成功，也不能当不存在。
9. **「只验签名」的中间件才是提权面，但伪造是否生效必须用对照组证明。** 同一服务常并存两种中间件：
   `CheckToken`（验签 + 查服务端 token 表）和 `CheckAdminOrNil`/`OptionalAuth`（解析失败就静默降级为匿名）。
   只有后者能用自签 token 拿管理员上下文。判断标准不是报错文案，而是**三组对照**：无 token / 伪造管理员 token /
   真实普通 token 打同一个写接口——三者响应完全一致，说明伪造被降级成匿名（报的是缺邀请码、缺验证码这类业务校验），
   **不能写成「已获得管理员上下文」**。claim 的枚举值去源码常量里读，别猜 0/1。
10. **「填了没反应」先用类型探针定位层级，再决定要不要换名。** 把 string 字段传成数字（或对象传成字符串）：
    Go/protojson 会报 `cannot unmarshal number into Go struct field RegisterUserReq.invitationCode of type string`，
    **点名结构体+字段 = 该字段确实被绑定**，问题只在值或位置；若传对类型仍报「不能为空/必填」，
    则是上一层 HTTP 结构体没有这个字段（老 API struct + 新 RPC proto），**换多少名字都不会生效**。
    这一条能一次区分「字段名错」「嵌套位置错」「接口本身功能性残缺」，本类栈实测 `invitationCode`（注册）与
    `verifyCode`（验证码登录）都是被 HTTP 层丢弃的：自助注册和验证码登录在该部署上根本不可用，不是缺邀请码/缺码。

## 流程

1. 拆包 → `strings` 找加密类名/常量 → 拿一把候选 key（原文 ASCII，不是它的 hex/MD5）。
2. 打一个必失败请求拿真实密文 → 按长度定模式 → 解密出明文 JSON（这一步是整个链条的转折点）。
3. 实现加密器（请求用），先明文跑通所有不想加密的接口，再对强制加密的接口包 `data`。
4. 用服务端报错逐字段推进 schema；注意嵌套位置与 header 位置（见铁律 4）。
5. 把每种「免鉴权 / 只读 / 写」原语过一遍：config、上传、枚举、验证码、版本、客服/下载域名——
   客户端配置接口经常把系统 UID、内部群组、第三方域名白送。
6. 对每个「成功」回读验证（铁律 6），再决定是否当战果上报。
7. 加密打通后仍然拿不到身份，是常态：下一步是**写原语 → 供应链/存储滥用**或**边缘/调试接口（pprof）**，
   不是继续爆 JWT。

## 坑

- 同一套代码换租户可能换 key：一个包里的 key 打不开另一个租户的同版本 API，别据此判定「方案猜错」。
- 固定 nonce/IV 常量 = 确定性密文，本身就是可上报缺陷（可重放）。
- 客户端 `imToken`/`chatToken` 这类 token 常属于独立集群，主站/后台的 secret 与它无关。
- 上传口限制扩展名/路径时（强制 `.png`、固定目录），别硬穿——把它当「生产 CDN 可被任意人写入」的证据，转向别的面。

## 参考

- `references/aes-gcm-reversal-recipe.md` — key 线索、长度判定表、Python 加解密器、schema 走查与假成功验证的完整命令级配方。
