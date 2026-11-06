# 漏采判定与定向补采(三层核验 / 独立进程补采)

适用:某台采集机停机数日(或被换机)后,用户问"是不是漏采了,把漏的补一遍"。原则:**先分三层定性,再补**——每层有独立核验法,判错一层就会误报或做整轮无用功。

## 一、三层各自怎么核验

| 层 | 内容 | 会不会漏 | 核验法 |
|---|---|---|---|
| 权威侧 | 8515 快照 / plat_enroll_map(报名·审核·中标) | 基本不会 | **逐行比对**:最新快照行 vs 池 index 条目 → 新增项目/新增包件/状态落后/同级更晚审核 四项计数,全 0 = 完整 |
| 平台字段 | `check_time`/`buy_time`/`hereor_time` | 不适用 | 直连平台拉一行原始行、**打印全部字段**(别只留 KEEP 的 8 个字段),看是否平台侧整体停更(节假日/审核节奏) |
| 逐项目明细 | 公告全文 / 包件清单 / bid_status / 竞价记录 | **会漏**(停机分片) | 该分片明细文件 mtime 停在停机时刻 + 权威侧该窗口有活动 = 真缺口 |

- 采集侧对权威快照通常是**每台各自增量拉、不分片** ⇒ 一台停机不影响权威侧;真正丢的只是它那一片的逐项目明细。
- 缺口窗口 = `/data_raw/<台名>/`(rsync 落点)最新文件 mtime 与其余台横比:明显落后那台即断供,该时刻即缺口起点。

## 二、四条反直觉坑(每条都实测踩过)

1. **`if changed:` 幂等合并** —— 零变更不重写 index ⇒ "index mtime 停在上周""行内没有 `src` 字段"都是**正常态**,不是"合并器从没落地"。判完整度只能逐行 rank 比对(见上表)。
2. **池目录 mtime 不是新鲜度代理** —— 一次批量重合并会把数万个项目目录刷成同一天(实测 4.4 万项同日),按 mtime 直方图会得出"明细早就冻结"的假结论。用「**权威侧活动 ≥ cutoff 的项目 × 明细 mtime < cutoff**」交叉表定缺口。
3. **单日窗口(`start==end`)返 0 行** —— 平台把零宽窗口当无数据。对账式补拉必须跨日:7 天窗 + 深翻页到末页不满 100 行(必要时两日窗格交叉验证)。
4. **`NON_MACHINE_DIRS` 只管健康/告警口径**,合并器遍历 `/data_raw` 是按目录分派的 ⇒ "新建落地目录(如 `m_snap`)被合并器跳过"**不是可用假设**(照此排查会空转数轮,踩过)。

## 三、定向补采(在接管该分片的那台机上起独立进程)

不要往运行中采集进程的 `state["targets"]` 注入:每轮结束 state 被进程回写,注入项直接消失(实测 75→85 又回 75/0)。

```python
# 机上 /tmp/backfill_proj.py —— 独立进程;产物落 /tmp/targets/,与 state 无关,merger 照常回传
import json, hashlib, collector as C
SHARD = 1
pids = json.load(open("/tmp/bf_list.json"))            # 缺口项目清单
# 票源:递归抽 /tmp/targets/_rail.json + /tmp/v6_state.json 里形如 [0-9a-f]{32} 的串
# 先按 md5(tok)%12==本机 SHARD 排序逐张试(实测 146 张候选里 1 张就够)
toks.sort(key=lambda t: (int(hashlib.md5(t.encode()).hexdigest(), 16) % 12 != SHARD, -len(t)))
st = next(t for t in toks if not C._in_cooldown(t))     # 先过冷却闸
targets = [{"projId": p} for p in pids]
C.fetch_project_details(st, targets)                   # 公告全文 + 包件清单(慢,限流节拍)
C.bid_status_check(targets)                            # 竞价/审核状态
C.try_fetch_bids(st, targets, None)                    # 竞价记录
```

- 启动口径:`setsid nohup python3 -u /tmp/backfill_proj.py > /tmp/bf.log 2>&1 < /dev/null &`,另发短命令 `tail /tmp/bf.log`(长连接会被掐)。
- 采集函数**内部吞异常且限流慢** ⇒ 判成功只看产物(每个 pid 目录里 `公告全文.json`/`包件清单.json`/`bid_status.json` 是否新增),不看返回值;日志长时间无新行 = 仍在跑,别重复启动。
- 一张可用票能补完整批:实测候选票 146 张,命中 1 张即把该批 20 个项目里缺的 10 个全部补回(`清单 20/20 (+10)`)。
- 新增/变更缺口清单只写文件(`/tmp/bf_list.json`)+独立进程消费即可,**零改动采集逻辑、零重启**;补采留下的 `/tmp/targets/<pid>/` 由 merger 正常回传入池。

## 四、收尾验收(两段,缺一不可)

1. 机上:`清单 x/y` 补齐 + 每个 pid 目录三件套齐(mtime = 补采时刻)。
2. 池侧:`/data_pool/<pid>/` 抽样文件数 + mtime 落在补采后(merger 每 120s 拉一次);再跑一次「缺口量化」应得 **0**(有权威活动但明细冻结 < cutoff 的项目数 = 0)。

汇报口径:先说**哪层真漏、哪层是我们误读**(各附证据),再给补采前后数字。
