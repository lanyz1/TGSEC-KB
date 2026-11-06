# 实战案例:QQLink 钱包 × KbitPay paymentCallback 验签逆向(2026-09)

目标:`https://api.qqlink.live/v1/quickChange/paymentCallback`(POST)— 代付到账回调,QQLink Go 服务端(wallet v1.0.534,52.9MB ELF)。

## 端点探测结果

- 空 POST `{}` → `{"ErrCode":50,"ErrMsg":"kbit 签名验证失败","ResData":null}` → 验签在参数解析之前,无 sign 必败。
- 30+ 变体全败:JSON/form × 排序/自然序 × secret 前后缀 × MD5/HMAC-SHA256/SHA256 × `&key=`/`&appSecret=` 拼接 × Kbit-Token/X-Kbit-Token/Authorization Bearer header。

## 错误码语义(该平台)

- `50` = kbit 签名验证失败(回调验签统一错误)
- `4044` = 缺加密协议(未加密请求统一 4044,管理台面)
- `4009` = User is not registered
- `40010` = 管理端需 IP 白名单
- `4013` = JWT 失效

## 二进制静态逆向路径(走通的部分)

1. 符号表(pclntab)确认函数存在:`quickChange.(*sQuickChange).QuickChangePaymentCallback`、`handleRemittance`、`VerifySignature`、`GenerateSignature16hex`、`GenerateSignature2`;KFiatPay API 路由:`/api/Pay/remittancesubmiitorder`、`/api/Pay/remittancequote`、`/api/Card/Reconciliation`。
2. 字符串锚定(关键 VA,Go 二进制 rodata):
   - `0x1397bda`(off):`[GetPnProducts] handle:kbit 签名验证失败` ← paymentCallback 返回源
   - `0x138f412`:`随机数已使用` + `签名验证失败`(nonce 防重放!)
   - `0x1392c75/0x1392e91`:`签名验证失败-1/-0`
   - `0x13b437d`:`WalletAccountCallback 签名验证失败/随机数已使用`
   - 字段/配置 key 簇:`kbit.appId`、`WebhookUrl`、`Kbit-Token`、`statusCode`、`sign data:`、`return_url`、`notify_url`、`trade_type`
   - 状态:`TRADE_SUCCESS`、`REMITTANCE_COMPLETE`
3. 回调处理函数解剖(0x11bcd00-0x11bd680 区):`app_id mismatch`(0x11bd680)、`callback_nonce`(0x11c7a40)、TRADE_SUCCESS 分支(0x11bd075)、幂等锁 `lock cmpxchg`(0x9a62a0 内)、Redis 调用密集(BFAdd/XAdd/Echo/RestoreReplace = nonce 防重放 + 队列)。

## 结论与教训

- **Go 内联死局实锤**:`VerifySignature`(0x98c620)是 thunk,正常路径只做参数搬移后 call 0x975da0;而 0x975da0 内部全是 gmap/yaml/websocket/redis 调用 = 通用工具转发,不是签名计算。crypto/md5.checkSum、sha256.Sum256 **直接 call 数 = 0**(被内联)。
- **lea xref 假阳性实锤**:初版 xref 扫 `48 8d ?? imm32` 把 `lea rcx,[rbp+disp32]`(modrm 0x8d,栈局部)当 rip-relative,命中一堆 redis 库函数;修正为 `modrm & 0xC7 == 0x05` 后命中才有效。
- **密钥归属判断**:全矩阵全败 = 大概率 test 线密钥 vs 生产配置不匹配,或验签方不在 Go 端(该平台 SignatureAuthMiddleware 在 ASP.NET Core 内网 10.0.11.5:7968)。Go 二进制只是签名消费者。
- **下一步现实路径**(供复用时参考):① test 环境黑盒验签(test 密钥全在手 → testapi.kbitpay.com/kfiat 发真实签名请求还原算法,通了再套生产);② 转 .NET 端逆向中间件;③ 绕回调伪造,用已拿到的 IDOR AppSecret 走商户 API;④ 已控 MySQL 直改配置(QUICKCHANGE_DAILY_EXEMPTION_LIMIT=999999 已确认存在)。
