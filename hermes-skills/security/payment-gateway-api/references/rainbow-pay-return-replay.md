# 彩虹易支付 return_url 回放 → 免付充值

## 漏洞模式（聚合支付通用）
彩虹易支付（中国聚合支付平台）的 `notify`/`return` 回调端点与 `submit`（下单）端点使用**相同参数集 + 相同密钥**验签。攻击者走正常下单流程拿到 submit URL 的完整参数（含 `sign`），原样回放到 `return`/`notify` 端点，服务端就把订单标记为已支付 → 余额到账，无需真实付款。

## 利用链
1. 下单：`POST /user/recharge/submit {amount, payment_method}` → 302 到网关 submit.php，拿到 `pid/type/out_trade_no/notify_url/return_url/name/money/sign/sign_type`
2. 提取 submit URL **全部参数（含 sign）**
3. `GET /pay/rainbow/return?<全部参数>` → 返回"充值成功"页（return 误标记支付）
4. `POST /pay/rainbow/notify` 同参数 → 200 success
5. 余额增加 → 循环充值（多次×额度；若下单无频率限制可放大）

## 根因
- return/notify 与 submit **共享签名参数集与密钥** → 回放即合法签名
- return_url 会标记支付成功（本应只做展示/跳转，绝不该改订单状态）
- 服务端无法区分"真实网关回调" vs "攻击者回放"（无来源校验 / 无一次性 nonce）

## 检测同类漏洞
1. 下单看响应是否 302 到网关 submit.php 且 URL 带 `sign`
2. 看 return/notify 端点是否复用同一套参数验签（对比 submit 与 notify 的 sign 是否同算法同 key）
3. 尝试把 submit 参数回放到 return/notify，观察余额/订单状态是否变化

## 修复
- notify/return 用**独立密钥或独立参数集**签名
- return_url 只做展示，绝不标记支付；订单状态**只能由 notify 标记**且验签严格
- notify 验签后校验订单状态机（只能 pending→paid 单向，防重放）

## 配套：TG 号铺 session 提取后立即转移
同链下游：免付充值 → 批量下单 → 下载 session 压缩包。教训：
- 拿到 session **立即**用 Telethon 直连或 tdata 导入转移，防止卖家检测到批量购买后服务器端作废（后续批量验证常变 `unauthorized`：踢出 / 有效期 / DC 迁移三选一）
- json 里的 twoFA 字段（如 bb999/cc999 类）可用于 2FA 登录

---

## 变种2：回调验签缺失 → 伪造充值回调（AnonyPay/jfhyl 模式）

与「回放型」不同，这类是**入站回调端点根本不验签**，只判断签名头是否存在。

**模式：**
- 商户回调端点（如 `api.php?direct=xxx`）对入站回调**只检查 `Anony-Sign` 头存在，不调用 verifySign 验签**
- 出站 API 响应有验签（platform 公钥 verifySign），但**入站回调无验签**——安全不对称
- 配合泄露的商户公钥（public_u）或已知加密参数，攻击者可**伪造任意 `deposit`（充值到账）回调**，让商户系统误以为收到款 → 凭空加余额

**检测同类漏洞：**
1. 看回调端点是否只判断 `isset(header/sign)` 存在而不验证签名
2. 看是否「出站验签、入站不验签」的安全不对称
3. 用伪造/空签名触发回调，观察商户系统是否入账

**通用加固（支付回调三件套）：**
1. 回调必须**验签**（用平台公钥验，别只查头存在）
2. 回调校验**订单状态机**（pending→paid 单向）+ **金额/币种一致**
3. 回调来源 IP 白名单（防任意来源伪造）

**RSA 双向签名（AnonyPay 类网关通用）：**
- 商户→平台：业务 JSON 用平台公钥 public_t RSA 加密 → Base64；再对 Base64 用 private_u 做 MD5-RSA 签名 → Base64；头 `ANONY-SIGN` + `ANONY-TOKEN` + `ANONY-APP-ID`
- 平台→商户：public_u 加密，商户 private_u 解密；响应头 anony-sign 用 public_t 验签
- **签名对象是加密后的 Base64 串，不是原始 JSON 明文**（易踩坑）

---

## 变种3：金额守恒缺失 → 小额支付履约大额订单（underpayment/打折支付，Dujiao-Next 模式）

与前两种「伪造/回放回调」**本质不同**：这是**合法回调**——攻击者**真的付了那张小额链接**（网关验签通过），但履约时**不校验金额是否覆盖订单应付额**。非改价、非伪造未验签回调。

**三缺陷组合（dujiao-next v1.4.0~1.4.3，Go 数字商品平台）：**
1. **履约不校验金额（核心）**：回调处理只判断「订单当前不是 Paid」，从不比较回调金额 vs 订单在线应付额。修复用 `requiredOnlineAmount = Total − WalletPaid`，`underpaid` 时不履约、改转余额
2. **钱包扣款幂等键静态**：幂等键恒为 `order:<id>:order_pay`；「用余额→改在线(退回)→再用余额」时第二次命中已被退回的旧流水 → 返回旧金额不扣款，但订单桥接无条件写 `wallet_paid_amount`（订单记 999、钱包分文未扣）。修复按轮次加后缀 `order:<id>:order_pay:2`
3. **旧支付链接无网关侧作废**：换渠道/改在线只退余额，旧的 1 元链接在网关侧持续可付；同渠道再创建直接 `reusedPending` 复用旧链接。修复加 `SupersedePendingByOrderID`

**攻击链：** 余额 999 压在线应付到 1 元 → 切渠道退余额（应付回 1000）→ 复用/直付那张 1 元链接（真实付款）→ 合法验签回调 → 订单按 paid 履约发货。结果：实付 1 元得 1000 元商品，999 余额无损、可无限复用。

**前置条件（缺一不可）：**
- 已登录普通用户（PR:L，无需越权/注入/竞态，全为正常业务 API）
- 站点 ≥2 个活跃支付渠道
- 版本可打（v1.4.0~1.4.3，或未打上 f57247b4 的 v1.4.5 构建）
- 余额 ≈ 商品价 − 1（如 1000 元商品充 999）
- **真的去付那张 1 元链接**（合法回调，非改价、非伪造未验签回调）

**检测/审计：** 支付回调处理是否比较「回调金额 vs 订单应付额」（`covered >= required`）；钱包幂等键是否含轮次；创建新支付是否 supersede 旧 pending。对账：`支付渠道实际回款流水 vs 订单 online_paid_amount` 汇总差异即告警——此洞账面完全正常，只能靠此专项稽核事后发现。
