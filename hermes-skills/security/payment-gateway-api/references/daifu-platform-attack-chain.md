# 代付平台攻击链（RuoYi 代付盘 · 威尔斯族 lwsdeployv）

龙胜代付（LWS）类「代付平台」：RuoYi 后端 + 商户后台 + 开放 API 网关，业务是银行卡代付（产品码 600）。区别于支付聚合平台（Fortis-Pay/qixinpay，见 payment-platform-backend.md）——这里是打「代付盘」自身：拖商户钥、读上游代付钥、驱动 create/pay 出金。

## 栈指纹
- RuoYi v3.8.7
- 商户后台 `merchant.<domain>`；开放网关 `create.<随机串>.xyz`
- 开放 API 信封：`AccessKey`/`Timestamp`/`Sign` → `{Code,Message,Data}`
- 签名：非空参 ASCII 排序 + `&SecretKey=` + MD5 **小写**
- 金额单位**元**；代付产品码 **600**（银行卡代付）
- 端点：`POST /prod-api/v3/create/pay`（下单）、`/prod-api/v3/notify/mchOrder`（查单）、`/prod-api/v3/notify/mchBalance`（查余）
- **禁套错**：青蛙 `/rest/withdraw`、LWPAY PATHINFO、芋道 Mock Token（同族代付盘 API 各异，指纹不对别硬套）

## 同族代付盘指纹分流（线索 · 待补全）
「威尔斯族」代付盘多变体，共用「商户后台 + 开放网关 + 代付 API」骨架，但端点/签名各异。以下仅从审计报告「禁止套错」提炼的**线索**，无完整端点数据，遇站先实测再回填：
- **青蛙**：代付端点走 `/rest/withdraw`（非 `/prod-api/v3/create/pay`）
- **LWPAY**：PATHINFO 路由（`/index.php/...` 类，非 RuoYi）
- **芋道（yudao）**：登录态 Mock Token（非 RuoYi AccessKey/Sign 信封）
- **CKPLR 尊界BBCC / CRMEB-Java 通道族**：Vben Admin + Sa-Token JWT-mixin，验签字段是 **`sing`**（拼错），`&key=` 后缀 + 大写；下游 20 台 CRMEB-Java（ch=277~312）通用一把密钥
- **天成 SCUI / 天鸿 fykknn / YHPay 银河**：Go+Laravel / Spring Boot 变体，签名各异（假签绕过 · `&key=` 大写 · `md5(nonce+curTime+appSecret)`）
⇒ **这批族的签名算法、端点、陷阱与破法四步详见 `references/daifu-signature-and-platform-families.md`**（同族分流先读它，再决定套哪套签名）

打同族站先做三步分流：
1. 认框架：RuoYi（`/prod-api` + Swagger `/swagger-ui/index.html` + Druid `/druid/login.html`）还是自定义 PHP（PATHINFO）还是芋道（`/admin-api`）
2. 认信封：`AccessKey`/`Sign`/MD5 小写 = 本盘 lwsdeployv；否则别套本盘签名算法
3. 端点各自确认后再打——别把 A 盘的 `create/pay` 硬套到 B 盘的 `/rest/withdraw`

## 攻击面（按价值排序）

### H4 严重 — common 票全站拖钥（最高价值）
低权/示例票（角色 `common`）dataScope 未限制：
`GET /prod-api/lws/merchant/list?pageSize=1000`
一次拉全站商户，每条含 `merchantNumber`（=开放 API AccessKey）+ `accessKey`（=SecretKey）+ `balance`。
→ 正余额户拖钥后可**真签**查余、驱动 create/pay。

### H5 严重 — 上游代付凭证泄漏
`GET /prod-api/lws/channel/list` 明文返回通道配置：
`threeMchNumber` / `threeMchKey` / `threeMchCode` / `threeSubmitAddress`
→ 泄漏上游代付/代收商户钥，可跨平台查余（仅 balance，勿对上游下单）。

### H1 高危 — 查单 Sign 非空即过
`/notify/mchOrder`：只要 `AccessKey` + 非空 `Sign` 就进查单逻辑，**不验商户真实性、不验签**。空签才报「Sign签名不可为空」；假商户+`Sign=x` 与真户假签均回「订单不存在」（而非「签名错误」）。

### H2 高危 — 查余商户存活预言机
`/notify/mchBalance`：假签下「签名不合法」= 商户存活，「商户不存在」= 空号。可**无密钥**普查商户号。

### H3 高危 — CORS 反射 + credentials
`merchant`/`create` 上 login、mchBalance 等 OPTIONS：`ACAO` 反射任意 Origin（含 evil.example）且 `ACAC=true`，允许头含 `authorization, admin-token`。

### H6 高危 — 初始密码配置泄露
`GET /prod-api/system/config/configKey/sys.user.initPassword` → `123456`

## IP 白名单门语义（关键，别套错）
`create/pay` 两种拒单文案含义相反：
- `[M…]未配置下单ip白名单!` = **拒单**：该商户尚未配置 API 下单 IP（**不是**「任意出口可下」）
- `[IP]非白名单,防火墙策略阻止访问!` = 已配白名单，但当前出口不在名单

## 出金链双卡教训
真实代付出金需过两道卡，缺一不可：
1. 商户已配置 API 下单 IP 白名单
2. 当前出口在该白名单内（或能写白名单 `/lws/white/add`）
「拖钥 + 跨平台凭据前提」成立 ≠「完成真实出金守恒」。本例 common 票 `white/add` 报「请求非法,权限不足」且商户未配白名单 → 真签下单被拒、余额 Δ=0，未完成真实出金。复测窗口：可写白或出口已入白时，小额 600 真单 + 查单/余额守恒。

## 修复要点（代付平台共性）
- 商户角色强制本户 `dataScope`；`merchant/list` 禁全站、禁返回 `accessKey`；已泄密钥全量轮换
- `channel/list` 脱敏 `threeMchKey` + 轮换上游钥 + 收紧来源 IP
- 查单先验商户 → 按钥验签 → 按 AccessKey 归属查单；查余先验签或统一错误文案
- CORS Origin 白名单，禁反射 + credentials 同开
- `initPassword` 配置键按角色鉴权 + 强制改密
