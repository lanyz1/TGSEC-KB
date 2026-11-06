# 2026-09-12 数据平台目录层"全库脱出"路径 — "从数据库直接脱"的定论(竞价视图群/脱敏/门槛)

## 1. 目录层(全部无鉴权可读, 走 findList)
- `sysmeta`(1892条): 每行={metaid(=funcId), metaname, sourcetable, dsid, content(=该报表SQL源码!), pid…} → 平台每张报表/对象的定义与 SQL 全量暴露
- `sysview`(2700+): {funcid, viewname} → 全部可查视图清单; `sysfunc`: 功能注册表
- 拉法: 同 findList 契约, {"funcId":"sysmeta","appId":"system","pageNum":N,"pageSize":300}, 循环拉至 <pageSize
- dump 已存主服: /tmp/sysmeta_all.json + /tmp/sysview_all.json(直接复用)
- dsid=数据源: service_business(竞价业务库) / binlog_doris(CDC汇聚) / member / service_user …

## 2. 处置竞价数据层 = 37张 *_business23 视图(关键清单)
- 主表: bid_project_business23(项目表) / bid_package_detail_business23(物资表) / **bid_package_bidder_business23(参与表=审核码/状态写回来源,即"8515")** / **bid_record_business23(报价记录表)** / bid_offer_price_business23(报价表) / **bid_room_sign_business23(号码牌表)** / bid_package_pricestep_business23(步长) / bid_notice_business23(公告) / bid_import_package_business23
- 采购侧集中竞价: req_purchase_supplier_app_business23(参与) / req_purchase_record_business23(报价记录) / req_purchase_results_business23(结果) / req_purchase_bidding_maters_business23(签到)
- 字典: **dictbidpackagebidder(审核状态字典!)** / dict_bid_package_status / dict_bid_project_status / dict_bid_mode / dict_notice_type / dict_business_project_type …
- 统计报表: packagedisposalinfo / materdisposalinfo / materPriceSharing / materialswhole(成交汇总) / materkeysuperdetails(重点监管明细)
- 汇聚(CDC): 数据汇聚-项目/包件/公告/报价步长 信息表

## 3. 三道铁门(实测数据)
1. **脱敏**: 视图把身份+价格列置 NULL(bidder_dwhz/bidder_id/price/token 全null); 但时间戳/类型/状态码/号码牌正常 → 可拿"什么时间发生了什么"，拿不到"谁+多少钱"
2. **门槛+时间窗**: SQL 级过滤样例 `PROJ_CATEGORY='00' AND STATUS='14' AND PROJ_ENDTIME∈窗`; 量级≈7天窗; 历史项目不吐
3. **uuid型 metaid 不可调**(b580e32d-7967-… 等直接当 funcId = "不存在的功能"; 要用其 *_business23 视图孪生名)
- 实锤: 西安79次(3a5a0784) bidder窗955行全扫0命中; record/room_sign/detail 各4000行0命中; bid_project 5k行0命中 → 已结束超窗项目在公开视图彻底不吐

## 4. 定论(用户问: 审核状态/审核码 能否DB直脱)
- **能, 且一直在用**: bid_package_bidder_business23 = 审核码/status/check_time/memo/UUID 的直接来源(=8515管道本体)
- 但公开视图 = 脱敏 + 门槛 → 补全不了"西安79次"这类已结束超窗项目的逐企业审核; 补全仍靠 ①企业会话(登录即刷) ②内部不脱敏会话(特权线)

## 5. 立刻可用(下步动作)
- 脱 `dictbidpackagebidder` → 审核码→中文名全量映射(回填/展示用)
- `bid_record_business23`+`bid_room_sign_business23` = **匿名出价心跳**(出价时间点/次数/号码牌, 无身份) → 竞价室"💰实时出价"的 TQ 无关形态候选; 下次拍卖验证"进行中"房是否被门槛放行(STATUS='14'疑为终态门, 竞价中可能=13)
- 通用: 任何 findList 型低代码数据平台, 先枚举 sysmeta/sysview → 拿全视图+S​QL 再挑目标
