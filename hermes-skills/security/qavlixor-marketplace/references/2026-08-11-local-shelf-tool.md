# 卖家本地自动上品工具（2026-08-11 交付，会话产物目录）

用户要求"卖家本地自动上品工具"→ 交付两版：CLI 脚本 + Web UI 版（后者用户拍板要"好看的前端 UI"，做了暗色科技风）。
产物在 `D:\跨境商城\会话产物\`：`qavlixor_auto_shelf.py`（CLI）、`qavlixor_shelf_ui.py`（Web 后端）、`shelf_ui.html`（前端）、`启动上品工具.bat`（GBK+CRLF，双击启动）。

## 上品链路（平台侧 API，工具全走这些）

1. **登录**：`POST /api/auth/login` body `{role:"seller", email, password}` → 拿 `gm_session` cookie（httpOnly 签名会话）。旧 4 个明文 cookie（gm_role/gm_email）已废弃，别再拼。
2. **读模板**：16 列 Excel（Sheet「商品数据」，跳过空行/标题空行；示例行靠"标题为空"跳过，不是固定行号）。
3. **提交**：`POST /api/seller/products`，payload 字段（与发品表单对齐）：
   - `title`（可带 brand 前缀）、`brand`、`category`（如"电脑办公"）、`status`（"草稿"/"已上架"）、`price`、`inventory`、`skuItems`、`detail`（卖点）、`shippingNote`、`productParams`、`shipBy`、`imageUrl`+`images:[{url}]`、自定义类目 `customCategory:{name,parentSlug}`
   - `skuItems` 每项 `{sku, name, price, stock}`（模板列格式 `规格名|编码|价格|库存;`）
   - `productParams` 每项 `{label, value}`（模板列格式 `参数名:值;`）
   - `shippingNote` 文本格式（平台解析源，必须一致）：`免运费` / `运费模板：X` / `自定义运费：首件 X + 续件 Y USDT，满 Z 包邮`
4. **图片**：https URL 直接传；本地路径 → `POST /api/uploads`（multipart `file` 字段）→ 返回 `url/path`（相对路径要拼 BASE）。多图 `;` 分隔，第一个=主图。
5. **限速**：单条间隔 0.4s（防风控），单条失败不中断整批，报告成功/失败原因。

## Web 版架构（零依赖本地工具模式，可复用）

- 后端：Python 标准库 `http.server.ThreadingHTTPServer` + 单线程 worker 跑任务 + 轮询状态（`/api/start` 启动、`/api/state` 返回 job 快照、/api/stop）
- 前端：单 HTML（无框架），700ms 轮询 state 渲染进度条/统计卡/滚动日志（日志按 count 增量追加，防重复）
- 启动器：`启动上品工具.bat`（`chcp 65001` + `cd /d %~dp0` + `python ...` + errorlevel 提示装依赖）
- Excel 路径经浏览器 `f.path`（Chromium 拖拽/选择都带完整路径）传给后端直接读

## 暗色科技风 UI 基准（用户认可，可复用）

`--bg:#0a0e1a` 深底 + 双 radial 渐变光晕（蓝紫）+ 毛玻璃卡片（`rgba(255,255,255,.04)` + 18px 圆角 + backdrop-filter）+ 主色 `#4f8cff→#7c5cff` 渐变（Logo/主按钮/进度条）+ 分段按钮（选中渐变高亮）+ 3 统计卡（成功绿 `#22d48a`/失败红 `#ff5d6c`）+ 滚动日志（左缘 3px 色条）。视觉模型评估结论：协调/干净/专业。

## 测试与清理模式

- 实测：limit=1 真实提交 → 确认落库（商品 id 返回）→ DB 删测试商品（`ProductImage`→`ProductVariant`→`Product` 三表按 productId 删）
- 保证金拦截：上架被拦时返回平台提示（类目档位→应缴），补缴后重跑即可；草稿不受保证金校验
- 翻译：新商品标题/描述进异步翻译管线（7 语言），详情页多语言稍后生效，不是 bug

## 相关坑

- 服务器跑 node 脚本调平台 API 时：登录必须拿 `gm_session`（`res.headers.getSetCookie()`），`.mjs` 里不能写 TS 类型注解（`as string[]` 会 SyntaxError）
- admin 账号密码曾失效：`AdminUser.passwordHash` 若是占位值（如 "session-auth"）→ 登录恒 401；用 `sha256:salt:hash` 格式（lib/password.ts hashPassword 同款）重置即可，文档密码 Gm2026@root
