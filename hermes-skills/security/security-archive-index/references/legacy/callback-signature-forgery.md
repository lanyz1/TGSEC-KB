<!-- archived from /root/.hermes/skills/security/callback-signature-forgery/SKILL.md on 2026-10-21 -->

---
name: callback-signature-forgery
description: "触发: paymentCallback, 回调伪造, 验签绕过, 签名验证失败. 验签绕过方法论。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/callback-signature-forgery`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/callback-signature-forgery/…')`，不要相对 `references/legacy/` 解析。

# 回调签名伪造 / 验签绕过 (Callback Signature Forgery)

对支付/代付/webhook 回调端点(paymentCallback/notify/return)做签名伪造与验签绕过的类级方法论。典型目标:站内记账(伪造「到账」回调)、代付状态机劫持。

## 工作流

1. **端点确认** — 从 IDOR/管理台/JS chunk 挖出回调 URL(POST paymentCallback 活着 = 探测目标)。空参数 POST `{}` → 若返回「签名验证失败」类错误码,确认验签在参数解析之前(无 sign 必败)。
2. **二进制定位验签逻辑**(有服务端二进制时):
   - 搜验签失败字符串(「kbit 签名验证失败」/「签名验证失败」)VA → 用 `scripts/string_xref.py` 找引用者 = 错误构造点,往回推核心逻辑。
   - 反汇编回调处理函数,解剖链路:验签 → **nonce 防重放**(Redis `callback_nonce` 等)→ **appId 匹配**(`app_id mismatch`)→ **幂等锁**(`lock cmpxchg`)→ 状态分支(`TRADE_SUCCESS`)→ 记账。
   - 字符串锚定线索:`kbit.appId` / `WebhookUrl` / `Kbit-Token` / `sign data:` / `return_url` / `notify_url` / `trade_type` 等字段名与配置 key 簇。
3. **动态签名变体矩阵**(静态死局后立刻转,见坑 2):对 live 端点串行、低频发:
   - 格式:JSON vs form-urlencoded vs query string
   - 拼接:排序 vs 自然序;`&key=SECRET` 后缀 vs `&appSecret=` vs 裸拼;secret 前缀 vs 后缀;md5 全/大写/16 位截断;HMAC-SHA256;SHA256
   - Header:`Kbit-Token` / `X-Kbit-Token` / `Authorization: Bearer <secret|md5|appId+secret>`
   - **判据**:响应从「签名失败」变为其他错误(参数缺失/订单不存在/成功)= 签名过了,再细化。
4. **密钥归属诊断** — 全矩阵全败时,最高概率是**密钥不匹配**(test 线密钥 vs 生产配置)。先确认目标端点用的配置源(loot config.yaml / DB wallet_config / 管理台 GetPayAppList),再谈算法。另一个可能:验签方根本不在这个二进制(如 ASP.NET Core 中间件链 RsaDecrypt→TokenAuth→SignatureAuth→IpSecurity),Go 端只是消费者——转向验证方或换攻击面。

## 坑 (Pitfalls)

1. **Go 内联死局**:导出的 VerifySignature/GenerateSignature 常是 thunk 包装,核心内联成接口调用;crypto/md5、sha256.Sum256 直接 call 数 = 0。确认包装结构后**立刻转动态**,不要烧光时间预算。
2. **lea xref 假阳性**:扫 `48 8d ?? imm32` 必须过滤 `modrm & 0xC7 == 0x05`(RIP-relative);`0x8d` 等是 `[rbp+disp32]` 栈访问。movabs `48 b8 <imm64>` 是字符串引用的兜底搜索。
3. **nonce 防重放**:回调通常要求未消费的 nonce(Redis SETNX 类),伪造时同参重放会被 `随机数已使用` 挡——先探测 nonce 字段与有效期。
4. **幂等锁**:记账处常带互斥(lock cmpxchg / 订单状态机),重复回调不重复记账;伪造的目标是「首达」而非重放。
5. **回调需完整链**:正确签名 + 新鲜 nonce + 匹配 appId + 幂等通过,缺一不可——不要只看签名。

## 支撑文件

- `scripts/string_xref.py` — 修正版 Go 字符串 xref 扫描器(严格 RIP-relative + movabs 兜底 + 字符串 dump)
- `references/payment-callback-case-qqlink.md` — QQLink×KbitPay 实战案例(端点/错误码/链路解剖/全败诊断)
