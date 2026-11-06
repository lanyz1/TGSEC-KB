# 95306 Session20 — 采集/合并/告警全链路完善(8515 自动更新 + 企业全量 + 运维陷阱)

2026-08-30。主线:8515 快照表自动更新、报名-包件自动核对、企业全量拉取、7 类告警闭环。

## 数据平台表侦察结果(bid_xxx_business23 系列,全部无鉴权 findList)

| funcId | totalSize | 内容 | 关键字段 |
|---|---|---|---|
| bid_project_business23 | 705(8月窗口) | 项目主表 | id(proj_id UUID)、bid_starttime、create_time、pub_end_time、project_explain、memo |
| bid_package_business23 | 2185 | 包件表 | id(pack_id)、proj_id(关联!)、pack_code、pack_name、end_time、outbid_date、bid_min_bidder |
| bid_notice_business23 | 2247 | 公告表 | id、proj_id、proj_code、not_title(结果公告) |
| bid_package_bidder_business23 | 8515 快照 | 包件-报名人 | proj_id、pack_id、buy_time、status(企业字段全 null) |
| bid_project_bidder_business23 及 23 个变体 | -1 | **不存在** | 8515 CSV(项目-报名人粒度,含企业名)来自跳板机侧数据库直查,非 findList 表 |

- **全表停更实证**:max(create_time) = 2026-08-27 16:57(项目/包件表一致);8515 报名表 buy_time 最新 2026-08-24。→ 数据平台整体只能作历史源。
- **西安局69次(f4d6e6e2)在项目表/包件表/公告表/报名表全部 0 命中** = 数据平台不覆盖该项目(项目级报名特殊项目)。
- 包件表 2185 有 pack_id + proj_id 关联,但同样是停更表 → 新项目 packId 实时仍唯一依赖审计 ST 链路。

## 8515 历史全量补拉
- 分月拉 2025-01 → 2026-08(params 起止时间,**每月 6000 条上限** = 6 页 × 1000)。
- 结果:**120,000 行 / 5,231 项目 / 17,607 包件**,buy_time 2021-11 → 2026-08-24。
- 历史行企业字段同样全 null(0% 非空)——只能做项目/包件级覆盖核对。
- 落地:转 `8515_快照_hist_2025_2026.json`(18.6MB)放 `/data_raw/上海/`(文件名匹配 `8515_快照*` 即被 merger 自动并入 `/data_pool/8515_快照/index.json`)。

## 企业全量接口(审计盲区补全)
- `GET /supplierPackage/getSupplierPackageList?statusGroup=buyed&bidType=02&pageNum=1&pageSize=50` + `Authorization: ST`
- 返回该企业**所有已报名项目**(id/projCode/projName)→ 逐个 `getBuyPackageList?projId=` 拉包件。
- 价值:一个 ST 枚举企业全量项目,**发现审计窗口外的项目**(报名早于采集器部署/审计漏捕)。
- 限频:每台采集机每小时 4 次(state["full_times"] 时间窗计数),写 `_ent_full_*.json` 根文件。
- merger `merge_ent_full()`:新项目(数据池无目录)→ 建目录+入 index(live=True,来源=企业全量);已有项目 → 按 packId set 去重补 pack_map。

## 告警闭环(7 类)
采集机 `_alerts.json`(giveup/overflow)→ rsync → merger `check_gaps()` 合并进 `/data_pool/gaps.json`(项目包件缺口/企业报名缺口/采集机告警)→ bot 每 5 分钟 `check_gaps_alert()` 对比签名(new 变化才推)→ broadcast。
- 项目包件缺口:8515 快照有 pack_id、数据池 pack_map 没有(历史报名未产生 ST 的项目)。
- 企业报名缺口:审计 enroll_ops(报名操作)有账号、pack_map 没有(采集链路漏捕)——当前 0 = 链路无漏。
- ST放弃:重试 ≥5 次失败记 giveup,不再无限重试。
- 审计溢出:**按页1 内 60 秒操作数 ≥100 判定**(滚动日志 5 页全满是常态,曾误报 4 台)。
- rsync 失败:`_rsync_fail()` 写 `/data_pool/rsync_fail.json`,bot 推近 15 分钟失败。
- merger 每轮 cron `*/5 * * * *`,需 flock 单实例锁(rsync 慢时防重叠)。

## 运维陷阱(实踩)
1. **now_ts UnboundLocalError**:审计溢出检测段(440 行)引用 now_ts,但定义在 500 行 → 4 台采集机部署后全挂。修复:改 `datetime.now()`。**部署后必 tail 日志,不能只信 py_compile。**
2. **审计溢出误报**:500 条审计覆盖 1.5 天滚动日志,5 页全满=常态。误报后 4 台 `_alerts.json` 全带 overflow。
3. **merger 无单实例锁**:cron 5 分钟 + rsync 4 台 219-250 文件耗时波动 → 07:20/07:25 两轮重叠并发。加 `fcntl.flock(LOCK_EX|LOCK_NB)` + 失败 `sys.exit(0)`。
4. **主服 bot 真身 = pix_bot_server.py**(非本地副本 pix_bot_v3.py);服务器文件可能比本地新(142,976 vs 125,719)→ **增量字符串补丁,禁止整文件覆盖**。
5. **paramiko 远程补丁**:sftp 读返回 bytes → `decode("utf-8","replace")`;主服文件 CRLF → 先 `replace("\r\n","\n")` 再匹配;写回后 `py_compile` + `grep -c 函数名` 验证(**别信字节数**:CRLF/UTF-8 差异致大小不符但内容正确)。
6. **本机直连采集机超时**:采集机只能从主服访问;本机脚本模式 = 连主服(Ed25519 私钥 `v6_master_key`,非口令)→ 主服执行 Python → 主服连采集机(口令 Ppikesi1xx 系列)。
7. **8515 index 检查**:`/data_pool/8515_快照/index.json` 结构是 `{proj_id: {pack_id: {...}}}`,不是 `{"projects": ...}` —— 用错键会误报"0 项目"。
8. **部署脚本复用**:采集机部署用"主服跑 Python → paramiko 连 4 台 → systemd restart"模式;杭州 journald 日志(文件 mtime 不更新但 systemd 状态正常)= 正常现象,看 `systemctl status` 或 journal。
