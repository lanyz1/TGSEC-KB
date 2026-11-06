# 传输层与解码（App API 收割）

## 1. 双层 base64 信封（最常见的「静默 0 命中」源头）

典型：`{"code":200,"data":"<双层 base64>"}` —— **登录失败也在信封里是 200**。

正确的解码链：**JSON → 解一层 → 砍掉前 N 个字符 → 再解一层 → JSON**。

- **每层要丢弃的前缀长度会变**（实测出现过 12 和 13），所以解码器必须**扫描 k = 0..25**，取解出来含 `{…}` 且最长的那个。写死 `substring(12)` 或 `range(0,10)` 会在某天全线失效且不报错。
- **补位按该段自身长度算**：`seg + "=" * ((4 - len(seg) % 4) % 4)`。写死 `"==="` 会在某些段上抛 `binascii.Error: Incorrect padding` 把线程弄死。
- **登录成败看内层**：内层 `{"code":401,"reason":"LOGIN_PASSWORD_ERROR"}` 才是判据；JWT 也在内层。只看外层 `code:200` 会把加密串当 token 写进文件。
- 有的端点 `data` 有时是**未解码字符串**，要 `if isinstance(data, str): data = json.loads(decjson(data))`，否则 `string indices must be integers`。

## 2. 请求加密（AES 帧）

- 帧 = `base64(IV(16B) || 密文)`，AES-128-CBC + Pkcs7。**记得 PKCS7 padding**，否则第一次调用就崩。
- 口令字段常是 `#PWD_BROWSER:<ts_ms>:<base64>` 这种带模式的串。
- key 硬编码在 H5 bundle 里，**按品牌不同** —— 换品牌域时确认用的是哪个 key。

## 3. 验证码字段名（各平台不同，必须实测）

- 图片字段可能是 `captcha_img`（配 `captcha_id`）而不是 `image` / `img` / `base64`。名字猜错时的表现是**「接口通了但解析不出来」**，很容易误判成接口挂了。
- 图片常是 **data URL**（`data:image/png;base64,…`）⇒ 必须 `split(",")[-1]` 再 `re.sub(r"\s+", "", b64)` 再补 `=`，否则 OCR 永远报 `cannot identify image file` 而代码不报错。
- 验证码**单次有效**，一次提交一个；失败整对重取。
- 识别优先 `ddddocr`（`DdddOcr(show_ad=False).classification(bytes)`），小尺寸数字图比 tesseract 稳。

## 4. 用真浏览器拿「登录报文真名」（WAF 挡住 curl 时）

SPA 登录页有 JS 挑战、curl 拿不到时：

1. 真浏览器打开登录页（挑战会自动过）。
2. 注入 fetch/XHR 钩子：包装 `window.fetch` 与 `XMLHttpRequest.prototype.open/send`，把**请求体**和**响应文本**推进一个全局数组。
3. 触发一次提交：`form.requestSubmit()` 或对输入框发真的 `keydown/keyup` Enter 事件（React 受控输入要先 `focus()`）。
4. 读回数组 —— 一次就拿到**完整请求体字段名**（实测是 `{username,password,captcha,captcha_id}`，而猜的 `uuid` / `captchaId` 全错）以及服务端**真实响应**。

**读响应体判拦截位置**：响应是防火墙页（`<title>网站防火墙</title>`）= 拦截发生在边缘、按 IP 规则 ⇒ 改参数无用，**只有换干净出口才有意义**。这条能把「我一直在调参」直接变成「我该换通道」。

> 注意范围：这个手法解决的是**报文形状未知**，不解决**IP 被边缘规则封**。别把「拿到字段名」当成「能登进去」。

## 5. 自检流程（任何一次批量扫描 0 命中时按顺序走）

1. 单号手工跑 `captcha → OCR → login`，**逐层打印中间串**，看到 `{"base64":…}` / `{"code":…}` 才说明解码器对。
2. 拿一个**已知口令对**复登，返回 `code:200` + 新 JWT 才算链路通。
3. 再上批量；并发一拉高就全线报错 ⇒ 降到 10~12 线程 + GAP。
4. **改了脚本必须重启进程**，否则跑的是旧代码。
5. 计数前先清洗 token 文件（按「手机号 + 下一行是 JWT」配对去重），否则报给用户的数会被打回。
