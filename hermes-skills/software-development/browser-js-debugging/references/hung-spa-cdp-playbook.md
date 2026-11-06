# 白屏 / 卡死 SPA：分级二分法（`?diag=N`）+ 进程级读数

页面白屏、harness 的 `Runtime.evaluate` 超时、`--dump-dom` 不返回三者同时出现时，**不要凭症状猜根因**，用「哪一层先死」把引导阶段切成可独立观测的层。每层只改一个变量、每层一个 `document.title` 打点、读数一律走浏览器进程级 HTTP。

## 前提纪律

- 在**生产构建产物**上测（`npm run build` + `npx vite preview --port N --strictPort`）；dev 冷启上千模块 + HMR websocket 会污染读数。
- **每轮测试新起一个 Chrome 实例**（`--headless=new --disable-gpu --no-sandbox --remote-debugging-port=9222 --user-data-dir=<scratch>`）；同一实例连开多个 `/json/new` 会让 target 状态变乱（`url` 空、`title` 陈旧）。用完 `/json/close/<id>`。
- 读数：`curl -s --max-time 5 http://127.0.0.1:9222/json/list` 取 `title`/`url`/`loading` —— **主线程死了也能读**，这是唯一不受页面状态影响的通道。

## 分级定义（每层只改一个变量）

| diag | 做到哪一步 | 通过就排除了什么 |
|---|---|---|
| 1 | 完整挂载（应用真实启动路径） | 整条引导链 |
| 2 | 只加载模块 + 解析路由，**不 mount** | 模块图 / import 图 / i18n 构造 / 路由表 |
| 3、4 | 绕过外壳，裸 `createApp(页面组件).mount()` | 该单页组件自身 |
| 5 | 真实 app **全插件挂载** + `router.beforeEach(() => false)` 禁止导航 | 插件安装 + 外壳 mount |
| 6 | 真实 app + 真实 router → **桩组件**路由 | router-view 渲染管线 + 导航 |
| 7 | 桩路由渲染**一个 UI 库组件** | UI 库组件渲染 |
| 8、9 | 桩路由绑定**真实页面组件文件**（模板-only 一个 / 全量一个） | 真实页面组件的 setup + 模板 |

判据：title 打到 `DIAG<N>:mounted` = 该层通过；停在 `:pre-mount` / `:navigated` = 卡在该层。

## 收缩规则

- **5/6/7/8/9 全过 ⇒ 嫌疑只剩「应用自身初始导航 + 生命周期」这一段，立刻停止查渲染层**。一次性排除整类嫌疑，比逐条读日志快一个数量级。
- 只在**未通过**的那一层里继续细分；已经过的层不重测（重复测已排除路径是纯浪费）。
- title 里的 `m=<matched.length>` 取 0 是 `app.mount()` 瞬间的时序值，**不是缺陷**。
- 「`--dump-dom` 超时」只能证明 `load` 没触发，**不能**证明主线程卡死；两者必须靠 `/json/list` 与 evaluate 两条通道交叉判定。

## 实现口径

- diag 分支写在引导段之后、`app.mount()` 之前，每个分支自行 `return`。
- 桩组件用 `{ render: () => null }`（免 import `h`）；要渲染 UI 库组件时 `const { h } = await import('vue')` 再 `h('a-button', null, () => 'x')`。
- 桩路由**不能**带 `meta.login` 这类守卫条件，否则会被守卫重定向走，测不到目标层。
- 要验证「初始导航」这一层时，也可以在挂载前先 `router.replace('/stub')` 再 mount —— 与「以当前 URL 启动」是两条不同的路径，分别测。
- **交付前必须把 diag 分支与 title 打点收敛成条件分支或删除**：非 diag 模式下它也会覆盖页面真实标题。

## 配套脚本

- 单点取值：`scripts/evaluate_cdp.js`（带 timeout，不静默卡住）
- 事件通道：`scripts/events_cdp.js`（抓原生对话框 / 异常 / console，同步阻塞场景下唯一可读窗口）
