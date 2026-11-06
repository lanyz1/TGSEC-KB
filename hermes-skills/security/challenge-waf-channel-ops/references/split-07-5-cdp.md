## 5. CDP 驱动纪律
- **拿结果必须用同步调用接口**（如 `t.call(...)`）；fire-and-forget 的 `send` 只返回消息 id ⇒ 取 cookie/响应体时会静默得到空值，白白绕远。
- 共享调试浏览器里一旦开了同家族的多个标签，**按精确 host 选页**，不要用域名家族子串（`xwallet` 会同时命中 `xwallet8` 与 `xwallet801` ⇒ 打错目标）。
- 新开标签用 `Target.createTarget`（部分实例上 `/json/new` 不灵）。
- ★**复用「现成」调试实例前先断言它真能用**：`/json/list` 里 url 写着目标域、tab 实际停在**错误页**（`location.host` 为空 / `chromewebdata`）是常态 ⇒ 页内 `fetch` 全部 `TypeError: Failed to fetch`（opaque origin），而脚本照常「跑完」并打印一批假否定。判据 = `location.host` 等于目标域 + `document.readyState`；不满足就 `Target.createTarget` 新建并重新导航，别在原 tab 硬发。**每批先打印宿主 origin 自证**，不满足则整批登记「未测」。
- ★**需要外联时自起独立实例，绝不杀已有 Chrome**：历史遗留的调试实例常**没有代理出口**（症状 = 导航一直加载/超时，如卡死的 `:9227`）⇒ 起新实例用独立 `--user-data-dir` + 新 `--remote-debugging-port` + `--proxy-server=socks5://127.0.0.1:<port>`（参数见 §12）；**杀进程必须先取得用户同意**，且旧实例可能承载着已解题的会话。起实例前先纯 HTTP 探一遍候选出口（`curl -x socks5h://127.0.0.1:<p> https://<host> -o /dev/null -w '%{http_code}'`），把已验证可通的写进 `--proxy-server`。
- ★**浏览器类脚本别在前台等**：导航/解题/页内 fetch 循环在终端前台极易撞满超时（实测 420s）⇒ 走后台 + 硬超时 + 结果落盘（`> xpN.out 2>&1`），再读文件判读；前台超时会把「还没跑完」误读成「通道不通」。
- ★ **自研「pump 型」CDP 客户端：`pump(seconds)` 只把事件喂给 `on_event`、不返回事件列表** ⇒ 要收 `Network.requestWillBeSent` / 读 `getResponseBody`，必须**覆写 `on_event` 自己攒**；写 `for e in t.pump(...)` 拿到 `None`，症状是「脚本只打表头就退出」。同理：`send` 是 fire-and-forget、必须用同步 `call` 才拿得到回执（§5 首条）。

