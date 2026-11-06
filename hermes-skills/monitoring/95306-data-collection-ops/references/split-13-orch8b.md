## orch8b 补漏(手动触发/排障) ★老生产口径,割接后新链路见上节

```
cd /opt/v6 && setsid nohup python3 orch8b.py > /tmp/orch8b_cron.log 2>&1 < /dev/null &
轮询: tail /tmp/orch8b_cron.log;每台 worker 日志 /tmp/bk8_N.log;结果 /tmp/bk_result_N.json
```
- 单实例锁 /tmp/orch8b.lock(pid 存活检测);seen = /tmp/bk8_seen_N.json dict {token: 登录时间},6h 裁剪,旧 list 格式自动弃
- worker 每台扫 shard%rounds 窗(30min 窗),命中漏采名单(miss_names=平台-采集差集)才拉 getBuyPackageList
- **v9.21(9/10):已结束≤30天纳入补漏**——"结束后任何登录=补采窗口":缺口企业(近30天已结束 101 项目/741 家,双盲类)此后任何登录(查结果/报新项目)即回填其历史项目包件。过滤点 orch8b.py `elif stg == "已结束"`(bidStarttime≤30天,与 plat_enroll 名册窗对齐);bk_worker/collector 零改动;cron 每5分钟自动加载。详见 references/2026-09-10-v920-v921-ended-backfill.md
- 失败先看沪0 是否存活:任何台连接失败 worker 不启动 → orch8b log "FAIL 沪0: "(空错误=超时)

