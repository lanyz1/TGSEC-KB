# 95306 新通道数据清单与解锁口径（2026-09-12 夜实测）

实测时点: 2026-09-12 18:40 UTC (09-13 02:40 北京)。全部 code=0 实测。

## 调用基座
POST https://cg.95306.cn/proxy/dataplatform/api/findList
body: {"funcId":F,"appId":"system","pageNum":1,"pageSize":N,"params":[{"key":K,"value":V}],"condition":""}
headers: Content-Type: application/json;charset=UTF-8; Referer: https://cg.95306.cn/bfwz-view/

## 通道 × 规模 × 解锁口径（totalSize 实测）
| funcId | 数据内容 | 全量口径 | totalSize |
|---|---|---|---|
| bid_package_bidder_business23 (b580) | 报名审核明细: pack_id/proj_id/uuid/buy_time/状态码/审核时间/memo(驳回原因)/isblackliststate(处罚); 身份列(bidder_name/phone/dwcode/bidder_id)NULL | start_time=0 & end_time=2099-12-31 00:00:00 | 938,330 (仅已结束STATUS=14项目) |
| biddingandsellingsupplier | 名册: 企业名+统一社会信用代码+buy_time+公告时间 | startDate=2015-01-01 & endDate=2099-12-31 | 967,419 |
| bid_package_business23 | 包件主数据 | start_time=0 & end_time=2099-12-31 | 156,488 |
| bid_project_business23 | 项目主数据 | 同上 | 54,305 |
| bid_room_sign_business23 | 参拍号码牌 proj_id+sign_num(+valid_or) | 窗口 8/25-9/30 | 40,911 |
| startingbiddetailspackage | A通道 id=项目ID → 每包 成交/流标+起拍价+成交价+中标单位名 (无状态门) | 直调 | XA79=8包 |
| startingpackagedetails | SPD companycodeorg/startDate/endDate/lowprice → 项目级 status(19/31/14)+status_name+jieguo_pub_time+pack_sum+deta_sum+pack_outbidprice+bid_starttime | 窗口直调 | 8/20-9/15 org=10 → 106 |
| buyersupplierorderinfocount | 采购方×供应商订单计数 | orderNum=0 | 5,507,744 |
| samepurchaserhighsamegoods | 同采购方同品比价 | itemNumber=0 | 14,836,602 |
| elasticSearch/scrapSuppliesQueryDataToEs | ES公告(无鉴权GET): noticeType 01=20,202 / 05=17,492 / 09=9 | 直GET | — |
| startingmaterialdetails (MATD) | A通道孪生(物资明细) | id=项目ID | 返回0异常待解 |

## 关键公式
b580(buy_time) ⟕ 名册(buy_time) = 企业×包×审核全矩阵。
b580 身份列 NULL → 靠 buy_time(秒级) 关联名册还原企业名+信用代码。b580 保留 uuid(记录ID)/pack_id/proj_id 不脱敏。

## 状态机(实网反推)
项目: 19=公告已发竞价未开始(报名中) → 31=竞价结束待结果公告 → 14=已结束(结公告发布)
包: 14=成交 / 22=流标。 bidder记录: 01=通过 / 22=成交。
翻转触发器: jieguo_pub_time 发布 → status 31→14 → b580 该项目审核明细解锁。

## 口令变化(2026-09-12夜)
- 名册 endDate="0" 单参数已失效(返回0)。现行: startDate=2015-01-01+endDate=2099-12-31 → 967,419。
- b580/三表: start_time="0"+end_time="2099-12-31 00:00:00" 有效。
- 窗口化名册(2026-07-01~09-15): 40,558 行。

## XA79 临战(西安局79次, PID=3a5a0784-7bd6-4ce5-a855-dc56c23026fe)
- 现状: status=31, jieguo_pub_time='-' (9/13 02:40 北京仍31)。
- 哨兵 /opt/v6/xa79_flip_watch.py + cron */15min(flock) 已上线; 翻转即日切收割 8/20-10/31 窗 b580 → /data_raw/xa79_flip/。
- A通道已锁 8 包结果: 001成交恒丰盛达/002+007+008成交宏达宇/004成交八方美/003+005+006流标。
- 名册: 19家/61条报名记录(含信用代码)。
- 解析前必须用 buy_time 连接(名册61条 buy_time ↔ b580 行)。
