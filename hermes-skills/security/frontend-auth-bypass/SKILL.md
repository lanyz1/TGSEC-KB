---
name: frontend-auth-bypass
description: >-
  前端认证破解：Altcha PoW、RSA 加密登录、公钥在 JS。
  触发：Altcha、PoW captcha、RSA 登录、JSEncrypt、前端认证。
  图形验证码走 captcha-ocr；极验走 geetest；H5 VIP 旗标走 client-state-skip。
---

# 前端认证（测绘引擎）

目标须在 scope。授权内默认打到 **L2**：算出 Altcha number，或抽出 RSA 并能加密登录体。  
先问只剩：改原超管密。

| 档 | 成立 | 不算 |
|----|------|------|
| L1 | 页面/JS 里有 challenge 或公钥 PEM | 只看到登录框 |
| L2 | `altcha` 撞出 number，或 `rsa` 出密文 | 没提交仍报绕过 |
| L3 | 授权站吃下密文/PoW 返回票 | 图验证码没走 OCR 卡 |

## 立刻跑

```bash
python3 tools/ops/frontend_auth_probe.py drive --base https://授权站 --case <案>
python3 tools/ops/frontend_auth_probe.py altcha --challenge <hex> --salt <s> --max 200000
python3 tools/ops/frontend_auth_probe.py rsa --n <modulus_hex> --e 10001 --text 'password'
```

`drive` 拉首页和 `/altcha` `/api/publicKey` 等路径，正则抽 JSON challenge、PEM、modulus。  
`solve_altcha`：`SHA256(salt + n) == challenge`，n 从 0 扫到 maxnumber。  
`rsa`：PKCS#1 v1.5 填充后 `pow(m, e, n)`。

产物：`测绘/frontend_auth/surface.json`。

图验证码并行：

```bash
python3 tools/captcha-ocr/ocr_solve.py --path captcha.png
```

## 六步

```text
① drive 认 Altcha / JSEncrypt / 公钥
② 有 challenge+salt → altcha
③ 有 n/e → rsa 加密登录口令
④ 登录 POST 用密文，不要改成明文撞
⑤ 滑块/极验交接专卡，不要在本卡硬猜
⑥ 票到手填对象矩阵「自己×读」
```

## 交接

| 认到 | 走 |
|------|----|
| 字母图验证码 | `captcha-ocr` |
| 极验 / 滑块 | `geetest-captcha-bypass` · `captcha_auto.py` |
| 前端 isPaid / VIP 旗标 | `client-state-skip` |
| 加密 API 整包 | `encrypted-api-spa` |

## 真源

- 手法：`docs/playbooks/测绘引擎专项探针作业手法.md`
- 探针：`tools/ops/frontend_auth_probe.py`

---

<!-- 以下内容合并自兄弟技能库 (2026-09-12) -->

---
name: frontend-auth-bypass
description: "破解前端认证: Altcha PoW+验证码+RSA加密登录。触发: Altcha, 验证码, 登录逆向。"
---

# 前端认证绕过(Frontend Auth Bypass)

针对"登录被前端加密/人机验证保护"的 Web 目标。核心: 前端 JS 逆向 → 提取密钥/验证算法 → 构造合法请求。

## 1. Altcha PoW 人机验证破解

### 识别
`GET /xxx/altcha/challenge` 返回:
```json
{"parameters":{"algorithm":"PBKDF2/SHA-256","nonce":"...","salt":"...","cost":1500,"keyLength":32,"keyPrefix":"..."},"signature":"..."}
```
前端 bundle 里有 `altcha-widget` 组件(`globalThis.$altcha`、`deriveKey`、`solveChallenge`)。

### 关键认知(别踩坑)
- **solution 的 signature 不是自己算的,是原样回显服务端 signature**(Ht 函数: `signature: f.signature`)
- **PoW 模式 = 暴力 counter 直到 derivedKey 前缀匹配 keyPrefix**: `SHA256迭代 cost 次(salt || nonce+uint32be(counter))`,前缀匹配 16 字节 = 2^128 **纯 Python 不可能**
- **正确解法: 用浏览器前端 worker 自动求解**(前端有完整 worker 并发暴力逻辑)

### 浏览器自动求解步骤(已实测)
1. CDP 打开登录页,等页面加载完
2. 找到 checkbox: `document.querySelector('altcha-widget input[type=checkbox]')`
3. **必须用真实鼠标事件点击**(JS `setter+dispatchEvent` 不触发 Vue 监听):
   ```python
   await ws.send({"method": "Input.dispatchMouseEvent", "params": {"type": "mousePressed", "x": cx, "y": cy, "button": "left", "clickCount": 1}})
   ```
4. 等待 60-90 秒(前端创建 blob worker 并发暴力 PoW,期间会看到 `blob:https://...` 请求)
5. 轮询 `input[name=altcha]` 的值,非空即成功
6. solution 是 base64(JSON): `{algorithm, challenge: keyPrefix, number: counter, salt: nonce, signature}`

### 纯 API 调用登录
```python
data = {"username": u, "password": rsa_encrypted, "altcha": solution}
```

## 2. AJ-Captcha 滑块验证破解(FastAdmin/EasyAdmin 登录)

识别: 登录页引入 `verify.js` + `aj-captcha/js/aes.js`(crypto-js),页面文案 "向右滑动完成验证"。

### 接口(已实测)
```
POST /adminlogin/index/getCaptcha    body: captchaType=blockPuzzle|clickWord
  → {"repData": {"originalImageBase64": 背景图, "jigsawImageBase64": 滑块图,
     "secretKey": AES密钥, "token": UUID}}
POST /adminlogin/index/checkCaptcha  body: captchaType + pointJson + token + clientUid + ts
```
缺 `captchaType` 参数时返回 `"captchaType参数不正确！"`(直接 POST 拿不到码)。

### 破解三步(全部实测通过)
1. **缺口识别**: 背景图(如 310x155)与滑块图(46x46,含透明区)→ 用 numpy 模板匹配
   - 先取滑块图 alpha>100 的有效区域,再去掉阴影(alpha>200 核心区)
   - 全图滑动(步进1)算 `np.abs(roi - jigsaw)[mask].mean()` 最小 score → x
   - **要精确**: 只算滑块核心区像素,候选 top3 逐个试
2. **AES 加密 pointJson**(关键坑): 前端 aes.js = **CryptoJS AES + mode:ECB + Pkcs7**
   ```js
   CryptoJS.AES.encrypt(srcs, key, {mode:CryptoJS.mode.ECB, padding: CryptoJS.pad.Pkcs7})
   ```
   Python: `AES.new(key.encode(), AES.MODE_ECB).encrypt(pad(json.dumps({"x":x,"y":5.0}).encode(), 16))` → base64
   - **用 CBC 会报 "请检查密钥是否正确！";改 ECB 后报 "验证失败！" = 加密对了只是 x 偏**
3. **checkCaptcha 提交**: `captchaType=blockPuzzle&pointJson=<urlencode(aes)> &token=<token>&clientUid=test&ts=<ms>` → `repCode=0000` 即通过

### 完整登录链(FastAdmin)
- 登录 = **滑块 + 图形验证码双验证**(滑块通过后仍需 `code` 字段)
- 图形验证码接口: `GET /adminlogin/captcha` 或 `GET /captcha/get`(PNG)
- **ddddocr 对字母数字混合识别率 ~10% 不可靠**;错误消息会泄露类型(`"验证码必须是数字"` = 纯数字可爆,否则字母混合换方案)
- **登录失败锁定**: 语言包 `"please try again after 1 day"` = 失败锁定 1 天,爆破前先测是否已锁(提交一次看返回)

### FastAdmin 识别(FastAdmin ≠ EasyAdmin)
- URL `?ref=addtabs` / 控制器 `/adminlogin/` 是 **FastAdmin**(非 EasyAdmin)
- 登录页 config JSON: `"fastadmin": {"version":"3.0.4", "api_url":"https://api.iuok.cn"}`
- FastAdmin 特征: `/adminlogin/ajax/lang?callback=define&controllername=index&lang=zh-cn` 泄露全部 UI 文案(功能面/错误语义)
- 上传配置泄露: config 里 `upload.cdnurl`(OSS 域名)+ `storage/driver`(aliyun/local)

## 3. 前端 RSA 加密登录逆向

登录接口 500/验证失败但参数正确时,查前端是否加密密码:
- 搜索 JS: `-----BEGIN PUBLIC KEY-----` / `setPublicKey` / `encrypt(`
- 提取 PEM 公钥 → pycryptodome `PKCS1_v1_5` 加密:
```python
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
ct = PKCS1_v1_5.new(RSA.import_key(PEM)).encrypt(pwd.encode())
enc = base64.b64encode(ct).decode()
```
- 注意: 加密后 base64,可能再 URL encode

## 3. 分享链接 token 泄露(公开分享页)

分享/邀请链接(免登录)可能直接泄露数据:
- CDP 打开分享链接 → 前端自动完成验证 → **localStorage 里自动存了 token**
- 提取: `JSON.parse(localStorage.getItem('share_sessions_v1')).tokens['<shareId>']`
- 用 token 调 `Authorization: Bearer <token>` 访问业务 API
- 分享详情接口可能泄露: 邀请码/账号列表/粉丝统计/代理邮箱

## 4. 用户枚举 + Go 后端识别

- 注册/发码接口错误信息差异 = 枚举 oracle: `"用户名已被占用"` vs `"邮箱格式不正确"` vs `"验证码已过期"`
- **Go 后端识别**: 500 响应含 `errors.SyntaxError{Pos:0, Src:"", Code:0x1}` = Go
- 错误信息泄露: 空 JSON body 报 `"Syntax error no sources available, the input json is empty"` = Go RPC 风格

## 5. S3 私有桶枚举

私有桶列表全 403 属正常,测试顺序:
- 根列表 `GET /` → 403 = 私有
- `?policy` `?acl` `?versioning` `?uploads` `?cors` `?website` → 全 403 = 配置安全
- **已知对象可读**(从 initChannelInfo/配置接口泄露的 URL 验证)
- 其他租户对象路径猜测(时间戳格式 `/YYYY-MM-DD HH:MM:SS/filename-epoch.ext`)→ 大多 403
- 搜索引擎搜 `"bucket.s3.region.amazonaws.com"` 引用 → 常被反爬拦截,低效

## 6. Cloudflare 429 限流绕过

- CF Error 1015 "You are being rate limited" = IP 被限
- 用住宅代理池(SOCKS5)轮换出口 IP
- 格式 `exit_ip|host|port|user|pwd`,Python `pysocks` 设置代理
- 请求间隔 3-4 秒 + 每请求换代理

## 相关
- Geetest 绕过: 见 wps-casino-platform-pentest(任意值可过历史验证)
- 分享页实测案例: references/dujiaoshou-share-leak.md
