# 2026-09-13 r12:竞拍生命周期解码 + 翻转收割架构(审核矩阵最终方案)

> 上承: `2026-09-13-audit-fill-channels-fired-results.md`(三通道实弹 + "下批待办")。
> 本文 = r12 探针(主服直发, paramiko runner)结果 + 收割架构落地。
> 字典路由已探明死(§2), 码值改从实网行数据反推 → 生命周期全解码。

## 0. 结论速览(最终形态)

- **字典视图 findList 不可调**: `dict_bid_project_status`(名称+UUID 双试) / `dictbidpackagebidder` /
  `dict_bid_package_status` 全返 `不存在的功能` → 码值从实网数据反推(§1)。
- **生命周期三态解码完成**: **19**=公告已发/报名中 → **31**=竞价结束、结果公告未发布 →
  **14**=已结束(结果公告已发布)。判据: `jieguo_pub_time='-'` ⇔ status=31。
- **XA79 解锁唯一钥匙 = 结果公告**: 31→14(或 jieguo 字段出现)时 b580 硬门解除 → 收割即得全矩阵。
  **翻转哨兵已部署**(§3, cron 15min 自动日切收割)。
- **矩阵公式(buy_time 连接键)**: 名册行(企业名+信用码+**秒级 buy_time**) ×
  b580 行(buy_time+pack_id+check_time/memo) 按 **buy_time** 关联 → 每家企业×每个包×审核状态;
  无需企业会话、无需 UUID 映射链。

## 1. 生命周期/码值(实网反推, 源码字典缺位)

- 项目级: 19 / 31 / 14(如上)。证据行: 临哈 3 次(bid 9/28 未来)→19; XA79 与上海 126 次
  (bid 9/11 已完拍、jieguo='-')→31; 广州 13 次(jieguo 9/7)→14 已结束。
- 包级: 14=成交 / 22=流标; bidder 记录级: 01=通过 / 22=成交(中标)。
- 同侪节奏: 广州 13 次 bid 9/1→结果公告 9/7(6 天)。XA79(bid 9/11)翻转窗口估 **9/14~9/18**。
- 顺手通道: 响应内常内嵌字典与视图配置 —— 如 ES 响应含 `dictUnitTypeList`、
  A 视图响应 `viewModel.allSysview.<view>.sysviewelements` = 该视图字段清单+搜索配置
  (`elementname`/`isfastsearch` 等, 读"可查字段"的捷径)。

## 2. r12 通道实弹矩阵(全部主服直发)

| 通道 | 关键参数 | 门控 | 实测 |
|---|---|---|---|
| startingbiddetailspackage | `id`=项目UUID | **全注释, 无项目状态门** | ✅ XA79(31) 8 行; 输出 status/jieguo_pub_time/proj_code |
| startingpackagedetails / SPDT | `companycodeorg`('10'=全路)/`startDate`/`endDate`/`lowprice`或`tallprice` | **无状态门** | ✅ **全状态(19/31/14)项目枚举新通道**; 输出 status/status_name/jieguo_pub_time/pack_sum/deta_sum/pack_outbidprice |
| bid_package_bidder_business23 (b580, **必须孪生名调用**) | `start_time`/`end_time`(PROJ_ENDTIME 窗) | 项目 STATUS='14' 硬门 | ✅ 活(窗口 77KB)但不含 31 态; 行保留 uuid/buy_time/pack_id; NULL 掉 bidder_name/id/phone |
| bid_package_business23 | 同上 | 同上 | ✅ 活(144KB) |
| bid_room_sign_business23 | 同上 | 同上 | ✅ 活(14KB); 行={sign_num,id,proj_id,valid_or} 无身份 |
| bid_offer_price_business23 / bid_record_business23 | 同上 | — | ❌ TimeoutError(弃, 勿耗) |
| biddingandsellingsupplier | `startDate`/`endDate` | 无 | ✅ 名册; 每行=一条报名记录; 含 bidder=null 行(无报名项目) |
| startingmaterialdetails | `id`=项目UUID | 疑另有门(与 A 视图似孪生) | ❌ totalSize=0(XA79), 异常未定论 |
| ES `/proxy/portal/elasticSearch/scrapSuppliesQueryDataToEs?noticeType=` | 无鉴权 | — | ✅ 01=20202 / 05=17492 / 09=9 条; 不支持关键词, 翻页 2000+ 不划算 |
| dict* 字典视图 | — | — | ❌ 不存在的功能(名称与 UUID 均不可) |

## 3. 翻转哨兵(已部署 2026-09-13, 主服)

- `/opt/v6/xa79_flip_watch.py`; cron:
  `*/15 * * * * cd /opt/v6 && flock -n /tmp/xa79_flip.lock python3 xa79_flip_watch.py >> /tmp/xa79_flip_cron.log 2>&1`
- 逻辑: 轮询 A 视图(status/jieguo) → 翻转(≠31 或 jieguo≠'-') → 日切收割 b580
  8/20~10/31(每日分页≤60) → 含目标 ID 的日整日 dump `/data_raw/xa79_flip/b580_<ts>_<MMDD>.json`
  → 写 DONE 标记; 无命中每 2h 重试。
- 目标 ID 组: `3a5a0784` + 包前缀 `6fc6c9a4/f40eed84/94ee82f2/dcd27e6c/90e237f8/16611220/5beb3fda/6913326d`。
- 试跑 ✅ `[09-12 17:20] status=31 jieguo=-`; 日志 `/tmp/xa79_flip.log`。
- 收割后动作: 拉回本地 → buy_time 关联名册(r11_roster.json, 79 次 61 条) → 出矩阵 → 按
  pack_map schema 契约回填(bot 读 审核状态/审核码)。脚本副本 = `scripts/xa79_flip_watch.py`。
- 通用化: 此模式适用于任何"31 态卡住"的项目 —— 换 PID/目标 ID 组即可。

## 4. 本地旧数据判定(勿再翻)

- `D:\渗透\95306_历史数据_导入\` 7 文件**全为 08-29 快照**(mtime); XA79(8/31 公告) 0 命中
  (cXAid=0, cSep=0, 文件内"第79次"均为他局) → **旧数据补不了 XA79**。
- 可用素材: `08文件_615267条`(19 列, 含 项目ID/包件ID/记录ID/投标人ID);
  `供应商联系信息_369711`(行); 恒丰盛达历史 1,405 次、宏达宇 600+ 次(映射素材充足)。
- **8515 增量(每30min, 6h 窄窗)只捕 PROJ_ENDTIME 落窗项目** —— 翻转发生在 endtime 窗外时
  增量永远抓不到 → 这正是需要哨兵日切回放的原因(勿指望 8515 自动补 XA79)。

## 5. 遗留 / 下批

- `861a5ffa`「竞价参与表」/ `cbf1014b`「竞买竞卖供应商报名统计」(service_business) 未探(需孪生名)。
- startingmaterialdetails 对 31 态项目返 0 的成因未定论(与 A 视图似孪生, 疑多一道门)。
- SPD/SPDT 无门通道 → 建议接入主管线做"进行中项目全覆盖"增强(19/31/14 全枚举, 填补发布→竞价前盲区)。
