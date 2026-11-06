# 数据池组成盘点与单项目 Schema — 95306 v6 实录(2026-09-01)

## 时区陷阱(查新鲜度第一坑)

- **主服 = UTC,采集机 = 北京时间(UTC+8)**。`index.json.updated`/`gaps.json.time` 是主服 UTC;`health.json.machines[].ts` 是采集机北京时间。
- 实测:主服 22:35(=北京 09-01 06:35),若拿"现在"直接减 index updated 会误判"merger 停摆 10+ 小时",实际刚更新几分钟。
- 判定链路:主服 `date` 确认时区 → index/gaps 的 updated +8h 换北京 → health.ts 才是采集机心跳(秒级新鲜,gap_s=距上次心跳秒数,<300 正常)。

## 数据池组成盘点方法

```bash
# 主服
python3 - <<'EOF'
import json, glob, collections, os
d = json.load(open("/data_pool/index.json", encoding="utf-8"))
# 结构: {"updated","source","projects":{projId:{...}}}   ← 不是 list!
projs = d["projects"]
print(collections.Counter(str(r.get("stage") or "无stage") for r in projs.values() if isinstance(r, dict)))
EOF
```

- **index.json 结构**:`{"updated","source","projects":{projId:{projName,projCode,bidStarttime,status,enterpriseCount,packCount,live,stage}}}`。
  - `stage` 分布 = 数据池状态快照(报名中/待竞价/竞价中/待发布/已结束/历史)
  - **index 里没有 packages/enterprises 字段**——统计包件/企业必须去 pack_map.json,直接解析 index 会得到 0(实测踩坑)
- **包件/企业统计**(pack_map.json,6,809+ 个项目的 `enterprises` 字段):
  - 企业记录结构:`{"单位","账号","信用代码","包件":[{packId,packCode,packName,审核状态,时间}],"时间","来源","记录":[{时间,来源}]}`
  - 包件字段名是中文 `"包件"`(list);`"记录"` 也是 list 别误计为包件
  - 去重包件含 `PROJ_LEVEL` 项目级报名占位(8515 来源),统计时注意
- **health.json**:`{"updated","machines":{机器:{ts,gap_s,targets,disk_mb,waf,status}},"bidding":{}}` — 4 机健康一览,status="✅ 正常" 或失败原因
- **gaps.json**:`{time, 项目包件缺口, 企业报名缺口, 待确认缺口, 采集机告警, new}` — bot 告警源
- 磁盘目录数 vs index 项目数不一致是常态:index 含 8515 历史导入(无目录),目录只覆盖实际采集项目

## 单项目目录 Schema(/data_pool/<projId>/,5 类文件)

| 文件 | 内容 | 来源 |
|---|---|---|
| 项目信息.json | projId/projName/projCode/bidStarttime/status/sellEnddate/src | selectSelfSellList(在网扫描)或 getSupplierPackageList?statusGroup=join(可参与列表,src=join)或 公告流 queryBusinessNoticeList(src=notice) |
| 包件清单.json | 公告id/公告标题/包件数/包件[{packCode,packName,保证金,竞价开始,竞价结束}] | queryBusinessNoticeList 按 projId 找公告 id → readNoticeInfo(公告全文)→ 正则解析"第NNN包"段落;公告标题变化(二次挂网)自动重拉 |
| 公告全文.json | 公告 notCont 清理后全文(部分项目有) | readNoticeInfo |
| 包件清单_<projCode>.csv | 包件清单导出版 | 主服 merger write_pack_list_csv(合并 4 台后) |
| pack_map.json | targetProj + enterprises{企业: {单位/账号/信用代码/包件[](packId+审核状态)/时间/来源/记录[]}} | 三通道:①审计抓 ST → getSupplierPackageList?statusGroup=buyed(该账号报名列表)→ getBuyPackageList?projId=(企业→包件+bidderCheckStatusName 审核状态+保证金/报价模式/物资条数)主力;②8515 快照 findList bid_package_bidder_business23(每 6h 增量,来源="8515",缺包件标 PROJ_LEVEL);③企业全量比对(每企业 24h 全量一次,补遗漏) |

## 采集更新链路(答复"数据池更新机制")

```
4 台采集机(分片 V6_SHARD,60s 轮询,systemd 单进程)
  → /tmp/targets/<projId>/(5 文件)+ 根级告警 json
  → 每 5 分钟主服 crontab merger.py:tar czf 全量打包(6-8s/台,1100-1800 文件)
  → /data_raw/<机器>/ 扁平化(pid_文件名)
  → 合并 /data_pool/<projId>/ + build_index(stage 重算)+ 分类 json + gaps.json + health.json
```

- 健康检查顺序:health.json(心跳/延迟/WAF)→ merger 日志轮次时间戳(确认每 5 分钟一轮在跑)→ index updated(+8h 换北京)
- rsync_fail.json 是**历史瞬时失败记录**(如广州 10:52 连接失败),不自动清除——别把旧记录当新故障;看 health 当前状态为准
- 双进程修复后采集机唯一 collector 的判定:cmd 以 `/usr/bin/python3` 开头(有 V6_SHARD 注入)、PPID=1、systemctl MainPID 一致

## 单项目核验速查

- 8/31 全量公告入池核验:`公告_831.json` 的 projId ∈ index.json projects → 46/46 缺失 0(双进程修复后达成)
- 采集机 src 标记 grep:`grep -rl '"src"[ ]*:[ ]*"notice"' /tmp/targets/*/项目信息.json`(注意路径是 /tmp/targets 不是 /opt/v6/targets)
