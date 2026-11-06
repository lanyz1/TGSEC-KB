## ★ 漏采补采机制(手搓版现役 —— 用户问「现在的漏采补采机制是什么样」先读这份)

**三段链**：`gapgen`(cron `8,18,28,38,48,58`，`master/gapgen.py`，产 `gap_projects.json` + 名册 `/tmp/bk8_ctx.json` + 覆盖基线 `cov.json`) → `orch`(cron `2-59/5`，按项目补齐腿，点名 `tools/gap_once.py <ctx> <shard>`，12 台×30min 窗=6h 一圈) / `backfill`(cron `*/30`+`timeout 900`，票池深翻页腿) → 采集机 `collector/gapfill.py`(三条匹配：全名归一 / 简名唯一包含 / uid 直命中；**包件真写进 pack_map 之后才标票已用**)。**手动口** = bot 项目卡「🔄 补采包件」→ 只写请求文件 → `repackq`(cron `*/2`) → 点名一台机 `tools/repack_once.py`(force 强拉) → `done/<pid>.json`。

**★「📦 新增包件」运维可见性通知**(2026-10-08 上线,树 `v6rel_202610080354`):补采腿回写的 `packs_add`
过去**无人播报**(树内 70 处命中全是统计日志文案)。现由 bot `packnew` 线程(300s,`bot/push.py::check_pack_news`)
**无条件广播** —— 降噪三律(首轮只建基线 / 按 项目+账号+packId 永久去重 / `pack_scan_cap`)+ 只读
`pack_seen.json`。**别再挂回订阅通道**:`check_subscriptions` 首行 `if not subs: return 0` 而本机订阅数常年 0
⇒ 挂进去等于永不触发(本轮实测)。落点判据与验收锚点见 `references/notify-channel-placement.md`。

- **红线两条**：① `gapgen` 只产清单**绝不写 pack_map**(写入口只有 `master/writer.py`)；② bot 只读，`apply_enable=0` 只回执零写，真动作只在主控/采集机侧。
- **两腿输入形状不同**(projId vs 企业全名)，混用 = 池里凭空多一批空目录；`remote_root` 取机器代码树(`/opt/v6/current`)，写死扁平路径会让 12 台每轮 `can't open file` 且**腿静默瘫痪**。
- **★为何「名单有、库里没有」的历史真缺不会自动补**(必答)：在网腿只遍历阶段 ∈ live_stages(已结束直接 skip)；账号腿只消费 `gaps.json` 的 `企业报名缺口`，而该段要求**审计里有真实提交证据**，没证据的只落 `疑似仅打开页面`(只记账不告警) ⇒ 条目恒 0。**不给虚假希望**，只能手动 `v6m.py repackq --pid <pid>` 或定向 `backfill`。

机制逐段、cron 原文、读数口径与判据源码位点见 `references/gap-backfill-pipeline.md`。

### ★ 导出总表对账（平台/采集/表格家数不符、部分企业联系方式缺失）

先认口径再动代码：三口径验算闭环、字段/维度陷阱、联系方式源在全局池根、缺号 A/B 两类根因 ⇒
`references/export-reconciliation.md`；可直接跑的只读探针（零平台请求、零写入）⇒
`scripts/regcsv_recon.py`（`csv` 模式本地分析导出表 / `pool` 模式主控对账 + 缺号逐家探测）。

**★「🔹平台外 / 名单未含」有双根因**（① 匹配维度错：平台登记名在池内 `用户` 字段、`单位` 常是简称；
② 平台名单接口分页行级抖动，现有 `shrunk` 防抖只防「数量变小」）——修复落点、判决实验、量化收益、
生产形状验证配方见 `references/2026-10-08-platform-out-match-fix.md`。**只改匹配与呈现，不动三口径。**

**★ 票源两轨 + 断流体检（票簿不涨 ≠ 采集坏了）**
生产采集吃的是**采集机本地 rail 票池**（`tokenrailquery` 登录流水，逐机自采自用，写 `/tmp/v6_run.log`）；主控 `/opt/v6/bid2_tokens_cn.json` 只是**备用票簿**，由上海机 `audit_harvest_cn.py`（`auditlog` 审计域）产出、主控 `audit_harvest_relay.sh` 每 10 分钟 scp 回主控。两轨互不依赖。
- `[tok_merge] jwt=0 st32=0` **不是报错** —— 是搬回来的文件与上次逐字节相同、无新票可并；要看 mtime 是否停滞，不要拿它当失败信号。
- 判「采集是否出问题」按序查五项，**任何一项红就是采集侧问题**：① 12 台 `cstats.json` 心跳新鲜度（>15min 才可疑）② 采集机 `/tmp/v6_run.log` 的 `rail 流水 … 本机票 N（新增 M）→ 池 K`（`新增 M>0` = 票源活）③ 主控 `汇总/实时项目汇总_18列.csv` + `index.json` mtime ④ `v6m.py orch/backfill/priv/bot` 进程在跑 ⑤ 只有①~④全绿才去查那条轨的 crontab。
- 停用的定时任务在 crontab 里被注释成 `#DISABLED_<月日>(<中文说明>) <原cron行>`，原文存 `/root/cron.bak.<时间戳>` ⇒ **恢复 = `crontab /root/cron.bak.<时间戳>`**（先 cat 比对）。看到 `#DISABLED_` 一律按「有意停」处理，先问是否复活，别当故障修。
- 机队 IP↔机名/用户映射在 `/opt/v6/jumpers.json`；主控可经 `/root/.ssh/id_ed25519` 跳采集机。

**★ 探针读数的四类必须分记，否则 `hits=0` 会被误读成「权限被拒」**
`priv_loop.py` 把「`您没有该功能的操作权限`」「`未登录`」「`系统服务异常`（风控 `code=100`）」「`HTTP4xx/5xx`（网关）」统一记 `bad` ⇒ `hits=0` 只等于**没拿回业务数据**，**不等于被拒绝**。
- 定性票面权限只认三条硬证据：① 换票回包的 `authority` 字段 ② `loadMenu` 返回体大小（93B = 仅最小自助菜单）③ **活票**在真实业务路径上的业务拒绝文案（如 `initProjInfo` → `您没有该功能的操作权限`）。
- 下「权限/可达性」结论前，先把探针台账按回包**分类计数**（风控 / 网关 / 无权限 / 未登录 各多少）；502/503 与 `code=100` 一律算「没打进去」，剔除后再判。
- 用票做任何实测前先确认**票是活的**：存量票簿的票过期后打出来全是风控/网关噪声，会把结论污染成假「全拒」。

**★ 票的能力边界（含「能不能踢该账号下线」）**：见 `references/ticket-sources-and-probe-evidence.md`。

**★ 判任意一条腿「真的在产出还是空转」**（在跑 ≠ 有产出：票过期 / 蓄水断粮 / 权限链不足三类墙，
以及 `alive=True` 假活、归档副本判「从来没成过」）⇒ `references/leg-health-diagnosis.md`。

**★ 别名归并表 `ent_aliases.json`（曾用名/改名，2026-10-08 上线）**：落 `/data_pool/ent_aliases.json`，
结构 `{"updated","note","groups":[{"canon":现名,"aliases":[旧名…],"note","src":"user|auto"}]}`；
`bot/aliases.py` 热读（mtime 缓存，`$V6_ALIAS_FILE` 可覆盖）、`bot/render.py::plat_alias_match` + `regcsv` 差异⑤ 消费。
自动挖矿 `alias_mine.py`（cron `40 */6 * * *`，**自带内部 flock ⇒ cron/手工都不得再套外层 flock**，否则 Errno 11）
扫「名录同信用代码多名 / 池内同登录账号多名 / 档案池两表」，`--days 180` 全窗约 6 个名录窗 / 8.9 万行。
**判据（实证）**：① `统一社会信用代码` 相同 = 同一法律主体 ⇒ **即使两名时间交叠也判改名**（工商登记名 vs 平台常用名，实测广州飞信）；
② 「同类实体」不必字号相近（实测 石家庄永盛发机车配件贸易 ← 石家庄永涛废旧物资回收，同码）；③ 规范化包含关系 = 简称↔全称；
④ 2 字简称不滤（阈值 `<2`）。**候选清单里的「已覆盖」条目和纯脏数据（括号重复，实测中国电子产品可靠性与环境试验研究所）一律不录** ——
录进去会把错误显示名带进导出表。写入纪律：只增不减 + 备份 `*.bak_<ts>` + `os.replace` 原子替换 + `src=user` 永不被 auto 覆盖；
bot 热读 ⇒ **改别名表不用重启 bot**。现况 8 组（2 user + 6 auto）。

### ★ ST 池「最小改造 3 处」（2026-10-07 落地，发布前必读）

细节/判决实验/真池只读验收数字见 `references/2026-10-07-st-pool-rebuild-3changes.md`;**发布 8 关链 + 上线后生产侧验证配方(含「零日志判活性」「traceback 定代次」「字节偏移判最后一段是谁写的」「主控 /tmp 常是远端路径」)见 `references/release-rollout-and-verification.md`**。四条硬规矩：

1. **票寿命是两档、不是一档**：`rail.ttl_min=45` 语义 = **新鲜阈值**（超了只标 `stale`，须先 `probe` 验活）；**真淘汰线是 `ttl_max_min=180`**（票实测活 1–3h，旧口径把中位数票用到一半就删）。改语义必须在 conf 注释写明理由。
2. **读盘/请求主键一律用池目录名，绝不是 `info["projId"]`**：实测 14,379 个目录里 **325 个二者不一致**，按 `projId` 读盘这批**全读空**（也是量测口径的硬约束：不可按 `projId`、不可用 `bidStarttime` 当窗选器）。
3. **两条派活腿（orch/backfill）各用各的远端文件名**，共用同一 ctx 路径 = 互相覆盖的真撞车。存量缺口走**独立名额**（`stock_max_names`），在网名额永不被挤。
4. **★「有闸无门」是必查的一类 bug**：加任何冷却/冻结/限额/退避闸门前，先 grep 那个记账函数**有没有调用者**（实测 `Guard.note_acct_risk` 全库零调用、上层把 `risk` 结果静默丢弃 ⇒ 闸门永久空转、坏票每轮重打白烧配额）。改闸门必须**同时**接上「触发点」+「收手动作」，并用夹具断言「坏票不再被当 alive 处理」。

- **口径提示**：`plat_enroll_map` 顶层 622 条，**只有 515 条带企业名单** ⇒ 报数必须说清是「条目数」还是「可判缺口数」。
- **拆模块承载棘轮**：文件 >400 行 / 函数 >50 行 ⇒ 真拆（本轮 = 存量缺口逻辑外移 `master/gapstock.py::StockMixin`，gapgen 只留一行 `merge_stock()`）；拆的理由要写进新模块 docstring（棘轮 + 独立风险面 + 可单独夹具 + 坏也只坏自己那条链）。

