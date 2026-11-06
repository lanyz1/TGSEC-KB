# 2026-08-10 资金分页 / 全站导出真实现 / 键缺语言区排查 / 售后批量状态限制

## 资金中心长列表分页（用户："一长串太长，每页10或20条"）
- `components/seller/PaginationBar.tsx` 通用分页条（页码统计 + 上一页/下一页，不足一页不渲染）
- `SellerFundsCenter.tsx` 接入 5 处：财务流水（overview + ledger 两个 tab）20 条/页（PAGE），提现记录/保证金流水/冻结明细 10 条/页（SMALL_PAGE）
- 4 个 page state + `useEffect(initialTab)` 切换 tab 重置 page=1
- 坑：frozen tab 原来是单元素三元，加 PaginationBar 后变兄弟元素 → 必须包 `<>...</>`（TS2657）
- 买家端资金记录页本来就有分页（fundRecords.slice），不用改

## 全站导出真实现（用户："导出点击无反应，是不是没配置"）
- 真相：之前全部是占位假实现（onClick 只 setNotice"任务已提交/后端待接"，注释明写），用户点"无反应"
- `lib/export-csv.ts`：exportCsv(filename, headers, rows) 前端生成 blob + a.download（BOM \uFEFF 防 Excel 乱码）
- 已接入 6 处：资金月结单（statement 汇总行）/资金流水（ledger 全量）/订单导出×2（顶部 SellerOrderExportButton + 表格 SellerOrdersTable，行=订单×商品拍平）/售后工单（AfterSaleCardRow）/批量发货（BatchShipRow）/商品导出（xlsx 占位分支删除统一 CSV）
- 商品导出原本 CSV 是真实现（downloadCsv），只有 xlsx 分支占位 → 删分支即可
- 坑：SellerOrderExportButton 原 props 只有 filteredCount/totalCount → 加 orders: OrderRow[]，orders 页传 rows（OrderRow 转换后的，不是原始 Order[]——TS2322）

## 翻译键缺语言区排查（用户："XX 不走翻译系统"）
- 症状：data-i18n 键切语言不翻 = 该键只在 zh 区有值，其他语言区缺失（getTranslation 返回 undefined → 不替换）
- 排查：`grep -c '"键名"' lib/translations.ts` < 6 → 缺区（en/es/fr/pt/ru/zh 六区；ar 区已删 2026-08-10）
- 修复：按语言区锚点插入——用该语言区已有的相邻键值定位（如 `seller.funds.wallet.feeBase` 的 es/fr/pt/ru/en 值各插一次），**勿用同一锚点循环 search（全插一处 → 键重复后者覆盖）**
- 实例：seller.funds.wallet.availableNote/availableNote2 原只有 zh 区 → 补 5 区（availableNote 含 {num(...)} 变量占位，翻译保留原样）

## 售后批量按钮"无法点击"（用户问为什么有这按钮）
- 批量同意退款/批量升级平台按钮 enabled 条件：仅 status="商家处理中" 且未 locked（selectedActionable 过滤）
- 用户勾选已退款/已关闭/平台介入的工单 → 按钮禁用是状态限制，不是 bug
- 批量升级平台：单条处理面板已有升级选项，批量场景少 → 用户质疑后建议删除（用户未最终拍板删哪些）

## 拆段翻译混合的整句预置（治标方法论）
- 症状："已Agree退还"/"Refund原因：Quality issue 同样" = 短词拆段翻译拼接 + 单字残留
- 治法：整句预置 UiTranslation（source 唯一键，i18nJson 7 语言 en/es/fr/pt/ru/ar/zh-CN），词典命中优先整串替换不拆
- 批量：GLM 5 词/批 prompt（严格 JSON 数组 {src,en,es,fr,pt,ru,ar}）+ findUnique/update/create upsert；长任务 nohup 挂服务器后台（`nohup node _q.mjs > /tmp/q.log 2>&1 &`）
- 后台扫描方法：delegate_task 子代理 grep 全站裸中文（无 data-i18n），按 T0 拼接词（已/待/未/共开头 2-4 字）> T1 按钮词 > T2 组合词排序；逻辑比较串（status === "已上架"）不渲染不可预置替换
- 服务器 node 脚本坑：静态 `import { PrismaClient } from '@prisma/client'` 报 ERR_AMBIGUOUS_MODULE_SYNTAX → 用动态 `const { PrismaClient } = await import(...)`；client 属性名 `uiTranslation`（小写 ui）；where 用 `source`（唯一键），不是 sourceText
- 词典操作勿动逻辑比较串（=== 字符串），否则改词典替换会断逻辑
