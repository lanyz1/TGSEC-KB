# 全历史四表收割(hf_pull.py)与拼表配方 — 2026-09-13

## 任务与规模(2026-09-12 全域口径实测,拼表对账目标)
| task | funcId | 全量规模 | 窗口参数 |
|---|---|---|---|
| b580 审核明细 | bid_package_bidder_business23 | 938,330 | start_time/end_time (datetime) |
| roster 名册 | biddingandsellingsupplier | 967,419 | startDate/endDate (date) |
| proj 项目 | bid_project_business23 | 54,305 | start_time/end_time |
| pack 包件 | bid_package_business23 | 156,488 | start_time/end_time |

端点/体不变:POST https://cg.95306.cn/proxy/dataplatform/api/findList,
body {funcId, appId:"system", pageNum, pageSize, params:[{key,value}…], condition:""}。

## 校准结论(09-13 实测,照抄可用)
- **pageSize=2000 全量返回**(不静默截断);**无 10K 深分页墙**:ps=100 pn=101(offset 10,000+)✓、ps=2000 pn=14 ✓、ps=2000 pn=6 ✓。
- 月片规模:b580 12K–23K/月;数据始于 **2021-01**(2020 全年 0);b580 2021 爬坡:1月192→3月12.5K。
- 页速:b580 ~2-3.5s/千行;roster 页更重(单月 23K=12 页≈116s)。全程 ETA:b580≈25-30min、roster≈40min、proj/pack≈10min。
- 磁盘 /data_raw 余 222G;月片 gzip jsonl 压缩友好。
- **窗口语义(关键)**:b580/proj/pack 严格 `> start` 且 `< end`(相邻月片零重叠,整分秒边界可能漏个别行,以总和对账);roster 是 `BETWEEN` **含双端点** → 相邻月片在月首日**重条,拼表前必须全行去重**。

## 运行时布局(主服 128.241.245.73)
- 脚本 `/opt/v6/hf_pull.py`(参数 `--task b580|roster|proj|pack --frm 2020-01 --to 2027-06 --ps 2000`;默认值即此);本地副本 `%LOCALAPPDATA%\Temp\hf_pull.py`。
- 数据目录 `/data_raw/95306_full/`:`<task>_<YYYY-MM>.jsonl.gz` 月片 + `ck_<task>.json` 断点(Python dict {月:行数},重跑自动跳过)+ `hf_<task>.out` 日志 + `hf_stat.py`(统计器)。
- 发射(幂等):`setsid nohup flock -n /tmp/hf_<t>.lock python3 /opt/v6/hf_pull.py --task <t> --frm 2020-01 --to 2027-06 --ps 2000 > hf_<t>.out 2>&1 < /dev/null &`
- 自愈 cron ×4(*/30,同锁文件;**跑完后应删除**):
  `*/30 * * * * cd /data_raw/95306_full && flock -n /tmp/hf_<t>.lock python3 /opt/v6/hf_pull.py --task <t> >> hf_<t>_cron.log 2>&1`
- 90 月片窗:2020-01..2027-06(早月空片也建 ck,未来新增数据由 cron 续补)。
- 快速进度:`python3 /opt/v6/hf_stat.py` → 每任务「月片数 总行数」四行。

## 守望与验收(本地 hf_watch.py)
- 150s 轮询,完成判据 = pgrep 锚定 `'^python3 /opt/v6/hf_pull.py'` 计数归零**连续 2 轮** + 每任务 ck 月片数 ≥90;`notify_on_complete` 自动叫醒。
- 大任务发射前先打校准弹(ps=2000 探、pn 深探、月片采样、df -h),别盲发射。
- 对账容差:总和 vs 上表目标允许 ±边缘行;缺口成规模时先查月片错漏,再把 `--frm` 提前补探。

## 拼表(收割完成后的下一步)
1. 月片 gz → 逐行 JSON;roster **先全行去重**(整行序列化 hash,消月首日重条)。
2. **buy_time 关联**:b580(uuid/pack_id/status/check_time/memo/buy_time) ⟕ roster(bidder_name/un_social_cr_code/buy_time) on buy_time → 企业×包×审核矩阵。
3. 富化:proj/pack 月片按 proj_id/pack_id 补项目编号/名称、包件号/名称。
4. 输出 CSV(项目编号,包件ID,企业名,信用码,审核状态码,审核时间,驳回原因,报名时间,…)→ gz。
5. 拉回本地 `D:/渗透/95306_历史数据_导入/`;删 4 条 hf cron;锁/日志按需清理。

## 发射踩坑(通用细节见 skill remote-daemon-ops)
- paramiko 对 `…&` 发射命令 `.read()` 会阻塞到超时(命令已执行);用非阻塞读取器。
- 锁被占时重发射会先把 `hf_<t>.out` 截断成稀疏空洞(flock 失败前重定向已生效);重发射前先 pgrep 查活。
- 多任务发射中途崩溃 → 部分已发部分未发;幂等"先查后发"验收脚本(hfchk2 模式)救回。
