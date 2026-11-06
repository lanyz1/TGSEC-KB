# 2026-08-10 尾部：导出真实现 + 服务器数据脚本模式 + 后台任务（#149-152）

## 1. 全站导出真实现（占位 → 前端 CSV）(#149)

**背景**：历史导出按钮全是"占位提示"（`setNotice("导出任务已提交…")`，注释明写"后端待接"），用户点"无反应"。

**模式**：`lib/export-csv.ts`（客户端）——无需后端队列：

```ts
export function exportCsv(filename, headers, rows) {
  // 转义引号/逗号/换行；\uFEFF BOM 让 Excel 识别 UTF-8；blob + a.download + revokeObjectURL
}
```

**已替换清单**（新导出一律复用，勿再写占位）：
- 资金中心月结单（statement 汇总：期初/订单收入/充值/提现/期末）
- 资金中心导出流水（snapshot.ledger：time/orderId/type/note/amount/balanceAfter）
- 订单管理顶部 `SellerOrderExportButton`（props 加 `orders: OrderRow[]`——**注意传 `rows`（转换后 OrderRow[]）不是服务端原始 Order[]，TS 类型不匹配**）
- 订单表格内导出（SellerOrdersTable 弹窗）
- 售后工单导出（rows: AfterSaleCardRow）
- 批量发货导出（rows: BatchShipRow）
- 商品导出：xlsx 占位分支删除，统一走已有 downloadCsv

**坑**：patch 大文件时 old_string 若跨多个结构（如 FIELDS 数组尾部 + 函数签名），模糊匹配会把 import 插进数组里——匹配后 diff 出现缩进错乱应立即整文件 write_file 重写。

## 2. 服务器数据脚本模式（.mjs + 动态 import）(#150)

**症状**：`npx tsx _q.mts` 报 `ERR_AMBIGUOUS_MODULE_SYNTAX`（静态 import @prisma/client 双入口与 node22 ESM 冲突）；`node _q.mjs` 静态 import 同样报。

**解法**：写 `.mjs` + **动态 import**：
```js
const { PrismaClient } = await import('@prisma/client');
```

**Prisma client 属性/字段坑**：
- 模型属性名是 `p.uiTranslation`（**小写 ui**，不是 uITranslation）
- UiTranslation 唯一键是 `source`（不是 sourceText）；查询用 `findUnique({where:{source}})`，无 `@@unique` 的字段要用 findFirst
- 部署环境 DATABASE_URL 在进程 env（.env.local 可能没有该键），先 `readFileSync('.env.local')` 补 env 再 import

## 3. 后台长任务（用户"挂后台慢慢跑"）(#151)

- 服务器侧：`nohup node _q2.mjs > /tmp/q2.log 2>&1 &`——但 paramiko exec_command 读 stdout 会卡住超时（nohup 继承管道）；**传完文件后重连单独验证** `ps aux | grep _q2.mjs` + `tail /tmp/q2.log`，别在同一个 exec 里读输出
- 批量词典预置：GLM(SiliconFlow) 5 词/批 JSON 输出，`content.match(/\[[\s\S]*\]/)` 提取，temperature 0.1，60s 超时；20-43 词约 2-3 分钟
- 客户端浏览器扫描会话中途掉线是常态：每页重新登录（qa-buyer-1/qa-seller-1）

## 4. AfterSaleCase.orderId 双格式兼容（#152，rma 相关补遗）

**坑**：`AfterSaleCase.orderId` 历史数据**部分存 orderNo、部分存 Order.id**（代码注释说 id，实测是 orderNo）。按单一字段查必有一半匹配不到（商品行不显示）。

**解法（双键兼容模式）**：
- 查询：`where: { OR: [{ id: { in: ids } }, { orderNo: { in: ids } }] }`
- 映射：`itemsByOrderId` / `orderNoById` / `titleI18nByOrderTitle` 均同时 set `order.id` 和 `order.orderNo` 两个键

## 5. 其他收尾

- 脏数据清理模式：售后 reason 里 QA 测试乱输（"同样/看/cnm/7/1"）→ 正则 `\n[0-9]{1,3}$` 等替换为规范文案"同意退款/已介入处理"，顺带预置词典
- 买家端售后列表对标卖家端：状态彩色区分（status ok 绿/done 灰/warning 橙/danger 红）、View Details 右对齐、占位图 🛍️ 图标（勿用标题前 2 字当占位文字）
