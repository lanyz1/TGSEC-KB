# 2026-08-10 词典批量预置 + 第三批分页 + 消息链接 + 溢出扫描（#154 之后的批次）

## 1. 服务器 node 脚本批量词典预置（实操模板）
- 传输：paramiko 上传 `_q.mjs` → `cd /www/tiktok && node _q.mjs 2>&1 | head -N; rm -f _q.mjs`
- 脚本头必须手动注入 env：`readFileSync('.env.local')` 逐行 `process.env[k]=v`（服务器 psql 不通，一律走 Prisma）
- **必须动态 import**：`const { PrismaClient } = await import('@prisma/client')` —— 静态 import 报 `ERR_AMBIGUOUS_MODULE_SYNTAX`（@prisma/client 双入口与 node 22 静态 ESM 冲突；tsx 也有同类问题，直接 node + 动态 import 最稳）
- **Prisma client 属性名 = `p.uiTranslation`**（小写 ui！写 uITranslation 是 undefined → "library.js 抛错"假象）
- **UiTranslation 唯一键 = `source`**（findUnique where:{source}；字段不是 sourceText！findFirst 也不行）
- i18nJson 结构：`{ en, es, fr, pt, ru, ar, "zh-CN": 原文 }`
- 批量翻译：SiliconFlow `THUDM/glm-4.5-flash`，一次 5 词/批，prompt 要求严格 JSON 数组 `[{src,en,es,fr,pt,ru,ar}]`，temperature 0.1，`AbortSignal.timeout(60000)`；20 词约 2.5 分钟、43 词约 3-5 分钟
- **长任务挂后台**：`nohup node _q2.mjs > /tmp/q2.log 2>&1 &` —— 注意 paramiko exec_command 直接跑 `nohup ... &` 会因 stdout 管道不关而**卡到 timeout**（脚本其实已启动）；挂完**重连验证**：`ps aux | grep _q2.mjs` + `tail /tmp/q2.log`
- 词库词条数：本次两批 20+43 词 0 失败；UiTranslation 累计 130+ 条

## 2. translations.ts 插键（语言区锚点法——防"7 键挤一处"）
- **错误示范**：7 语言循环 `re.sub` 同一锚点 → 每次 search 都命中第一个匹配 → 7 个键全插在同一语言区 → JSON 重复键后覆盖前，所有语言显示最后一个值（灾难）
- **正确**：每语言区用**该区特征值**定位锚点行（如 `seller.funds.wallet.feeBase`：es="Tarifa de retiro" / fr="Frais de retrait" / en="Withdrawal fee"），在锚点行后插入该语言值；完成后 `grep -c '"键名"'` 验证 = 语言区数
- zh 区已有键时跳过；**ar 区没有 seller.nav.* 键**（历史遗留，ar 界面侧栏为中文，非本轮引入——不要花时间找 ar 锚点，找不到就接受）
- 本会话实例：① availableNote2 只有 zh 区（11200 行）→ 5 区补齐（含 availableNote 带 `{num(...)}` 变量的键，翻译时保留占位）② 订单 filter 键：shipping/done 6 区改单值 + 新增 received/closed 6 区（同锚点行内连插两键）

## 3. 第三批长列表分页（PaginationBar 复用，组件在 components/seller/PaginationBar.tsx）
- **卖家订单**（服务端组件）：searchParams 类型加 `page`；`ORDER_PAGE_SIZE=20`；`rows`（全量）用于导出，`pageRows`（切片）传给表格；分页条 Link 带 `baseQuery`（status+q 保留）；页码统计 `safeOrderPage / orderPages 页`
- **★searchParams Promise 只 await 一次**：`const { tab, page } = await searchParams`；再 `(await searchParams).page` 会错（Promise 已消费）
- **售后工单**（client 组件 SellerAfterSalesList）：listPage state + `pagedRows` 切片只影响显示；**批量勾选/批量操作基于全量 rows**（翻页不丢勾选）；PaginationBar 放列表后、导出弹窗前
- **买家收藏**（服务端 /favorites）：URL 分页；**联合类型要拆两个切片变量**（`pagedProducts`/`pagedStores` 分开 slice，一个 `pagedFavs` 传两处会 TS2322）
- **JSX 兄弟元素坑**：`{cond ? (<table>…</table><PaginationBar/>) : null}` 必须包 `<>...</>`（TS2657）—— 加 PaginationBar 时最容易踩
- 既有分页确认不用改：买家订单（10/页）、买家资金记录、卖家资金中心 5 列表（上批）

## 4. 消息商品卡片链接角色分流（卖家端 404 修复）
- 原 ChatWindow MessageCard 写死 `/products/${id}`（买家端商品页）→ 卖家视角下架/删除商品 → 404
- 修复：MessageCard 加 `role: ChatRole` prop（原组件签名没有 role，须从 ChatWindow 两处 `<MessageCard>` 调用传入）；`role === "seller" ? /seller/products/${id} : /products/${id}`
- 买家消息列表页与聊天窗共用 MessageCard，一处修复两边生效

## 5. 切语言布局溢出扫描方法（"框超出背景"排查）
- 浏览器**切 ar**（文本最长最易溢出）→ 等 ~15s 翻译 → 检测：`document.documentElement.scrollWidth > clientWidth`（文档级横向滚动）+ `[...document.querySelectorAll('body *')].filter(el => el.scrollWidth > el.clientWidth + 8 && el.scrollWidth > 300)`（元素级）
- 实测 7 页面（主页/订单/资金/详情/消息/购物车/登录）doc 均无横向滚动；元素级 3 类：
  - `.market-product-title`（**两处 CSS 定义** 1412 与 7656）→ `display:-webkit-box; -webkit-line-clamp:2; overflow:hidden`
  - `.ftb-badges`（支付渠道条）nowrap → `flex-wrap: wrap`
  - `.lst`（ChatList 会话预览文本，**CSS 完全没定义** → 默认不截断）→ 加 `overflow:hidden; text-overflow:ellipsis; white-space:nowrap`
- **★CSS 同名类 patch 第二处必错位**：old_string 只写类名首行会匹配到第一处；patch 后旧属性悬空残留 → **改完必须 read 检查上下文 + 删残留**（本会话踩 2 次）

## 6. 全站导出真实现（假占位清理，lib/export-csv.ts）
- 历史 6 处"导出任务已提交，完成后可下载"全是假实现（代码注释明写"后端待接"）→ 用户报"点击无反应"
- `exportCsv(filename, headers, rows)`：BOM + blob + a.download（Excel 中文不乱码）；文件名带日期
- 接入：资金月结单（statement 汇总行）/资金流水（snapshot.ledger 全量）/订单（表格内 + 顶部 SellerOrderExportButton）/售后（rows）/批量发货（rows）/商品（删 xlsx 占位分支统一 CSV）
- **导出组件要数据**：SellerOrderExportButton 加 `orders: OrderRow[]` prop；调用处传**服务端转换后的 rows**（OrderRow[]），传原始 Order[] 会 TS2322（缺 displayStatus/statusTone 等 7 字段）

## 7. 卖家端侧栏功能区重构（PortalShell sellerNavGroups）
- 店铺运营：工作台-入驻资料-通知中心（顺序）；客户服务只留售后工单+买家消息；资金管理只留资金中心（余额划转页保留、仅导航隐藏）；**新增分组"设置与开发"**（账号设置+反馈与建议）
- 新分组标题键 `seller.nav.settingsDev` 按 §2 锚点法 6 区插入；键值 en="Settings & Development"
- patch 大段 JSX 若错位（import 插进数组）→ **write_file 整文件重写**（用户偏好整文件重写非补丁）
