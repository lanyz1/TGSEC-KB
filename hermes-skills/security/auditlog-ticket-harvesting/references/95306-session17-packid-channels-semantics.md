# 95306 Session 17: 包件获取渠道全验证(2026-08-30)

核心目标:packId(进行中项目企业+精确包件ID)获取零缺失。本会话完成全渠道验证与语义实锤。

## 结论速览

| 渠道 | 鉴权 | 内容 | 实时性 | 结论 |
|---|---|---|---|---|
| 审计 ST → getBuyPackageList | 企业 ST | 该企业报名包件 | 60s 轮询实时 | ✅ 主渠道(按企业隔离) |
| bid_package_bidder_business23(8515 快照) | 无 | pack_id+proj_id+status+竞价价 | 滞后 ≥6 天 | ⚠️ 仅历史补全/核对 |
| 项目报名表(CSV 8515 条来源) | 无 | 企业+报名时间,无 pack_id | 8/28 快照 | ❌ 无 pack_id |
| 竞价日捕获 | 企业 ST | 竞价登录 → 全量捕获 | 8/31 09:00 窗口 | 🎯 补缺关键窗口 |

## getBuyPackageList 语义(实锤)

- `GET /supplierPackage/getBuyPackageList?projId=X`,`Authorization: ST`,`Referer: https://cg.95306.cn/bfwz-view/`(防盗链必须)
- **按企业隔离**:只返回当前企业自己报名的包件。zjjqdw123(张家界帅帅家政)ST 有效但拉西安局69次 → data=None
- 错误特征:401=ST 无效;`{"code":100,"msg":"系统服务异常"}`=部分账号 ST 已失效(同批 8 个票 5 成功 3 失败)
- **反全项目包件需要每个报名企业各自的活 ST**——"一票反全量"不成立

## ST 生命周期(实测修正)

- **会话级复用**:同一账号会话期内多次操作同一 ST(YNHKSMYXGS 11:06 = 12:15)
- **有效期 ≥3 小时**(09:45 票 12:39 有效)——早期"30 分钟 TTL"判断错误,勿按 TTL 猜,直接实测 user/info
- 审计提取:`operation_details` 正则 `serviceTicket=([0-9a-f]{32})`
- 审计接口限流/故障时返回 `{"code":900000,"msg":"服务器异常"}` → 重试

## 报名操作两种审计形态

- `redirectEnrollUrl`(cg.95306.cn 主站)→ 带 serviceTicket,可提取 ✅
- `skipJoinPage`(bid.95306.cn/api/execute-server/page/skipJoinPage 竞价系统)→ 无 ST ❌

## 8515 快照表细节

- 表名:`bid_package_bidder_business23`,无鉴权 findList
- 响应:`{"code":0,"data":[...],"totalSize":N}`(totalSize 在顶层)
- 字段:pack_id/proj_id/buy_time/check_time/status/current_price/...;**bidder_id/dwcode/phone/person/bidder_name 全 null**
- **params 通道**(`[{"key":"start_time","value":...},{"key":"end_time","value":...}]`)过滤"入库/更新时间"非 buy_time;condition 通道无效(返回 0)
- 空 params 时 totalSize 可能不返回(data 仍全量)
- 滞后:8/25 后无新报名入库;8/28-31 更新窗口仅 124 条(8/24 前旧数据补录)
- 西安局69次(8/22-24 报名 70 条)在该表 0 条 → 项目级报名不进表

## 缺票根因链条(用户核心关切)

1. packId 唯一来源 = getBuyPackageList(需该企业有效 ST)
2. 企业报名后不再登录 → 无 ST → packId 永久缺失(西安局69次 22 家:8/22-24 报名,采集机 8/28 才部署,之后无人操作)
3. 反证:dff20093(8/29 报名 27 家)→ 100% 捕获(报名发生在 bot 运行期)
4. **bot 运行后新项目可 100% 全覆盖**(审计 60s 窗口 + 500 条 + 失败重试 + 补拉)
5. 补缺窗口:竞价日企业必登录 → 自动捕获

## 部署事故:systemd run_once 循环

- 现象:采集机 5-7 秒一轮高频轮询 + 间歇停机空窗(12:11-12:29)+ 目标系统 `UnknownHostException: cg.95306.cn`
- 根因:crontab 设计的 `if __name__ == "__main__": run_once()` 改 systemd 常驻后进程退出 exit 0 → Restart=always 无限重启循环
- 判据:`systemctl status` → `Process: ... (code=exited, status=0/SUCCESS)` + `Active: activating (auto-restart)`
- 修复:`while True: try: run_once() except Exception: log(...); time.sleep(60)`
- 验证:轮询间隔日志 12:35:24 → 12:36:24 = 60s ✅

## 数据流架构(v7.23+)

- 采集机(4台):60s 轮询审计(5页/500条)→ 新 ST 识别(user/info)→ 拉 43 目标项目包件 → `/tmp/targets/<projId>/` + `_enroll_ops.json` + `8515_快照/`
- merger(主服):rsync 拉取(现在支持根级 JSON 文件)→ 合并 pack_map → **merge_8515_snap()**(8515 增量合并 `/data_pool/8515_快照/index.json`)→ **check_gaps()**(三方核对 → `/data_pool/gaps.json`,含"项目包件缺口"+"企业报名缺口",变化才标记 new)
- 缺口核对数据源:采集机 `_enroll_ops.json`(审计报名操作:projId → {账号: 时间})vs pack_map 企业账号

## 本会话临时脚本(本机 Temp)

ssh_verify_causal*.py / ssh_test_sem*.py(接口语义)/ ssh_find_live*.py / ssh_test_filter*.py / ssh_test_cond.py(condition 无效实证)/ ssh_pull_xa69*.py / ssh_ana*.py / ssh_tail_logs.py / ssh_sysd_diag.py(systemd 判据)/ ssh_deploy_retry.py / ssh_deploy_merger.py / ssh_check_merger.py

## 遗留

- 西安局69次:待 8/31 09:00 竞价日捕获(22 家企业必登录)
- merger 主服部署后 md5 验证未完成(上传大小 23738 vs 主服 26623 疑云未决,需确认 sftp 写入是否成功)
- bot 读取 gaps.json 推送告警:下一轮实现
