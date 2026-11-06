# 95306 Session13 — TG Bot 产品化全貌(v3.2→v4.1)+ 供应商主数据

## 系统最终架构(2026-08-29 晚)
```
4 台国内采集机(上海8.133.188.178/杭州121.43.97.73/广州8.138.236.124/成都47.108.152.60)
  └─ collector.py 每 60s:审计抓 ST → 目标发现(48h窗口翻3页) → 企业识别 →
     getBuyPackageList → 落盘 /tmp/targets/<projId>/ + 心跳 v6_heartbeat.json +
     bid_status.json(竞价状态) + bid_live.json(出价尝试 bidRoom,尽力而为)
海外主服 128.241.245.73:12971(qfgR3okF9wfn4PXF)
  ├─ merger.py 每5min(加速时2min)并行拉4台(sftp)→ /data_pool/<projId>/
  │   {项目信息.json, 包件清单.json+CSV, pack_map.json, 18列CSV, bid_status.json}
  ├─ pix_bot_server.py(TG bot,直连TG无需代理)
  └─ CHANGELOG.md / users.json / subs.json / favs.json / accel.json / health.json
数据池: 13,173 项目 / 43,870 包件 / 615,259 条报名 / 7,399 企业档案 / 369,710 供应商主数据
```

## 数据池关键机制(踩坑后定型)
- **merger 覆盖历史 bug**:merger 每轮重写 index.json 会把历史项目(13,145)挤掉只剩 live(20)。
  修复:index 写入前先读旧 index 合并(保留历史,只更新 live 条目);企业数统计从"合并后的 pack_map.json"
  读取(否则 8515 导入的 18 家被采集机空数据覆盖回 0)。
- **pack_map 合并保留**:merger 写 pack_map 时 merge old(历史/8515/手动收集)+ new(采集机),不能整体覆盖。
- **8515 实时报名数据**(8,515 条,含进行中项目)按 proj_code→projId 关联导入,企业级报名标记
  packId="PROJ_LEVEL"(无 pack_id 的项目级占位),来源="8515项目级"。
- **collect_one.py 手动收集**:关键词多轮询(原词/第N次/第N次废)+ **路局名+次数双条件**精确定位公告
  (搜"武汉局69次"=0 条但"第69次废钢铁"=9 条,必须同时匹配"武汉局"和"第69次"才不选错西安局69次)。
- **动态生成下载**:主服无 18列文件但 pack_map 有企业 → bot 点按钮动态生成 CSV(gen18/genpacks 回调)。

## Bot 产品化功能清单(v3.2→v4.1)
1. **权限分层**:ADMIN_IDS(3人)+ users.json allowed 动态鉴权 is_allowed()/is_admin();
   管理员用户中心可见"🔐 授权管理"按钮,可自主添加/移除授权用户(输入 chat_id → 保存 → 通知新用户)。
   被授权用户无此按钮,伪造回调被"⛔ 无权限"拒绝。
2. **版本更新公告 push_update(version, changes, stats)**:只推本次变更(新增/优化/修复分节),
   **绝不重复历史版本内容**(用户明确要求);CHANGELOG.md 每版本只记本次;帮助页"📜 更新记录"
   读 latest_update(3)。
3. **用户中心**:/start 动态数据总览(项目/包件/企业/加速状态/订阅数/版本)+ 全功能按钮。
4. **订阅事件推送**:sub_checker 线程每 60s 对比 sub_state.json 快照:
   新报名(ent 集合 diff)/审核状态变化(packId→status diff)/竞价状态变化(未开始→竞价中→已结束)自动广播。
5. **健康监控**:health_checker 线程每 5min 读 health.json(merger 从各机心跳汇总),
   心跳 gap>300s 推告警(health_alert.json 去重,恢复后清除)。
6. **报表**:weekly_report(周报,周日 20:30 自动)/market_report(物资类型分布)/rank_report(企业报名 Top10,
   从全量 pack_map Counter)。
7. **体验**:/wh69 快捷、/cmp A+B 项目对比、/fav 企业收藏、📋 项目详情包件展开前5包+竞价状态、
   Excel 下载(实际为 UTF-8-BOM CSV,Excel 可开;TG 文档 50MB 限制,大文件 zip 后检查大小)。
8. **推送节奏**:每日汇总 20:00 + 周报周日 20:30 + 订阅事件 60s + 健康告警 5min + 更新公告(部署时)。

## 供应商主数据导入
zip 内 05_供应商联系信息含手机法人_369710条.csv(131MB,28字段)→ 主服 /data_import →
import_supplier.py 按企业名生成 /data_pool/供应商/<名>.json{信用代码/法人/联系人/手机号/注册地址/成立日期}。
bot sup_profile() 先查企业档案再查供应商目录,合并补全手机/法人/信用代码/地址显示。

## 验证结果
- 武汉局69次:13 包 + 18 企业(包件 CSV 兜底显示)
- 供应商深度:河南凡欧 → 手机 <PHONE-REDACTED>
- 覆盖率:13,173/16,891 = 78%(历史全量)
- 企业排行:河南崇锐贸易 453 次
