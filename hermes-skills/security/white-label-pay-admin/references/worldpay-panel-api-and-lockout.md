# WorldPay/GBKPay 白标收银面板 — 免鉴权接口与锁定纪律

CF 罩住的收银/后台,**业务 API 全部可穿 CF 使用**。源站 IP 不是打业务的前置条件;一天全押源站 IP 往往是低产出路线。

## 免鉴权接口(直接穿 CF,实测活)

- `GET /api/getSetting` → `{"Country","PlatformName","PayPageVersion","TimeZone",...}`;`PlatformName` 即产品名(`GBKPay`/`StarPay`/`9MPay`/`TAKAPay`)。取也用作指纹。
- `GET /api/getTwoFactorAuthEnabled?userName=<u>` → `{"TwoFactorAuthEnabled":bool,"UserTypeId":N}`。
  **这就是免鉴权用户枚举原语**;`UserTypeId`:2=Shop、3=ShopAgent、4=Admin。
- `GET /api/getOrder?trackingNumber=<n>` → `NoOrder`(接口活、单号不存在)/ 订单 JSON。无鉴权。
- `POST /api/login` body `{userName,password,TwoFactorAuthCode}` — 响应标记:
  - `["NoUser"]` — 无此用户
  - `["PasswordError"]` — **用户存在 + 密码错**(枚举确认器)
  - `["PleaseLogin"]` — 需登录
  - `["TryAgainLater"]` 或 CF 429 — 限速,退避
  - `["AccessFailedCountLimit"]` — 按账号锁
- `POST /api/createOrder` 需字段齐:ShopUserLongId / ShopOrderId / Amount / ShopInformUrl / PayerKey / PaymentChannelId / CurrencyId。
- 设备/OTP 类(`registerRocketDevice`、`verifyBKashOTP`/`verifyNagadOTP`/`verifyRocketOTP`/`verifyGCashOTP`)实测**全部要求登录**,不是未授权面,别再浪费轮次。

## 锁定与限速纪律(踩过血坑)

- `AccessFailedCountLimit` 是**按账号**的,锁定时长远超一小时。
- **绝不轮询"解锁"接口**:每一次失败/探测都会把计数器重置并**续锁**。实测:某号刚解锁,一发多余尝试立刻重新锁死 → 又赔一小时。
- 撞密预算 = 每个号没命中就**当烧掉**,只用你真正信的高概率默认口令;别拉大字典。
- 优先打**从未喷过**的活号;维护活号台账(用户名 / UserTypeId / 2FA 开还是关 / 是否已锁)。
- 多租户子域(`gbk`/`su77`/`taka`/`9m9mm`/…)共用同一 API;账号很可能是全局同一 DB → **默认锁也是全局的**。

## 字段校验顺序 = 假阴性陷阱

`createOrder` / LongId 探测时,服务端**先校验 `PaymentChannelId`/`CurrencyId`,后校验 `ShopUserLongId`**。字段给不全 → 直接回 `NoPaymentChannelId`/`NoCurrencyId`,用户校验根本没跑。
→ 不带全字段的 LongId 爆破会得到**假阴性**;某字段缺失时的"全 NoUser"不能证明 ID 不存在。

## 兄弟品牌指向性

- CF 全域品牌子域:`711TK/889Pay/AxisPay/BMXPay/HRPay/SwiftPay/LZPay/IMPay/BePay/GTAPay/QXPay/lifebd/spbd` 等,同套代码。
- `*.lucky1pay.com` 这类兄弟域可能**泛解析到同一 Aliyun ALB**(芋道兄弟后台),可用 `--resolve` 把目标品牌域指过去对照。
- 同 IP 常以 Host/路径分流:worldpaypp 收银 `getSetting` 与芋道 `/admin-api` 可以共存。
