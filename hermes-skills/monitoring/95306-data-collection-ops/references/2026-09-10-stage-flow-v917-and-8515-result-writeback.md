# v9.17 竞价结束→已结束 即时流转 + 8515 包件结果回写(2026-09-10)

## 用户口径(定论,勿再回退)
- "竞价结束后的项目应自动并入已结束";bot 设计注释(「竞价完自动进🏁」「竞价结束自动转已结束」)同口径。
- 修复前 `_stage_of` 把竞价关闭的项目压进"待发布"最多 7 天 → bot 🏁 菜单(严格 `stage=="已结束"` 过滤)看不到刚结束项目 → 用户报"不会自己并入"。

## 三层根因(全部已修, v9.17)
1. **timedelta 断链**(同日更早修复): merger.py 缺 `from datetime import timedelta` → `_days_after` NameError 被 except 吞 → 兜底失效,老项目永久卡"待发布"。
2. **7 天停留设计**: 改为竞价室关闭(max_end 过)即 `return "已结束"`;"待发布"桶仅留 stats 兼容位,不再产生。
3. **UTC/北京时区**: 主服 Etc/UTC,`_stage_of`/`_is_live`/`classify_all` 原用 `datetime.now()`(UTC) 跟平台北京时间比 → 状态切换晚 8h。统一 `(datetime.utcnow() + timedelta(hours=8))`。bot 端用 `_bj_now_dt()`。

## 核实数据(实测 before→after)
- 待发布 93(全为 0~1.7 天内刚结束,无一 >7 天)→ 0;已结束 21435 → 21534
- 修复后当天 09:16~10:39 结束批次即时入已结束;仅 2 个"竞价中" = 结束时间未到(19:00/12:40) → 语义正确
- bot 🏁 菜单读 index.json(5s 缓存) → 数据侧生效即见,无需重启 bot
- 口径分歧(已知,别"修"错):🏁 菜单 = stage=="已结束";`/q` 搜"已结束" = 平台 status==14(结果发布后);卡片状态标签 = 平台 status 原值

## 8515 快照:同包多行聚合(重要教训)
- `bid_package_bidder_business23` 行 = (包件×报名者) 级匿名行(bidder_name 全 null);状态码 01=通过/22=中标/03=拒绝/00。
- 旧合并"任意后写覆盖" → 已决标(22)被 01 行盖回"竞价中"。v9.17b 改**最高优先级聚合**: 22>01>03>00,同级取最新 check_time。
- 变更计数只算真实值差:别把 `src`(来源文件名)变化计入——每轮全量重读会报数万假变更(81k→12k 降噪)。
- 快照 index `if changed:` 才落盘 → 新增字段(price)必须同时进变更判定,否则回填不持久化。
- **8515 源无成交价**:66 文件 171,500 行 current_price 非空 = 0(字段存在永远空);single_price_list 同空;current_price_time 有值(19,578 行)。成交价须另寻通道(候选:竞价详情/公告正文,未验证)。

## 包件结果回写(apply_8515_results)
- 挂 merger 主流程: `merge_8515_snap → _ch = audit_diff() → apply_8515_results(_ch)`
  —— audit_diff 返回值改为**完整变更清单**(落盘文件仍 top-40 截断,供 gen_gap 附推)。
- 首轮全量(flag `.apply8515_done`),其后仅变更项目;写 pack_map["包件结果"] = {状态,码,成交价,审核时间,报名时间};写盘 tmp+os.replace。
- 实测: 2674 项目 / 12411 包件(已决标 9644 / 竞价中 2292 / 未通过 271 / 待处理 204)。

## 部署与验证模式(可照抄)
- 本地断言脚本: 逐条 `s.count(old)==1` + 替换 + py_compile + 备份;paramiko put /tmp → 远程 py_compile → cp .bak → mv。
- merger daemon 每轮 spawn 新进程 → 改文件即部署,无需重启。**验证必须等"部署后启动的轮次"**:轮询"开始合并流程"时间戳 > 部署时间,再等该轮"完成:"。
- 用户铁律: 先取证再改 —— 改前 read-only 检查脚本出 before 数据,改后同口径复测。
