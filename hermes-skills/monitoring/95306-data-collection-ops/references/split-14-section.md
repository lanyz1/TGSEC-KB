## 漏采判定与定向补采(用户问"是不是漏采了"时)

**先分三层定性再补**,别把平台自身节奏当成我们漏采:

1. **权威侧**(8515 快照 / plat_enroll_map)—— 核验法 = 最新快照行 vs 池 index **逐行比对**:新增项目 / 新增包件 / 状态落后 / 同级更晚审核 四项计数,全 0 = 没漏。**不许拿"池文件 mtime 停在上周"或"行内没有 `src` 字段"当证据**:合并函数是**幂等**实现(零变更不重写),mtime 不动是正常态(踩过:据此误判"增量合并从没落地")。
2. **平台字段会整体停更** —— `check_time`/`buy_time`/`hereor_time` 可因节假日/审核节奏停在某天。**诊断第一步 = 直连平台拉一行原始行、打印全部字段**(不要只留 KEEP 字段,停更的那个字段可能正好被裁掉),再比"采集机快照行数 vs 深翻页总行数",一致 = 没漏。
3. **逐项目明细**(公告全文 / 包件清单 / bid_status)才是真会漏的一层:停机分片(`md5(proj)%12==shard`)的项目那段时间没人拉。真缺判据 = 明细文件 mtime 停在停机时刻 + 权威侧该窗口有活动。

**池目录 mtime 不是新鲜度代理**(一次批量重合并把几万个目录刷成同一天);缺口量化用「权威侧活动 ≥ cutoff × 明细 mtime < cutoff」交叉表,冻结项目数 >0 才是真缺口。

**定向补采 = 在接管该分片的那台机上起独立进程**,不要往运行中采集进程的 `state["targets"]` 注入(下轮被回写覆盖,实测 75→85 又回 75/0)。骨架:

```python
import collector as C                      # 与采集进程互不干扰;merger 只看 /tmp/targets/,与 state 无关
pids = [...]                               # 缺口清单(权威侧活动 ∩ 明细冻结)
toks = [...]                               # 票源:递归抽 /tmp/targets/_rail.json + /tmp/v6_state.json 里的 32hex,
                                           #       先按 md5(tok)%12==本机 shard 排序逐张试(实测 146 张里 1 张即够)
st = next(t for t in toks if not C._in_cooldown(t))
targets = [{"projId": p} for p in pids]
C.fetch_project_details(st, targets)        # 逐项目明细(慢,限流节拍)
C.bid_status_check(targets)                 # 竞价/审核状态
C.try_fetch_bids(st, targets, None)         # 竞价记录
```
- 启动:`setsid nohup python3 -u /tmp/backfill_proj.py > /tmp/bf.log 2>&1 < /dev/null &`,再发短命令读日志(长连接会被掐)。
- 采集函数**内部吞异常且限流慢** ⇒ 判成功只看产物(`/tmp/targets/<pid>/` 里 `公告全文.json`/`包件清单.json`/`bid_status.json` 是否新增),不看返回值;日志长时间无新行 = 仍在跑,别重复启动。
- 收尾两段验收:①机上 `清单 x/y` 补齐且三件套齐;②`/data_pool/<pid>/` 抽样文件数 + mtime 落在补采后(merger 每 120s 拉),再跑一次缺口量化应得 **0**。
- 汇报口径:先说**哪层真漏、哪层是我们误读**(附证据),再给补采前后数字 —— 本轮两次误判(权威侧滞后、合并器跳过)都是靠"逐行比对 + 平台原始行全字段"推翻的。

详见 `references/miss-audit-and-targeted-backfill.md`。

**8515 快照链路巡检 / 权威完整性核验配方**（用户问「8515 快照更新正常吗」时用）：抓取器 `fetch_8515_inc.py` cron `*/30`（funcId `bid_package_bidder_business23`，按平台**内部更新时间**窄窗，经 RELAYS 中继，只在新行才落 `/data_raw/m_snap/`）→ `merger.merge_8515_snap()` 进 `8515_快照/index.json`（**对账键 = `[proj_id][pack_id]`**，用 uuid/bidder 会 0 命中误判「全丢」）→ `audit_diff` → 回写 pack_map → bot 菜单B 推送。核验 = m_snap 全量 ∪ 逐包件对账（缺 0 / 不一致 0）+ 平台**独立宽窗查询**交叉（缺 0）；池文件 mtime 不是新鲜度代理（幂等不重写）。详见 `references/8515-pipeline-and-completeness-verify.md`。

