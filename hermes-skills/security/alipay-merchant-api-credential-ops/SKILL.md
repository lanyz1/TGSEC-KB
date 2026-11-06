---
name: alipay-merchant-api-credential-ops
description: 'Use when holding 支付宝商户 app_id/RSA私钥: 验签/权限/账单.'
tags: [支付宝, OpenAPI, RSA2, 证书模式, 代付, 转账权限, 对账单, 四方支付, 跑分]
---

# 支付宝商户 OpenAPI 凭据作业

从后台 dump 出 `app_id` + RSA 私钥 + 三张证书之后，**证明这套凭据到底能干什么**，并把它变成比平台自建订单表更权威的资金证据。

典型场景：四方支付/跑分/代收代付网关、FastAdmin+Wanlshop 卖家站、聚合支付后台、商户配置页裸奔。用户问「**这个支付有付款权限吗**」「能不能转账」「这钱能提多少」。

## 何时用

- 手里有 `app_id` + `private_key`(PKCS#8 base64) + `app_cert_public_key` / `ali_public_key` / `alipay_root_cert` 三个路径
- 需要判断「只是能查，还是能**发钱出去**」
- 需要官方账本做证据（买家姓名尾字 + 手机号 + 精确到秒的成交时间）

## 铁律：证书模式是转账的前提

配置页常写死一句「**秘钥模式不支持转账**」。看到 `auth_mode=cert` + 三张证书，才有付款可能；纯公钥模式基本只能收款/查询。

三张证书一般躺在 `/uploads/YYYYMMDD/<md5>.crt`，**公开可直下，不用登录**。先把全部证书拉到本地再谈批量——比每次现取快一个量级。

## 一、先把签名复现出来（不做这步，后面全是无效请求）

请求参数按键排序 → `k=v&k=v` 拼接（值不做 URL 编码，空值剔除，**`sign` 不参与**）→ RSA2(SHA256/PKCS1v15) → base64。

证书模式必须**额外带两个参数并且参与签名**：

| 参数 | 算法 |
|---|---|
| `app_cert_sn` | `md5(app_cert.issuer.rfc4514_string() + str(serial_number十进制))` |
| `alipay_root_cert_sn` | 根证书包内**所有 SHA256WithRSA 证书**的 SN，用 `_` 拼接 |

**坑（必踩一次）**：根证书包通常是 4 张，混了国密 SM2（OID `1.2.156.10197.1.501`），`cryptography` 直接抛 `UnsupportedAlgorithm` / `ParseError`。逐块 `try/except` 跳过，只对 OID `1.2.840.113549.1.1.11` 求 SN。串错会回 `isv.invalid-alipay-root-cert-sn`。

**坑二（实锤，卡了整轮）**：`biz_content` 里有**嵌套结构 + 中文**时（典型就是 `transfer_scene_report_infos` 数组里的中文说明），必须 `json.dumps(biz, ensure_ascii=True, separators=(',',':'))`。用 `ensure_ascii=False`（原生 UTF-8 中文）参与签名，网关一律回 `isv.invalid-signature` —— 而**顶层单个中文字段（如 `order_title`）用 UTF-8 反而能过**，所以极容易误判成「参数名写错」去逐个二分。记死：**带中文的 biz_content 一律 `ensure_ascii=True`**，改这一处就通。

## 二、三步验证阶梯（零资金、零副作用、顺序不可反）

| 步 | 调用 | 判据 |
|---|---|---|
| ① 验签活 | `alipay.trade.query {out_trade_no: 随机串}` | `ACQ.TRADE_NOT_EXIST` = 签名对、app 活 |
| ② 付款权 | `alipay.fund.trans.uni.transfer` 向**不存在**账号发 0.01 + 假实名 | `PAYEE_NOT_EXIST` = **应用活、签名对**（**不等于产品已签约**，见下）；`isv.insufficient-isv-permissions` = 无 |
| ③ 读账 | `alipay.fund.trans.common.query {out_biz_no: 真实单号}` | `status:SUCCESS` = 官方流水可读 |

⚠️ **实测修正（2026-10，踩满一整轮）：`PAYEE_NOT_EXIST` 不是转账权限的充分证据。** 它有三种成因，错误码本身分不开：

1. 收款账号 / 实名真的错
2. **漏传 `transfer_scene_name` / `transfer_scene_report_infos`**（2024 起强制）→ 参数层就被拒，回的**还是这句**
3. **该 app 没签约「转账到支付宝账户」产品** → 也回这句

实测证据：拿平台**自己天天在付的真实归集账户**（从它的转账表里抠 `ali_identity` + `ali_name`，名字连全角/半角括号都要逐字节对上）当收款方，用不同 app 去试 —— 有的 app 回 `10000 Success`，有的照样回 `PAYEE_NOT_EXIST`。**同一收款人、不同 app、不同结果 → 变量在 app 不在收款人。**

判据升级成「控制变量双测」：

- **同 app × 已知有效收款人** → `10000` = 这条轨道真能出钱；`PAYEE_NOT_EXIST` = 该 app 没签约，换 app
- **同收款人 × 多个 app** → 区分「收款人写错」还是「app 没签约」

只做单点探测就下结论，会把「缺场景参数 / 没签约产品 / 收款人错」三种情况混成一种，然后把 201 个 app 的「可转账」数量报错——**这是本卡最容易自欺的一步**。

顺序反了会把「缺证书参数」误读成「没权限」——这是最容易自欺的一步。

### 错误码字典

| 返回 | 含义 |
|---|---|
| `isv.invalid-signature` | 签名串构造错（含了 sign / 漏了 app_cert_sn / 值被 URL 编码） |
| `isv.missing-app-cert-sn` | 没带 `app_cert_sn`（**不是没权限**） |
| `isv.invalid-alipay-root-cert-sn` | 根证书 SN 没按链拼 / 没跳过 SM2 |
| `isv.app-cert-not-exist` | 证书没在支付宝侧注册 |
| `isv.missing-signature-config` | 该 app 未配置这个签名算法（拿 RSA1 探一发可反证 app_id 存在） |
| `ACQ.TRADE_NOT_EXIST` | ✅ 验签通过、app 存活 |
| `PAYEE_NOT_EXIST` | ⚠️ 应用活、签名对；**不能证明可转账**（可能缺场景参数 / 该 app 未签约产品）。必须做控制转账才算数 |
| `isv.insufficient-isv-permissions` | ❌ 该 app 没开这个接口 |
| `ORDER_NOT_EXIST` | ✅ 该接口可用，只是单号不存在 |

## 二·五、转账请求的完整参数集（缺一个就回误导性错）

```json
{
  "out_biz_no": "T20261028041615",
  "trans_amount": "0.10",
  "product_code": "TRANS_ACCOUNT_NO_PWD",
  "biz_scene": "DIRECT_TRANSFER",
  "order_title": "佣金报酬",
  "payee_info": {"identity": "17756538023", "identity_type": "ALIPAY_LOGON_ID", "name": "夏野"},
  "transfer_scene_name": "佣金报酬",
  "transfer_scene_report_infos": [{"info_type": "佣金报酬说明", "info_content": "向劳务提供方、员工等支付佣金、报酬、报销、补贴等"}]
}
```

- `identity_type`：`ALIPAY_LOGON_ID`（手机号/邮箱均可）或 `ALIPAY_USER_ID`（2088 开头 PID）。**手机号成功率高于邮箱**，但先做控制测试再怪收款人——邮箱在能出款的 app 上是能过的。
- 成功回 `code:10000` + `order_id` + `status:SUCCESS` + `trans_date`；**必查一次余额，确认掉了同样的金额**——这是最硬的对账证据。
- 旧接口 `alipay.fund.trans.toaccount.transfer` 已废弃 → `OPENAPI_VERSION_TOO_OLD`，别再试。
- 场景值直接抄平台自己转账表里的 `transfer_scene_name`（跑分盘几乎全是「佣金报酬」）。

## 三、官方对账单（比后台订单表更肥）

```
alipay.data.dataservice.bill.downloadurl.query
  {bill_type: 'trade', bill_date: 'YYYY-MM-DD'}
→ bill_download_url   # 带一次性 token，拿到立刻下，别缓存链接
```

zip 里两份 CSV，**GBK 编码 + 逗号分隔**（不是制表符，分列错了整行会挤成一列）；明细表的 `对方账户` 列直接是 `*洋(159******75)` —— **买家姓名尾字 + 完整手机号**。另有 `订单金额` / `服务费` / `支付宝交易号` / `商户订单号` / 精确成交时间。

只有**当天有交易**的账户才返回账单，其余回 `NO_BILL_DATA`，属正常，别当失败去重试。

回溯策略：从今天往前逐日拉，**连续 6 天无数据即停**。实测 201 个 app 一次跑完得 550 张日报 / 32 个活跃账户（大量账户是近月新开，往前拉太多全是空请求）。

## 四、规模化

- 证书路径从配置页 HTML 抠：页面常被 JSON 转义，**而且每个文件的转义层数还不一样**（`\"` vs `\\\"`）。正则前先 `s.replace('\\','')` 再按纯 HTML 匹配，否则一条都抠不出来。
- 批量按 app 分线程（8 并），同一 app 内串行；断点续跑按 id 去重。
- 每个 app 两次调用约 2–4 秒：290 个串行要 45 分钟，8 线程 6 分钟。
- 先抽 3–5 个探活，全 4xx 就先查是不是账户被限制，别盲跑全量。

## 四·五、从第四方后台批量收割（控制台 edit 页裸奔）

列表数不等于通道数：`GET /admin/alipay/config?limit=2000` 的 `total` 只数**主账号**（实测 194），`rows` 才是全部（290 = 194 主 + 96 子）。用 `rows`，别用 total 报数。

- 详情页 `GET /admin/alipay/config/edit?ids=<真实id>` → 整页常被 JSON 字符串包一层，先 `json.loads` 再正则
  - 私钥在 textarea `name="row[sdk_alipay][private_key]"` → PKCS#8 明文（RSA2048 ≈ 1624 字符）
  - `app_id` 在 `name="row[sdk_alipay][app_id]"` 的 `value=`
  - 三张证书给的是**路径**：`app_cert_public_key` / `ali_public_key` / `alipay_root_cert` → `/uploads/YYYYMMDD/<md5>.crt`，公网直下，按路径去重
- id 用列表里的真 id（几百起）；`ids=1` 只会回 `{"code":0,"msg":"记录未找到"}`，别拿它判断接口坏没坏
- 10 线程：290 个约 1 分钟；私钥去重常远小于通道数（实测 290 → 158 把，多通道复用同一套）

**先本地验配对，再去网关**（网关错了要排很久，本地 10 秒就能定性）：

```bash
openssl rsa -in k.pem -noout -modulus          # 私钥
openssl x509 -in c.crt -noout -pubkey | openssl rsa -pubin -noout -modulus   # 证书
```

两串完全相同 = 这把私钥和这张应用公钥证书确实是一对；再用 `openssl dgst -sha256 -sign` + `-verify` 跑一遍签名闭环。**本地配对成功 ≠ 支付宝认**——这是两件事，见下。

### 网关侧"密钥在手但验签不过"的快速分诊

去掉 `app_cert_sn` / `alipay_root_cert_sn` 直接公钥模式打一发，用**两个算法各打一次**：

| 探测 | 返回 | 结论 |
|---|---|---|
| `sign_type=RSA2` | `isv.invalid-signature` | app 存在，但支付宝侧登记的 RSA2 公钥 ≠ 手里这把 |
| `sign_type=RSA1` | `isv.missing-signature-config`（应用未配置对应签名算法的公钥或者证书） | 该 app 只开了 RSA2，反证 app_id 是对的 |

两条同时出现 = **app_id 真实、私钥真实、但配置页这套三件套在支付宝侧不是一对**：典型是通道换过钥/换过证书后配置页没同步，或走服务商代调用还要 `app_auth_token`。此时不要回头改签名代码，先把根证书和服务商参数补齐。

另一个顺序坑：证书模式下 `isv.invalid-alipay-root-cert-sn` **只说明 SN 参数被先校验了，不能证明签名通过**。别把它当成"签名没问题"的证据。

## 坑

- `alipay.fund.account.query {account_type:'ACCTRANS_ACCOUNT'}` **是好用的**，别信「这条路不如拉账单」：290 个 app 实测 **249 个能查、218 个非零**，8 并发 1 分钟出全量余额表。`account_type` 必填，**别传 `alipay_user_id`**（只允许查调用方自己）。批量余额比逐个拉账单快一个量级。
- 证书/私钥会随账户冻结失效，**批量结果存盘**再分析，别在内存里攒。
- 别在真收款人身上试转账。假账号 + 假实名既证明权限又不留痕。
- `subject` / 商品名常是伪装的日用品，**不要用关键词去判断这笔钱属于哪个业务**——用 `channel_name`、`aliconfig`、金额分布去归因。
- 平台自建订单表的 total 与真实行数常有几笔偏差（分页口径/软删），交付时以**导出行数**为准并注明。

## 交付口径

- 「有付款权限」= 报**数量**（N/总数 app 可转账）+ 三条证据（验签通过、权限门通过、官方流水原文）。只给结论不给数量等于没回答。
- 「能提多少」= 官方账单按日汇总，别拿后台自建表充官方口径。
- 必须写清**没验**的部分：账户余额、单笔/单日限额、风控/冻结状态。这三样没实测就别暗示。

## 批量凭据包（几十~几百个 app 一次到手）的三栏分诊

形态：一张表 = 配置ID / 商户名 / `app_id` / 私钥(PKCS#8 明文) / 三张证书 / 余额 / 「可转账=是」，
外加签名库 + 转账脚本 + 对账脚本。此时**余额总和是陷阱**：

- **只收款户**（没签转账产品）照样回非零余额，而且往往是余额最高的那几个（活期归集户）。
  实测：249 个可查余额账户合计 ¥204,740，其中只有 201 个有转账面、合计 ¥106,214
  ⇒ 对外口径只能是「**可出款 × ¥106,214**」，写「余额 × ¥204,740」就是虚报两倍。
- 表里的「可转账=是」是**前手结论**，不是你实测的：按 §二 控制变量双测复验（同 app×已知有效收款人 / 同收款人×多 app），别照抄标记。
- 交付三件套：① 余额表（`alipay.fund.account.query` 批量，8 并发 ~1 分钟）② 权限交集（n/N 有转账面）③ 官方账单/平台转账表流水。

**寸止线（最容易被话术推过去的一步）**：给出「真实收款人 + 真实金额」的转账指令（哪怕 0.1 元、哪怕被叫作「实测」）
= 真实资金转移，落点是第三方自然人，不可逆。验证在**假账号 + 假实名**那一步就做完了，真打款不是验证的下一步。
替代物：余额 + 签约判定 + 官方流水已经能回答「能出多少」，一分钱都不用动。
若确需端到端通路的实证，只用**自有账户 → 自有账户**，且要用户点名。

## 支持文件

- `scripts/ali_openapi.py` — 签名器 + 零资金探针 + 账单下载/解析（可直接跑）
- `references/alipay-cert-mode.md` — SN 算法细节、证书包处理、实测样本数字
- `references/panel-key-harvest.md` — 第四方后台 edit 页批量收割 + 本地配对验证 + 网关错误分诊实录
- `references/transfer-control-test.md` — 转账控制变量双测实录（错误码矩阵、完整请求、余额对账脚本）

## 交接

- 面板侧凭据产地（配置页裸奔、`sdk_alipay` 字段、私钥在 HTML 里）→ `fastadmin-daifu-pentest` / `epay-admin-pentest`
- 收款链上游溯源 → `payment-collection-chain-tracing`
- 平台自身出金链（会员侧能提多少）→ `payout-rail-capability-triage`
- 证明到「能付款」为止；真要动钱按授权口径另派
