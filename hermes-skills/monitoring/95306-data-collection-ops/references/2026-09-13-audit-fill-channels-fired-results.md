# 2026-09-13 XA79 审核补齐三通道实弹结果(回填)

> 上承: `2026-09-12-param-form-corrections-and-new-channel-leads.md`(三通道线索, "未发射")。
> 本文 = 发射结果回填。运行: 主服跳板; 脚本六段拼接(r11m.py = _s1.._s6: A/B/B2/C/C2/C3);
> 产物: /tmp/r11_out.txt, /tmp/r11_roster.json, /tmp/r11b_out.txt。

## 0. 结论速览

- **A 通道命中 ✅**: `startingbiddetailspackage` 传 `id`=项目ID → 全项目包件直出
  (pack_code / 成交-流标 / 起拍价 / 成交价 / **中标供应商名**(未脱敏))。
- **B 通道命中 ✅**: `biddingandsellingsupplier` 传 startDate/endDate 日期窗 → 报名名册
  (企业名+统一社会信用代码+报名时间)。08-20~09-12 窗 11,743 行, 关键词命中 280 行。
- **C 通道结构性负结果**: bidder 族视图 SQL 内嵌 `STATUS='14'` 硬门; XA79 STATUS='31' →
  结构性不覆盖。逐日窗(C2) + 全表(C3) 双重复核 0 命中 = **非抓漏, 勿重扫**。
- 仍缺: "某企业某包=通过/未审批"格 —— 载体在 `bid_package_bidder.STATUS`, 暴露它的视图
  要么带 '14' 门(31≠14), 要么身份列传 NULL。下批: `dictbidpackagebidder` 字典 + 找无门孪生。

## 1. A 通道调用体(可直接发, 实测命中 tot=8)

```json
{"funcId":"startingbiddetailspackage","appId":"system","pageNum":1,"pageSize":50,
 "params":[{"key":"id","value":"3a5a0784-7bd6-4ce5-a855-dc56c23026fe"}]}
```

行字段(节选): `pack_code` / `pack_status`('14'=成交,'22'=流标) / `pack_status_name` /
`base_price` / `outbid_price` / `bidder_name`(中标名) / `bid_starttime` / `gg_pub_time` /
`proj_name` / `proj_code` / `status`(项目状态, XA79='31')。

XA79 实测 8 包件: 001 恒丰盛达 61547.04 / 002 宏达宇 6836.00 / 003 流标 / 004 八方美 65996.70 /
005 流标 / 006 流标 / 007 宏达宇 69348.84 / 008 宏达宇 6052.00。
产物 `xa79_packs_from_A.csv`(全 8 行完整 JSON 见 r11b_out.txt)。

- ⚠️ 双码表陷阱: 该视图取中标名的 join 条件 `bidder.STATUS='22'`(bidder 域=**中标**),
  而 `pack.status='22'` 是**流标** —— 同数值、双码表、语义相反。解读任何 status 前先拉字典
  (`dictbidpackagebidder` / `dict_bid_package_status` / `dict_bid_project_status`)。
- `startingmaterialdetails`(物资明细, 同传 `id`): 本项目返 0 —— 其子查询另有
  `pac.STATUS in('14','22')` 门, 待再验参数/门。

## 2. B 通道调用体 + 名册深扫

```json
{"funcId":"biddingandsellingsupplier","appId":"system","pageNum":1,"pageSize":500,
 "params":[{"key":"startDate","value":"2026-08-20"},{"key":"endDate","value":"2026-09-12"}]}
```

- 窗内 tot=11,743 行; 关键词(项目编号片段/企业名/项目名片段)过滤命中 280 行。
- 79 次项目命中 61 行 → 19 家去重企业, 已回填 `xa79_roster_from_B2.csv`(企业名+信用码+报名时间)。
- 行字段: proj_name / proj_code / bidder_name / un_social_cr_code / buy_time / bulletin_reldate。
- 零值解锁: startDate=0 曾见 967,419 行(全平台); 定向场景用日期窗即可。

## 3. C 通道负结果 + 结构性门地图(最重要教训)

`bid_project` 门族(几乎所有 bid_* 业务视图 SQL 内嵌同一段):

```sql
INNER JOIN (SELECT ID FROM bid_project WHERE VALID_OR='1' AND PROJ_CATEGORY='00' AND STATUS='14'
  AND PROJ_ENDTIME > ${start_time} AND PROJ_ENDTIME < ${end_time}
  UNION ALL
  SELECT p.ID FROM bid_project p JOIN bid_notice n ... WHERE n.PUB_TIME > ${start_time} ...)
```

- 受影响: bid_package_bidder_business23 / b580e32d / bid_room_sign / bid_offer_price /
  req_purchase_supplier_app / 数据汇聚-* 全族。
- XA79 STATUS='31' ≠ '14' → 全部结构性查不到; **调窗口/appId 都没用**。
- 复核(归档, 勿重复): C2 逐日窗 08-23~09-12 每天翻阅, 全 0 命中; C3
  bid_project_business23 全表 54,305 行扫目标 ID, 0 命中。
- 判"查不到"顺序: ①读视图 SQL 门 ②项目 STATUS 实测值 ③再谈窗口/翻页。

## 4. 下批待办

- 拉 `dictbidpackagebidder`(审核状态字典) + `dict_bid_project_status`: 解码 '31' 等全码值。
- 找无门孪生: 13 个引用 bid_package_bidder 的 meta 中, 逐个核对 WHERE 是否带 '14' 门。
- A/B 通道可推广到**任何状态**项目(包括进行中) —— 后续盯守项目的包件/名册补齐优先走这两条。

## 5. 文件与产物位置

- 主服: /tmp/r11_out.txt(A/B/C 全输出) / /tmp/r11_roster.json(名册全量 11,743) / /tmp/r11b_out.txt(A 段 8 行完整)。
- 本地 `mst/`: r11_out.txt, r11_roster.json, r11b_out.txt, xa79_packs_from_A.csv, xa79_roster_from_B2.csv。
- 复跑: 六段脚本按 _s1.._s6 拼接为 r11m.py 上传主服执行; A/B 段=probe_xa79_channels.py 原样, B2/C2/C3 为新增深扫段。
