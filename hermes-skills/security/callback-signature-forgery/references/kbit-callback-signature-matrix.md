# KbitPay kbit 回调验签黑盒矩阵(2026-09 实战,QQLink 案)

目标:`POST https://api.wallet8.top/v1/kbit/callback`(KbitPay→wallet 入金/划转回调)。
已知生产密钥:`kbit.appSecret = <REDACTED> config.yaml)。

## 核心发现:无签名差分

**所有请求(含完全不带 sign 字段)均返回同一错误 `{"ErrCode":50,"ErrMsg":"kbit 签名验证失败","ResData":null}`。**

→ 服务端根本没读到 sign 字段 = **请求结构不对**(不是算法不对)。算法爆破浪费;下一步应猜结构:
- sign 字段的真实名称/嵌套层级(可能 body 整体被包成另一层信封)
- 验签数据来源可能是 header / query / 特定字段拼装,而非整个 body
- 参考同平台 walletFunds 回调的 `{Data, Signature}` 结构(Data 为 JSON 字符串)

## 已试矩阵(全部同错误,记录避免重跑)

签名算法(8):md5(ts+secret)、md5(secret+ts)、md5(body+secret)、hmac_sha256(ts)、
hmac_sha256(body)、sha256(ts+secret)、md5(全部参数)、hmac_md5(ts)

字段名变体(6):sign / signature / signValue / signData / clientSignature / sig

Header 变体(8):X-Sign、X-Signature、sign、Signature、Authorization、
X-Timestamp、clientTimestamp、clientSignature(全带错值 + 无签名)

结构变体(6):data=JSON字符串+sign、data=对象+sign、data=base64+sign、
data+sign、{Data,Signature}、{Data, sign_md5}

## 错误字符串归属(诊断要点)

`kbit 签名验证失败` 在二进制中的上下文是 `[GetPnProducts] handle:kbit 签名验证失败`
(wallet→kbit **出站请求的响应验签**),与入站回调验签共用字符串。
同一失败串 ≠ 同一验签方——需分别确认验签实现。

验签函数符号:`wallet/pkg/kbit.(*KBitClient).VerifySignature` @ 0x98c620
= thunk 表(jmp 0x975b20),真正实现 @ 0x975b20(内联,不在 pclntab)。
0x975b20 内部:类型 hash 比较(0x7efbbf65/0xf88732b8)→ [rdx+0x540] 取 secret → call 0x6668c0(类型断言)。

## 同域鉴权分层探测(方法论)

用 GET/POST/空 body 探同域端点,得到三层中间件地图:
- `GET /v1/assets/getAssetsStatistics` → `token解析失败-1`(token 中间件)
- `POST /v1/asstes/transferDeduct` → `Invalid AES key or data`(AES body 解密中间件)
- `POST /v1/kbit/callback` → `kbit 签名验证失败`(签名中间件)
- `POST /v1/asstes/withdrawCoin` → `token解析失败-1`(先 token 后解密)

「AES 先于签名」= 解密是第一层中间件,签名是第二层(业务内)。
