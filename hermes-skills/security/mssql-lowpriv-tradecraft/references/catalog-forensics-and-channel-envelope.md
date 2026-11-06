# 目录级快查与通道考古（717kk 收尾实录 · 2026-10-14）

## 通道信封实测（查询设计先对齐这四条）

| 限制 | 实测值 | 对策 |
|---|---|---|
| 应用层单查询上限 | ~25–30s 静默砍（PHP-FPM；无 marker、无报错） | 大表全扫永远拿不到：改 TOP / 轻视图 / catalog |
| 单次标量读长度 | ≤~1900 字符 | 大结果分块；一次别贪 |
| 运行日志窗口 | 滑动 ~500KB ≈ 20 分钟内容 | marker 快采；超时后隔几分钟 late-collect 回捞 |
| 客户端超时预算 | ≥100s（内部重试循环 60–75s） | timeout 给小 = 杀在打印结果前（假「无输出」） |

轻查询来源：预置报表视图（本案 `vw_dayreguser` 一类）、当日表、catalog 视图。回避：base 表 COUNT/MAX、INFORMATION_SCHEMA 全量（大库超时）。

## 家族地图（一次看清上千张日表）

```sql
-- 按去 8 位日期后缀聚合行数（index_id 0/1 = heap/clustered）
SELECT base, SUM(ss) total FROM (
  SELECT LEFT(t.name,
         CASE WHEN t.name LIKE '%[_][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'
              THEN LEN(t.name)-9 ELSE LEN(t.name) END) base,
         ps.row_count ss
  FROM <DB>.sys.tables t
  JOIN <DB>.sys.dm_db_partition_stats ps
    ON ps.object_id = t.object_id AND ps.index_id IN (0,1)
) x GROUP BY base ORDER BY total DESC;
```

本案结果：OM_OperationLogsDB 共 7,619 张 → 有数据仅 3 族：`T_RoomOnlineLogs` 57,754,063（房间在线聚合：MobileCount/Android/IOS/Browser，无 PII）、`T_HallOnlineLogs` 1,674,686、`T_UserSetOperateLogs` 229。其余 7,600+（注册/操作/风控类日表族）全空。

## 墓碑判读（被清 vs 从未写过）

```sql
SELECT SUM(leaf_insert_count) ins, SUM(leaf_delete_count) del,
       SUM(leaf_update_count) upd, SUM(range_scan_count) scans
FROM <DB>.sys.dm_db_index_operational_stats(
     DB_ID('<DB>'), OBJECT_ID('<DB>.dbo.<表>'), NULL, NULL);
```

- 计数为**实例启动以来累计**（RDS 长期不重启 ⇒ 有历史意义）；TRUNCATE 不计 leaf_delete。
- `ins=0 del=0` + 全空 ⇒ **从未写入**；`del>0` ⇒ 常规 DELETE 清过。
- 名场面：`T_RegisterLogs` 家族 1,523 张日表（2022-02 → 2026-10，一天一张），列 = `id, LoginCode, Phone, Realname, Cardno, QQ, AddTime`（手机+实名+卡号+QQ = 整套 KYC）——**全 0 行 + ins=0 del=0** ⇒ 注册 KYC 在这套平台上**架构性从未落地**（不是被删，是没写过）= 「打码=源头无存」结论的最硬证据。
- 判定补充：看**最近一张日表**——今天的也空 ⇒ 管道已死/从未接入，而非定时清理。

## 多波 PII 列普查（单波必漏）

- 波1 手机形：`phone|mobile|cel|tel|msisdn` → 本案产出 34,249 明文（已交付）+ 1755 万打码（源头即打码）。
- 波2 身份形：`email|mail|bank|card|cpf|doc|address|realname|chave` → 新增候选列全部 0 行（email/银行/证件面干净）。
- 波3 无特征名字段表：通用变更日志（OldValue/NewValue 形态）**名字扫不到**——只能抽样看内容。
- 新发现的空列族照登记（本案：`HXTB_UserPolicyRecord_*` 打捞系风控分表 + `BankScore` 列）——「有结构无数据」本身是证据。

## 共享通道白嫖

同一错误日志混有**其他队伍/引擎**的探测、payload、翻列记录（本题识别出「CL」队 ~6.6 万发 schema 探测，payload 前缀可辨）。定期 grep 入案卷 = 白得一份「他们挖到哪了」的情报；他们扫空的方向 = 已被验证的死路，省自己的时间。

## 守望脚本三段式（长跑纪律）

- **watch → raw → parse 三段分离**：采集脚本只拉原始日志片段落 `raw`；解析独立脚本读 `raw` 落 `state/diff`。
- **heredoc 吃管道坑**：`echo "$R" | python3 - <<'PY'` —— heredoc 覆盖 stdin，解析器读到空输入**静默写 0**（表现为「秒败」假象，真排查烧过时间）。修复：原始数据落临时文件 + env 传路径（本案 `newreg_watch.sh` + `nr_parse.py` 组合）。
- **静默守望**：告警脚本 stdout 空 = 不投递；cron 只在有输出时提醒（不刷屏）。发现面 = 活边（新注册流）+ 对方动作（CL 扫描）+ 基线变化（手机形态）。

## 收尾时在跑的活体面（清单式）

- `vw_dayreguser` 新注册流（43+/日，全人名式，无手机形态）
- 运行日志轮询（marker / 他队扫描 / 新错误）
- 监督循环保活 `xwatch/xpoll`；30 分钟 cron 报警
