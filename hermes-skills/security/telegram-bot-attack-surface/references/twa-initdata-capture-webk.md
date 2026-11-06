# TWA initData 抓取配方 — Web K + CDP（2026-10 实战验证）

用途：给定任意可登录的 TG 账号（Telethon .session），抓取其对任意 bot 的 **WebApp initData**，以该账号身份直调 TWA 后端的 HTTP API（QF 类自定义控制台、FastAPI 类服务均实测通过）。

## 0. 前提
- Telethon session（批量号包常见：`api_id:2040` + Telegram Desktop 公共 hash `b18441a1ff607e10a989891a5462e627`；号 json 常带 `twofa` 密码）。
- chromium（Chromium 族均可）+ playwright python：用 `browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")` 挂现有 chrome。
- 目标 bot 有**真 webview 按钮**（非 URL 按钮）。

## 1. 起浏览器
```bash
chromium --headless=new --no-sandbox --remote-debugging-port=9222 --user-data-dir=/tmp/prof about:blank &
```

## 2. 登录 Web K（选择器实测）
1. `page.click("text=LOG IN BY PHONE NUMBER")`
2. 手机号输入 = **contenteditable** `.input-field-input`（第 2 个；K 版此处没有 input 元素）。点击 → `Control+A`、`Delete` → `keyboard.type('+<国家码><号>', delay=80)`（自动切国家）。
3. 点 `NEXT` → "We have sent you a message in Telegram with the code."
4. 验证码框 = 真 `<input>` 但**隐藏**（click 会超时）→ JS focus + 键盘：`page.evaluate("document.querySelector('input[type=text]').focus()")` → `keyboard.type(code, delay=150)`（5 位自动提交）。
5. 2FA 屏：密码框 = `input.input-field-input`；`input.stealthy` 是**诱饵框**（focus 到它静默失败）。登录成功 = chat 列表出现。

## 3. 读登录码（Telethon，独立进程！）
- 码来自 **777000**：`Login code: 34921.`；历史多条混杂 → 带 `m.date` 挑**最新一条**（本次 20s 新）。
- **不要与 playwright 同进程**：playwright sync 环境下 `asyncio.run()` 报 `cannot be called from a running event loop` → 拆两步命令。

## 4. 打开 bot → webview
1. 搜索：`input.input-search-input` → 输入 bot 名 → 点结果文本。空会话先 `START`。
2. webview 按钮 class `reply-markup-button is-web-view`；`text=...` click 超时改用 JS：`[...document.querySelectorAll('*')].find(e => (e.innerText||'').trim()===TXT).click()`。
3. 弹 `To launch this web app...` → `.popup.active button:has-text('LAUNCH')` → 等 10s+。

## 5. 抓 initData（关键坑）
**playwright `page.frames` / `querySelectorAll('iframe')` 都看不到 mini-app 的跨进程 iframe。** 用原生 CDP：
```python
bs = browser.new_browser_cdp_session()
t = bs.send("Target.getTargets")
for ti in t["targetInfos"]:
    u = ti.get("url", "")
    if ti.get("type") == "iframe" and "tgwebappdata" in u.lower():
        frag = urllib.parse.urlparse(u).fragment
        initdata = urllib.parse.parse_qs(frag)["tgWebAppData"][0]  # 再解一层编码
```
- initData = `query_id=...&user=%7B...%7D&auth_date=...&hash=...`（user 内层再解一次）。
- 有 auth_date 时效（后端常见 1h~24h 窗口），抓到立即用。

## 6. 使用 initData
- 自定义头：`X-Telegram-Init-Data: <initData>`（QF 控制台类）。
- FastAPI 类：`POST /api/session {"initData": "..."}` → `{token}` → `Authorization: Bearer <token>`。
- 端点名各异（/api/auth/telegram 等）——先翻前端 JS 或 `/openapi.json`。
- **身份 ≠ 权限**：admin 面仍由服务端 role/白名单判定（否则 403 或静默丢弃，实测不一致：JSON 报错 vs 无响应）。

## 7. 变体与副产物
- bot 按钮是 **URL 按钮**（非 webview）→ 无 initData 下发 → 走 web-bind 流（`POST /web/session` → link_code → Telethon `/start web_CODE`）。
- webview iframe 主机名可能 = **未入 CT 日志的新部署子域**（如 `wuzi-20261006.pc28gj.cc`）——每次记录 host 并顺手探其 API。
- 先探 dev 后门：`/api/health` 的 `devMode`、`/api/auth/dev`——prod 通常已关（`开发登录已关闭`）。
- 登录 Web K 会在账号上新增设备会话（可见于 Devices）——事毕可考虑清理。
