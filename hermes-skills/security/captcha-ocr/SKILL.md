---
name: captcha-ocr
description: >-
 授权目标上的图形验证码 OCR（ddddocr）与旁路分流。用户提到验证码、captcha、
 ddddocr、登录码、OCR 过验证码时使用。滑块/点选/GeeTest 走 captcha_auto.py，
 不要本 Skill。GVA 领奖验证码墙可先 OCR 再接 ginvue 探针。
tags: [验证码, 图形验证码, 登录验证码, 验证码识别, ddddocr, 打码, ocr, 验证码挡着]

---

# 图形验证码 OCR（Cursor Skill）

> 旧名 `captcha-ocr-bypass` 已重定向到本卡，勿再展开旧正文。

## 何时用

- 简单数字/字母图被挡在登录或发奖接口前
- 用户明确要自动化过 captcha（非短信接码）

## 真源（按序）

1. `tools/captcha-ocr/ocr_solve.py`
2. `docs/playbooks/图形验证码OCR与旁路.md`
3. 旁路优先：Redis `captcha_codes`（若依）、业务禁用验证码、人工 `--confirm`
4. 滑块/极验 → `python3 tools/ops/captcha_auto.py solve --url … --case …`
5. CF/Turnstile → `scrapling` / `cf_session`，**不是** ddddocr
6. **云打码（双 provider 自动路由）**：`python3 tools/ops/captcha_router.py solve <type> <url> <sitekey>`
   - **NextCaptcha**（主力，余额 $326）：`python3 tools/ops/nextcaptcha_solver.py <type> <url> <sitekey>`
     - 内置 API Key，无需环境变量
     - 支持：text / recaptcha / recaptcha_v3 / hcaptcha / turnstile / recaptcha_mobile
   - **CapMonster**（备用）：`python3 tools/ops/capmonster_solver.py <type> <url> <sitekey>`
     - 需 `CAPMONSTER_API_KEY` 环境变量
     - 支持：text / recaptcha / recaptcha_v3 / hcaptcha / funcaptcha / turnstile / slide（本地 ddddocr）
   - **统一路由器**自动选最佳 provider：本地能解→ddddocr；云→NextCaptcha 优先→CapMonster 备用

## 强制步骤

1. 确认 host 在 `config/scope*.json`。
2. 未装依赖：`bash tools/captcha-ocr/install.sh`
3. `python3 tools/captcha-ocr/ocr_solve.py doctor`
4. 识别：
 - 本地图：`ocr_solve.py file --path <图> --case <案卷>`
 - 授权 URL：`ocr_solve.py url --url <验证码URL> --case <案卷>`
5. 证据：`exports/bot-recovery/<案卷>/测绘/captcha_ocr/`
6. 识别失败 → 试 `--beta`；仍失败 → 人工码或旁路，勿死磕

## 不要做

- 对未授权域拉验证码图
- 把滑块/行为验证当成 OCR 题硬解
- 默认自动化刷生产登录（高噪声先问）

---

<!-- 补充视角: captcha-registration-bypass (兄弟技能库 2026-09-12) -->

---
name: captcha-registration-bypass
description: "验证码/注册关突破工具箱。触发: 验证码, 注册, 滑块, 收信, 注册关, 邮箱验证码, 短信验证码。"
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
- **字母数字混合识别率 ~10% 不可靠**;纯数字 >90%
- 先提交一次错误码,看错误消息是否泄露类型("必须是数字"/"格式不正确")
- 验证码 URL 常见: `/captcha` `/captcha/get` `/code` `/verifycode`

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

## go-captcha 族补记（2026-10 吸收）
- slide（滑块）：边缘检测 + 坐标定位 → 接近全解
- click（点选）：协议逆向完成度约 80%
- token 有生命周期/复用约束 → **按序换取，勿并发预取**

---

## 外部库增量（2026-10-11 分享包）

## 7.5 带验证码的爆破工具链（captcha-killer / Intruder / wfuzz）

```text
场景: 登录接口每次请求都要带验证码 → 传统字典爆破失效，需要"每请求新码 + 自动识别"。

Burp 路线（captcha-killer-modified 插件，图形化作业首选）:
  ① 抓验证码图请求 → 右键 Send to captcha panel
  ② 插件面板配"识别接口": 本地起一个 HTTP 识别服务（把 ocr_solve.py 包一层），
     插件 POST 图片过去、把返回文本写回 Intruder 的 payload 位
  ③ Intruder: 位置 = 用户名 + 密码 + code(插件结果)；线程=1 + 延迟；注意失败锁定

命令行路线:
  wfuzz -z file,users.txt -z file,pass.txt -z file,<(码序列) ...   # 码需外部脚本实时生成
  hydra -l admin -P pass.txt https-post-form "/login:user=^USER^&pass=^PASS^&code=^CODE^:F=错误"

自写循环（最可控，优先）:
  img = GET /captcha（同一 session cookie）→ code = ocr(img) → POST /login(pwd, code)
  ★ 验证码与 cookie/session 强绑定：必须同一会话取图+提交，禁止并发复用同一张图
```

纪律：**先测锁定策略**（失败 N 次锁多久）与"是否只查格式"；锁定一开爆破即废且可能锁死合法账号。
线程=1 + 延迟，批量/大字典动作先报备；识别率不足走人工读码兜底（§2.5）；命中即停。

## 2.5 一次性验证码: 先量命中率 + 重试纪律(GVA 领奖实测 30–40%)

§2 的「纯数字 >90%」只适用于噪点少的图。实测同一 ddddocr 在 **5 位数字 + 干扰线**的领奖码上只有 **30–40%**
(放大/裁剪/对比度增强全上仍不稳) ⇒ **命中率必须先量再写结论**,别把「纯数字」当高识别率代名词。

一次性机制的两个致命误判(会让人得出「爆不了」的错误结论):
1. **同 captchaId 第二次提交与「码识别错」返回同一文案** ⇒ 拿一个 id 硬刷/并发必然全灭,
   而且把有效尝试浪费在废 id 上(「5 线程全被拦」不是并发被防,是 id 已被首请求消耗)。
2. **不分类响应就重试** ⇒ 把门禁层之外的业务结论(已领取/条件不满足)当成验证码错,无限空转。

纪律:
- **重试只允许发生在门禁层错误**(验证码错误/失效);其余类别立即停机落证据。
  期望尝试次数 ≈ 1/命中率(30% → 约 3 次),据此设 `--max-attempts` 与限速。
- **一图一码**: 每次尝试必须新取图;要提吞吐就**一次取多张各自配对**,不要并发撞同一 id。
- **人工读码兜底**(命中率不足时的正解,不是死磕 OCR): 验证码图落盘 + 记 captchaId → 人工读 →
  用**同一次取图**的 id:code 立即提交(错配 = 白刷)。
  现成路径: `ginvue_admin_probe.py captcha-dump` →(图给用户读,或 `ocr_solve.py file --path <png>`)→ `claim-loop --captcha-id <id> --code <码> --confirm`。
- **OCR 之前先测校验强度**: 固定码 `00000` 能进业务层 = 只查格式(直接跳过 OCR);空码能进业务层 = 空值绕过;
  但空值被「必填」拒 ≠ 绕过(假阳性防线,见 `api-param-name-discovery` 核心技术 3)。
