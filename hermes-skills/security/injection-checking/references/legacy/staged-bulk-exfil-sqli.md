<!-- archived from /root/.hermes/skills/security/staged-bulk-exfil-sqli/SKILL.md on 2026-10-21 -->

---
name: staged-bulk-exfil-sqli
description: "Use when dumping a whole DB through SQL injection."
triggers: [全库脱下来, 堆叠查询, staged exfil, 暂存表, 整库外带, bulk dump, STRING_AGG, 脱库引擎]
---

> 归档卡：原目录 `/root/.hermes/skills/security/staged-bulk-exfil-sqli`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/staged-bulk-exfil-sqli/…')`，不要相对 `references/legacy/` 解析。

# 堆叠查询暂存式全库外带 (staged bulk exfil via SQLi)

**何时用**: 注入点只能回显表达式结果(报错通道 ~200 字符/次), 但**堆叠查询成立**(`waitfor delay` 有差分 / 分号批处理生效), 而目标要"整库几百万行脱下来"。实测吞吐 ≈ 1 MB/s, 远超逐字符报错注入。

## 链路
1. **选暂存表**: 业务库里已存在、当前用户有写权限的表(判据 `has_perms_by_name('db.dbo.T','OBJECT','INSERT')=1`), 至少有 `nvarchar(MAX)` 列可装整块。
   **别用 `sys.partitions` / `dm_db_partition_stats` 判断表是否存在** —— 缺 `VIEW DATABASE STATE` 权限时它们静默返回 0 行, 会把真实存在的库误判成"零表"。改用 `sys.tables` 直查。
2. **payload 尾部必须加 `--`** —— 注入点后面往往拼着原生 SQL 尾巴(`ORDER BY x desc OFFSET 0 ROWS FETCH NEXT n ROWS ONLY`)。没注释掉就会出现 `Invalid column name 'X'` / `Incorrect syntax near the keyword 'ORDER'` 这类**假故障**, 让人误判成 INSERT 语句本身有问题。
3. **服务端打包 + 自校验尾标**: `STRING_AGG(字段, char(1)) + char(2) + CAST(COUNT(*) AS nvarchar(20))` ⇒ 每块自带"服务端声称行数", 客户端解析后可自校验, 不符自动重推 3 轮。
4. **分组推 → 立即读回 → 立即擦除** (见下)。
5. **三方一致才算成功**: 落盘行数 == 服务端声称行数 == 目录 `count(*)`。两个数字对不上就别宣布完成。
   JSON 逐行转储时按**可解析行数**判完整, 不看字节数 —— 400KB 的产物可能只装着 330/2297 行; 不达标必须在产物名与报告里标注「部分转储」, 禁止把部分当全量写进影响量化。

## 用血换来的规则
- **每组推完立刻读回 + 立刻擦除(只擦自己 tag)**: 最隐蔽的坑。若整表跑完才擦, 已暂存行随组数累积, 读回响应越来越大(实测量级: 累积 12MB 通得过 / 27MB 被掐 / 72MB 必断), 症状是"小表好好的, 大表莫名其妙断连"。改成守恒后单次响应恒定 ~1MB, 200 万行的表照过。
- **分页偏移 off-by-one**: SQL 用 `row_number() > off` 时, 偏移必须是 `i*per` 而**不是** `i*per+1`, 否则每张表静默丢第一行(症状: 33,781 vs 33,782, 差 1 行查半天)。
- **排序键要稳定**: `%%physloc%%` 实测分页不稳(曾丢 24 块)。改用首列 `ORDER BY [首列]` 兜底, 再用全列 `ORDER BY c1,c2,...` 二级兜底 —— 全列排序下并列行的值完全相同, 重复取/漏取都不改变最终结果集。
- **前缀镜像表要双份计数**: 二开/fork 系统的 `.env DB_PREFIX` 常指向「真身」表族, 而旧前缀表族原样保留并镜像同一份数据(如 `pre_*` 与 `pay_*` 行数一一对应)。只查一族就写「该表仅 1 行 / 这站没数据」会直接低估影响面; 结论里要写明哪一族是真身、两族各多少行。
- **PHP 站先过转义层再谈编码**: 目标用 `daddslashes()`/`addslashes()` 时单引号会被吃掉 ⇒ 字面量改用数据库自己的引用(PostgreSQL `$$...$$` 美元引用); 回显通道优先找能把表达式文本整段带回来的参数(形如 `backurl?param=`), 一次请求拿回结果比逐字符快两个量级。

## 无人值守健壮性(整库跑数小时, 必需)
- **push 和 pull 都要 try + 重试**(3 次 + 断线重建会话)。只包 push 不包 pull 是常见疏漏: 一次读超时就掀掉整张表, 前面几十块白跑。
- **断点续传台账**: 每表落 `{表: {ok, rows, recs, srv, file, ts}}` 到 JSON, 重启时跳过 ok 表 ⇒ 进程被杀只损失当前表。
- **每组打进度日志**, 别只在整表完成时打 —— 否则大表跑十几分钟, 外部看像卡死, 会误判"任务挂了"。
- **并行要分命名空间**: marker 前缀 + 产物目录 + 台账文件三者独立, 多个脱库任务才能并存互不擦除(否则互相删对方的暂存行, 双双空转)。
- **托管方式**: 用 `terminal(background=true)` 直接跑 python 进程本体; 前台 `nohup/setsid` 会被工具拒绝, 而"包装 shell(`nohup ... &` + sleep) + 立即退出"的写法会被回收并连带杀掉子进程(现象: 日志停在某表中间、无 traceback、无完成行)。
- **巨表参数**: 单块 150KB 时 200 万行表要数千块(数小时); 提到 400KB×2 块/请求(响应 ~1.3MB)可把块数砍到 1/3。块大小受"单次响应别超 ~2MB"约束, 与累积问题无关。
- **吞吐参考**: 5.8 s/块(150KB) · 小表每表元数据开销(列/行数/均长)约 15-20 s, 200 张小表 ≈ 1 小时。

## 痕迹与恢复原状
- marker 写进固定列(如 `Error`), 值带唯一前缀; 每表读完立即 `delete where 前缀 like 'HM:表:%'`; 脚本启动与结束各做一次**只删自己前缀**的全清。
- 收尾核验残留 = 0, 暂存表行数回到基线; 为跑任务而建的临时管理账号一次性全删并逐条核验。
