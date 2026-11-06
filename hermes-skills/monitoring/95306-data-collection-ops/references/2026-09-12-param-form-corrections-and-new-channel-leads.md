# 2026-09-12 审核补齐: 参数形态勘误(缺数据第四查) + 三条新通道线索 (西安79次案例)

> 上承: `2026-09-12-audit-detail-fill-mechanics.md`(缺口标准答法/机制)、`2026-09-12-watch-xa79-and-final-sweep.md`(盯守+公开面终验)。
> 类级对照: lowcode-dataplatform-pentest `2026-09-12-rescan-zero-unlock-and-b580e32d.md`(零值解锁/全表负结果/b580e32d 调用矩阵)。

## 0. 状态快照(09-12 16:00Z 主服实测)

- XA79(pid `3a5a0784-7bd6-4ce5-a855-dc56c23026fe`): 19 家去重 × 8 包 = 152 格, **51 格有值**。
- watch_xa79: st32 399→416, **filled=0**(全天) — 416 ST + 291 JWT 票池与 19 家账号逐一对账, **0 命中**(池内没有目标企业的新票)。
- audit_harvest: pool_st=416 / pool_jwt=442→291; 14:00 后 new_st=0(收割器在跑, 只是无新票)。
- priv 特权池: 185 条 / 23 alive, 端点矩阵 hits=[](功能权限门挡, 约半数 HTTP502)。
- 结论不变: 补全 = ①企业会话(登录即刷) ②内部/采购方会话 — 两源当前均空; 同时找**参数用对后**的新通道(本文件)。
- 8 个包件ID(扫描/对账用, uuid 前 8 位): `6fc6c9a4` `f40eed84` `94ee82f2` `dcd27e6c` `90e237f8` `16611220` `5beb3fda` `6913326d`。

## 1. 勘误: 参数形态被忽略 → 多张 meta 的"0 行"可能是假阴性

**教训(第四查)**: 判"该 meta 无数据"前, 先从 `sysmeta.content` 提取声明参数(`\$\{(\w+)\}` 占位符), 按声明逐参测试。
用通用 startDate/start_time 两形态轮试就下"0 行"结论的 meta, 本平台至少 3 处踩过:

- `startingbiddetailspackage` / `startingmaterialdetails`: 声明参数 = **`id`(项目ID)** — 此前只被 start/end 形态探过(得 0), **从未用 id 打过**。
- `biddingandsellingsupplier`: 声明 `startDate/endDate`(日期形态); 零值解锁 967,419 行(详见 rescan ref §3)。
- `materdisposalinfo` 家族(+ materPriceSharing / packagedisposalinfo / *bureau/zd): 声明含 **`packstatus`** —
  SQL: `IF(''=${packstatus},pack.status IN('14','22'),pack.status=${packstatus})` → 直接传值可绕 14/22 门("换锁不换表")。
- 修订提示: `2026-09-12-watch-xa79-and-final-sweep.md` 里"报表族 ×3 参数形态全 0 → 不可用/无覆盖"的结论, 据此改为**待复测**(声明参数未含于 3 形态)。

## 2. 引用 bid_package_bidder 的全 13 meta = 审核数据渠道地图(q271 枚举原文)

| meta | 声明参数 | 备注 |
|---|---|---|
| materdisposalinfo | endDate,jointSaleTypes,level,**packstatus**,payTypes,platformId,startDate | 物资统计报表 |
| materPriceSharing | endDate,jointSaleType,packstatus,payType,startDate | 价格共享报表 |
| materdisposalinfobureau / -zd | + dwdm | 路局变体 |
| packagedisposalinfo / packagedisposalinfobureau(-zd) | dwdm,endDate,jointSaleType,level,packstatus,payType,platformId,startDate | 包件统计 |
| b580e32d-7967-4330-a016-767a19cca90e | end_time,start_time | 「竞价参与表」= 孪生名 bid_package_bidder_business23; uuid 直调=不存在的功能 |
| startingmaterialdetails | **id** | 起拍物资明细 |
| startingbiddetailspackage | **id** | 起拍包明细 |
| biddingandsellingsupplier | startDate,endDate | 报名名册(企业名+信用码+报名时间) |
| "select if(...)" ×2 | — | metaid 本身是 SQL 片段(坏), 调=不存在的功能 |

## 3. 三条新通道(证据在手, 待实测 — 未发射)

### 3.1 startingbiddetailspackage / startingmaterialdetails — 按项目ID直查

SQL 关键段(meta content 原文, 直读 `bid_package_bidder`):
```
LEFT JOIN (select pack_id,BIDDER_NAME from portal_service_business_bid_package_bidder bidder
           where bidder.`STATUS` = '22' and VALID_OR = '1') bpbi on bpbi.PACK_ID = pac.id   -- 中标单位
...
and bid.id = ${id}
```

调用体(可直接发):
```json
{"funcId":"startingbiddetailspackage","appId":"system","pageNum":1,"pageSize":50,
 "params":[{"key":"id","value":"3a5a0784-7bd6-4ce5-a855-dc56c23026fe"}]}
```
- 期望产出: 每包 状态/成交价/**中标单位名**(STATUS='22')。同族 `startingmaterialdetails` 触发前先读全 SQL(可能带额外硬门)。

### 3.2 biddingandsellingsupplier — 名册(身份钥匙, 无状态)

- 声明 startDate/endDate; 零值解锁 967,419 行(q271: win=8272 / zero=967419)。
- 行含 `bidder_name` + `un_social_cr_code` + `buy_time`(无 pack_id / 无审核状态)→ 拼图源("谁")。

### 3.3 materdisposalinfo 家族 packstatus — 换锁不换表

- 传 `packstatus` 指定包状态; 家族 6 变体同构, 可选 platformId/dwdm/level 组合。待组合日期窗实打 XA79。

## 4. b580e32d「竞价参与表」完整 SQL(09-12 提取, 供复核与后续变体测试)

```sql
SELECT RATINGLEVEL, PACK_ID, NULL AS BIDDER_NAME, NULL AS SINGLE_PRICE_LIST, NULL AS HEREOR,
 NULL AS CHECK_PEOP, NULL AS PERSON, ISBLACKLISTSTATE, UUID, b.ID, NULL AS DWCODE, NULL AS CURRENT_PRICE,
 STATUS, BUY_TIME, HEREOR_TIME, NULL AS PHONE, BADNOTESTATUS, PROJ_ID, NULL AS BIDDER_ID,
 CURRENT_PRICE_TIME, MEMO, CHECK_TIME, VALID_OR, NULL AS ADDRESS
FROM bid_package_bidder b
INNER JOIN (
  SELECT ID FROM bid_project WHERE VALID_OR='1' AND PROJ_CATEGORY='00' AND STATUS='14'
    AND PROJ_ENDTIME > ${start_time} AND PROJ_ENDTIME < ${end_time}
  UNION ALL
  SELECT p.ID FROM bid_project p JOIN bid_notice n ON n.proj_id=p.ID
   AND n.notice_type='09' AND n.VALID_OR='1' AND p.STATUS='22' AND p.VALID_OR='1' AND p.PROJ_CATEGORY='00'
   WHERE n.PUB_TIME > ${start_time} AND n.PUB_TIME < ${end_time}
) a ON a.ID=b.PROJ_ID AND VALID_OR='1'
```

- 保留: STATUS / CHECK_TIME / MEMO / UUID / BUY_TIME / PROJ_ID / PACK_ID / RATINGLEVEL; 抹除: 企业名/手机/单位码/BIDDER_ID。
- 缺身份 → 走 uuid→企业名映射链(lowcode-dataplatform-pentest: `uuid-company-name-mapping-chain.md`)。
- dsid=service_business(活库直读); 对外必须用孪生名 `bid_package_bidder_business23`。

## 5. 下一步探针(脚本已备, 未发射)

- `scripts/probe_xa79_channels.py`(本技能): A=starting* 传 id; B=名册带 08-20~09-12 窗; C=bidder 多窗(全窗只校验 totalSize/样例 — 全表负结果已档, 勿重扫)。
- 发射后回填本文件结论; 若 A 命中, 对照 pack_map 回填每包状态与中标名。
