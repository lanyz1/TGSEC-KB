# 全量审核矩阵拼表管线 (2026-09-13 建成)

## 管线总览
1. **全量收割**（已完成一次, 2026-09-12/13）: 主服 `/opt/v6/hf_pull.py` 四任务
   - b580(竞价参与明细)=938,330 / roster(名册)=1,000,575 / proj(项目)=54,305 / pack(包件)=156,488
   - 落盘 `/data_raw/95306_full/{任务}_YYYY-MM.jsonl.gz`（90 月片, 2020 全空, 数据始于 2021-01）
   - 每任务 `ck_<任务>.json` 记录月完成数; 断点续传; cron(*/30) flock 自愈
2. **拼表** `/opt/v6/jfull.py`（30 秒跑完全量）:
   - 连接键 = `(proj_code, buy_time)`：b580.buy_time(秒级) × roster.buy_time；proj_id→proj表→proj_code 桥接
   - roster 可用率 99.6%（名册行含 bidder_name+buy_time+信用码）; 歧义键仅 0.03%
   - 产出 `/data_raw/95306_full/matrix/matrix_YYYY.csv`（UTF-8 BOM, 17 列）
   - 命中率 99.90%（979 行名册无记录）; 月度边界按 b580.id 去重（227 条）
3. **交付**: 本地归档 `D:\渗透\95306_历史数据_导入\审核矩阵_2021-2026\`（6 年度 CSV + preview + README）

## 审核状态码（三年全量交叉验证, 勿再用错）
| 码 | 含义 | 铁证 |
|---|---|---|
| 01 | 审核通过 | memo 恒空 + 审核时间全有 |
| 03 | 审核驳回 | **100% 带驳回原因 memo**（如"无资质文件"） |
| 22 | 成交/中标 | memo 空 + 审核时间有 |
| 00 | 未审核 | 96.7%+ 无审核时间 |

## 关键边界: 进行中项目(status=31)审核明细公开面不可见
- 西安79次(proj_id 3a5a0784-7bd6-4ce5-a855-dc56c23026fe)全库搜证: b580/proj/pack 表 **0 命中**, 名册(roster)有 70 行
- 即: 报名期/待结果公告期的项目, 其审核明细行(bid_package_bidder)不在公开列表; 31→14 翻转后重跑 jfull.py 即补入
- 参与者会话补录通道: `watch_xa79.py`（cron */10）盯票池 `bid2_tokens.json` st32 中属于 19 家的会话 → `getBuyPackageList?projId=` 拉取回写 pack_map; 无票时 filled=0（正常）

## 复现/增量命令
```
cd /opt/v6 && python3 jfull.py          # 全量重拼（30s）
zcat /data_raw/95306_full/b580_*.jsonl.gz | grep -Fc '<uuid>'   # 搜证
```
