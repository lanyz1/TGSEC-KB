# hCaptcha Workflow（无感验证 · 补环境）

hCaptcha 隐私优先人机验证。无感验证通过则零交互；未通过弹图片题（点击/拖拽）。核心加密在 `hsw.js`（wasm）。目标示例：steam 注册页。

## 识别信号

- `checksiteconfig` 接口返回 JWT（解码含 sitekey 等）；`hsw.js` 核心加密文件；`hcaptcha.html` 地址 v1 后跟版本号（约每周更新）
- 验证接口请求体/响应体均为乱码（ArrayBuffer/buffer 格式）
- 通过判定：响应 `generated_pass_UUID` 值以 `P1` 开头

## 加密入口定位（hsw.js）

- 参数：`v`=版本、`sitekey`、`host`、`hl`、`pdc/pem`(时间)、`c`(checksiteconfig 参数)、`motionData`(时间戳+轨迹)、`n`=hsw.js 核心加密结果
- `n = r.solved`，`r = e.proof`，异步链：JWT 解码 → wasm 加载（`aG` 方法）→ 加密
- 逆向法：全局 xhr 断点 → 跟 Promise 链 → `xr` 方法 → `n(i.req, o)` 进 hsw.js → 解码 JWT → 加载 wasm

## 补环境检测点（关键）

1. **RTCPeerConnection**（WebRTC 点对点）
2. **RTCRtpSender / RTCRtpReceiver**
3. **OfflineAudioContext**（音频数据处理）
4. **WebGL2RenderingContext**（参数多，从浏览器直接 copy）
5. **描述符检测**：用箭头函数创建（无 prototype 属性），如 `"prototype" in AudioBuffer.prototype.getChannelData`
6. **Math 精度差异**（引擎底层数学库不同）
7. **字体指纹**（从浏览器导出方法）
8. **canvas 指纹**
9. **Worker / SharedWorker**

## 插桩分析点

- wasm 与 JS 交互存取的参数：`kc.Ob` → `fm`（wasm 方法）→ `Mv` → 大数组（补环境对照点）
- 环境检测结果存入大数组，补环境后逐项对照
- 可手动改 hsw.js 用标准 JSON 格式 + html 头部 CSP 只保留 work 属性，让请求体显示明文

## 交付

- 纯协议难（wasm 交互复杂），首选补环境（Node + 全套浏览器 API 模拟）+ hsw.js
- 环境不行会返回验证码图片链接
