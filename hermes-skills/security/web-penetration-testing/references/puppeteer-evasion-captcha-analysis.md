# Puppeteer/浏览器自动化规避与验证码分析实战

## 环境

- **Container**: `scraper` (browserless Docker 镜像)
- **Puppeteer 路径**: `/usr/src/app/node_modules/puppeteer`
- **执行**: `docker exec -e NODE_PATH=/usr/src/app/node_modules scraper node /tmp/script.js`
- **浏览器**: HeadlessChrome/121.0.6167.85 (via browserless)
- **浏览器less API**: `/scrape` (基础HTML提取, 可用), `/function` (返回空—不可用)

## Browserless Scrape 端点

```bash
docker exec scraper curl -sk -X POST "http://localhost:3000/scrape" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://target/login","elements":[{"selector":"html"}]}'
# 返回: {"data":[{"selector":"html","results":[{"html":"<html>...","text":"..."}]}],"debug":{...}}
# 注意: 不支持 options.waitFor 参数 — 会报 "options is not allowed"
```

## Browserless /function 端点

`POST http://localhost:3000/function` 返回 **HTTP 200 但 Content-Length: 0**。此容器中不可用于执行自定义Puppeteer代码。

## Puppeteer 直接执行 (在容器内)

```bash
# 确认 puppeteer 可用
docker exec scraper node -e "const p = require('/usr/src/app/node_modules/puppeteer'); console.log('ok')"

# 执行脚本 (需 NODE_PATH)
docker exec -e NODE_PATH=/usr/src/app/node_modules scraper node /tmp/script.js
```

## 浏览器指纹规避 (全部已验证生效)

### 注入方式: `page.evaluateOnNewDocument()`

**必须在 `page.goto()` 之前调用**, 在每个新 document 创建时注入。

### 完整规避套件

```javascript
await page.evaluateOnNewDocument(() => {
  // 1. navigator.webdriver — 最重要的检测点
  Object.defineProperty(navigator, 'webdriver', {
    get: () => false, configurable: true,
  });

  // 2. navigator.plugins — 模拟有插件 (headless默认length=0)
  Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5], configurable: true,
  });

  // 3. navigator.languages — 模拟中文浏览器
  Object.defineProperty(navigator, 'languages', {
    get: () => ['zh-CN', 'zh', 'en'], configurable: true,
  });

  // 4. chrome.runtime — 极验Geetest检测项
  window.chrome = {
    runtime: {
      connect: () => ({}), sendMessage: () => {},
      onMessage: { addListener: () => {} },
      onConnect: { addListener: () => {} },
      id: 'nope',
    },
    app: {
      isInstalled: false,
      InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
      RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' },
    },
    loadTimes: () => ({}), csi: () => ({}),
  };

  // 5. hardwareConcurrency & deviceMemory
  Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
  Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });

  // 6. WebGL vendor/renderer 覆盖 (用于 WebGL fingerprinting)
  const origGetParameter = WebGLRenderingContext.prototype.getParameter;
  WebGLRenderingContext.prototype.getParameter = function(param) {
    if (param === 37445) return 'Intel Inc.';
    if (param === 37446) return 'Intel Iris OpenGL Engine';
    return origGetParameter.call(this, param);
  };

  // 7. Canvas fingerprint 微扰动 (极小噪声避免完整指纹被检测)
  const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
  HTMLCanvasElement.prototype.toDataURL = function(type, quality) {
    const ctx = this.getContext('2d');
    if (ctx) {
      const imageData = ctx.getImageData(0, 0, this.width, this.height);
      if (imageData && imageData.data.length > 0) {
        imageData.data[0] = imageData.data[0] ^ 1; // 翻转第1个像素最低位
        ctx.putImageData(imageData, 0, 0);
      }
    }
    return origToDataURL.apply(this, arguments);
  };
});
```

### CLI flag (puppeteer launch args)

```javascript
const browser = await puppeteer.launch({
  headless: 'new',
  args: [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--disable-web-security',
    '--disable-features=IsolateOrigins,site-per-process',
    '--window-size=1920,1080',
    '--disable-blink-features=AutomationControlled',  // 关键! 移除 Blink 自动化标记
    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
  ]
});
await page.setViewport({ width: 1920, height: 1080 });
```

## 网络请求拦截

### 拦截 XHR/fetch 请求

```javascript
await page.setRequestInterception(true);

page.on('request', request => {
  const url = request.url();
  // 只捕获特定URL
  if (url.includes('/tools/') || url.includes('ajax') || url.includes('geetest')) {
    capturedRequests.push({ url, method: request.method(), postData: request.postData() });
  }
  // 阻塞不必要的资源
  if (['image', 'media', 'font', 'stylesheet'].includes(request.resourceType()) 
      && !url.includes(TARGET)) {
    request.abort();
  } else {
    request.continue();
  }
});

page.on('response', async response => {
  const body = await response.text().catch(() => '[CANNOT READ]');
  capturedResponses.push({
    url: response.url(),
    status: response.status(),
    body: body.substring(0, 500),
  });
});
```

## 验证码类型判断 (capchaType 对应表)

从 Vue SPA `site.config` 或 `site.optionStates` localStorage 中的 `capchaType` 字段判断：

| capchaType | 类型 | JS组件 | API端点 |
|:----------:|:----:|:------:|:--------|
| 1 | 自定义拼图 (puzzle) | `customGeetest` (`0000-CXC5r6S3.js`) | `userStore.ClickGeetest()` |
| 2 | **极验 Geetest v3** | `initGeetest` (`gt.js`) | Geetest JSONP /gettype.php |
| 4 | 普通图片验证码 (4位) | 内置 | `userStore.RandImage()` |
| 5 | 混合验证码 (6位) | 内置 | `userStore.MixVerificationCode()` |
| 6 | Robot 滑块拼图 | `RobotBtn + VerifySlide` | `userStore.ReqGet()` → `userStore.ReqCheck()` |
| 7 | **Robot 文字点选** | `RobotBtn + VerifyPoints` | `userStore.ReqGet()` → `userStore.ReqCheck()` |
| 8 | Robot 数字计算 | `RobotBtn + robotCount` | `userStore.ReqGet()` → `userStore.ReqCheck()` |

### 触发条件

验证码在 `login()` 方法中根据 `attachedValidation` 和 `capchaType` 控制显示：
- `geeTestInit()` — 仅 capchaType===2 时调用
- RobotBtn — 仅 capchaType===6/7 时显示
- 普通验证码 — capchaType===4/5 时显示
- `robotCountCheckApi()` — capchaType===8 时调用

### Robot 验证码 (capchaType=6/7) 流程

```
1. User clicks "点击按钮进行验证"
2. $refs.verify.show() → 弹出验证窗口
3. ReqGet() API → 返回图片 + token + secretKey
4. User interacts (slider/click words)
5. Coordinate data encrypted with AES key "XwKsGlMcdPMEhR1B"
6. ReqCheck() API → 验证坐标
7. If success: robotBtnStatus=2, captchaToken set
8. Login proceeds with captchaToken
```

**ReqGet 响应结构**：
```json
{
  "code": "success",
  "data": {
    "originalImageBase64": "...",  // 原图 Base64
    "jigsawImageBase64": "...",    // 滑块图 Base64 (capchaType=6)
    "wordList": ["A","B","C"],     // 待点击文字 (capchaType=7)
    "token": "...",                // 后续ReqCheck验证用
    "secretKey": "...",            // AES密钥
    "isNeedValid": true/false
  }
}
```

**ReqCheck 请求**：
```javascript
const payload = {
  pointJson: AES_encrypt(JSON.stringify({x: x, y: y}), secretKey),
  token: <REDACTED>,
};
```

### Geetest 初始化参数 (capchaType=2)

gt.js 加载 `initGeetest` 全局函数。调用方式：
```javascript
initGeetest({
  gt: "gt值",           // 从注册/登录API的register1返回
  challenge: "challenge值",
  new_captcha: true,
  api_server: "api.geetest.com",
  offline: false,
  product: "bind",      // 或 "popup", "float"
}, captchaCallback);
```

## AES 加密分析

Vue SPA 中的加密方式 (`vendor-DNhkrRvw.js`):

```javascript
// AES 加密 (CryptoJS)
const AES_KEY = "<REDACTED>";  // 硬编码密钥
function encrypt(plaintext, key) {
  const k = CryptoJS.enc.Utf8.parse(key);
  const iv = CryptoJS.enc.Utf8.parse(key); // 注意: IV=Key (不安全)
  return CryptoJS.AES.encrypt(plaintext, k, {
    mode: CryptoJS.mode.ECB,  // ECB模式 (更不安全)
    padding: CryptoJS.pad.Pkcs7,
  }).toString();
}
```

**API 请求格式**:
```json
POST /tools/_ajax/login
Body: "AES_Base64_Encrypted_String"
```

**API 响应格式**:
```
"gzipped_base64_string"  // 标准 Java/Spring ResponseBodyAdvice 压缩
```
解码: `base64.b64decode()` → `zlib.decompress(..., 16+zlib.MAX_WBITS)` → UTF-8 JSON

## 触发的 XHR/Tools API (新葡京娱乐城)

| Action | 说明 | 时机 |
|--------|------|------|
| `getSiteInitData` | 站点初始化 (含capchaType, siteId等) | 页面加载 |
| `getExtGameConfig` | 第三方游戏配置 | 页面加载 |
| `randImage` | 通用验证码图片 (capchaType 4/5) | 登录页加载 |
| `forgetPwdSeting` | 忘记密码设置 | 登录页加载 |
| `login` | 用户登录 | 点击登录按钮 |
| `ReqGet` | Robot验证码图片+token | 点击验证按钮 |
| `ReqCheck` | Robot验证码坐标验证 | 滑动/点选后 |
| `ClickGeetest` | 自定义拼图验证码初始化 | capchaType=1 |

## 注意事项 / Pitfalls

1. **puppeteer 模块路径**: browserless 容器中 puppeteer 安装在 `/usr/src/app/node_modules/`，不是标准路径。必须设置 `NODE_PATH=/usr/src/app/node_modules` 或使用绝对路径 `require('/usr/src/app/node_modules/puppeteer')`。

2. **page.evaluate 中的变量名冲突**: evaluate 回调在浏览器上下文执行，外层 JS 的变量名 (如 `i`) 与其内部变量不可见。传递参数: `await page.evaluate((arg) => { ... }, argValue)`。

3. **browserless /function endpoint**: 某些 browserless 版本中 `/function` 返回 200 但空内容(body-length=0)。原因未知，可能是版本兼容性或配置问题。改用容器内直接 node 执行 puppeteer。

4. **canvas fingerprint 扰动**: 只在 toDataURL 调用时修改，不影响实际渲染。噪声幅度极小 (1bit 扰动)，不影响用户视觉但改变 canvas hash。注意：某些网站同时对比 canvas 数据和 WebGL 指纹，需同时覆盖。

5. **ECB mode AES**: 所有块相同内容加密结果相同——这是特征，可用于识别加密模式。
