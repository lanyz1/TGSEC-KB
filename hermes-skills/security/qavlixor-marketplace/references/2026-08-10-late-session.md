# 2026-08-10 晚场：批量操作删除/导出真实现/分页补全/订单筛选拆分/溢出扫描/消息搜索

## 全站导出"占位"→真实现（用户报"点击无反应"）
- 6 处导出全是假实现（setNotice"任务已提交"占位，注释明写"后端待接"）：资金月结单PDF/资金流水/订单(顶部+表格)/售后/批量发货/商品xlsx
- 统一方案：`lib/export-csv.ts` exportCsv(filename, headers, rows)——前端 Blob + a.download + \uFEFF BOM（Excel 中文不乱码）
- 涉及：SellerFundsCenter(月结单/流水)、SellerOrdersTable、SellerOrderExportButton(props 加 orders: OrderRow[]；调用处传**转换后的 rows** 而非原始 Order[]，否则 TS2322)、SellerAfterSalesList、SellerBatchShipList、SellerProductManager(xlsx 占位分支删除统一走 CSV)
- 教训：UI 按钮"看起来有功能"但后端没接 = 用户报"没反应"，先 grep "已提交/占位/后端待接" 定位

## 长列表分页（复用 components/seller/PaginationBar.tsx）
- 前端切片模式：资金中心 5 列表（财务流水20/提现10/保证金10/冻结10，tab 切换重置 page）；售后 10
- URL 服务端分页模式：卖家订单 20（searchParams page + baseQuery 保留 status/q + 表格用 pageRows、导出用全量 rows）；买家收藏 20（商品/店铺两 tab 分开切片避免联合类型）
- 已有分页不动：买家订单列表(10)/买家资金记录
- 注意：多个兄弟 JSX 元素必须包 Fragment（frozen tab 踩 TS2657）

## 订单状态筛选拆分（"运输中+已收货""已完成+已关闭"合并→分开）
- 7 tabs：全部/待发货/运输中/已收货/退款售后/已完成/已关闭；matchesOrderFilter 单状态匹配
- 翻译键：6 语言区 shipping/done 键值从合并名改单项名 + 新增 received/closed 键（脚本按"键值"锚点改+插，每区 2 处共 12 处）
- displayStatusOf 状态标签本来就是分开的（运输中→待收货/已签收→已收货），只有筛选合并

## 买家端切语言布局溢出扫描法（用户报"框超出背景"）
- 浏览器实测：切 ar（文本最长）→ 等翻译 15s → 遍历 `document.querySelectorAll('body *')` 找 `el.scrollWidth > el.clientWidth + 8 && el.scrollWidth > 300`
- 实测 7 页面 doc 均无横向滚动（docSW=docCW），只有元素级溢出 3 处：market-product-title line-clamp 2 / ftb-badges flex-wrap:wrap / .lst ellipsis
- ★market-product-title 在 globals.css 有**两处**定义（1412 + 7656），只改一处不生效；第二处 patch 时 old_string 只写 2 行会被 fuzzy 错配（见下）

## 售后批量操作删除（用户拍板"两个都删"）
- 批量同意退款/批量升级平台 + 批量栏 + 勾选框 + runBulk/selected/actionableRows 全删；导出按钮单独右上保留；分页保留
- 单条"处理工单"面板里仍有升级平台仲裁选项（批量只是删列表入口）

## 风险店铺 UI 删除（用户"删掉就行"）
- 管理端店铺管理：风险筛选下拉/风险列/编辑行风险下拉/riskClass 函数；详情页风险等级/riskLabel 函数
- DB riskLevel 字段保留不动（只删界面）

## 消息搜索买家昵称无结果
- 根因：conversation.buyerName 存量存的是邮箱；peerName 用 User.displayName 纠正（已有逻辑），但搜索只匹配 peerName → 昵称搜不到
- 修复三层：ChatSummary/ChatConversationSummary 加 buyerEmail 字段 + ChatList 搜索匹配加 item.buyerEmail + DB 回填 buyerName=邮箱→displayName（9 条）
- ★会话显示正常 ≠ 搜索正常：显示字段和搜索字段要分开验证

## ★词典批量预置脚本（服务器后台跑）
- 静态 import '@prisma/client' 报 ERR_AMBIGUOUS_MODULE_SYNTAX（双入口冲突）→ 必须 `const { PrismaClient } = await import('@prisma/client')` 动态 import
- Prisma 模型属性名是 `uiTranslation`（不是 uITranslation）；唯一键是 `source`（不是 sourceText）→ findUnique({where:{source}})
- 翻译通道：SiliconFlow + GLM，5 词/批，temperature 0.1，prompt 要求严格 JSON 数组 {src,en,es,fr,pt,ru,ar}，正则 `content.match(/\[[\s\S]*\]/)` 提取
- 大批量挂后台：`nohup node _q.mjs > /tmp/q.log 2>&1 &`——★paramiko exec_command 读 stdout 会卡死超时（后台进程继承管道），但脚本实际已启动；用 `ps aux | grep _q.mjs` 验证
- 60 条高风险裸中文由 delegate_task 静态扫描产出（排除 data-i18n/t()/逻辑比较串/translations.ts），T0 拼接词（已/待/未/共/第+）最优先；全量 1773 条存 cache/qavlixor_scan.json

## ★★插键脚本陷阱：pat.search 每次从 src 开头找"第一个匹配"
- 同一键名锚点会 7 次都插在**同一位置** → 对象重复键后者覆盖前者 → 所有语言返回同一个值（灾难）
- 正确：按"语言区键值"定位锚点（各语言区键值不同，如 feeBase 的 es/fr/pt/ru/en 值各不相同），插入后 grep 验证键计数 = 语言区数
- memory 早有"插键按语言区锚点值定位"——本次踩坑证实原因：键名锚点必然全插第一处

## ★patch fuzzy 错位 3 例（删除函数/块后必须立即 read_file 验证）
1. CSS 第二处定义：old_string 只写开头 2 行 → fuzzy 匹配到错误位置，残留内容插进新块（悬空属性）
2. 删 riskLabel 函数：old_string 含相邻函数名 → 替换后 statusLabel 行重复
3. SellerOrderExportButton：patch 把 import 插进字段数组中间（缩进全乱，最终 write_file 重写）
- 规律：patch 删除/替换大块时 old_string 要含完整上下文（函数签名+完整函数体），替换后立刻读文件验证语法；结构乱套时直接 write_file 整文件重写

## 买家端售后(rma)列表商品行不显示——★orderId 双格式兼容
- 现象：卡片有 orderId 显示但商品行（图/名）不渲染；vision 显示"右侧松散/占位图难看"
- 根因：AfterSaleCase.orderId 历史数据存的是 **orderNo**（19 位数字），代码按 Order.id（cuid）查 → findMany 查空 → itemsByOrderId 空
- 修复：查询 `OR: [{ id: { in: ids } }, { orderNo: { in: ids } }]`；映射双键（order.id + order.orderNo）；titleI18nByOrderTitle 键 `${order.id}::${title}` 和 `${order.orderNo}::${title}` 双份；详情页 findUnique→findFirst OR
- 顺带对标修复：状态标签彩色区分（statusClass ok=绿/done=灰/danger=红/warning=橙 + CSS .status.ok/.done）、占位图改 🛍️ 图标（font-size 22px，不再截标题前2字）、标题 line-clamp 2、View Details 右对齐、语言切换器图标"文"→🌐

## 其他
- 运费模板复制功能删除（按钮+openCopy 函数，键留着无害）
- "已Agree退还"类拆翻混合：整句词典预置（已同意退还/同意退款/退款原因等），强刷生效无需部署
- 脏数据清理：售后 reason 里商家乱输的"同样/看/cnm/7/1"批量替换为规范文案（同意退款/已介入处理）
