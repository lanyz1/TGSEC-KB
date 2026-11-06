# sdfaka 发卡系统渗透(ttkx.ssy25.cn 实战,2026-08)

## 指纹
- Cookie: `sdfaka_pro_session`(Laravel 加密 cookie)+ `XSRF-TOKEN`
- 首页 Vue3 SPA 内 `window.APP_CONFIG = {token: '<32位hex>', url: ''}` — **token 硬编码全站复用,免登录调 /ajax/* 接口**(token 就是请求令牌)
- 会员中心独立页 `/member/login`(layuiadmin + crypto-js + slider_captcha.obf.js)
- CDN: xqdcdn.cn;源站 Apache(404 页泄露主机名前缀 izj6cd*,阿里云 ECS)

## API 模式(核心)
- `POST /ajax/{action}`,body JSON `{"_token": APP_CONFIG.token, ...}`
- **响应 = base64(JSON)** → 必须先 base64 解码再读!
- 无 CSRF 要求(前端不带头),游客可调
- 路由探测:404=不存在,**419=Laravel CSRF(路由存在需 token)**,200=可访问;`GET /ajax/*` 全部 200(空 data,需要 POST+参数)

## 关键端点
| 端点 | 参数 | 说明 |
|---|---|---|
| /ajax/index | _token | 全站商品(cat + goodList) |
| /ajax/buy | gid | 商品详情(field/set/activity,游客优惠券设置) |
| /ajax/submitOrder | orderInfo{payType,count,email,goodid,discount,field} | **免登录免验证码下单**;email=11位手机号(TouristVoucher);返回 orderId(SUB+30位hex),type=2 时跳 /pay?order_id= |
| /ajax/orderInfo | order_id | **游客查任意订单详情**(password=卡密字段,未支付脱敏;邮箱/金额/状态泄露) |
| /ajax/discount | quanma,gid | 优惠券查询 |
| /ajax/notify | - | 空壳(非支付回调) |
| /member/register | username,password,滑块 | 注册需滑块验证码 |
| /member/account/sendCode | JSON{phone,slider_verification_code} + X-CSRF-TOKEN header | **短信验证码正确接口**(勿用 /member/api/sms/sendCode — 那是错接口,返回"请输入正确的手机号码"误导);成功 {"code":1,"msg":"短信发送成功"},**响应不含验证码** |
| /member/account/bindPhone | _token,phone,slider_verification_code,code | 绑定手机;**限流 1分钟3次**(空 code 也计数,报"1分钟内最多请求3次");错误码"短信验证码错误" |

## 滑块验证码完全绕过(关键)
- 前端 `slider_secure_simple.js`:**加密密钥硬编码** `"SliderCaptcha2024SecretKey!!"`
- 加密算法:AES-CBC(key=SHA256(secret)),随机 16B IV 前置,base64 → `{data: b64(iv+ct)}` POST `/slider/verify`
- **generate(/slider/generate)与 verify 必须共享 cookie**(token 绑定 session;urllib CookieJar 或 curl -c/-b)
- **trail 元素必须为数组 `[x,y,t]`**(非对象 {x,y,t})— 服务端按 `$point[2]` 访问
- **x 校验存在但容差 ±15px**:固定 x=150 盲试单轮 ~40% 通过(不是"不校验");错误响应 `差距: Npx` 可校准但跨 token 无效(每次 generate 缺口随机)。15 轮内成功率 ≈99.9% —— 别死磕图像分析(边缘对/亮度窗口实测全偏)。
- 成功返回 `{code:0, msg:"验证成功", verification_code:"<32hex>"}` → 该 code 用于注册/登录接口
- 调试神器:**PHP 错误消息泄露内部结构** — "Undefined array key 2"→ trail 元素格式错;"滑动轨迹异常"→ 密钥正确已过解密层,只差轨迹;"数据格式错误"→ 顶层结构错

## 注册/登录自动化(滑块已破 → 会员链路)
1. generate → 伪造 verify → verification_code(见上节;注册表单字段名 `verification_code`,页面隐藏域 `slider_verification_code`)
2. `POST /member/register {username,password,confirmPassword,qq,verification_code}` → code:0 注册成功
3. `POST /member/login/submit {username,password,verification_code}` → code:0 登录成功(session cookie 落地)

## 会员中心攻击面(登录后)
- `/member/cashier/addFunds` — 充值(**需先绑手机**,否则报"请先绑定手机才能进行充值";绑手机短信验证码也走滑块 → 已可绕过)
- `/member/cashier/withdraw` — 提现(资金链末端)
- `/member/cashier/record` — 资金流水
- `/member/sub/*`(classify/goodSetting/orderList/overview/stationSettings)— **会员可开独立发卡子站**,自带收款/回调面
- `/member/order/list`、`/member/account/bindPhone|password|uplevel|userPin`
- 充值页有**充值卡**(`/member/cashier/recharge_card`,卡号 card_m + 卡密 card_p):若充值卡号可枚举/可预测 = 直接白嫖余额。实测:带 _token + X-CSRF-TOKEN header + Referer 仍恒 500(服务端 bug/功能禁用,参数名穷举 card_no/card_pwd 也 500)— 别死磕
- 在线充值表单 POST `/member/cashier/addFunds {_token,userId,money,type}`(Laravel _token 页面生成,500 报错页=CSRF 不匹配)
- 会员订单数据:`GET /member/order/data?page=1&limit=10`(layui table 源,JSON{count,data});**游客订单不关联会员账号**(游客下单的卡密只能在 /ajax/orderInfo 按 order_id 查)
- 提现 `/member/cashier/withdraw`:GET 500、POST 419(需 X-CSRF-TOKEN header),功能被绑手机前置
- 支付平台 301.pay.xqd.cn:API 返回 `{"code":-4,"msg":"No Route"}`(有 JSON 框架可枚举路由);/payment/check_status 带 Referer 仍 404

## 绑手机卡点(充值/提现/子站统一前置)
- 链路:滑块绕过 → `sendCode`(正确接口见上表)→ 短信码 → `bindPhone`
- 短信码**不返回响应**、不可预测、bindPhone 限流 1分钟3次 → 爆破不可行(6位=数月)
- 唯一可行:真人收码(用户自己手机)或用真实号段;虚拟号/测试号(<PHONE-REDACTED>/<PHONE-REDACTED>)被服务端额外校验拒绝("请输入正确的手机号码")
- 未绑手机时:充值页/子站页均显示"请先绑定手机才能进行充值/使用分销功能"(统一拦截,4288B 提示页)

## 防御面(已验证)
- SQL 注入:order_id 参数化,安全
- 价格篡改:count 负数/0 被拒、999999 报库存不足、price 字段覆盖无效(金额服务端计算)
- 支付:第三方聚合支付(301.pay.xqd.cn,支付宝扫码),其 /payment/check_status 需 Referer

## 工具链注意(PYTHONPATH 污染修复)
- urllib 直连 CDN TLS 握手超时 → 改用 curl subprocess(`-sk -c cookies.txt -b cookies.txt`)
- 本机 PYTHONPATH 指向 hermes venv 导致 python3/uv 用到坏 PIL → `env -u PYTHONPATH uv run --with pillow --with numpy python3`
