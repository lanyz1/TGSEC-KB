---
name: browser-js-debugging
description: "网页JS报错/交互失效诊断: headless Chrome+CDP抓console错误。触发: 按钮不跳转。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [chrome, cdp, javascript, debugging, frontend]
    category: software-development
---

# 浏览器 JS 诊断(headless Chrome + CDP)

诊断"网页能渲染但交互不工作/按钮点了没反应/JS 报错"类问题: 用 headless Chrome + Chrome DevTools Protocol 抓真实 console 错误, 并脚本化点击验证行为。比肉眼排查/猜快一个数量级。

## When to Use

- 用户报"点击 X 没反应 / 不跳转 / 表单提交无效"但 curl 页面 200、HTML 结构正常
- 页面渲染正常(SSR 部分可见)但动态交互失效
- 需要确认 JS 运行时报错的具体位置和数量

## 诊断阶梯(先廉价后昂贵)

1. **curl 结构检查**: `__SKU_DATA__`/内联 JSON 完整性、`<script>` 闭合、外部 JS 引用清单
2. **静态资源 200 检查**: 页面依赖的 /static/js/*.js、CDN 资源逐个 `curl -w '%{http_code} %{size_download}'`(404/0 字节 = 交互挂掉)
3. **CDP 真实浏览器**(核心): headless Chrome 加载页面 → 收集 `Runtime.exceptionThrown` / `Runtime.consoleAPICalled` → `Runtime.evaluate` 点击目标按钮 → 对比点击前后 DOM 状态(class 变化/display 变化/location)
4. **修复后复测同一脚本**: 错误数归零 + 点击后 DOM 状态变化 = 修复确认

## 核心脚本

`scripts/cdp_console_diag.js` — 通用 CDP 诊断脚本(Node 22+, 无第三方依赖):
- 参数: `URL`(必选)、可选 `CLICK_SELECTOR`(点击后验证)
- 输出: 页面状态(jQuery/Vue/fbq 存在性、关键 class)、点击前后 DOM 对比、全部 console 错误
- 用法: `node cdp_console_diag.js https://example.com/page "#buyBtn"`

## 页面白屏 / 卡死：改走 CDP 直连通道(harness 与 dump 都会失效)

harness 的 `Runtime.evaluate` 依赖页面主线程，`--dump-dom` 依赖 `load` 事件；SPA 引导阶段出问题时两者**永久挂起而不报错**。此时换这三条通道：

1. **从浏览器进程级 HTTP 读进度**：CDP 端口开着时 `curl -s --max-time 5 http://127.0.0.1:9222/json/list` 取 `title` / `url` / `loading` —— **页面主线程死了照样能读**。配合代码打点(`document.title='BOOT:pre-mount'` → `app.mount()` → `'BOOT:mounted <fullPath> m=<matched>'`)就能把「挂载 / 路由 / 渲染做到哪一步」变成可轮询字符串。这是区分「真卡死」与「只是 load 没触发」的唯一廉价手段。
2. **evaluate 必须自带 `timeout` 与自救 race**：主线程被占住时请求被吞、连接**挂着不报错**，脚本会静默卡死 ⇒ `Runtime.evaluate {timeout: N}` + `Promise.race` 兜底(见 `scripts/evaluate_cdp.js`)。`Debugger.pause` 在被同步阻塞时同样不响应；要调用栈只能用 `Profiler.start/stop`(采样在独立线程)。
3. **只收事件的通道最耐用**：`Page.enable`+`Runtime.enable`+`Log.enable` 后监听 `Page.javascriptDialogOpening` / `Runtime.exceptionThrown` / `Runtime.consoleAPICalled` / `Log.entryAdded`(见 `scripts/events_cdp.js`)。**原生 alert/confirm 会同步阻塞主线程**，症状与死循环几乎一样；不做事件监听就会误判成「代码在循环」。

### 踩过的坑(实测)

- **`--dump-dom` 的 `exit 124` / 0 字节只证明 `load` 没发生，不证明脚本跑不完**：dump 等 `load`，任何挂起请求(外链图片/字体/CDN)都让它永不返回；`--virtual-time-budget` 在有挂起请求时虚拟时钟不推进。**禁止据 dump 超时下「主线程卡死」结论** —— 先读 `/json/list`。
- **`--host-resolver-rules="MAP * ~NOTFOUND"` 会连 `127.0.0.1` 一起打死** ⇒ 页面自身 `ERR_NAME_NOT_RESOLVED`，读数全成噪声。要隔离外链只能逐个映射到黑洞端口：`MAP host.example 127.0.0.1:9`(秒失败)。
- **一个 Chrome 实例连开多个 `/json/new` 后 target 会乱**(`url` 变空、page target 只剩一个、`title` 陈旧)⇒ 每轮测试新起实例、用完 `/json/close/<id>`；读数前先核对 `type==='page'` 且 URL 与预期一致，别拿陈旧 title 下结论。
- **`ws` 装到独立 scratch 工程**(`npm init -y && npm i ws`)，用 `WS_PATH` 指过去，别污染被测工程依赖。
- **调试插桩不许留进交付物**：`document.title` 打点会覆盖页面真实标题，交付前收敛成条件分支或删除。
- **`closeAll()` / 关掉最后一个标签会杀死整个 Chrome 进程**（`headless=new`）⇒ 后续 evaluate 全 `undefined`、读数被自己污染。探针默认**只读**：不关标签、不新建标签（`--no-reset`）。
- **WS 探针退出必须延迟**：`process.exit(0)` 紧跟 `ws.close()` 会被管道缓冲截断 ⇒ `setTimeout(() => process.exit(0), 400)`，catch 分支同样延迟。
- **探针不许吞 CDP 错误**：`r.error` 原样返回（前缀 `CDP_ERR:`）—— `Inspected target navigated or closed` 这类决定性信号被静默丢掉后，剩下的全是误导性读数。
- **脚本内 `nohup … &` 起的 Chrome 会随脚本退出被杀** ⇒ 用 PowerShell `Start-Process … -WindowStyle Hidden` 脱离式拉起，再轮询 `/json/version` 等就绪；启动前只按 `--remote-debugging-port` 清理**本任务历史实例**，别 taskkill 全部 chrome。
- **目标不断导航时，页面会话会不断失效**：`Debugger.pause` 无响应、`ECONNRESET`、evaluate `navigated or closed` 都可能只是“页面正在重启”的下游现象，不是脚本或页面本身的毛病 —— 先数导航再下结论。

### 导航风暴 vs 主线程卡死（先数导航，再读 DOM）

`--dump-dom` 超时 + `Debugger.pause` 无响应 + evaluate 全 `undefined` 的组合**不等于卡死**：也可能是**启动期整页重载循环**（页面每几毫秒重启一次，所有依赖“稳定文档”的读数都拿不到）。判据只看一件事：**请求的导航数 vs 实际提交的导航数**。

- 用**双层导航监视器**：浏览器层 `Target.targetInfoChanged/targetCreated/targetDestroyed`（**渲染进程死了仍继续报**，`targetInfo.url` 就是页面真实 URL）+ 页面层 `Page.frameNavigated` / `Page.frameRequestedNavigation`。浏览器层与页面层可以同一个 WS 连接：`Target.attachToTarget{targetId, flatten:true}` 拿 `sessionId` 后再发 `Page.*`。现成工具：`scripts/navwatch_cdp.js`。
- `frameRequestedNavigation.reason` 直接指认发射源：`reload` = `location.reload()`/`history.go(0)`/`router.go(0)`；`scriptInitiated` = `location.href=`/`pushState`；`formSubmissionGet` = 表单；`metaTag` = meta refresh。
- 实测特征：“**多次 `reason=reload` 指向同一 URL、却只提交 1 次 `frameNavigated`**” = JS 在渲染期反复触发导航（请求发出但未提交）。此时排除卡死：每轮 `document.title` 打点仍能读到 `BOOT:mounted` 即证明 mount 跑完了。
- 定位发射点：搜 `.vue`/模板里的**属性形式处理函数**（`:onXxx="fn()"`）—— 反编译重建产物高发，每次渲染真调一次（详见 skill `webapp-rebuild-from-recon`）。
- 一条命令跑完整闸（build → preview/Chrome 探活 → 重载计数 → DOM/异常/截图）：`scripts/gate_runtime.sh`。

分级二分法(`?diag=N` 逐层切分引导阶段)见 `references/hung-spa-cdp-playbook.md`。

## 关键技术细节(踩过的坑)

- **必须连 page target 而非 browser target**: `/json/version` 的 webSocketDebuggerUrl 是 browser 级, `Page.enable` 会报 `-32601 wasn't found`; 要 GET `/json` 找 `type === 'page'` 的 target
- **Node 22 自带全局 WebSocket**, 不需要 npm install ws(权限受限环境也能跑); 原生 WebSocket 用 `addEventListener('message')` / `ws.onopen`, 没有 `.on()` / `.removeListener()`
- 错误收集必须在 `Page.navigate` 之前注册 `Runtime.enable` + message 监听
- 点击验证要对比 `before/after` 的 class/display/可见性(如 `mainContent.hidden` → `checkoutContent` 显示), 别只看 location(很多交互是页内切换不跳 URL)
- **前置注入的采集器只能证明「装过」，不能证明「没报错」**：`Page.addScriptToEvaluateOnNewDocument` 装的 `window.__cap` / `__errs` 采集器在导航后仍存在，但读回**空数组**往往只是探针未生效、被重载清掉或装在另一个 target 上 ⇒ **空集合不是「无错误」的证据**。每次读数前先写入一个哨兵值再读回自证探针活着，并用事件通道（`Runtime.exceptionThrown` / `Log.entryAdded`，见 `scripts/events_cdp.js`）交叉验证，两者都空才敢下结论。
- **「是我改坏了还是它本来就这样」只能用同环境基线对照回答**：把**原厂/旧版产物**用同样方式起在同机另一个端口，同一轮里比可测读数（守卫跳转后的 URL、`document.title`、`#app` 的 innerHTML、关键全局对象类型）。实测两侧都只渲染注释节点 `<!---->` ⇒ 是缺后端的环境现象，**不是回归**；靠推理判「应该没事」会把环境缺陷记成自己的 bug，或反过来漏掉真回归。
- **探针代码里不要出现多字节字符**：经上下文压缩/转录后会被替换成占位符，回放到执行器就是 `SyntaxError: invalid character` ⇒ 探针注释与字符串一律用 ASCII 写，报告里再用中文说明。

## 高频根因模式

1. **第三方库初始化抛错中断 jQuery ready 回调** ⭐最常见:
   - 症状: 页面渲染正常, 但所有按钮绑定失效(点啥都没反应)
   - 机理: `$(document).ready(function(){ new Swiper(...); ...; $('#btn').on('click', fn); })` —— Swiper 等库在回调开头抛错 → 整个回调中断 → 后续所有绑定未注册
   - 修复: 库初始化**整体 try/catch** + 元素存在性检查(`document.querySelector` 判空), 保证业务绑定代码一定执行
2. **Swiper thumbs 时序**: 主轮播 `thumbs: {swiper: '.thumb-swiper'}` 传选择器字符串, 若缩略轮播未先初始化 → `$el` null 报错。**先建 thumb 实例, thumbs 传实例引用**
3. **script onload 调未定义函数**: `<script src="x.js" onload="foo()">` 但 foo 定义在后续脚本 → ReferenceError。核对 onload 回调函数名与定义位置, 或去掉无效 onload(逻辑若在别处自行执行)
4. **同步 script 阻塞**: 某个外部 JS 加载失败/超时会阻塞其后所有脚本执行(cdnjs 等公共 CDN 不可达时常见)
5. **提交函数依赖缺失(点提交但 0 网络请求)** ⭐: 表单提交函数内部调用未引入的库(如 `layer.load()`)→ ReferenceError → **$.ajax/fetch 提交永不执行**(UI 显示"提交中…"后无动静)。诊断: Network 层监听 `Network.responseReceived` 抓提交接口 URL——**0 请求 = 前端函数在发请求前抛错**, 有请求才看响应。修复: 自托管缺失库并 head 引入, 或提交函数内 try/catch。连带坑: 提交函数返回 `undefined`(提前 return)会被误判"已放行"——检测返回值时用显式哨兵(如 `result === false ? 'blocked' : 'proceeded'` 会把 undefined 算成 proceeded)
6. **服务端 Error 不落前端**: 提交请求发出但响应 500(空 body)——后端 PHP `ArgumentCountError` 等是 Error 不是 Exception, `catch (Exception)` 捕获不到 → Fatal 500。前端表现为"提交失败/卡住"; 必须看服务器错误日志(`/var/log/php_errors.log`)定位, 并回查最近改动过的调用链(参数签名变了但调用点没同步)

## Verification

- [ ] 诊断脚本输出 ERRORS(0)
- [ ] 点击后 DOM 状态按预期变化(表单显示/页面切换/location 跳转)
- [ ] 用户复测通过

## References

- `scripts/cdp_console_diag.js` — 通用诊断脚本(改 URL/选择器即可复用)
- `scripts/evaluate_cdp.js` — 带超时的单点取值探针(主线程被占住时返回 timeout 而非挂住)
- `scripts/events_cdp.js` — 只收事件、不做 evaluate 的通道(抓原生对话框/异常/console)，同步阻塞场景下唯一还能读的窗口
- `scripts/navwatch_cdp.js` — **双层导航监视器**（浏览器层 `Target.*` + 页面层 `frameNavigated`/`frameRequestedNavigation`）：渲染进程崩溃后仍能读数，是「重载风暴 vs 卡死」的唯一判据工具；输出行含 `reason=`/`frameNavigated`/`loadEventFired`/`targetCrashed` 可直接 grep 计数
- `scripts/gate_runtime.sh` — 一条命令的运行期闸门（前置 build/预览/Chrome 探活 + 重载计数 + 可选 DOM/异常读数）
- `references/hung-spa-cdp-playbook.md` — 白屏/卡死 SPA 的分级二分法（`?diag=N` 完整分级表、收缩规则、判据与纪律）
