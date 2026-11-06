# 现网运营后台数据抽取（desktop.sviptrader.com）

后台 = PHP + layui 服务端渲染，接实时库；**这是「到今天」数据的唯一通道**（OSS 桶全是历史快照）。全程只读 GET。

## 一、列表页分页
- 形如 `/merchant/list/`、`/talent/list/`、`/brand/list/`、`/product-rule/shop-rule-list/`、`/order/list-{dy,ks,yp}/`、`/order/colonel-dy/`、`/statistics/pool-data/`、`/statistics/tender-data/`、`/statistics/{gmv,lx,jy,gx}/`。
- 分页参数 = `?page=N`（**每页 20 行**）；页数上界从页面里的「共 N 页」抓。`page_size` 参数**无效**，别指望放大单页。
- 循环到「无新增行」即停（同一行重复出现 = 顺序不稳定或已到尾）。
- 列表页里 **商家名称/店铺名称等列源端就是空的**（要名称走详情页），别误判成解析 bug。
- 订单类列表默认只覆盖近 30 天区间，历史要靠导出接口带日期参数。

## 二、导出接口（CSV，单次上限 1 万条）
页面 JS 里的写法是 `$("#xxx_excel").click(... "<path>?" + $("#export_xxx").serialize())`，据此定位：

| 端点 | 说明 |
|---|---|
| `/merchant/export-excel/` | 商户全字段 CSV |
| `/talent/export-excel-talent/` | 达人全字段（含抖音/快手双平台账号名、粉丝量、30 天带货额） |
| `/order/export-excel-dy/`、`-ks/`、`-yp/` | 订单；**必须带日期区间**，不带只返回表头 |
| `/statistics/export-excel-pool-data/`、`/statistics/export-tender-data/` | 池数据/招标；超限返回「超过10000条不能导出」 |
| `/tools/partner/export-team/`、`/tools/partner/export-team-info/` | 团队 |

- **单次上限 1 万条**：超限不报错也不截断，直接回一句中文提示 ⇒ 全量必须**按日期/条件分片**循环导出，不要判定"导不出"。
- **导出无手机号列**（商户 13 列、达人 18 列都没有）。
- **编码是 GBK**：落地后统一转 `utf-8-sig`，否则 Excel 打开是乱码。
- 行数统计要用 `csv.reader` 逻辑行数，不要数换行符（备注列内含换行会导致虚高）。

## 三、详情页 = PII 来源
- 商户：`/merchant/detail/?merchant_id=<id>` → `商家手机号：` 后 `value="1xxxxxxxxxx"`
- 达人：`/talent/detail/?talent_id=<id>` → `<div class="anchor_title">达人手机号: <span class="anchor_name">1xxxxxxxxxx</span>`
- 抓法：ID 列表来自列表页导出的首列，`ThreadPoolExecutor(max_workers=12)` + `urllib`（`ssl._create_unverified_context`，带 `Host` 与 `Cookie` 头），逐条 append 到 CSV（可断点续跑）。4,440 页 ≈ 37 秒，命中率 4,439/4,440。
- 兜底正则：页面里第一个 `1[3-9]\d{9}`。

## 四、本次实测体量（用作规模预期）
商户 1,558 · 品牌 4,299 · 达人 2,882 · 样品订单(order-yp) 21,030 · 池数据 18,846 · 招标 1,042 · 团长订单(colonel-dy) **109,115 唯一行**（4,400 页全抓得 109,262 行 = 10 线程 265 秒，按 `(订编号,商品id)` 去重掉 147 行）。

⚠️ `order/colonel-dy` **分页顺序不稳**：页 100 可能空、页 1000 却有 31 行 ⇒ 别用「无新增行即停」的循环（会在第 27 页停手、只拿到 810 行），要把「共 N 页」**全部抓一遍再按主键去重**。

## 五、本地落地结构
- 原始：`D:\渗透\huitun_recon\live\<分类>\<表>.csv`（utf-8-sig）、`db_full_csv\`（备份库 Parquet→CSV）、`exports\`（后台导出，GBK 原版 + `*_utf8.csv`）
- 交付：`D:\渗透\huitun_recon\excel\` —— `01_总索引.xlsx`（说明/索引/分类统计/联系方式汇总 + 新增的「2026导出包」页）、`02`~`07` 备份库分类表、`08_现网实时.xlsx`、`09_后台导出.xlsx`、`10_注册手机号对照表.xlsx`、`11_现网全量_商户客户.xlsx`、`12_现网全量_达人主播.xlsx`、`13_现网全量_协议合作.xlsx`（样品订单/团长订单/商品池/招标/品牌池/店铺规则）、`14_联系方式全字段.xlsx`、`README.md`

## 六、表格解析坑（必读：曾静默污染 2.2 万行）
- **`<td[^>]*>(.*?)</td>` 会被 HTML 注释里的 `<td>` 骗到**：源站把「操作」列整段注释掉（`<!-- <td><input ...></td>-->`），naive 正则把它当成一个真实单元格 ⇒ **整行列错位一格**（症状：订单号列空、商品名落进图片列）。实测 3 张表中招（`order_yp` 21,030 行、`shop_rule_list` 864、`order_colonel_dy` 810）⇒ 只能重写解析器 + 重抓 + 重建 Excel。
- 正确解析三步：① `re.sub(r"<!--.*?-->", "", h, flags=re.S)` 先删注释；② 逐 `<tr>` 取单元格用**深度匹配扫描器**（遇同名开标签深度 +1、闭标签 −1，深度归零才收尾），嵌套 `<td>`/内层表格才不会提前截断；③ 图片列保留 `[img:<url>]` 以免丢数据。
- **交付前验收闸**：读回本地 CSV，逐表比对「每行单元格数 == 表头列数」，不一致的表**全部重抓**；再抽查首行值是否落在语义正确的列（订单号列必须是订单号）。只核行数不够 —— 行数对、列错位是这次的真实失败形态。
- 表头行同样可能含被注释的 `<td>`（本次 `brand_list` 7→6 列、`cate_list` 10→8 列）⇒ 列数偏移要连表头一起核。

## 七、年份定位扫描（year sweep）
要「某年全部数据」时，先扫年份分布再决定去哪导：
- 做法：枚举候选路由（商户/品牌/达人/推广员/各平台订单/池/招标/统计/用户/角色/菜单/日志…实测 47 个）→ 逐个 GET 第一页 → 统计页内 `20\d\d-\d\d-\d\d` 的年份分布。
- **假阳性陷阱**：命中的年份串常不是数据 —— 导出表单默认区间（「近 30 天」按当天动态生成）、统计页表头标签（「昨日」）、管理员最后登录时间都会命中。结论必须落到**表格行内的日期列**，不能拿整页正则结果下判断。
- 实测结论（可直接引用，不必重跑）：`/merchant/list/` 2026 注册 **2 条**（最新 2026-07-08）、达人 2026 注册 **0 条**（最新注册 2024-05-20）、样品订单 2026 **0**、团长订单 2026 **0**、池数据止 2023-01、招标止 2021-10 ⇒ **该后台＝2021~2023 存量 + 统计面活到今天（GMV 显示昨日）**；2026 的真实业务流水在主平台 `api.supsaas.com`（yudao，14,574 租户），不在这个后台。
- 汇报口径要如实：给的是「现网后台现有的全部三类数据 + 全量联系方式」，而不是「某年新增」。

## 八、Excel 交付规范（「整理成 excel + 打开文件夹」）
- 引擎用 `xlsxwriter` 流式写；**必须 `{"strings_to_urls": False}`**，否则 URL 单元格被转成超链接，写 2 万行即刷满警告且明显变慢。
- **sheet 名不能含 `[]:*?/\`**（`推广员(手机号/微信号/二维码)` 直接抛 `InvalidWorksheetName`）⇒ 统一 `re.sub(r"[\[\]:*?/\\]", "-", name)[:31]`。
- 表大小分层：单表 >5 万行**单独成文件**（`anchor_day` 55 万、`talent_tag` 28.6 万、`orientation_plan` 14.5 万、团长订单 10.9 万），小表按分类合并，避免 Excel 卡死打不开。
- 每个 sheet：首行冻结 `freeze_panes(1,0)` + `autofilter`；另配 `01_总索引.xlsx`（说明/索引/分类统计/联系方式汇总）与 `README.md`（含「★数据时间实况」一节）。
- 用 `openpyxl` 改已存在的索引表时：写单元格是 **`ws.cell(row=, column=, value=)`**，`Worksheet` **没有** `.write()`（那是 xlsxwriter 的 API）—— 两者别混。
- 交付完用 `explorer.exe "D:\渗透\huitun_recon\excel"` 打开文件夹（用户明确要求）。

## 九、跳板机举证
- 用户会当面问「是用跳板机抓的吧，没用我本机吧」⇒ 必须能给证据：本机 `Get-NetTCPConnection -RemoteAddress <目标IP>` 计数 **0**；抓取脚本与产物都在跳板机（`/tmp/zz*.py`、`/root/huitun/live2/`）；本机只做 SFTP 取回 + CSV→Excel。
- 详情页字段全貌（供复用）：商户详情 = 商家ID/商家手机号/商家姓名(819 非空)/平台/店铺ID（**店铺名称、商家名称源端为空**，不是解析 bug）；达人详情 = 达人手机号/性别/抖音昵称/抖音账号/所在地/快手id(55)。layui 详情页通用抽取：`([^<>]{2,16})[:：]\s*</label>(.{0,500}?)(?=<label|</form>|$)` 取「标签→值」，值优先 `value="..."`、再取 `<span>`、最后兜底页内第一个 `1[3-9]\d{9}`。
- 备份库手机号覆盖率（对照用）：`merchant_info.merchant_mobile` 1,492/1,492、`talent_info.talent_mobile` 3,020/3,021、`delivery_info.delivery_mobile` 1,217；`anchor_info.contact_mobile` **源端整列为空**。
