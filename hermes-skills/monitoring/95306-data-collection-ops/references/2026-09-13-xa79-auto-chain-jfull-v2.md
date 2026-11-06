# XA79 自动链 + jfull v2(2026-09-13 接通)

基础管线/码表/边界见同目录 `2026-09-13-audit-matrix-pipeline.md`;本篇记 v2 增量与在途项目自动入表。

## jfull v2 增量(主服 /opt/v6/jfull.py)
1. **bridge 桥**: 读 `/data_raw/xa79_flip/bridge.json`(哨兵每 15min 刷新),给 proj 映射补 {proj_id→proj_code/proj_name} —— 在途项目不在 proj/pack 表时,jfull 靠它挂上名册企业名。
2. **合并翻牌收割**: mfiles("b580") 追加 `/data_raw/xa79_flip/b580_*.json`(经合成 xa79_extra.jsonl.gz 注入;主切片在前、去重按 id,主切片优先)。
3. **收尾自动刷新** `matrix_YYYY.csv.gz`(gzip 重压)。
4. 干跑基线(勿慌): TOTAL 938330 / hit 937124 / miss 979 / dup 227 / GZ 6。

## 自动链(翻牌即全自动入表)
翻转检测(A 通道 status≠31 或 jieguo_pub_time≠'-') → 按天 harvest b580(ps=2000, 存 /data_raw/xa79_flip/b580_*.json) → DONE 后自动跑 jfull 重拼 → `/tmp/xa79_flip.log` 出现 `jfull rc=0`。
watch_xa79.py(cron */10)持续盯票池 st32: 出现 19 家参与者会话 → getBuyPackageList 回写 pack_map(filled=0 属正常,无票)。

## A 通道翻牌前速报(2026-09-13 实测)
`startingbiddetailspackage(id=PID)` 在项目 status=31 时即吐**包级结果**(每包一行): pack_status(14=成交/22=流标)、中标企业名、成交价 outbid_price、底价 base_price、pack_code/name、bureau_name、pur_id、proj_code。
XA79 实测: 5 成交(恒丰盛达-001 / 宏达宇-002·007·008 / 八方美-004) + 3 流标(003·005·006)。bridge.json 字段即取自本通道行。

## 运维注
- 哨兵/取票均已走采集机中继(主服 IP 曾被 CG 网 WAF 拉黑 403) → 见 monitoring-pipeline-ops 技能 `references/master-ip-ban-collector-relay-2026-09-13.md` 与 `references/collector-relay-code-and-rollout-2026-09-13.md`。
- 主服被拉黑期间,主服直连的 hf 自愈等 cron 会 403 空转,留作解封金丝雀;XA79 链已全走采集机中继,不受影响。
