# 自建 CDP 浏览器驱动 + 图形验证码解题回路

**何时用**：需要「真浏览器」才能过的闸（极验 / JS 挑战 / 受控组件表单 / blob 验证码），而手头的浏览器封装不可用或不想依赖它；或需要在真实 UI 流程里**抓完整请求体**。

---

## 1. 拉起系统里已有的 Chromium 并暴露 CDP

```bash
unset https_proxy HTTPS_PROXY http_proxy HTTP_PROXY ALL_PROXY all_proxy   # 出口代理会让下载/握手失败
CH=$(command -v chromium || command -v chromium-browser || readlink -f /snap/bin/chromium)
"$CH" --headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage \
      --remote-debugging-port=9222 --remote-allow-origins=* \
      --user-data-dir=/root/.chrome-probe --window-size=412,915 about:blank &
curl -s --noproxy '*' -m 8 http://127.0.0.1:9222/json/version     # 应回 Browser/Protocol-Version
```

`dbus` 报错（`Failed to connect to the bus`）**无害**，忽略。

---

## 2. 极简 CDP 驱动（`websocket-client`，无需 Playwright）

```python
import json, time, urllib.request, urllib.parse, websocket
CDP = "http://127.0.0.1:9222"
def http(path, method="GET"):
    req = urllib.request.Request(CDP + path, method=method)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode() or "{}")

class Tab:
    def __init__(self, url="about:blank"):
        try:    info = http("/json/new?" + urllib.parse.quote(url, safe=""), "PUT")
        except Exception: info = http("/json/new?" + urllib.parse.quote(url, safe=""))
        self.ws, self.id = websocket.create_connection(info["webSocketDebuggerUrl"],
                                                       timeout=60, suppress_origin=True), 0
    def cmd(self, method, **p):
        self.id += 1
        self.ws.send(json.dumps({"id": self.id, "method": method, "params": p}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == self.id: return m
    def js(self, expr, wait=True):
        r = self.cmd("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=wait)
        try: return r["result"]["result"].get("value")
        except Exception: return r
```

**要点**：
- `/json/new?url` 用 **PUT**（部分版本 GET 亦可）；返回里带 `webSocketDebuggerUrl` 与 `id`（**target id**）。
- **持久化 target id / ws 地址到文件 ⇒ 后续进程可重连同一标签页**（两阶段提交的关键，见 §4）。
- `Runtime.evaluate` 要 `awaitPromise=True` 才能拿到 `fetch`/`canvas` 的 Promise 结果。

---

## 3. 真实鼠标事件 & 受控组件填表

```python
def click(x, y):                     # 必须成对：pressed + released
    for t in ("mousePressed", "mouseReleased"):
        cmd("Input.dispatchMouseEvent", type=t, x=x, y=y, button="left", clickCount=1)
        time.sleep(0.09)
```

```javascript
// React 受控组件：直接改 .value 不触发状态更新，必须走原生 setter + input/change
const set = (el, v) => {
  const d = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  d.call(el, v);
  el.dispatchEvent(new Event('input',  {bubbles:true}));
  el.dispatchEvent(new Event('change', {bubbles:true}));
};
```

**在点按钮之前**包一层 `window.fetch` 与 `XMLHttpRequest.prototype.open/send`，把请求体写进 `window.__reqs` ⇒ **在真实 UI 流程里抓到完整 body**（比手拼字段准一个量级）。

---

## 4. blob 验证码 → 视觉解题回路（两阶段）

1. **阶段 A（脚本）**：开注册/登录页 → 触发提交（弹出验证码）→ `canvas` 导出 blob 图 → 存盘 → **把 target ws 地址写文件**。
   ```javascript
   const img = Array.from(document.querySelectorAll('img')).find(i => (i.src||'').startsWith('blob:'));
   const c = document.createElement('canvas');
   c.width = img.naturalWidth; c.height = img.naturalHeight;
   c.getContext('2d').drawImage(img, 0, 0);
   return c.toDataURL('image/png');
   ```
2. **阶段 B（脚本）**：按文件里存的 ws 地址**重连同一标签页** → 回填 + 真实鼠标点击 → 提交 ⇒ **验证码会话不失效**（每次刷新/重开页都会换码）。

### 提高视觉定位精度

```python
cmd("Emulation.setDeviceMetricsOverride", width=500, height=828, deviceScaleFactor=3, mobile=True)
cmd("Page.captureScreenshot", format="png")     # 1500x2484
```

- 用 `getBoundingClientRect()` 拿**元素 CSS 坐标**，裁剪区 = `[x*3, y*3, (x+w)*3, (y+h)*3]`。
- 让视觉模型**只报百分比坐标**（0-100%），再换算 `CSS = 元素x + pct*元素w` —— 比让它报像素坐标可靠得多（模型会自己猜错分辨率）。
- 提交按钮同理：查 `[class*=submit]` 的 rect 中心点再 `click`。

### 「按顺序选择汉字」类验证码（botion / GeeTest 同形）

实测结构：`botion_wrap > botion_subitem > botion_window`（**272x181 背景图，汉字烘焙在 JPEG 里，无独立 DOM 节点**）+ `botion_submit`；**提示字是 3 张独立的 22px 精灵图**（URL 即该字的指纹，可逐张放大识别）。

**诚实边界**：把 22px 缩略图 + 一幅带旋转/点阵化汉字的 JPEG 交给通用视觉模型做**像素级定位**，命中率不稳（本案多次 `Please try again`）。已验证可行的是**整体回路**：CDP 真实鼠标事件 + 图片导出 + 视觉读数**是通过的**（后端返回 `用户不存在`/`用户名或密码错误` 而不是 `6022`，即令牌被接受）。要稳定通关需换成**更高精度手段**：把背景图按 `background-image` 的 URL **原图下载**（而不是截屏）、提示字精灵图与图内字形做**模板/特征匹配**，或接打码服务。

**另**：`Select in this order` 的提示字**必须是图里存在的那几个**；若视觉报「某提示字未找到」，先把图里**全部**汉字连同百分比坐标列出来，再与提示对照 —— 提示字常被模型读错一个字。

---

## 5. 纪律

- 画面尺寸用 `Emulation.setDeviceMetricsOverride` 固定，否则同一坐标在不同 dpr 下含义不同。
- 每次提交失败都要**重新刷新验证码**（一次性）；两阶段重连是唯一能保住会话的方式。
- 抓到的 target id 用完即弃；`/json/list` 可按 URL 关键字筛回自己的标签页。
