# 数据平台 findList 表现状 + 历史全量拉取 + v6 merger/collector 运维

## 1. 数据平台表(无鉴权 findList)——2026-08-30 实测:全部 8/27 16:57 停更

| funcId | 内容 | 8月窗口量 | 用途 |
|---|---|---|---|
| bid_project_business23 | 项目主表 | 705 | 历史源(停更) |
| bid_package_business23 | 包件表(pack_id/proj_id/pack_code/pack_name) | 2,185 | 历史源(停更) |
| bid_notice_business23 | 公告表(not_title/proj_id) | 2,247 | 历史源(停更) |
| bid_package_bidder_business23 | 包件-报名表(proj_id/pack_id/buy_time) | — | 8515 快照源(停更 8/24) |
| aggregation_bfwz_bfwzpackage_a | 已结束项目包件(pack_id!) | 1,645 | 已结束项目兜底 |
| biddingandsellingsupplier 等 | 报告中的无锁报名表 | **0(已停)** | 不可用 |

- **condition 通道不通**(like 过滤全 0),只能走 params(start_time/end_time)窗口
- **企业字段全 null**(bidder_id/dwcode/phone/person/address 非空 0%)——只有 proj_id+pack_id+buy_time
- **8/27 后创建的项目查不到**(如郑州9次二次 8/19 创建也不在→覆盖范围有限,部分路局/二次项目缺失)

## 2. 历史全量拉取(2025-01~2026-08 分月)

```
每月 6000 条上限(6 页×1000)拉满,20 个月 = 12 万条
→ 5,231 项目 / 17,607 包件(8515 快照合并进 /data_pool/8515_快照/index.json)
buy_time 范围 2021-11 → 2026-08-24
```

## 3. v6 merger 运维(2026-08-30 修复的坑)

- **单实例锁必须 `import sys`** — fcntl.flock 拿锁失败时 `sys.exit(0)`,缺 import 直接 NameError 崩溃(锁被占时每轮 cron 崩)
- **rsync 增量**:listdir_attr 拿远程 mtime,本地同 mtime(<2s)跳过 → 全量 560 目录变秒级增量;每台 110s 时间预算 + ThreadPoolExecutor `f.result(timeout=125)` 防挂死(主服无 rsync/sshpass,纯 paramiko)
- **审计溢出判定**:滚动日志 5 页永远全满(500 条覆盖 ~1.5 天)——必须按"页1 内 60 秒 ≥100 条操作"才算真溢出,否则天天误报
- **采集机分片**:V6_SHARD=0-3 环境变量(systemd service 加 Environment=),proj_id 哈希 %4 → 每台 ~160 目标,防 637 目标×ST 请求爆炸
- **性能关键**:每个 ST 先拉 `getSupplierPackageList?statusGroup=buyed`(该企业已报名项目列表)→ 只对命中目标拉 getBuyPackageList → 请求量从 160/ST 降到 2-5/ST;企业全量拉取(_ent_full_)限频 4 次/小时并复用同一份 buyed 列表
- **发现顺序**:selectSelfSellList 默认排序混入 1118 个已结束项目(14=成交),15 页翻不到目标 → **必须按 status 参数过滤拉取:13=竞价中(1)/19=发布中(169)/22=待竞价(468)** = 637 个在网项目;过滤 projName 含"测试"
- 主服时区 UTC(日志时间戳),采集机 CST(日志差 8h)

## 4. 用户纪律(多次强调)

- **95306 一切操作(含浏览器/JS 抓取)绝不用本机,全走主服/采集机(paramiko 经主服)**
- 写操作(participateInProject/offer)= 永久红线;SM4 写接口已复刻但仅作研究
- 报告方法论(桌面 95306_完整渗透报告_20260828.md)为已验证基线,新发现优先对照它
