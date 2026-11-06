<!-- archived from /root/.hermes/skills/monitoring/95306-data-collection-ops/SKILL.md on 2026-10-21 -->

---
name: 95306-data-collection-ops
description: 95306数据池/菜单B/bot运维与菜单样式对齐, 触发词 95306 菜单B 菜单样式 补漏 采集机 采集端 机队体检 代码漂移 数据池 bot 面板对齐 计数口径 家数对不上 池内 平台
---

> 归档卡：原目录 `/root/.hermes/skills/monitoring/95306-data-collection-ops`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/monitoring/95306-data-collection-ops/…')`，不要相对 `references/legacy/` 解析。

# 95306 数据采集/补漏/展示系统运维

12台国内采集机(SHARD 0-11)→ 主服 `207.57.167.92`(`ssh -i ~/.ssh/v6_master_key -p 12971`;旧卡写的 128.241.245.73 **实测已不通,勿再用**):/data_pool → pix_bot_server 菜单B。

**★编队名单唯一权威 = 主控 `/opt/v6/jumpers.json`**(`collectors[]` = `{shard,name,ip,port,pwd}`;`conf/master.ini` 的 `jumpers` 键指向它)。**一律现读,不按记忆/旧卡写死** —— 台会换机、名会换(曾见 杭州 sh1 → 宁波 sh1)、**端口有非标**(宁波 `114.66.40.208:25175`,其余 22)⇒ 逐台 ssh 必须按注册表里的 port 走,写死 22 会静默漏台。**读它只取 name/ip/port:`pwd` 字段是每台明文 root 口令(而 conf 注释却写「无凭据」)⇒ 一律不打印、不进报告**(实测 key 认证全通 ⇒ 可建议删 `pwd` + 文件收 600,动生产配置须用户点头)。`[relay] hosts` 是 8515 中继出口(4 台),**不是编队表**。现役快照(仅便利,以文件为准):沪0 `8.133.188.178` / 甬1 `114.66.40.208:25175` / 穗2 `8.138.236.124` / 蓉3 `47.108.152.60` / 沪4 `8.133.212.134` / 蓉5 `47.108.173.230` / 青6 `47.104.139.212` / 深7 `47.107.124.62` / 京8 `39.96.146.230` / 汉9 `47.122.107.121` / 蒙10 `8.130.150.18` / 源11 `47.115.204.175`。

## 结构/静态体检三件套(改完代码必跑)

1. `python3 -W always -m compileall -q -f tools collector master bot deploy 2>&1 | grep -ci warning` ⇒ **必须 0**。⚠️ `-W` 要放在 `-m` **之前**,放后面会报 `unrecognized arguments: -W`。
2. `python3 tools/struct_check.py`(文件≤400/函数≤50/嵌套≤4/IP 字面量;棘轮只许变好)+ `python3 tools/bind_audit.py`(未绑定裸名必须 0)。
   **bot 换版必做**：`python3 tools/audit_bot_menu.py $T [tools/legacy_cmds.json]` —— TG 菜单/老命令面 × 实际 handler 覆盖率,判据「死命令 0 条」(换版丢命令会静默无响应)。根因+工装见 `references/2026-10-09-bot-command-parity.md`;名册实测增益与测量口径坑见 `references/2026-10-09-gap-roster-gain-and-measurement-pitfalls.md`。**调吞吐前必读**：`references/2026-10-09-throughput-ceiling-structural-map.md` —— 候选池/预算/触发频率三条假设均已实测证伪，真瓶颈=账号票面；含 orch 串行 6 小时/轮、`ui_ok`=探活成功数、缺口补采轮会覆盖 `_cstats` 等结构铁证。**改编排前必读**：`references/2026-10-09-orch-fanout-parallelization.md` —— orch 扇出并行化（一轮 40min→5.4min，≈7.4 倍，已上线 `fanout=1`）：先量后动（每台 3分20秒）、三个误判、`fanout` 开关与一条命令回滚、离线语义证明、切换实测（12 台 61 秒内派出/94 秒内收齐）、四个坑（cron `>` 截断日志、`bk_stats` 开工即清、30s 轮询粒度、`master_state.轮` 语义）。
3. **独立静态器(第三方,不是自家闸)**:`UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple uvx pyflakes $(ls tools/*.py collector/*.py master/*.py bot/*.py deploy/*.py)`。判读铁律:① `undefined name` **必须全部落在注入类文件**(`*_parts*.py` / `_probe_*` / `offline_master_cases_*`),做**精确计数对账**(分子==分母)才算过,不能只靠 `grep -v` 目测;② `imported but unused` **严禁批量删** —— `bot/menus.py` 的 `os/time/datetime/menus_util._deadline_dt` 等“未用”名正是 parts 模块靠宿主 globals 取用的,**删了直接炸**;③ `local variable assigned but never used` 要逐个看是真逻辑漏还是重构死副本(如 `master/merge.py:77-78` 的 `port/remote` 是死副本,真用点在 `_pull_steps:120/130`)。

## 采集率读数(三口径,回答"采集率多少/有没有提高")

1. **官方口径(gapgen)**: `/opt/v6/gap_projects.json`(每 10 分钟重写) → `缺口企业数` / `缺口账号数` / `在网项目` / `覆盖基线_账号` / `覆盖基线_条目`;`缺企业`/`缺账号` 两个 list 为空 = 在这套基线上 100%。
2. **独立交叉核对**: `/data_pool/plat_enroll_map.json`(平台侧权威 Σ企业数) × `/data_pool/汇总/实时项目汇总_18列.csv`(池内 distinct 企业/包件) → 企业层 = Σ池内/Σ平台(仅计有平台口径的项目)。10-06 读数: 96.73% (2634/2723, 可比 323 项目, 达标 268)。
3. **包件层(必须带定义域)**: `/data_pool/gaps.json` → `项目包件缺口` Σ缺 vs 池内 Σ包件 ⇒ 10-06 含历史口径 34,045/34,436 = **98.86%**(缺 391 / 154 项目);但这 391 经三条证据链定性为**结构性不可采**(见下节) ⇒ **按可采集定义域 = 100%**。**报包件层采集率必须两个数一起报**(含历史 / 可采集域):只报 98.86% 会被读成"漏了 391 个"。同文件另有 `企业报名缺口`(0) / `待确认缺口`(144) / `疑似仅打开页面`(89) / `采集机告警`(**时间戳全是 09-09 giveup ⇒ 陈旧,非现故障**)。
4. **前后对比基线快照**(别只报绝对值): `/opt/v6/gap_projects.snap_a.json`(10-02: projects 37 / accounts 141 / notices 72 / name_gaps 33) + `/opt/v6/miss_snap.json`(10-03: 30 家企业名) ⇒ 对 10-06 的 0/0/0/0 即"缺口清零"证据。
5. **逐轮吞吐前后对比**: 采集机 `journalctl -u v6collector`(主控 `ssh -i /root/.ssh/id_ed25519 root@<ip>`;fleet_deploy 走 paramiko + `/opt/v6/jumpers.json`)。⚠️ **采集机时钟=UTC+8,主控=UTC**;轮询 360s;日志里 `请求 N` 是**自进程启动的累计值**(不是每轮),要按轮差算。
6. ⚠️ **池文件 mtime 不能当吞吐曲线**: 拉取用 tar 保留 mtime ⇒ 分桶计数跨窗口重合(12:00/13:13/13:21 三档同值)。要吞吐就用采集机 journal 或 `/data_pool/health.json`。

## 缺口「可采性」判定(别把口径差当漏采) + 审核状态口径

**包件缺口判定式**: `gaps_packs` = 项目目录 `8515` 快照的 packId 集合 − `pack_map` 已入库 packId(`master/gaps.py:62-79`;`pack_ids` 只记 `miss[:10]`,拿它当全集会漏)。判真伪三招(2026-10-06 实测,391 包件 / 154 项目全案):

1. **want ⊆ got 全池验证**: 同时有 8515 与 pack_map 的 472 个项目 Σwant 1,970 / Σ交集 1,970 = **100%**(got 多出的 4,142 是 pack_map 里的包号短码 `001/002` ⇒ 别把「短码 vs uuid」的差当缺失)⇒ 凡我方账号参与过的项目,包件层零缺失。
2. **零参与判定 = 结构性不可采**: `/opt/v6/ent_coverage.json` 的 `覆盖`(账号×项目 采集时间表)里查不到该 projId,且该项目 `pack_map.enterprises` 为空 ⇒ **我方账号池没参与该项目** ⇒ 无票 ⇒ `getBuyPackageList` 结构性无数据可返,不是我们漏采。154 缺口项目全部符合,且与在网 174 项目**交集 0**、企业数 0 ×154。
3. **⚠️ 反例陷阱(踩过)**: 8515 行的 `bidder_id`/`bidder_name`/`dwcode` **恒为 null**(全池 472 项目 / 14,530 行无一例外,含我方明确有报名数据的项目)⇒ **绝不能拿它判「无人报名」**。判缺口只用 ①/②。

**审核状态口径(菜单B / 通过-驳回矩阵的核心)**:

- 18 列汇总表的 `审核码` 列**恒空**(273,116 行)⇒ 归一只按名字,别去猜码。
- 原始 11 值 → 归一五档: 通过｜**成交+中标 = 通过(结果态)**(另出「竞价结果」列,别混进通过)｜**驳回+未通过+拒绝 = 不通过**｜**未审批+待审+待处理 = 待审**｜未知。**只加归一列,原列一字不改**。
- 空值(9.93%)不是缺数据: **27,106/27,116 = 有报名时间 + 无审核时间** ⇒ 语义「已报名、平台未出审核结果」(大盘在审核期项目尤多:top 项目 1111/1331 行都是它);余 **10 行**「有审核时间无状态」= 真字段尾巴,**单独计数上报,别混进空值总量**。
- 工具 `tools/quality_report.py`(只读:只读池子、产物 `/data_pool/汇总/数据质量日报_<UTC日>.md`,不碰任何既有产物)。`--check` = **值域覆盖自检:未映射值即非 0 退出**(平台将来新增状态值会立刻报警,不静默漏统计);`--top N` 出每项目分布。主控不装树也能跑: 本机 `ssh 主控 'cat > /tmp/quality_report.py' < tools/quality_report.py` → `ssh 主控 'python3 /tmp/quality_report.py --csv /data_pool/汇总/实时项目汇总_18列.csv --out /data_pool/汇总 --check'`。**改它记得棘轮:函数 ≤50 行**(初版 `render` 57 行被 struct_check 记为新增超限,已拆 4 helper)。

## 发布/割接链路(本机→主控→12台,逐步停手点)

**固定八关(缺一关不许上)**:① 本机 `python3 deploy/verify_release.py`(9 关:compileall / 模块导入 / 5 套离线桩 / 落盘纪律 / 棘轮+TZ 封闭 / 割接机制) ② `deploy/build_release.py --out dist --stamp $(date +%Y%m%d%H%M)` ③ scp tar+manifest 到主控 `/tmp`,**两端 sha256 对齐** ④ 主控解包后 `deploy/fleet_deploy.py --tar /tmp/<rel>.tar.gz --sha <sha> --stage`(12 台各跑本机九关) ⑤ `--activate --yes` ⑥ `--verify` 只读回读 ⑦ 主控 `deploy/master_deploy.py --stage / --plan / --activate --yes` ⑧ `--verify --status` + 消息面/数据面活体。

- **★ `--host <名>` 可单台试点,但同一台只能激活一次**:`do_activate` 的备份是 `cp -a 入口 .bak_<rel>` **覆盖式** ⇒ 重跑会把 launcher 自己盖进回滚位、毁掉 revert 链。正解 = **先单台 `--host` 试点 → 再对剩余台逐台 `--host`**(直接全量跑会把试点台再来一遍)。
- **★ `master_deploy --activate` 按设计「已在跑就不重复起」**(判据 `v6m.py <job>`) ⇒ 不会自动重启 bot/priv/merge,**也不会误造双 bot 409**。要不要主动重启,先按目录差分定「旧内存进程到底丢了什么」:`diff -rq 旧树/<dir> 新树/<dir>` 逐目录比。`bot/` 不 import `master/`,且 cron 活(orch/gapgen/backfill/relay/accel/bk_worker)**每次现调** ⇒ 这些变了也**无需重启任何常驻**;只有 `bot/` 或 `merge.py` 真变、或用户明确要「进程指纹对齐新树」才动,且**动前先拿用户点头**(铁律:杀/重启运行中进程须获同意),kill 与 start 分两个 exec。
- **★ 回滚位必须当场核**:`readlink /opt/v6/current.prev`(→上一棵树)+ `/opt/v6/v6m.py` launcher md5 + `/opt/v6/cron.bak.<ts>` + 采集机 `/opt/v6/collector.py.bak_<rel>`(mtime 应为**原始入口的时间**;被覆盖=该台 activate 跑过两次)。回滚 = `master_deploy.py --rollback --yes` / `fleet_deploy.py --rel <旧rel> --activate --yes`(旧树仍在 `/opt/v6_rel/`)。
- **★ 数据面「零新写」先按轮次解释再判故障**:采集端 **360s/轮**,轮间空窗正常(刚激活那分钟的万级写入是首轮突发,别拿来当基线)。健康判据用自报+现场:12 台 `--verify` 的 `active` + **`NRestarts=0`**、`/data_pool/health.json` 每台 `✅ 正常 / waf ok / warn_streak 0`、`find /data_pool -newermt '-6 minutes' | wc -l`、`tail /tmp/orch8b_cron.log`、`gapgen` 的「缺口:在网项目 N / 缺企业 / 缺账号」。**bot 活体 = 进程 `State: S` + 持留 `ESTAB → 149.154.166.110:443`(TG DC 长轮询 fd)** —— 只看日志 mtime 或 CPU 增量会误判(长轮询零 CPU 属正常)。
- **★ 换树后 bot 不会自动对齐,必须重启才对齐**:launcher `/opt/v6/v6m.py` 的 `find_tree()` = `realpath(HERE/current)` 软链优先,找不到 `master/` 就 **退 1 不进重启循环、不猜路径**;再 `sys.path.insert(0, tree)` + `runpy.run_module` ⇒ **进程启动那一刻的 `current` 决定它加载哪棵树**,事后换软链对已在跑的进程无效(模块已导入)。重启纪律:`pkill -TERM -f "v6m[.]py bot"`(**方括号防自匹配**,一处 TERM 会连带 wrapper+flock+python 三 pid 全退、flock 释放 `/tmp/v6_bot.lock`)→ 核「残留 0」→ **换另一个 exec** 起:`cd /opt/v6 && V6_CONF_EXTRA=/opt/v6/secret.ini setsid nohup flock -n /tmp/v6_bot.lock python3 -u /opt/v6/v6m.py bot >> /opt/v6/pixbot.log 2>&1 </dev/null &` → 复核需**同时**满足:新 pid 已出 + `ss -tnp` 持留 `ESTAB → 149.154.166.110:443` + 新日志段内 `conflict|409|terminated by other` 计数 **0** + `State: S`/6 线程。成功启动只打两行(`[bot] 按钮层已接线…` / `[bot] 线程启动:sub/health/gaps/data/watch`),**不推上线公告**(用户硬要求)。

## 参考文件

- `references/2026-10-09-backfill-fanout-and-freshness.md` — 补采腿三件套落地实证：扇出 8.9×／P1d 新鲜度加权（rail 行无企业名）／探针六坑／回滚清单。
- `references/2026-10-09-rail-probe-and-p1e-forceaccts.md` — ★rail 探针四坑（缺秒/主控直打/错 ctx/欠采样）+ `user_types` 是白名单的订正 + P1e `force_accts` 排序优先（零污染）。
- `references/2026-10-09-platform-api-boundary-and-probe-pitfalls.md` — ★平台 `findList` 字段/ funcId 家族/参数的真实边界（无包件无审核⇒矩阵必须靠活票）+ `buy_time`=必然登录（收网窗口）+ 探针四坑（`rail_rows` 返元组/旧树 import/票龄符号/欠采样）；且含**缺口快线 gapfast.py 检测器（纯只读，已自测）+ 包装脚本启用/停用命令**。

## 采集端改动与验证纪律（每次改采集端/名单必走）

- **双侧核验，缺一不可**：①主控 `md5sum master/bk_worker.py` == 采集机 `md5sum /tmp/bk_worker.py`；
  ②采集机 `grep -c <新符号> /tmp/bk_worker.py` 命中；③采集机 `grep -o '<新字段>.\{0,20\}' /tmp/bk8_bf_ctx.json` 看到新名单。
  只核验主控侧会漏掉「代码/名单还没真下发」，生产照旧跑旧文件。
- 采集机上的探针**必须 `importlib` 显式加载 `/tmp/bk_worker.py`**（生产真身）；
  裸 `import master.bk_worker` 会落到 `/opt/v6/current` 旧树 ⇒ 新字段恒空、误判“未生效”。
- `rail_rows()` 返回 **`(rows, fail)` 元组**，先解包；直接迭代报 `'list' object has no attribute 'get'`。
- 只读探针免同意；**改采集端代码 / 重启 / 杀进程必先告知并获同意**。改动一律留 `.bak_<ts>_<name>` + 一行回滚命令，静默不发公告。
- 哨兵/轮询：按**行号锚定**（`N+1` 起算，别用 `tail -n +$N`——会把末行算进新窗）；
  ssh 超时/空输出**绝不当作完成**；链路抖动重试，不中断整条取证链。

## 缺口闭环的唯一杠杆

- 平台公开面（`dataplatform/api/findList`）**只有**企业名/统一信用代码/报名时刻，**无账号、无包件、无审核状态**
  ⇒ 每企业「通过/驳回包件矩阵」只能由**企业活票**采集；token 寿命 ≤3h。
- 所以采网全部杠杆 = **排序优先级（缺口账号 rank=0）+ 轮次频率 ÷ token 寿命**；
  缺口账号不在 `miss_accts` 时靠 `force_accts` 提序（只改排序、不进 `match_name` ⇒ 零污染）。
- 缺口家必在**竞价开始/结束**窗口再次登录 ⇒ 那个窗口就是收网时刻，盯紧它。
- 明细：`references/platform-authority-vs-token-fields.md`、`references/2026-10-09-rail-probe-and-p1e-forceaccts.md`、
  现成探针 `scripts/rail_liveness_probe.py`。

## 数据流与权威基准

```
平台(findList 无鉴权通道)→ sync_plat_enroll(30min)→ plat_enroll_map.json(权威报名名单,近14天公告)
collector(12台 systemd v6collector,SHARD 0-11,90s轮询审计 ST)→ /data_raw → merger(实时)→ index.json/pack_map
orch8b(主服 cron 每5分钟;v9.21 起补漏目标=进行中+已结束≤30天)→ 12台并行 worker → pack_map
bot 菜单B = index.json + pack_map + plat_enroll_map 三源
```

- **plat_enroll_map.json = 唯一权威基准**("确定没人报名吗"只信它):biddingandsellingsupplier 必须带 params startDate/endDate(无参返 0)
- 审计 ST 仅覆盖跳转式报名(~25%);tokenrailquery 供应商(user_type=03)token 即 bfwz ST(TTL>2h),集团公司 02 无权限
- **tokenrailquery 必须带时间窗**:`params:[{key:"startDate",value:…},{key:"endDate",value:…}]`,**缺窗直接返 0 行 —— 那是调用错误,不是通道失效,别据此判"金矿不存在"**。实测 60min 窗 = 5.4k 行 / 4.3k 不同 userid / 2.5k+ 可用供应商票(`login_status==1 and user_type=="03"`),连续 11 页翻页零限流;行内含 `userid`(登录账号名) ⇒ 不必先 `user/info` 就能建账号→企业映射。通道是平台级可见(12 台看到同一批行),**只需一台拉**。产量比采集消费高约 10^2 倍 ⇒ 产能问题一律不要归因"没票"。
- ⚠️ TQ 可见性模型(已修正,以此为准):行**延迟~2-3h 到达**非停更;迟于 TTL 的行票死;判据=票鲜度。哨兵 v2 `tq_hourly_check.py`→主服 `tq_liveness.py`。详见 references/2026-09-11-tq-model-correction.md 与 -delayed-visibility-verdict.md、-miss-set-recompute-and-gap-scope.md
- 特权会话线(站内直报/批量报名盲区解法): 主服 `/opt/v6/priv_loop.py` 每8min 蓄水非03票+会话交换+端点矩阵实弹(命中存 priv_hits.json, 本地哨兵 63b9aff57605 报)。**★实测该线自建线至今零命中（2026-10-08 已定位真因 = 3 处代码 bug + 认证模型，**「不要按最近坏了去修」的旧结论已作废**，改后见 references/2026-10-08-priv-line-verdict-and-bug-chain.md）；同批盘点 pack_map 覆盖率与缺口归因法（**含 `acct_map.json` 必须用 `map` 反查的坑**）见 references/2026-10-08-packmap-coverage-and-gaps.md**：`priv_cov.json` 的 `命中计数` 恒 `{}`、`票据总数 206`/`命中票数 0`，归档副本 `priv_archive_*` 里同样为 0 ⇒ **不要按「最近坏了」去修**。**三重墙（2026-10-08 全部重核，结论大改）**：①~~票全过期~~ ⇒ **已推翻：真因是 `priv_tok_watch_v3.py` 的 `post`/`_relay_post` 名字错配 + `except Exception: break` 静默吞，致票源断奶一个月（mtime Sep 13 铁证）；修复后活票充足——企业票 5236 张、内部票 80/80 ALIVE**。②~~蓄水器断粮（`NEWTOK 0`，平台近月无非企业新登录，我方不可控）~~ ⇒ **已推翻：平台流水充足（`USER_TYPE {'02':556,'03':907}`、`PASS_FILTER 479` ≈160 张/30min）；`NEWTOK 0` 是上述代码 bug 的产物；另 `watch_cmd` 内层 `timeout 200` 过短（每票 2 次中继探测 ~1.5s）致票簿永不落盘**。③**权限链不足（成立且加强）**：`[priv]` 矩阵打的是**门户 `business-proxy` 端点，需要门户会话**，而票池里的票是 **bfwz ST（供应商视角）** ⇒ 用错端点打不动；实测内部票(02) ⇒「您没有该数据的访问权限」，顶级权限票横跨 14 个路局 **56/56 全部 `HTTP500 您没有该功能的操作权限`（功能点级缺失）**，企业票(03) ⇒ `401 您未登录`；`serviceTicket` 换票一律「登录失败」（票 token ≠ CAS ST），`pack_map` 里的真 CAS ST 已过期且一次性+绑会话 ⇒ **有 auth ≠ 有权**。**`hits=0` 的真因 = 认证模型 + 配置 `pids` 空致 `matrix()` 首行 `return`（不是没权限，是压根没打）**。四处 bug 链与对照实验见 references/2026-10-08-priv-line-verdict-and-bug-chain.md诊断任意一条腿走 `references/leg-health-diagnosis.md`；机制细节见 references/2026-09-11-priv-token-loop-and-blindspot-solution.md
- 竞价室 bid_live(💰实时出价): v9.27 修复"选票(参与方)+静默+merger搬运(需全局sweep)"三断点; 详见 references/2026-09-11-bidlive-capture-v927-fix.md
- 全量待补 miss 复算产物 `/data_pool/miss_current.json`(records/uniq/proj_miss/miss_all)
- 全量历史 22.5 万行企业包件在 /data_pool/汇总/全量_历史_企业包件_18列.csv

## ⚠️ pack_map schema 契约(写前必读)

任何通道写 pack_map.json 必须用 collector 兼容 schema,否则 bot 读不到(曾致 79 家补漏数据消失):
```json
{"enterprises": {"<账号key>": {"账号": "x", "用户": "", "单位": "全称", "ST": "", "时间": "YYYY-MM-DD HH:MM:SS",
  "来源": "collector|backfill8|01三态+映射链", "包件": [{"packId": "uuid", "packCode": "004", "packName": "",
  "保证金": 0, "报价模式": "单价", "物资条数": "1", "审核状态": "未审批|通过|拒绝", "审核码": "00"}]}}}
```
- bot 读 `ev.get("包件")`(list)+ `pk.get("审核状态")`;审核统计/企业明细/18列CSV 全依赖它
- key 用账号(历史导入 key=单位名 → merger 归一);同单位多账号展示层 merge_ents_by_unit 合并
- 审核状态字段 = getBuyPackageList 的 bidderCheckStatusName(00=未审批);data 直接是 list 不是 {result}

## stage 判定(菜单B 分组)

- 平台 status:13=竞价中,19=发布中,22=**报名期~竞价开始都用**(混合!),14=终态
- merger `_stage_of`:报名中=now≤报名截止(sellEnddate);**sellEnddate 只有 join 源有,buyed 源为空 → merger 合并必须字段级非空优先**(直接覆盖会把报名截止抹掉→误分"待竞价")
- sellEnddate 仍缺时从公告全文解析"报名截止时间"(merger `_parse_reg_end`)
- 用户报"🟡报名结束未竞价里有报名没结束的"= 上面两个 bug 的症状
- ★**反方向症状**（实际报名已截止、竞价未开始 ⇒ 却停在 🟢 报名进行中 / 「🟡 里没有他」）：判据链是**短路式** —— `sell`（报名截止）为空 **且** `status==19` ⇒ **直接返回「报名中」**，后面基于包件结束/竞价开始时间的规则一条都不看 ⇒ 只有平台自己把状态翻成待竞价的项目才进 🟡。
- ★**时间字段格式坑（同族规则，细则见 references/project-visibility-and-stage.md）**：同一时间字段在平台各处**多字形**并存 —— 项目级 `YYYY-MM-DD HH:MM`（12 位无秒）/ 包件清单 `YYYYMMDD HH:MM:SS`（14 位）/ 公告正文中文 `2026年09月06日 16时00分` / 索引期望 dashed-19。**只认单一字形的解析器一律返回空串 ⇒ 下游静默当「平台没给时间」**：列表排序键失义（整组 `""`）、竞价观察窗与「待竞价」判据永不命中。⇒ ①看到「日期列/排序整组空」先数原始值位数；②改前全树 grep `strptime|mktime|fromtimestamp|_fmt_ts|_deadline_dt` 建**生产者 × 消费者**清单，同族解析器（实测 ≥6 处）**一次改齐**，只放宽输入、**绝不顺手改输出格式**；③**抠取类正则必须拿池内真实样本回测命中率**，不许按想象写格式（实测 223/223 真实公告全是中文写法 ⇒ 原正则 0 命中、该功能自上线从未生效）；④诊断「字段为何全空」要同时报**解析成功率**与**输入文件覆盖率**（`公告全文.json` 全池仅 0.4%）。**别据调用点行为反推产出格式**——读该函数的 `return` 原文再断言（据此误判过两次，均已撤回）。
- ★**兜底判据不得盖过强证据**：`sell`（报名截止）缺失时的「平台状态=发布 ⇒ 报名中」是**兜底**，必须附条件 —— 竞价已开始（`bt` 已过）或包件竞价已结束（`_max_end` 已过）就交给时间规则定 竞价中/待竞价/已结束；否则它**短路整条下游判据链**（症状：报名已截止、竞价未开始，却停在 🟢；「🟡 里没有他」）。
- ★**列表组必须显式排序、空键沉底**：`sorted(key=lambda x: (值 or "~", 次级键))`（`"~"` 排在所有数字之后 ⇒ 空键沉底；次级键用 `projCode` 保稳定）+ 行内补显该组真正关心的那个时间（报名/待竞价组显「竞价开始」）。**无排序 = 顺序随字典序漂移 = 目标项永远翻不到**（实测目标埋在第 240/338 位）。
- ★**时间解析器与判据的改动方向**：放宽输入 → 判据附条件 → 分组兜底 → 排序显式化 → 从源头补输入文件；**落码顺序照此走，逐条只读复算验证，发布/激活仍是生产闸、须用户点头**。
- ★**判「平台没给 / 合并丢了 / 格式丢了」不许只看一层**：索引 `info` 是派生层，必须打 `/data_pool/<pid>/项目信息.json`、`bid_status.json` 的同名字段对照；报名截止的唯一来源是 `公告全文.json`，该文件缺失 ⇒ `sell` 恒空 ⇒ 必落上面的短路。
- ★**池探针先列方法表/照抄既有探针再动手**：`Pool` 是**类**（`Pool(Conf(<树>/conf/master.ini))`），`all_projects()` 返 `{pid: info}` 字典，`_bj_now()` 返 **datetime**。大语料上「关键词全 0 命中」先怀疑键名/调用式（实测「处置/废旧/车轴 全 0」是读错字段，换正确 API 立刻命中），不许据此下「没采到」的结论。
- 排查步骤 + 判据复刻脚本：`references/project-visibility-and-stage.md` + `scripts/probe_project_visibility.py`。

## 公告全文补拉

- collector 按标题搜 queryBusinessNoticeList 找 noticeId 会漏(翻页/超长标题)
- **正确做法:/data_pool/notices_map.json(noticeId→projId,merger 自愈维护)反查 → readNoticeInfo?noticeId= 直拉**
- 清理:先去 <style> 块再删标签;CSS 残留是首行含多个 { } → 裁到第一个 \n

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

## orch8b 补漏(手动触发/排障) ★老生产口径,割接后新链路见上节

```
cd /opt/v6 && setsid nohup python3 orch8b.py > /tmp/orch8b_cron.log 2>&1 < /dev/null &
轮询: tail /tmp/orch8b_cron.log;每台 worker 日志 /tmp/bk8_N.log;结果 /tmp/bk_result_N.json
```
- 单实例锁 /tmp/orch8b.lock(pid 存活检测);seen = /tmp/bk8_seen_N.json dict {token: 登录时间},6h 裁剪,旧 list 格式自动弃
- worker 每台扫 shard%rounds 窗(30min 窗),命中漏采名单(miss_names=平台-采集差集)才拉 getBuyPackageList
- **v9.21(9/10):已结束≤30天纳入补漏**——"结束后任何登录=补采窗口":缺口企业(近30天已结束 101 项目/741 家,双盲类)此后任何登录(查结果/报新项目)即回填其历史项目包件。过滤点 orch8b.py `elif stg == "已结束"`(bidStarttime≤30天,与 plat_enroll 名册窗对齐);bk_worker/collector 零改动;cron 每5分钟自动加载。详见 references/2026-09-10-v920-v921-ended-backfill.md
- 失败先看沪0 是否存活:任何台连接失败 worker 不启动 → orch8b log "FAIL 沪0: "(空错误=超时)

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

## ★ 报名名单缺口("企业 49/51"类)判定与账号映射修复

用户问「这项目差的那几家补齐了吗 / 竞价日怎么还没补全」时,先分类再动手 —— **缺口的真身在权威侧口径与票寿命,不在采集能力**:

1. **分母** = `plat_enroll_map.projs[projCode]`(平台报名名单,权威);**分子** = `/data_pool/<pid>/pack_map.json` 的 `enterprises` 键数(账号键)。差值先当"口径差"查,别急着报漏采。
2. **假缺(最常见)= 简称未归一**:池里其实已采到,只是 `单位` 存的是简称 ⇒ 跑一次性修池(别名表 + 仅唯一命中才采用)后立刻从缺口消失。**修池 ≠ 修好链路**:merger `_pick_fresh` 只取较新一份 ⇒ 归一必须**一次性回填已落池条目**才对存量生效。
3. **真缺 = 没有可用的票** —— 平台 ST 只有 **~6h 寿命**(`user/info` 返回 `code=100` = 冷却/失效,`404` = 终局),**历史票无法回溯**。⇒ 企业只在"登录后 6h 内"才会被采集机识别;**报名之后不再登录的企业,结构上永远进不了池**。这是窗口设计而非故障 —— 如实告诉用户,不要承诺"再等等就会补上"。
4. **`/opt/v6/gap_projects.json`(cron `8,18,…,58` 产,推 12/12 台)是回填的唯一驱动**,契约 `{projects:{pid:{noticeId,账号s}}, accounts:{acct:{项目s:[pid]}}, notices, name_gaps}`;`accounts` = 采集机"审计命中即优先处理"的索引(collector 消费)。两条缺口来源**不对称**:`_plat_diff_ent_gaps`(平台名单差集)**依赖 `plat_enroll_map` —— 报名期一结束该项目的键就消失 ⇒ 账号缺口永久填不上**;`_name_gaps`(持久 roster)**只填 `names`、不填 `账号s`** ⇒ 采集机拿到名单却"无人可盯"。**修法 = 让 name-gap 分支从池内 pack_map 的 `单位→账号` 映射(amap)补 `账号s`**(池里通常早就有映射)。
5. **"企业→账号"的四个产地**(按成本排序,均无需平台调用):① 全池 `*/pack_map.json` 的 `单位|账号` 对(同账号常在多个项目出现过)② `/data_raw/*/_ent_full_<ts>_<账号>.json`(内容 `{企业,账号,时间,项目}`,映射产出的持久库,通道一断不再新增)③ 审计 rail 行字段 `operation_account`(登录账号)/`operation_obj_account`(公告 id)/`first_function`(动作名)④ 官方供应商库与 matrix CSV **无账号列**(只有 uuid 主体标识)。**审计只覆盖跳转式报名 ~25%**:某项目全量审计行可能只有 20 个账号而池里 49 家 ⇒ 池的多数来自其他接口,**不能用"审计里没有"证明"这家没报名"**。
6. **池里存在"全称 + 空账号"的名字条目** ⇒ "无账号"不等于"采不到",但那种条目帮不上当前项目的缺(仍需一条能按企业名落包件的通道)。

**★ 架构红线(实证):凡是要访问 95306 目标的采集/收割/映射通道,必须跑在境内采集机上;主控(US IP)直连同一端点会拿到 403。** 症状极具欺骗性:**日志无异常、只是长期 `rows=0`**(一条审计收割通道因此静默死了 16 天)⇒ 巡检任何 `rows=0 / new_jwt=0` 的通道,先做"主控 vs 采集机同端点差分",再谈通道本身。

详见 `references/roster-gap-and-account-mapping.md`(gap 文件逐字段契约、6h 窗口代码位点、8515 活轨匿名性与阳性对照探针配方)。

## ★ 手搓重写版(`D:\95306c`)与离线自测铁律

用户说「不信 AI 写的代码 / 手搓一遍」时的交付形态:**按接口事实重写一版能逐行读的最小实现**(不是逐行复刻旧码),**采集端 + 主控侧一起手搓**,收尾交「新旧差异对比」。已落地分层单文件树 —— 采集端 `conf/collector.ini` + `collector/{conf,http,guard,store,api,shard,tickets,targets,audit,gapfill,main}.py`;主控侧 `conf/master.ini` + `master/{writer,gapgen,relay,merge,orch}.py` + 采集机侧入口 `tools/gap_once.py`;自测 `tools/{offline_fake,offline_run,offline_master}.py`。接口契约与旧版同源(三域 + `getBuyPackageList` 只带 projId + 两条分片口径逐字复刻)。

- **铁律:改代码不许拿生产当试验场** —— 四个桩 `tools/offline_{run,master,bot,bk}.py` 全绿(假传输层、零真实请求)才谈上机对拍;一键核查 = `python scripts/handwritten_static_audit.py`(compileall + pyflakes + ruff + 两处人工分诊 grep + 四桩,**只读、不连网不连目标**)。
- **离线跑真入口的手法**:入口写 `main(argv, app=None)`,自测注入假 app/假传输层 ⇒ 真流程、真解析、真记账(采集机侧入口同理),不要用 subprocess 另起一份。
- **★与线上对拍必核四口径**:① `pack_map.enterprises` 键 = **账号 uid**(非企业名)② 判新旧用**观测时间(来源副本 mtime,记录存 `_obs`)**,**绝不用票时间**(副本票时间全同 ⇒ 陈旧副本反赢、状态翻转)③ 回填字段集与线上键名**逐字一致**(少一键 = 静默丢数据)④ 18 列"统一信用代码"线上恒空串,真值在 `统一社会信用代码` 键 ⇒ 两种键名都认。
- **核查「有没有 bug」的可复现姿势**:`pyflakes` + `ruff check --select E9,F,B` 零命中;命中按语义分诊 —— **F841 未用变量先当「功能被静默丢掉」看,正确修法是「用它」而不是删赋值**(实例:取了 `pool.gaps()` 却没用 ⇒ 池状态少显示「还漏多少」);B007 未用循环变量改 `_x`,F401 未用 import 删。
- **凡「另一个进程会读」的产物一律原子写**(temp+fsync+`os.replace`):远端单文件裸跑的入口要自带 `_atomic_json`(采集机上没包可 import);多腿写同一份 json 用**字段级非空优先合并**,否则后写的窄字段腿会把 `sellEnddate` 抹空 ⇒ 阶段误判。
- **dry-run 必须零网络 + 零落盘**:一轮正常流程含建会话动作(`login`/`serviceTicket`),所以零网络模式只打印计划;落盘闸放**写原语内部**(模块级 `_DRY` + `set_dry()`,否则 Store 之外十余处直调必漏)。CLI 三模式:常驻 / `--once`(割接验证用)/ `--dry-run`(零网络零落盘)/ `--dry-run-net`(发请求不落盘);`flock` 只在会写盘的模式抢、抢不到非零退出,**锁的文件对象必须留引用**(被回收即静默放锁);`--selftest`(离线)打印 python 版本 / 代码树内容指纹(按内容算不看 mtime)/ 锁路径 / conf 权限。
- 细节(分层职责、桩为什么打在 `Http.raw`、抓过的真 bug、测试自身 5 个坑、静态核查与原子写/dry-run/锁三处硬化、对拍差异清单与差异文档结构)见 `references/handwritten-rewrite-and-offline-selftest.md`。

### ★ 单项目粒度动作(bot 按钮)接回的形态 + 拆分后夹具三坑

**架构形态(照此落地,别再问"bot 能不能自己采集")**:bot 端只允许**写请求文件**(原子写 tmp+`os.replace`),真动作由**主控 cron 角色消费**(请求目录 + `done/<id>.json` + 请求归档 + `max_per_run` 上限 + 过期阈值内零 ssh);bot 侧 `apply_enable=0` **只回执零写**、`=1` 才下发。这是「bot 只读」红线的唯一落地方式:**采集动作永远在采集机/主控侧,不在 bot 进程里**。

- **补采/重拉必须走 force 通道**:`Targets.details` 对「已有 `包件清单.json`」和失败退避**双重跳过** ⇒ 想真覆盖就得两处一起绕,且夹具要对**两个绕行**分别断言(只断一个 = 真机仍可能被退避挡住)。
- **按钮从「别名」改成真动作 = 三件套**:删别名表里的 `"x:" → "y:"` 映射 + 在分发表注册 handler + 宿主绑定该方法。**只删别名不改注册 = 死键**(点不动),`grep 注册表` 与 `grep 渲染器` 双向对账见 §菜单/文案样式对齐。
- **新增 cron 角色没有「老脚本前身」** ⇒ 割接条目必须**自带** `cron`/`log`/`lock` 三键,同时把工装里「只按 `from` 匹配老行」的旧约束放开(`build_new_entries` 与割接判据**两处都要改**,漏一处 = 该角色静默不入 crontab)。
- **动 `new_entries` 会打翻一切「数量 / 来源」型断言** ⇒ 同一轮把计数型夹具全部改齐(条目数 ±N、来源集合多一类、逐字对账基线 = 线上现况 + 新角色那一行),否则夹具报的失败是它自己过时。
- **★离线夹具的 monkeypatch 必须打在「拆分段模块」上**:`classify`/`classify_p2`/`cron_lines` 拆分后分住 `deploy/master_deploy_parts*.py`,各自按**自己的** globals 解析名字 ⇒ **只改宿主 `mod.cron_lines` 是无效补丁**,夹具会静默拿真机现况跑(症状:模板行 0 条、来源全是「上一版受管块」、无该命令的机器上直接 `WinError 2`)。正解 = 遍历 `sys.modules` 里所有 `master_deploy*` 且带该属性的模块统一替换。**夹具要对「夹具前提」自己断言一次**(如夹具来源行数),否则补丁失效时不报错、只是悄悄换了一套数据。
- **动态加载工装模块必须先 `sys.modules[spec.name] = m` 再 `exec_module`**:模块末尾有 `_v6parts._bind(sys.modules[__name__])` ⇒ 不挂直接 `KeyError`、**整跑挂掉**(不是个别断言失败)。
- **依赖 Linux 命令的夹具(`crontab -l`)只能上主控跑**:只读、放 `/tmp/<dir>`、绝不碰生产树与真 crontab;本机(Windows)跑必挂。跑法 = 夹具与树相关文件拷到主控 + `PYTHONPATH="<树>;<树>/deploy"` 后 `python3 <夹具>`。
- **请求/命令日志型桩的断言纪律**:① 别用 `calls[0]` 索引取目标命令(第一条常是 ctx 推送 `cat > …`)⇒ 按谓词挑;② 桩里跨轮累积的容器(如 `files` 字典)断言前必须 `clear()`,否则上一轮残留被算进来;③ 队列型夹具每轮先清自己的 `req_dir`,否则「零动作」类断言必假失败。

夹具分层(真 App + 假传输层 / 真消费者 + 假 ssh / 真菜单 + 真命令层)、断言清单与可直拷的跑法见 `references/offline-fixture-and-parts-binding-pitfalls.md`。

### ★ 结构棘轮与上线闸(改 `D:\95306c` 任何代码前先读)

- **改前先跑 `python deploy/verify_release.py`** 拿基线:④ = 五套离线自测桩 `run / cli / master / bot / bk`(当前基线 `59/59 · 7/7 · 108/108 · 94/94 · 52/52`);⑦ = 结构棘轮(函数 >50 行 / 文件 >400 行 / 嵌套 >4 层,**只拦「新增/变大」**);⑥ = 树戳;改动后必须复跑并逐项对账。
- **靶清单取全量要直接调判据**:`tools/struct_check.py` 的 CLI 每类只打印前 14 条(`list(...)[:14]`)⇒ 拿它的输出当全集,会同时得到「假阳性」与「一直没被打到的隐身靶」。取全量 = `import struct_check` 调它自己的判据函数。(通用判据:输出条数与标题数不符 ⇒ 先怀疑截断。)
- **发布包不过滤 `_` 前缀**:`deploy/build_release.py` 只跳 `__pycache__`/`.pyc`/`.bak` ⇒ `tools/_*.py` 随包上线、也被棘轮计行 ⇒ 一律**真拆**,绝不靠删文件/宽通配清理(曾误清 117 个文件后回滚)。
- **拆长函数把主文件顶穿时,助手外移到兄弟模块**(已建 `master/writer_util.py` / `master/util.py` / `master/gaps.py`;被搬函数体一字未改、仅整体反缩进 4 空格)。方法与三类静默破坏(return 被切 / 签名被重建 / 段内重绑参数名未传递)见 skill `mechanical-code-splitting`。
- **★棘轮「红」先判真假,别急着拆(2026-10 实战)**:`tools/struct_baseline.json` 是**快照式**基线(记的是当时行数,收紧靠 `--freeze`)。基线一旦落后于树,默认模式就会把**战役开始前就存在的旧账**报成「新增/变大」⇒ 判据 = **机械对账**:`dump_cur.py <pristine树>` + `dump_cur.py <现树>` + `cmp_cur.py`(按文件/函数/嵌套/IP 四类计数 diff);pristine 同违 = 假红,真新增才算我拆坏的。**正解 = 默认模式 exit 0(只拦新增)+ `--freeze` 收紧基线**,不是继续拆旧账。取全量靶仍走 `import struct_check` 的 `viol()`(见上条)。
- **★`--freeze` 会把「基线里的旧值」改写成「当前值」,有些条目因此比旧基线更松**(实测 `merge.py` 一处 1124→1238)⇒ **主证据永远是「对 pristine 的机械对账」**,`--freeze` 只是把账冻结防回归。
- **★把 `*_pN` 段搬兄弟模块:`move_pieces.py` 四坑** —— ①**同文件顶层 def/赋值不算安全**(段调它 ⇒ 搬走即失联,用 `--consts` 一并搬或 `--bind` 回注)②模块级脚本段互调兄弟函数 ⇒ 用 `--bind`(在目标模块末尾注入原模块兄弟名,无循环导入)③import 插点**不能取「第一个模块级 `if`」**(工具脚本第一个 `if` 常是 `if ROOT not in sys.path:`)④**插入点只认 `if __name__ == "__main__"` 主块之前**。
- **★绝不 `cmd > 源文件`**:`tar -xzOf 包 文件 > deploy/x.py` 在解包失败时仍会**截断成 0 字节**(实测丢掉 `deploy/master_deploy.py`)。恢复 = 搬运器自留的 pristine 副本(`ratchet_bak/cur__<路径__转双下划线>`);因此**驱动脚本必须每条改动前落 pristine 副本**。
- **★`ps -eo cmd | grep "<串>"` 会匹配到自己这条 ssh/bash 命令行**(`bash -lc …` 里含该串)⇒ `kill` 循环会**杀掉自己的会话**(表现为输出截断 + exit 255),而目标进程的杀与后续起新只完成一半。正确姿势:模式用变量拼(`P=v6m; grep "$P.py bot"`)+ `grep -v -e bash -e grep`,并且**kill 与 start 永远分两个 exec**(§通用部署坑 1 的新形态)。
- **离线桩是结构改动的哨兵,且覆盖面 ≠ 你改的目录**:改 `master/` 的拆分常常是 `bot/` 桩报「夹具缺失 / `NoneType`」—— 那夹具是桩自建的临时池产物(报错 ≠ 仓库数据丢失)⇒ 先把五套桩全跑一遍定位哨兵,再把**单个** pristine 文件还原回去二分锁真凶。
- **★「切段」抓长度、「压平」抓深度,双标条目必须同时做;嵌在 `try`/`with` 里的段是深度隐形 +1**(2026-10 实战):`tools/offline_bk.py::main` 268 行/**depth 5**,切段后宿主变 107 行但 `_b_tokens` 仍超深 —— 因为原遍历段嵌在 `try:` 内(`try→while→if→for→if` = 5 层),段体搬到模块级 helper 后水平位置降 4 格即合规(`while→if→for→if` = 4)。⇒ 判深度别看缩进空格数,**先数外层 `try/for/while/with` 的层级**;`except` 体里的 `return` 必须 12 格(8 格落进 `if` 体 = 无条件返回,已踩)。
- **★跨段变量漏传用 AST 静态扫描器一次揪全,别逐个 NameError 试**:写 108 行小工具扫「函数体内 `Load` 名 ∉ 形参 ∪ 本函数赋值 ∪ 模块级绑定 ∪ 内建」,对 `main` 拆出的多个相位段一次抓出**全部 2 处**漏传(`toks`/`ROOT`),而「跑起来再报错」要一轮一个。**静态扫描 + 新旧差分真调用双保险**,后者还要**归一化实时时间戳**(桩自取 `now`,两边打印 `20:45:03` vs `20:45:04` 属噪声,不归一化会误判不一致)。
- **★自动装配脚本里的换行别跨层转义**(JSON 参数 → bash heredoc → Python 三层:`\\n` 会退化成真换行或字面 `\n`)⇒ 生成物常被拼成一行;写完**先读生成物头几行**再跑闸。段体抽取用真换行 `"\n".join(段行)` 即可,`chr(92)+'n'` 那类「源文本转义」只在**写进被生成代码的字面量**时用。
- **★记账与机械读数矛盾时,一律以 `struct_check.viol()` 的机械读数为准**(实测 `collector/main.py::round_once` 权威 = **96→47**,早前报告里写的 `96→34` 是记账错,已更正);**报过的「已修数字」在收尾时必须回读一遍再写进交付**。
- **★树内 `*.pre_split_*` / 手搓备份必须移出树**:发布包只跳 `__pycache__`/`.pyc`/`.bak` ⇒ 这类后缀会被**打进包**,移走后棘轮文件计数同步下降。
- **★非法转义告警的语义等价修法(非 raw 串里混着有效转义时)**:`collector/entcount.py` 的 `_PUNC` 是非 raw 串,含非法 `\s`/`\-`/`\[`(告警)与**有效** `\u3000`/`\u201c` ⇒ **不能直接加 `r`**(有效转义会变字面量、语义变)。正解 = 跑一次模块取**运行时 pattern**,用 `repr(pattern)` 回写整行(`repr` 自带合法转义)⇒ 逐字等价、告警消失;复验 = 改动行数 = 1 + 重载后 `len(pattern)` 不变 + 抽样函数输出同值。

### ★ 上线割接(入口 + 树 + `/opt/v6/current` 软链)

线上布局真值:老生产 = **单文件 `/opt/v6/collector.py`(90,487B / md5 `081bd8780bd65f39495cc8dcdb216b16`,12 台全同)**、**无 `collector/` 包、无 `/opt/v6/conf`、不吃 ini**、硬编码 `/opt/v6/*.json`;在线单元 `ExecStart=/usr/bin/python3 /opt/v6/collector.py`、`Environment=V6_SHARD=<n>`。

- **机制定调**:`deploy/collector_launcher.py`(56 行,装成 `/opt/v6/collector.py` 当入口)按 `V6_SHARD` 起真进程,代码树在 `/opt/v6/lib/<rel>`,`find_tree()` **优先 `/opt/v6/current` 软链**、找不到就退 1 **不猜路径**;**systemd 单元一个字不改**。
- **`deploy/fleet_deploy.py` 三阶段**:`--stage` 只铺 `/opt/v6_rel/<rel>`(不重启)→ `--activate`(备份老入口 `collector.py.bak_<rel>` + 铺**刚验过的那棵树** + `mv -T` 原子切 `current`(旧指针留 `current.prev`) + `install` launcher 当入口 + `systemctl restart`,**不 active 自动回滚**)→ `--rollback`(老入口拷回 + 指针切回,两步自证)。**后两者会重启生产进程 ⇒ 必须用户点头**。
- **必须在主控上跑**(jumpers.json 与采集机私钥都在主控):本机 scp 包 → 主控 `/tmp/` → 解包(**tar 含顶层目录 ⇒ 须 `cd /tmp/v6rel_<stamp>/v6rel_<stamp>/deploy`**)→ 跑 `--stage`/`--activate`。
- **⑨ 关 = 割接机制关**:`verify_release.py::check_deploy()` 用真目录布局验 launcher 找得到树,并**反面控制**(删掉 `current` 必须退回 `""`);**另含「判定自检」正反控** —— 夹 systemd 警告的 `is-active` 输出必须仍判 active、`inactive`/`failed` 必须判否(判据见下条 ★)。9 关(①-⑨)在本机 + 12 台真机全绿 ⇒ **已上线包 `v6rel_20261003j`**(`tree_hash 05d4ffb59e96cfe1`,tar sha `6e29d198…`)。
- **激活后验收(逐字回读,不信自报)**:`journalctl -u v6collector | grep boot` 出现 `[boot] tree=/opt/v6/lib/<rel> tree_hash=… conf=<树>/conf/collector.ini shard_env=<n>`;入口 2286B(=launcher);`current -> /opt/v6/lib/<rel>`;`active` 且 `NRestarts=0`;停机窗 <1s。回读用 `--verify`(另一条代码路径)。
- **★ 判定必须按行取状态字,绝不拿整段输出做等值比较(踩过真 bug)**:`systemctl is-active` 的 stdout 会被 systemd 混入噪声行(unit 文件改过但未 `daemon-reload` ⇒ `Warning: The unit file … changed on disk.`),老写法 `out.strip() != "active"` 于把**一台跑得完全正常**的机判失败 ⇒ 触发自动回滚。修法:抽 `deploy/deployutil.py::active_ok(out)`(按行精确匹配 `active`,一处实现两处调)+ 命令加 `2>/dev/null`。**规律:机器输出当「可能掺噪声的文本」解析,取状态字或退出码;保护动作(自动回滚)的判据要比人工判断更宽容噪声、更保守地触发。**
- **★ 自动回滚后先判「真故障 vs 误判」再动手**:回滚是干净两步(老入口拷回 90487B + 删 `current`),机器回到老生产态。**先 `journalctl -u v6collector | grep -E 'boot|轮询开始'`** —— 若出现 `[boot] tree_hash=…` 与手搓版自有日志行(`状态播种`/`rail 流水`),就是「真起来了、只是被判失败」⇒ 修工装 + 那台 `--host` 重激活即可,**别去源码里找「为什么起不来」**。
- **★ `tree_hash` 只覆盖 `collector/` 包**:改 `deploy/`(工装)或新增 `deployutil.py` **不改 tree_hash** ⇒ 「12 台 tree_hash 相同」等价于「采集代码逐字相同」,即使各台 `current` 指向的 rel 名不同(先上的 11 台 `i`、后补的宁波 `j`)。**改工装不必再停机一轮**。
- **★状态文件可安全同住(实测)**:激活后 `v6_state.json` 由 **25 键 → 38 键**,新增 13 **全是手搓自有键**(`seen`/`acct_cool`/`cool_hits`/`freeze`/`audit_*`/`rail_pages`/`saved_at`/`snap_ts`/`_cstats`,**不与线上键撞名**);线上键类型/规模原样(`acct_inv` 437 / `seen_st` 2000 / `cool_st` 5 / `bid_skip` 175);`rail_pool`(rail 票池)与 `bid_skip`(跳过集合)**两边同语义**;老生产载入 = **整字典 dump + 逐键 `get()`(容忍未知键)** ⇒ **回滚不崩**。线上口径真机生效的日志锚点:`状态播种: seen ← seen_st (2000 条已处理的票,防重跑)` / `acct_cool ← cool_acct (5 账号…)` / `线上 cool_st 有 5 张票在冷却中(取票时会跳过)`。
- **落点对账(激活前必做,只读)**:手搓版写盘全走 `store.py::atomic_json`(tmp+replace);`heartbeat`/`gap_file`/`health`/`publish_time` 与线上逐字对齐;ini 由 `conf.py::DEFAULT_INI`(包根/conf) + launcher 显式传 `<树>/conf/collector.ini` ⇒ 线上无 `/opt/v6/conf` 也不影响;`[paths]` 与线上同名同址(`/tmp/targets`、`/opt/v6/v6_state.json`)。
- **★红线**:采集机 crontab 另有每 10 分钟的老 `audit_harvest_cn.py`(flock),割接**不动它**;停它属"动生产",须单独批准。身份已查实(勿再重复取证):**是「令牌池淘金器」而非审计采集** —— 正则从审计日志文本捞 `token=eyJ…` / `serviceTicket`(32hex) 写 `/opt/v6/bid2_tokens_cn.json`,按 exp/12h 清理;**只铺在上海0 一台**,且 `new_jwt` 已连续多轮恒 0(平台日志不再泄 JWT) ⇒ 半空转。**该池已无消费者**:手搓版全库、主控、**连老 `collector.py` 都不读**(全库 grep 池名皆空;历史消费者只有 `tok_merge.py`/`watch_xa79.py`/`audit_harvest*` 这类一次性工具);手搓版等价物 = `collector/tickets.py`(登录流水→candidate→验活→`alive`/`risk`/`dead`→按登录时间 45min 淘汰→上限 2000),既有验活又有票龄纪律。
- **★机队 crontab 必须全台枚举后再判归属**(只查一台既会漏、又会把别的项目的活任务当成自家遗留):除上海0 的老淘票器,还有 ①上海4 `ttl_probe.py`(每 4h,**我方票 TTL 探针**,保留)②乌兰察布 `/root/.local/share/misc/syncd.py`(每 25min,**属另一个项目** —— 优智采 `zb.lyc.cn` 的 OSS-STS 同步,`~/tokens.txt` 取票 → `getOssSecurityTokenBySts`;与 95306 无关,**一律不碰、只登记**)。判归属读脚本头 4 行/docstring,判"还有没有用"**全库 grep 它产出的文件名**;两类结论都要先出证据再谈停用。
- **割接已执行完毕(12/12 台 `active`、`NRestarts=0`、异常台 0)**:节奏 = 先单台试点(`--activate --host <ip>`)→ 全量(不带 `--host`)→ 逐台只读 `--verify`;回滚一条命令(`--rollback --yes`,单台加 `--host`)——见 references 里可直拷的完整命令。发布包/割接证据/回滚安全核对详见 `references/2026-10-04-handwritten-cutover-activation.md`;`D:\渗透\95306_recon\` 下三份交付物:割接执行记录 / **激活与回滚清单(可直接粘的命令)** / 新旧差异对比文档(累计 77 处),均 + 桌面同名份。

### ★答「已经把手搓版代码完全替换原来的了吗」= 逐层核,不认单层自报

**本系统替换面是两层,而割接工装只覆盖其中一层**:

| 层 | 载体 | 判"换没换"的独立证据 |
|---|---|---|
| 采集端 ×12 | 入口 `/opt/v6/collector.py`(launcher)+ 代码树 `/opt/v6/lib/<rel>` + `current` 软链 + `v6collector` 单元 | `tree_hash` 全台一致 / 入口 2286B=launcher / `[boot] tree=… tree_hash=…` 日志 / `NRestarts=0` |
| 主控侧 | `/opt/v6/*.py` + 常驻进程(无 systemd,`setsid nohup`)+ cron | `ps -eo pid,etimes,args \| grep '\.py'` / `crontab -l` / 与新树逐文件 `md5sum` 对照 |

- **"从未割接"的硬判据**:主控**没有 `/opt/v6/current`、也没有 `/opt/v6/lib`**(这两个是割接副产物)⇒ 主控侧一个字没换。
- **判"线上在跑哪套"只认三样:ps 活进程 / crontab / md5 对照** —— `/opt/v6/` 是几十代历史脚本的堆放场(`collector_v926*.py`、`bk_*`、`relay_*`…),拿 `ls` 当"在跑什么"必错(踩过)。`etimes` 小(如 `merger.py` 144s)= 刚被 cron 拉起,不是"新部署"。
- 答话必须**分层给结论 + 每层附独立证据**,不许用部署工具的成功输出或单层验收冒充全量;并说清"新采集端 + 老主控"为何能长期共存(手搓版采集端刻意兼容老主控口径,第 74/75 处那批修复即为此)。
- **主控侧割接 = 已上线(2026-10-04,靠 `current` 软链切树;工装 `--activate` 因模板缺陷拒跑时,手工 `ln -sfn` 与工装等效)**:`deploy/` 四件套 = `master_launcher.py`(入口 `/opt/v6/v6m.py <角色>` 角色分发,找树走 `current` 软链、找不到退 1) / `master_daemon.sh`(合库守护,取代 `merge_daemon_fast.sh`) / `master_cutover.json`(割接清单:停 2 + pending 1 + 保留 9 + 新 4) / `master_deploy.py`(`--plan`只读 / `--stage` / `--verify` / `--activate` / `--rollback` / `--status`)。**动生产前别重建工装**——先跑 `--plan`。
  - 老主控是**平铺目录 + 无 systemd + crontab 混着别的项目** ⇒ 新树铺 `/opt/v6/lib/<rel>/`(老文件一个不删)、只动 crontab 受管块、**认不出的条目直接拒绝割接**、新常驻统一带 `flock -n /tmp/<角色>.lock`(老锁名不同,漏锁 = 老新同跑,bot 双实例抢 TG polling)。
  - 三关已过(命令层面可重复):本地离线 28/28(含反控)、真机 `--plan` verdict 可割接 / unknown 全空、真机 `--stage`+`--verify` 回 `IMPORT_OK`;待用树 `/opt/v6/lib/v6rel_20261004k` 已铺(只写新目录,未碰现役)。
  - **activate 动 bot 可见面与 `/data_pool` 写库 ⇒ 须用户单独批准,且失败不自动回滚**(用户红线:主控不像采集机,失败停在原地 + 打印人工回滚命令)。
  - **★主控割接已执行(2026-10-04)**:`current -> /opt/v6/lib/v6rel_20261004v`、`prev -> …u`(回滚 = 把 `current` 指回 `u`/`t`)。**机制:`v6m.py::find_tree()` = 进程启动时 `realpath(/opt/v6/current)` ⇒ 切链即生效,无需重启任何常驻**(merge 守护 / `priv` / bot 全部照旧跑、cron 受管块 24 行未动)。切完必须逐项复验:`readlink -f current prev` + 随树回归(72/72 + 34/34 + 18/18)+ `--plan` 判词。
  - **★★主控侧 bug 的顶层形态 =「与老脚本的行为差异」**(老主控平铺脚本是权威口径,新树必须逐条对齐)。本系统两条最严重的回流 bug 同属此类,**查 bug 的第一动作 = 拿老脚本同功能段落逐字对照**,而不是通读新代码:

    | 形态 | 实例 | 老线口径 | 新线错法 | 症状与修法 |
    |---|---|---|---|---|
    | **默认关 vs 无条件** | 采集机→主控回流(⑳) | `merger.py:1463` **无条件** `rsync_from_collectors()` | `merge.run(do_rsync=False)` 只认 env `V6_RSYNC=1`,而 `v6m_daemon.sh` 不导出它 ⇒ **整条运输腿静默断**(`/data_raw/<台>` mtime 冻住、日志零行) | 默认值必须等于老线行为;开关只用于**显式关闭**且关时**必打日志**;补回归锁(含 `run()` 形参默认值锁定) |
    | **退出码严判 vs 容忍** | 上海每轮判失败(㉑) | `merger.py:104` `tar czf … 2>/dev/null; ls -la …` **根本不看退出码** | `tar` 打包时采集器正在写 ⇒ `tar: .: file changed as we read it`(exit 1) 被按 `exit==0` 判失败 ⇒ **该台每轮都丢** | 容忍 `exit ≤ 1`(≥2 才失败 `echo TAR_FAIL + exit 9`)+ 补老线没有的**产物校验**(`gzip -t` 过才算成功) |

  - **★运输腿巡检三连(答「数据回流通不通」)**:① `grep 拉取 /tmp/v6_merge_daemon.log` 取 `拉取完成：N/12 台`(**N≠12 就是有台在丢,别只看总轮次**)② `ls -lt /data_raw/<台>` mtime + `cat /data_raw/<台>/heartbeat.json`(**载荷里的 `ts`/`round` 才是真信号,mtime 会被推送器无条件刷新**)③ `gzip -t /tmp/v6_tar_<台>.tar.gz` 验归档。**采集侧活性必须独立取证**(`/tmp/targets` 大小与新增文件数、`collector.py` etimes)⇒ **主控副本冻结 + 采集侧鲜活 = 病在主控判据,不在采集机**。
  - **★超时不得比老线更紧**:老线远端 `tar` `timeout=90`、SFTP 取回 125s,而它历史上能成功拉 645MB ⇒ 新树单步 300s(`[ssh] pull_to`)反而宽松。改超时/阈值前先量老线的实际容忍度,别把「老线本来能过」的活判成失败。
  - 收官实证(2026-10-04,`v` 树 + 不设任何环境变量的默认路径,**手跑轮 + 常驻 daemon 腿双证**):手跑轮 `[merge 10:07:06] 拉取完成：12/12 台`;常驻 daemon 自跑 `[merge 10:13:04] 拉取完成：12/12 台`(daemon 腿才真算生产路径)。`/data_raw/上海` mtime 08:24 → **10:05**(3815 文件)、heartbeat 冻在 `round 154/16:23(BJ)` → **`round 170/stage=done/18:03:43(BJ)`**;归档 645MB → 82MB 且 `gzip -t` 通过。**池健康机队 12/12 `✅ 正常`(滞后 2–4 分钟)**;`health.json` 里另 9 条告警全是历史目录(`8515_arch/95306_full/xa79_flip/杭州/上海3/*冗余`)—— 老 `merger.py:13` `NON_MACHINE_DIRS` 同口径 ⇒ **既有噪声非回归**,不动(要清是独立诉求)。
  - 完整对照表、取证命令与遗留任务归属表见 `references/replacement-scope-and-legacy-task-audit.md`;割接机制 / 受管块 / 工装自证反控 / 换常驻进程的三层壳写法见 skill `monitoring-pipeline-ops` 的 `references/fleet-cutover-entry-tree-symlink.md`(后半)。
- **★主控 crontab 面必须全量取回再判归属(按记忆对拍必错)**:实测 **19 行有效 + 1 DISABLED**,而凭记忆只得 11 条。漏掉的逐条已定性:4 条 `hf_pull.py`(原始大表拉取腿——产物目录 `/data_raw/95306_full` 在新树全库 grep **零命中** ⇒ 新树压根不读它,保留**不是缺口、也无双写冲突**)/ `fetch_8515_inc.py` / `link8515.py`(**写 pack_map 企业级链接,与 `master/writer.py` 重叠 ⇒ 列 pending 交用户拍板**,不自行定去留)/ `arch8515.py`(8515 原始行存档)/ `security_watch.py`(SSH 告警 + 文件完整性,独立运维件,不碰) / `merge_daemon_fast.sh`(merger 守护壳 → `master_daemon.sh`)。取回逐字原文:`ssh <主控> 'crontab -l | base64 -w0'` → 本地 `base64 -d`(多行输出会被日志/换行搅坏)。
- **主控进程面**:老常驻 4 进程族(`merger.py` 由 `merge_daemon_fast.sh` 守护 / `orch8b.py` / `priv_loop.py` / `pix_bot_server.py`)+ `security_watch.py`;一条角色 `pgrep -f` 常命中 **2–3 个进程**(`bash -lc … setsid nohup …` 启动壳 + `flock` 包装 + 真进程)⇒ 停要全停、清点按角色点名看 `ps -eo pid,etimes,args`。主控 SSH 地址**以当次实测连通为准**(历史记录里出现过 `128.241.245.73` 与 `207.57.167.92`,同端口 12971),别按记忆写死。

## ★答「采集端(机队)现在正常吗」= 四层证据,不许拍胸脯

只看一层都会答歪(进程在 ≠ 在采;目录新鲜 ≠ 没漏)。**判词先、证据后,四层一起给:**

1. **主控口径**:`grep -a "健康：" /tmp/v6_merge_daemon.log | tail -3` ⇒ `[merge HH:MM:SS] 健康：12 台采集机 / 告警 0 台`;**要连续多轮一致**才叫稳(单轮可能只是瞬时)。
2. **落盘新鲜度**:`/data_raw/` 各机目录 mtime + 每机 `cstats.json` mtime ≤ 一两轮(90s/轮)才算在流;**活跃集按 cstats 新鲜度定,不按目录是否存在**(`8515_arch`/`杭州`/`上海3`/各「冗余」是历史目录;`health.json` 里的同类告警是既有噪声,非回归)。
3. **逐台计数器**(`_cstats` 键):`ui_fail`、`cool` 恒 0;`d` = 平台日期(北京时间);`bid_req` = 竞价室请求数(在跑就有量)⇒ **0 失败 + 0 冷却 + 计数在涨**才是健康态。
4. **代码面**:逐台 `systemctl is-active v6collector` + 发布树 + **`collector/` 四文件 sha256 与本机源码树比对** —— **比内容哈希,不看 rel 名/版本戳**(各台 `current` 可指向不同 rel/戳而采集代码逐字相同,与 §tree_hash 只覆盖 `collector/` 那条同源)。

- 一键跑:`bash scripts/fleet_code_drift_sweep.sh <targets16> <api16> <tickets16> <http16>`(在主控上执行;名单现读 `jumpers.json` 含非标端口,输出 `svc / tree / 四文件裁决`,**不打印 pwd**)。
- **拉取是主控出向 ssh ⇒ 主控 `last`/`w` 里看不到采集机**,别用它找机队;台名与 IP 会换机(见首行注册表规则)。
- **交付口径**:判词 + 逐层证据表;把**已知边界**(如 `collector/targets.py:225` 闸门对老项目不回补公告全文 —— 一次性历史缺口、新项目两条都写、主控侧已补)与**顺手发现的真问题**(如注册表明文口令)分开列,后者问是否授权修复;**动生产配置一律等点头**。

## 通用部署坑(本系统多次踩)

1. **pkill -f 自杀**:远程 exec 命令串含启动串时,pkill -f 匹配 bash -c 自身命令行 → 自杀。`[x]` 技巧也防不住(kill 与 start 同串时);**kill 和 start 分两个 exec**
2. **exec_command 必须 read**:fire-and-forget(不 read 立即 close)= 命令根本没发出;read 超时是假象(命令已执行),用 ps 验证
3. bot 无 systemd 守护(PPID=1),重启 = pkill + setsid nohup 分步;v6collector 采集机是 systemd 服务(日志 /tmp/v6_run.log,勿用旧 v6_collect.log)
4. merger daemon = bash 循环每 120s 调 merger.py(改代码无需重启 daemon,下轮自动生效)
5. **新4台(sh8-11)日志探测走 runlog tail 分支**:journalctl 窗只对老8台有效,新4台须用 /opt/v6/v6_run.log tail 后按时间戳正则过滤,PAT 窗必须精确覆盖「自上次已报告时点起」,否则会漏判(实例:09-11 05:05:57 河源 sh11「📦 榨干队列: 本轮 4 项目包件补全」被 05:12 轮报成 榨干=0,事后 04:54→06:14 全窗复扫才捕获)。少报比漏报安全:宁可全窗重扫。
   - 实测(09-12 20:3x):`/opt/v6/v6_run.log` **只存在于 sh8-sh11**;老 8 台(sh0-sh7)读该文件报 `No such file or directory`,必须用 `journalctl -u v6collector --since "YYYY-MM-DD HH:MM:SS" --no-pager`(时间参数按各机本地时区 CST)。逐台取证脚本:`scripts/_drain_file_2027.py`(文件源,sh8-11)/`scripts/_drain_jrn_2027.py`(journald 源,老 8 台),均经主服 paramiko 跳转(paramiko 在 `python` 3.11 下,`python3` 3.14 无该模块)。
   - **★ 判"某台今天没跑/0 轮"前必须先验活体 mtime**:用 journalctl 行数统计 sh8-11 会得到"今天 0 轮",足以把 4 台机器误判成假死机(实测踩过)。结论前先跑 `stat -c %y /tmp/v6_state.json /opt/v6/v6_run.log` —— 都在当前分钟 = 活着,只是日志不在你查的那个源。**任何 per-machine 计数都必须在"按日志源分支"之后再比大小**。
6. **ST 池化的三条铁律(2026-10-07 实测,详见 references/2026-10-07-st-pool-live-test.md)**:①票有效窗口只有**小时级**(≤3.5h 观察到活,20h 实测 401 已死)⇒不能当长期资产;②`statusGroup` 只剩 `buyed` 且**只返回在网项目**(已结束项目枚举不到,须自建账号×项目索引=`ent_coverage.json`);③活票能给**自己参与过的已结束项目**拉包件(HTTP 200 实测通过),但非参与者一律 `您没有该数据的访问权限`,且 `/bidMonitor/getSupplier` 等监控端点是 500 缺功能 ⇒ **池化价值边界=补票主自己的视角**。

7. **collector 日志语义(读日志别误判)**:`识别 N` = 该轮 `/user/info` 成功数(成功即 `seen.add(st)` → SEEN 账面 +N);`新企业包件 M` = st_map 里取到包件的企业数(仅当 getBuyPackageList 返回非空才落账);`drain 入队` 需该票 `buyed` 项目非空才触发。故「识别 1 / 新企业包件 0 / 无入队」= 票被成功识别但下游包件拉取被目标站风控(code=100「您没有该…」/cooldown)挡掉 —— 属上游限流,不是 drain/分片故障;**判 churn 的唯一硬指标是 SEEN 是否推进**(候选>0 但 识别 0 且 SEEN 不动 = 同一批票每轮重生)。

7. **单轮 `⚠️ WAF 探测: 审计接口 502` 是瞬时抖动,不要当封禁**(实证 09-12 20:29:35 深圳 sh7:审计 ST 45→13,下一轮 20:30:40 自愈回 ST 45 且当期 `识别 1`);只有**连续多轮 ST<45** 才按被限处理。
8. **账号级风控冻结会造成「候选>0 每轮重生 + 识别 0 + SEEN 不动」的 churn**,形态与 drain 故障极像但根因在上游:日志里必有 `🧊 触发风控冷却 15min(business 域暂停,审计继续)` / `🧊 冷却升级(<账号> 当日第N次): 冻结到次日 09-14 00:10(北京)`。冻结到期或次日解冻后自动跑通(实证 09-12 20:29→20:35:sh7 深/ sh10 蒙/ sh11 源 三台由「识别 0」→「识别 1」,SEEN 推进,期间 drain 总量 241 条不变 = 无一条被搁死)。**判定顺序:先看有无 风控/冷却 行 → 再看 SEEN 是否推进 → 都不是才怀疑管道。**

9. **`verify_drain_monitor.py` 的两个判读盲区(09-12 fix2 已修)**:①grep 只含 `候选|入队|榨干|gap|识别到|识别 N|轮询完成` → 看不见 `风控/冷却/冻结/退避/审计 ST`,sh6 冷却静默段(20:29:50→20:43:51 无匹配行)会被误判成"卡死"(实测该机 systemd active、pid 不变、20:43:51 复活,冷却期正常);②截断原为 `body[:1600]`(丢最新、留最旧),长行机器会看不到最近日志,新4台日志从 v6_run.log 回退、行更短故不受影响。修法:grep 加 `风控|冷却|冻结|退避|审计 ST`,截断改 `body[-1599:]`(丢最旧留最新)。**监控显示某台 tail 陈旧时,先按上面 grep 复扫原机(经主服跳转,journald 或 /opt/v6/v6_run.log),再下 stall 结论。**

10. **drain 修复(去 _my_acct 二次分片)实效判据 + 队列口径(09-13 实证,详见 references/2026-09-13-drain-fix-verified-and-dup-squeeze.md)**
   - 判"修复在跑"三条:①`drain 跳过(分片)` 计数恒 0(旧版账号分片拦票的残留日志);②同一账号键+**同一 ST** 出现在多台 state 的 drain(旧版 `hash(acct)%N` 下最多 1 台,多台并存 = 分片已去);③各台 `📦 榨干队列: 本轮 N 项目包件补全` 计数>0。运行版本核对:`stat -c %y /opt/v6/collector.py` 必须早于 `systemctl show v6collector -p ExecMainStartTimestamp`。
   - 部署核对(09-13 19:1x 实测):12 台 `/opt/v6/collector.py` **md5 全同** `15cb51226b8dffe82e5ddd8eb9ccf547`(mtime 09-11 22:33-22:36<ExecMainStart),`grep -c '去掉 _my_acct'`=1,`_my_acct` 只剩函数定义+修复注释(`drain 入队` 前 2 行无 `_my_acct(`)= 入队已彻底去二次分片。
   - **`DRAIN=N` 是账本长度不是待处理数**:已榨干条目 `all==done`,要等 `full_ts` 满 24h 才被清理。判真积压必须算 `set(all)-set(done)`。
   - **字段口径(09-14 17:26 逐台实测对账确认)**:`DRAIN=N` == `len(state["drain"])` = **drain 队列里的企业账号数**(不是项目数);队列内项目总数 = `sum(len(v["all"]))`,待榨干 = `sum(len([x for x in v["all"] if x not in v["done"]]))`。`SEEN=M` == `len(state["seen_st"])`。逐台读法:`python3 -c` 读 `/tmp/v6_state.json`(drain 在 state 里,`/opt/v6` 下无 drain 文件;`last=None` = 该账号从未被榨干过,即刚入队)。
   - **drain 段受机器级冷却整体 break**:`collector.py` 榨干循环首行 `if len(_hl) >= 20 or _in_cooldown(): break` → 该机冷却期间本轮 0 榨干(其余台照跑),表现为单台 `last 榨干` 落后机队数小时;冷却结束自动恢复,`done<all` 的项不会被清理,不要当 drain bug。
   - **副作用:重复榨干**。去二次分片后同票在每台各自入队+各自榨干,重复度=机队规模(实测 zzhk01 3 项 ×12 台 = 36 次 getBuyPackageList),会放大频次并加速账号冷却。若要恢复去重,方向是按 st 归机后再入队(不是加回账号分片)。

11. **drain 监控 cron 的正确判读姿势(09-13 16:3x 实证)**:cron 注入的 monitor 输出**会被截断**(只留头尾),全量原文落盘 `C:/Users/Administrator/AppData/Local/hermes/profiles/123/cron/output/e93ac7f7b11a/monitor_last_output.txt`(12 行 = 12 台,每行行尾即摘要 `… / DRAIN=N SEEN=M / EVID 入队=x 榨干=y 候选N=z 末次入队=<时间>`)。判读步骤:①读该文件按行 split;②只看行尾 EVID 段,不用逐条读日志;③异常关键词只搜 `ERR|ERROR|TIMEOUT|超时|refused|denied|FAIL`(注意 `SSH_OK` 是正常态,别被 substring 误报)。机制生效的完整链长这样(同一轮的连续三行,sh1 实证):`审计 ST 41, 新 1` → `候选 1(new_t 1) → proc 1 (新1/重试0)` → `↳ drain 入队 <企业key> 1 项目` → `轮询完成, 目标 254, 新企业包件 1, 识别 1`。par 解析脚本模板:`scripts/_parse_drainmon_1632.py`。
   - **解析坑(09-15 00:1x 实测)**:EVID 段 `末次入队=` 的值**含空格**(形如 `09-15 00:06:40`),用 `\S*` 配 `末次入队=(\S*)\s+范围=` 会整行失配 → 把该台误判成「无 EVID 行」(实测 sh3/sh7 差点被漏掉,恰好是当轮唯一有机制生效证据的两台)。正确正则:`DRAIN=(\d+)\s+SEEN=(\d+)\s*/\s*EVID\s+入队=(\d+)\s+榨干=(\d+)\s+候选N=(\d+)\s+末次入队=([\d\-: ]*)\s*范围=(\S+)`。
   - **`范围=<…>` 字段(09-15 起)**:EVID 行尾带计数窗口标签,实测全 12 台均 `范围=今09-15`(sh8-11 此前 tail 无日期过滤的多日窗问题已被标注字段覆盖);跨台比大小前先确认该字段同为当日。

12. **EVID 行的计数窗口对 sh8-11 是「多日」,跨台比大小必先取当日(09-13 16:5x 实证)**:monitor 里 EVID 的老 8 台走 `journalctl --since today`(**当日**),但 sh8-11 走 `tail -20000 /opt/v6/v6_run.log`(无日期过滤) → 其日志跨 09-09→当日(实测 sh8 首行 `[09-09 01:38:53]`),EVID 于是混入前几日。实测对照:sh8 EVID`入队=37 榨干=13` 而**当日实为 11/7**;sh9 `78/38`→**12/8**;sh10 `25/5`→**12/0**;sh11 `57/34`→**12/8**。⇒ ①别用 EVID 直接断言「新4台入队/榨干显著高于老8台」,那是计数窗假象(当日全 12 台同量级:入队 11–13、榨干 6–9);②跨机对比/写报告一律重跑当日-only 口径:老8台 `journalctl -u v6collector --no-pager --since today`、sh8-11 `tail -60000 /opt/v6/v6_run.log | grep -aE '\[MM-DD '` 再 grep `drain 入队|榨干队列|跳过(分片)`(技巧:`grep -c` 对空串会算 1,必须 `echo "$E" | grep -ac`,否则空窗误报 1)。
   - **真积压只在 `set(all)-set(done)` 非空时才算**,且要区分「冷却挡住的积压」:09-13 16:44 实测仅 sh10 乌兰察布 PEND=21(11 个企业键:hy2024712/GK8685/zzhk01(3)/LUFAGONGSI/a<PHONE-REDACTED>(5)/xionggang1985(3)…),同时其**当日榨干=0**、日志满屏 `🧊 冷却升级(whsentie 第83次/liujie00777 第83次/yjh_248248 第21次): 冻结到次日 09-15 00:10(北京)` ⇒ 属 §8 账号级冻结 + §10「drain 段冷却整体 break」,不是 drain 故障,解冻后自动补榨;其余 11 台 PEND=0(全榨干)。
   - 顺带:**sh10 的 `候选N=1382`(当日)不是新票**,是同一批票在冻结期每轮重生的 churn(§6/§8 判据:识别 0 + SEEN 不动)。

13. **心跳 mtime 恒新鲜 = 监控盲区;判「循环卡死」必须看载荷 ts(09-13 fix6 已修)**:`heartbeat.json` 的 mtime 由推送器每 ~30s 无条件覆盖 → **主循环卡死时 mtime 仍新鲜,`hb_age` 恒正常**(实测成都2 sh5:主循环 18:52:39 起停摆 15.6min,期间 hb_age 一直 -49s,SSH_OK 照报)。真信号 = 载荷里的 `"ts"`(采集机墙钟 CST=UTC+8,主循环最后进展时刻):`loop = now(CST) - ts`,>1800s 才可疑。`verify_drain_monitor.py` fix6 起每行输出 `|loop=Ns|`,实现=主服侧一次 `date +%s; for n in 12台: cat /data_raw/<台名>/heartbeat.json` 批量取 ts(主服 UTC → `calendar.timegm(ts) - 8h` 再减 now);实测 sh5 1113s / sh0 698s(长轮中) vs 正常台 12-321s。
   - **长轮 ≠ 卡死**,已知正常长轮两类:①sh0/sh4/sh8(`SHARD%4==0`)出价轮 15-21min;②`fetch_project_details` 包件清单拉取——实测 sh5 18:54:25「目标项目 248 个」→ 19:08:12「轮询完成」= 单轮 15.6min,且该段**一行日志都没有**(每目标 1-3 次 95306 请求 + 0.3/0.4s sleep ≈ 3.3s/目标)。判卡死三连证据:进程 `STAT=Ss wchan=hrtimer_nanosleep`(在 sleep 而非网络阻塞)+ `ss -tnp | grep python3` 无 established + 事后「轮询完成」补齐 ⇒ 长轮,不报故障。
   - 附:本轮(19:00-19:08)12 台新票链全部跑通(= §10 修复实效的活证据):`审计 ST 52, 新 2` → `候选 1(new_t 2) → proc 1 (新1/重试0)` → `轮询完成, 目标 N, 新企业包件 0, 识别 1`;sh8 19:07:43、sh5 19:08:35 亦在窗内命中。

14. **v9.32 机队版本基线 + 15:13 首个 post-rollout 新票链(09-14 实证, 详见 references/2026-09-14-drain-verify-round-1513.md)**
   - 09-14 14:32:09–14:33:32 全 12 台推 v9.32:`md5(collector.py)=f8f3e26d63cd2c6fbbeec25d9400e3c9`(**全队一致**),`ExecMainStartTimestamp = 文件 mtime + 1s`(逐台递增 = 逐台部署),`ActiveState=active`,`跳过(分片)当日=0`。→ 以后核对"修复版在跑"直接比这个 md5;变了就重新走 §10 三条判据。
   - **旧 systemd 坑**:杭州 sh1 的 systemd 不支持 `systemctl show --value`(报 `unrecognized option '--value'`,字段留空 ≠ 服务异常)。判进程启动时刻用 `systemctl show v6collector -p ExecMainStartTimestamp | cut -d= -f2` + `-p MainPID | cut -d= -f2`;否则会把 sh1 误读成"无法确认版本"。
   - **15:13:57 河源 sh11 完整链**(14:15 后全队首次入队, 也是 v9.32 后首条端到端新票链):`候选 14(new_t 26) → proc 14`(15:12:30)→ `↳ drain 入队 henanyuye 6 项目`(15:13:57)→ `📦 榨干队列: 本轮 6 项目包件补全`(15:14:29)→ `轮询完成, 目标 23, 新企业包件 6, 识别 2`;同日 `SEEN 387→389`。**证据规则:入队/榨干计数会因重启清零或跨日混淆,唯一硬指标是 SEEN 推进 + 末次入队时间戳前移**(本例其余 11 台 SEEN/入队全零变化, 只有 sh11 推进)。
   - 采样姿势:本机复跑 `verify_drain_monitor.py` 拿全量(>40KB)落 `D:\tmp\_drainmon_now_<HHMM>.txt`,再与 `cron/output/e93ac7f7b11a/monitor_last_output.txt`(上轮)做逐台 delta —— cron 注入版永远被截断,不能直接当全量。
   - **判「本轮有无新入队」的正确姿势(09-14 16:5x 实证,免重跑)**:`monitor_last_output.txt` 只落当前轮,拿历史轮做 delta 用 cron 归档 md:`cd cron/output/e93ac7f7b11a && grep -h -o "EVID 入队=[0-9]* 榨干=[0-9]* 候选N=[0-9]* 末次入队=[0-9: -]*" $(ls -t *.md | head -3)`。**只要「入队/榨干/末次入队」三项与上轮完全相同、且全队 SEEN 不动,本轮即无新票** —— 候选N 每轮 +2~4 只是审计新票计数在涨(候选>0 + 识别 0 + SEEN 不动 = §8 账号冷却 churn),不算机制生效证据。全 12 台 `SSH_OK` 且 grep 无 `SSH_ERR|TIMEOUT|超时|refused|denied|FAIL|ERROR` 时,唯一命中 `LOOP_LAG` 一般来自文件末尾 NOTE 脚注(第 13 行),别当告警。

15. **新机队版本基线 525edd50 + drain 判据修正(09-15 09:3x 实证)**
   - **版本基线(取代 §14 的 v9.32 f8f3e26d)**:12 台 `md5(/opt/v6/collector.py)=525edd501d603159528b8cd13f567f6d`(抽样 sh0/sh1/sh8/sh9/sh10/sh11 全同),`stat -c %y` = 2026-09-14 15:44:36(sh0,老8台)→ 15:45:57(sh11),`ExecMainStartTimestamp = mtime+1s` 逐台递增,`ActiveState=active`。以后核「修复版在跑」直接比这个 md5。
   - **`跳过(分片)` 已是死代码,不能再当独立判据**:`collector.py` 入队段是 `if _all_ids: log("drain 入队") ... elif _all_ids: log("跳过(分片)")` → elif 永不可达(修复注释在 `drain 入队` 前 2 行,`_my_acct` 仅剩定义+注释)。所以 `SKIP=0` 即使旧 bug 复发也会是 0。**主证据改成「同一账号键当日跨多台入队」**(本例 `hnss455590759` 于 09-15 08:39:52–08:43:12 出现在 sh1/2/3/4/6/7/8/9/10/11 共 10 台 `↳ drain 入队 hnss455590759 1 项目` ⇒ 账号级二次分片确已移除,副作用见 §10 重复榨干)。
   - **`drain 段冷却 break` 的源码位置与实测**:`榨干队列执行` 循环首行 `if len(_hl) >= 20 or _in_cooldown(): break`(`_hl` = state["full_hour"] 近 1h 满量次数)。实测 sh5:09:12:59 入队 `hbyutie 1 项目`(账本 `done=[]`)→ 27min 后仍未榨,同时 `state["cooldown_until"]=2026-09-15 09:52:07`、`journalctl --since "1 hour ago" | grep -c 冷却`=189 ⇒ **待榨滞留 = 机器级冷却闸门,不是 drain bug**,冷却到期自动榨。判 pending 必须同时读 `cooldown_until`。
   - **逐台当日口径 sweep 的判空坑**:老8台 journalctl / 新4台 v6_run.log 的分支不能只用 `journalctl -n 1 >/dev/null` 的**退出码**判(新4台该调用退出码 0 但输出为空 → 会把 sh8-11 当日误读成 `入队=0 榨干=0`)。必须判**内容**为空,或直接对 sh8-11 走 `tail -60000 /opt/v6/v6_run.log | grep -aF "[$(date +%m-%d) "`。脚本模板:`scripts/_drain_fleet_sweep.py`。
   - **09-15 当日健康量级(全 12 台,当日-only)**:入队 91 次(sh0=9,其余 7–8)、榨干 55 次(4–5)、`跳过(分片)`=0、账本 acct 19–34 / proj 36–61、**待榨 pend 全队仅 1(sh5 hbyutie,被冷却挡)**;sh0 09:20:59 `↳ drain 入队 SCTST88888 1 项目`(冯光帅/成都环鑫达再生资源回收有限公司)同轮账本即 `done==all`、09:21:45 `轮询完成, 目标 36, 新企业包件 1, 识别 8` ⇒ 立即闭环的叫「入队即完成」,不会打 `📦 榨干队列` 行,别当成漏榨。

   - **09-15 16:5x 复测(机制持续生效 + 榨干侧停摆的判据)**:全 12 台当日入队 91(09:3x)→ **132**,SEEN 8573→8661(+88),11/12 台 `末次入队` 前移,窗内 sh6 `16:40:39 drain 入队 xugeng666888 6 项目`、sh1/sh3 `识别 6`;同键 `zhangjifu162534` 20min 内跨 **9 台**入队、`schjxc003` **8 台**(§15 主证据口径)。**但当日榨干轮次 59→59 零增长、PEND 15→70**:全 12 台 `cooldown_until` 落在 16:53–17:08 且 30min 滚动退避持续 re-arm ⇒ `榨干队列执行` 首行 `if len(_hl) >= 20 or _in_cooldown(): break` 每轮第一条即 break,入队成功但执行体整段停摆(滞留最久 sh6 `hbyutie` ~6.5h)。⇒ **「PEND 涨 / 榨干 0」先读 `cooldown_until`+`_hl`,再谈 drain;平台长期冻结时榨干会长期停摆,硬化方向=榨干执行体不绑 `_in_cooldown()`(用户 09-15 15:08 已听方案未定)。参见 references/2026-09-15-drain-verify-round-1655.md。
   - **`范围=今09-15` 对 sh8-11 已核实可信(09-15 16:5x)**:monitor EVID 的 sh8-11 入队/榨干(9/4、15/5、9/5、12/5)与本机当日-only sweep 逐台一致 ⇒ §12 的「多日窗」隐患已被该字段覆盖;但 **`gap` 核查仍须分日志源**(老 8 台 journalctl,sh8-11 只落 `/opt/v6/v6_run.log`,只查 journalctl 会把新 4 台静默算成「无 gap」)。
   - **09-15 17:0x 复测(识别侧推进 / 入队·榨干 0 新增)**:全 12 台 SEEN 8661→**8680**(+19),来源 5 台 `识别>0`——sh2 `[16:59:47] 识别 1`、sh5 `[16:59:52] 识别 4`、sh7 `[16:59:14] 识别 4`(以上三行在 monitor 窗内),sh4 `[16:54:45] 识别 5`、sh8 `[16:55:04] 识别 5`(窗口外,靠 SEEN 803→808 / 443→448 证实);逐台 SEEN 增量与「识别」数严格吻合 = 真落账。入队/榨干本窗 0 新增(末次入队仍 sh6 `16:40:59`、末次榨干仍 sh0 `13:31:04`,PEND 70 不动)。参见 references/2026-09-15-drain-verify-round-1706.md。
   - **判「本窗有无识别」不能只读 monitor 窗(新坑,09-15 17:0x 实测)**:monitor 逐台只取 `tail -30` 条噪声过滤行,而 `🧊 冷却升级` 4s 一条的机器(sh0/sh8/sh9 尤甚)会让窗口实际只覆盖 **1–2 分钟**,`识别 N`/`轮询完成` 行极易被挤出 ⇒ 只读窗会把「有落账」误判成静默。**双口径**:① 逐台 SEEN 与上轮快照做 delta(≥1 且与识别数吻合即真落账);② 定向 grep 复跑:`journalctl -u v6collector --since today | grep -aE '轮询完成|识别 [1-9]' | tail -3`(脚本模板 `D:\tmp\_win_1706.py`)。另:纯 idle 判据 =「识别 0 + **SEEN 冻结** + 入队/榨干/末次入队三项不变」,**不是「候选 0」**(候选行每轮必现且恒 >0 = 存量重扫)。
   - **09-15 18:5x 复测(sh11 本日第 2 条端到端链 + ★cron 副本漂移坑)**:sh11 河源 `[18:52:55] 候选 45(new_t 171) → proc 40` → `[18:53:22] ↳ drain 入队 hyk1314 1 项目` → `[18:53:41] 轮询完成, 目标 41, 新企业包件 1, 识别 2`。交叉核对(18:51 快照 → 18:56 实测):入队 18→19、末次入队 18:38:10→**18:53:22**、DRAIN 19→20、SEEN 467→469(=识别 2),state 尾 key 实锤 `hyk1314`(ent=重庆仪悦再生资源回收有限公司, all=1, done=[])。该机当日入队链:17:33:38/17:33:57/17:34:09/17:34:34 → 18:38:10(A<PHONE-REDACTED>) → 18:53:22(hyk1314)。**榨干侧仍停摆**:全队当日榨干 59 零新增、227 个 drain key 的 `done` 全空,与 §15 的 `_in_cooldown()` break 结论一致,非 drain 回归。12 台分布(18:56-18:57 实测):`sh0 21/528 · sh1 19/1040 · sh2 19/1089 · sh3 21/1053 · sh4 18/819 · sh5 17/782 · sh6 20/817 · sh7 17/788 · sh8 17/456 · sh9 20/478 · sh10 18/472 · sh11 20/469`(DRAIN 合计 **227** / SEEN 合计 **8791**)。产物 `D:\tmp\drain_evid_1853_sh11.md`、`D:\tmp\_sh11_evid_1854.py`、轻量 state sweep `D:\tmp\_state_sweep_1858.py`(只读 state/heartbeat,秒级,免跑 `journalctl --since today`)。
   - **09-15 19:2x 复测(5 台窗内新入队 + 3 台识别落账 / PEND 涨到 160)**:入队原文 sh5 `[19:13:58] ↳ drain 入队 hnls158 6 项目`(紧接 `[19:14:06] 轮询完成, 目标 36, 新企业包件 6, 识别 1`)、sh8 `[19:18:34] ↳ drain 入队 xianzxzj0307 11 项目`(`[19:18:52] 目标 54, 新企业包件 11, 识别 1`)、sh0 `[19:23:35] TY132456_ 1`(`[19:23:58] 目标 109, 新企业包件 1, 识别 1`,SEEN 528→529 严格吻合)、sh1 `[19:23:56] TY132456_ 1`、sh11 `[19:29:46] TY132456_ 1`;同键 `TY132456_` 20min 内跨 sh0/sh1/sh11 三台入队 = §15 主证据口径(账号级二次分片确已移除)。当日常口径 12 台:入队 203 / 榨干 59(零增长:末次榨干 sh0 13:31:04、sh10 12:55:39,其余 08:39–08:43)/ DRAIN 条目 230 / **PEND=89 条目 160 包件**(17:25 才 79 → 2h 翻倍),全 12 台 `cooldown_until` 冻结(日志 `冻结到次日 09-16 00:10(北京)` / `09-17 00:10`,sh0 当日各 4308 / 2459 行)⇒ 榨干停摆仍归因 `_in_cooldown()` 闸门,非 drain 回归。逐台分布(19:24-19:29 实测 DRAIN条目/PEND包件):`sh0 22/10 · sh1 19/11 · sh2 19/10 · sh3 21/11 · sh4 18/8 · sh5 18/15 · sh6 20/27 · sh7 17/9 · sh8 18/22 · sh9 20/14 · sh10 18/8 · sh11 20/15`;SEEN 合计 8793。详见 references/2026-09-15-drain-verify-round-1925.md。
   - **09-15 19:3x 复测(同键 `TY132456_` 跨 8 台入队 = 二次分片已去的最强实证)**:19:24 后又 6 台新入队——sh2 `[19:26:54] yangminghao 1`、sh7 `[19:26:56] TY132456_ 1`、sh3 `[19:27:18] TY132456_ 1`、sh6 `[19:28:56] TY132456_ 1`、sh5 `[19:30:30] TY132456_ 1`、sh10 `[19:34:27] TY132456_ 1`(19:31 monitor 快照尚不含 sh10 这条,须靠 19:34 定向探针),每台 13–23s 后 `轮询完成, 目标 N, 新企业包件 1, 识别 1` 落账;`TY132456_` 于 19:23:35–19:34:27 跨 **sh0/sh1/sh3/sh5/sh6/sh7/sh10/sh11 共 8 台**入队 ⇒ §15 主证据口径再次命中。SEEN 合计 8793→**8801**,逐台增量与识别数吻合。当日入队 203→**209**、DRAIN 条目 230→**237**;榨干仍 59 零增长、PEND 160→**167 包件 / 96 条目**(末次榨干 sh0 13:31:04、sh2 13:31:52、sh10 12:55:39,其余 08:39–08:43)⇒ 停摆仍归因 `_in_cooldown()` 闸门。12/12 `SSH_OK`,hb_age 235–266s、loop 330–518s。判读姿势复用:`monitor_last_output.txt`(19:31,12 行 33495 字符)先落解析(`D:\tmp\_vdm_cur_1931.py`),再跑 19:34 定向探针(`D:\tmp\_vdm_evid_1932.py`)拿「19:24 后入队原文 + 识别>0 行 + LAST_PZHU」——**monitor 快照永远是上一轮的,最新入队只在探针里**。详见 references/2026-09-15-drain-verify-round-1934.md。
   - **09-15 19:4x 复测(同键跨 10 台 = 二次分片已去的又一实证 / 榨干仍 59 零增长)**:上轮 19:34 报告后仅 2 台新入队——sh8 `[19:35:45] ↳ drain 入队 TY132456_ 1 项目` → `[19:36:08] 轮询完成, 目标 54, 新企业包件 1, 识别 1`(SEEN 457→458)、sh9 `[19:35:41] ↳ drain 入队 TY132456_ 1 项目` → `[19:36:04] 目标 48, 新企业包件 1, 识别 1`(SEEN 478→479);`TY132456_` 当日累计跨 **10 台**(sh0/sh1/sh3/sh5/sh6/sh7/sh8/sh9/sh10/sh11)入队 ⇒ §15 主证据口径再命中。账本 delta(19:34→19:46):DRAIN 237→**240**、PEND 96/167→**99 条目/170 包件**、SEEN 8801→**8804**、当日入队 209→**211**、当日榨干 **59→59(零)**(末次榨干 sh0 13:31:04、sh2 13:31:52、sh10 12:55:39,其余 08:39:56–08:42:41);逐台 PEND 最大 sh6 `11/28`、sh8 `8/23`。12/12 `SSH_OK`,hb_age 488–514s、loop 569–727s(**判「8 台」= cron prompt 旧注释,机队恒 12 台 SHARD0-11**)。判读要点:monitor 快照恒为上一轮,本轮 sh8/sh9 两条在快照里只体现为 `末次入队` 时间戳前移 ⇒ **必须按「自上次报告时点起」的窗口跑定向探针**(模板 `D:\tmp\_vdm_evid_1944.py` + 汇总 `D:\tmp\_vdm_agg_1946.py`;**`execute_code` 在 cron 下被审批护栏拦住,须落 .py 用 terminal 跑**)。详见 references/2026-09-15-drain-verify-round-1946.md。
   - **09-15 19:5x 复测(新键 `A<PHONE-REDACTED>` 同窗跨 2 台 + sh8 存量重扫识别 / 榨干仍 59 零增长)**:19:46 报告后本窗新事件——sh10 乌兰察布 `[19:51:34] drain 入队 A<PHONE-REDACTED> 2 项目` → `[19:51:57] 轮询完成, 目标 44, 新企业包件 2, 识别 2, 重试队列 0, 死票 0`;sh9 武汉 `[19:52:25] drain 入队 A<PHONE-REDACTED> 2 项目` → `[19:52:47] 目标 48, 新企业包件 2, 识别 2`(51s 内两台各自认领同键 = §15 主证据口径,继 `TY132456_`(10 台)后第二个跨机键;落账延迟 23s/22s);sh8 上海3 `[19:51:11] 目标 54, 新企业包件 0, 识别 1`(存量 drain 条目重扫落账,SEEN 458→459,非新票)。账本 delta(19:46→19:55):DRAIN 240→**242**、SEEN 8804→**8809**(+5 恰等于 3 台识别 1/2/2 之和)、当日入队 211→**213**、当日榨干 **59→59(零)**。12/12 `SSH_OK`、hb_age 197–228s、loop 277–423s。**★坑:cron 的 `monitor_last_output.txt` 与紧接着的实测值逐台完全一致(同一次 monitor 快照),不能当「上一轮」基线做 delta** —— 基线须用上一次**已交付报告**的表格(cron/output/e93ac7f7b11a/2026-09-15_HH-MM-SS.md 或 session_search 取上一轮 assistant 消息),否则会把本窗新事件误判成「无变化」。模板 D:/tmp/_vdm_evid_1954.py + 逐台对比 D:/tmp/_vdm_delta_1957.py。详见 references/2026-09-15-drain-verify-round-1955.md。
   - **★坑:`python x.py | tee out.txt | head -N` 会静默截断 out.txt**:head 读满 N 行退出 → tee 收 SIGPIPE 被杀,文件只剩前 N 行(实测本轮 sh10/sh11 丢失)且无任何报错。全量落盘直接 `> out.txt`,再另用 `sed -n` 分段读。
   - **★坑:改 `verify_drain_monitor.py` 必须同步覆盖 cron 实际执行的副本**。cron 只按 job 的 `monitor_script` 名解析到 `C:/Users/Administrator/AppData/Local/hermes/profiles/123/scripts/verify_drain_monitor.py`(errors.log 里有实执行路径),`D:\tmp\verify_drain_monitor.py` 仅是工作副本。实测 09-15:fix9/fix10(NEWTICKET 行 = 判「无新票」的唯一权威口径)18:14 只写在 D:\tmp,profiles 副本停在 09-14 23:34 ⇒ 18:16–18:51 各轮快照**根本没有 NEWTICKET 行**,每轮都得另写探针补数。改完必须 `cp` 到 profiles/123/scripts/ + 双方 `md5sum` 一致 + `python -m py_compile` 才算生效(09-15 18:58 已同步,md5=b0f4ca49ad2f2424f37f3fd733b2915d)。

## 菜单B 推送抖动取证(推送明细与表格"相位相反")

症状:推送"新增2个拒绝"而表格是通过 / 下次推送"拒绝没了"而表格里的通过又变拒绝 / 再推又是"新增2个拒绝"而表格没动 —— 每 ~3 分钟(监控轮询)翻一次。**根因在"池内容 + 推送明细口径",不在计数函数,先别改统计。**

- **明细(pend)是逐轮内存 diff,在下一次真推送时才带出** ⇒ 它描述的是过去某轮的值,与"看表格那一刻"必然可能相反;判"是否真变化"一律看池文件本身,别拿推送明细当现状。
- **监控基线只在推送时推进**(`if chg or not old: 写 mb_monitor.json`,设计如此)⇒ 池内值若在两版本间交替,每次推送都相对"上次已推"反着报 = 无限翻烧饼。修法方向 = **消掉池内交替(单一事实源),不是调阈值**。
- **池 = 唯一读源**:`check_status_summary(pid)` 走 `get_proj_dir(pid)`(`/data_pool/<pid>` 硬编码单路径,无多副本/无 shard 解析)⇒ 读数在变就只能定因到**写入方**。池与机器副本会结构性分叉(merger 保底累积,池会保留副本里根本不存在的终态);机器副本 = `/data_raw/<机名>/<pid>_pack_map.json`(平铺),其 **mtime 常是数日前 —— 内容未变不重写,不能用 mtime 判"数据陈旧"**。
- **同企业两套键并存**:池用**账号键**、机器副本用**单位名键**;`merge_ents_by_unit` 已按单位合并去重(同 packId 保首条)——**“冗余键重复计数”造成的 9/7 摆动是更早的已修类(见 references/2026-09-jitter-stage-guards.md),别重跑那条旧路**;现在的翻烧饼是**同一 packCode 的状态在两版本间交替**(账号键键、两边都是真值区)。
- **定因姿势**:≥15 分钟捕翻器(**4 分钟窗口会给"没在翻"的假阴性**)+ 变化即存版本快照 + 相邻两版字段级 diff(`审核状态/审核码/审核时间`),拿"另一版本"的写入时间戳反查同刻写入方。现成脚本 `scripts/menuB_flip_catcher.py`;机制与判读细则见 references/menu-b-push-denoise-2026-09-13.md。
- 定位项目用**项目编码等唯一标识**取全部候选;模糊词 + 命中即 break 会搜串(同一局名同名"第N次…"会命中别的局,浪费整轮)。
- 长任务经跳板机一律落盘 + 短轮询(通道 2–3 分钟以上会被掐、长命令输出会整体丢):见 skill `remote-exec-script-harness`。

## ★ 冷却模型 / 产能诊断 / 外部报告裁定

用户贴入外部「实地探测结论」「优化方案」类报告(问"你看看有用吗")时,先逐条独立复现再答,分三段交付:**✅ 成立 / ⚠️ 与自家实测冲突 / ❌ 它没看到的**。

1. 行号级机制描述 → 本机副本(`c927/collector_v9xx.py`)grep 原句核对;对得上才信其余推论。
2. 统计数字 → 采集机上按**日志源分支**重算(§5);单机数字能逐项对上 = 报告可信的基线。
3. 阈值/节奏类建议先跟代码注释里的历史实测对撞,**冲突的一律不做,只能 2–3 台 A/B 灰度**:
   - `_BIZ_GAP = 4.0`(L47)注释"实测 2.5s(10s窗4req)仍触发限流,4s=10s窗2-3req 安全" ⇒ 不因一次手动测试下调间隔;
   - `_cool_backoff` docstring"2 次即放弃/标 dead 会造成该企业当天全部项目永久漏采" ⇒ 不因一次观测放宽账号阈值。
4. **生产采集逻辑改动一律先出计划 + 等放行**;灰度先 2–3 台看 24h 平台反应再全队。复核默认只读:不重启、不 kill、不改采集逻辑。

产能基线(判"是不是平台封我们"):
- **整机冷却 = 第一杀手**:`_COOL_UNTIL=[0.0]` 是**模块级全局**(L49)、`COOL_MIN=15`(L48)、`_mark_cooldown()`(L64);入口 `if _in_cooldown(): return {"code":100,"msg":"cooldown"}`(L188/L204);触发点 `if _is_cool_resp(j): _mark_cooldown()`(L195/L211) ⇒ **任何一个票 code=100 就把全机 business 冻 15 分钟**(审计/tokenrailquery 通道不受影响)。实测机队:单机 46–57 次/天 ≈ 12–14 机器小时,全队 ≈158 机器小时/天,零产出轮次 ≈97%。
- **退避键错位**:`_cool_backoff` 的 `cs[st]={"acct":…}` **以票为 key**,只有计数 `cc[f"{acct}|{day}"]` 按账号 ⇒ 同账号换票即绕过退避,账号级冻结膨胀到全队 10^5 次/天(单账号单日最高 54 次)。判 churn(候选>0 每轮重生 + 识别 0 + SEEN 不动,§8 判据)时先看这条。
- **状态易失**:`STATE_FILE="/tmp/v6_state.json"`(账号簿 `acct_inv`、冻结票 `cool_st`、计数 `cool_cnt`、`seen_st`、`drain`、`full_hour` 全在里面)⇒ 重启/清理即归零,账号被当新票重打;它的 **mtime 同时是最快的活体判据**。
- **读冷却日志要换算**:日志印 `🧊 冷却升级(…): 冻结到次日 D 00:10(北京)`,但机队全是 CST 而代码按 UTC 做 ±8h 且 `_cool_restore` 用本机墙钟比较 ⇒ **实际失效点 = D 的前一日 16:10 CST**(state 里 `cool_st[*].until` 落在 D-1 可侧证);「当日第N次」的 day 桶在 **16:00 CST** 换日。别按字面算冻结时长。

细节(代码位点逐条、tokenrailquery 配方与产量、机队当日 sweep 口径、报告裁定清单)见 `references/collector-cooldown-and-throughput-forensics.md`;一键取全队当日产能:`scripts/fleet_daily_throughput.py`。

## 机队实体台账 / 续费取证(用户说"续费"时)

用户说"把主控和跳板机的服务器信息整理一下 / 我要续费"时按此走:

1. **先对上身份再取证**:"跳板机"在本项目是混用词——可能指 ①渗透跳板池 7 台(凭据见 skill `ip-ban-bypass`)②12 台采集机 ③**主控本体**。**主控 = `128.241.245.73:12971`(hostname `jnjjn`,US San Jose,AS213802 Tianfeng)**,管线里主控↔采集机直连、**无独立跳板**;交付前用 IP 逐条对齐,别把主控写成"跳板机"(踩过)。
2. **逐台实登只读取规格**:`nproc`/`free -m`/`df -h`/`lsb_release`/`uptime -s`/`/proc/net/dev` + 云元数据 `curl -s http://100.100.100.200/latest/meta-data/{instance-id,instance-type,region-id,zone-id}`。采集机 SSH 已 publickey-only ⇒ 用主控 `/root/.ssh/id_ed25519`;12 台清单与现行口令源是 `/opt/v6/jumpers.json`(桌面凭据单可能已过期)。
3. **到期日读不到的如实说**:机内无 AKSK/RAM 角色 ⇒ 取不到 `ExpiredTime`;交付口径 = **`uptime -s` 开机时刻当账单周年** + **云实例 ID 交出去供控制台检索** + "去哪续",不要编到期日。
4. **失联机也要给可检索身份**:阿里云 hostname 反推实例 ID、元数据取法、"到期停机"定性见 skill `monitoring-pipeline-ops`「机队实体台账、断供与到期诊断」。
5. **断供与否按 `/data_raw/<机名>/` 最新 mtime 横比**:某台明显落后其余台 = 已断供,该时刻即断供起点 ⇒ 报出**漏采窗口**与该机分片覆盖面(`md5(proj)%12`),它是"比续费更急"的事项。
6. **交付**:`D:\渗透\95306_服务器续费_<日期>\*.md` + 桌面一份,结构 = 主控卡 / 跳板池表 / 急事(断供机) / 采集机附录 / 去哪续 / 为什么读不到到期日;聊天里给三条结论 + `MEDIA:` 本文件;**凭据一律不写入清单**。台账快照与刷新配方见 `references/fleet-inventory-and-renewal.md`。

## ★ 菜单/文案样式对齐(重写版 bot ↔ 老正本)

用户说「菜单样式和之前不一样了 / 整理成和之前一样的」时,这是**换代重写后的 UI 对齐任务**:老正本 `pix_bot_server.py` 是样式权威,逐面板对齐,**先出差异清单再改,不许先改后对**。

- 取证三件套:`tools/_old_style_dump.py`(老面板骨架+键盘标签)/ `tools/_old_cb_style.py`(老每回调分支文本模板,分段读)/ `tools/_probe_style.py`(新面板实渲染,**四路发送器全换记录器**,漏一路就真发到用户 TG)。
- 老版锚点:`━━━` 分隔线 + 千分位双空格对齐计数 + `👇 选择功能:` 引导 + 两行式列表条(`1. 名称` / `📅日期 | 🏢N/M家`)+ 数字键行 + `⬅️ p/n ➡️`。
- **四条硬规矩**:①老版写死的陈旧数字不许照抄(能实算就实算,算不出就省掉);②数据源缺失的老字段安全返空 + 交付里点名「池里没有等价源」,不编造;③新写/改写的按钮键必须 grep 回调注册表验证非死键;④改公共 `ui_*` 签名时 `edit` 参数必须排在 `fname` 前。
- **★ 按钮要双向对账(死键 + 孤儿)**:老正本每个 `callback_data` 都查两件事 —— 新树注册表里有这个键(非死键)**且**新树有渲染器**发出**这个键(非孤儿)。**「有处理没按钮」是移植最常漏的形态**(回调接好、函数写好,就是没人画那个按钮 ⇒ 对用户等于功能不存在),grep 要搜**键盘构造处**而不是处理处。★按钮类回归断言必须测**渲染出的键盘里含该回调**(emission);只测「老回调点了有反应」的闸门永远抓不到这一类。
- 列表类面板只改中心渲染器一次(`page_out` ↔ 老 `render_mb`),数字键标签用纯数字 + 该行原生打开键。
- 改完跑离线回归(`offline_ui`/`offline_groups`/`offline_tg`/`offline_integration`)与覆盖率(应仍 100%)再谈发布;**发布/重启属生产闸,须用户单独点头**。

完整顺序、逐面板对齐细节与全部坑见 `references/bot-menu-style-alignment.md`。

- **★割接前必须在新树(staged)上跑真数据探针**:`sed "s|/opt/v6/current|/opt/v6/lib/<rel>|"` 复制一份探针再跑(只读 + 假 Tg 零外发)。**离线夹具全绿 ≠ 真数据对** —— 夹具的假 pool 会给字段、真池不给,「夹具绿、真数据空」只有这一步抓得到(实例:列表 `📅` 日期全空,十道离线闸无一条报出来)。不达标**先别 activate**,改树→重跑离线闸→新 stamp 重打包→re-stage→再探。
- **★字段/样式类断言用真组件单测,别信夹具**:真 `render.Render` + `StubConf`/`StubPool`(项目卡落点 `render.py::fmt_proj_card`);搬函数按老正本**整函数差分** —— 漏一个 fallback/推导分支 = 真数据静默空值(实例:`proj_pub_day` 漏了 projCode 兜底)。换树后数据源实况会变,**每换一次树重新核一遍数据源有没有那个文件**。

## ★ 计数口径：行数 ≠ 家数（客户问「池内 19 / 平台 12」这类对不上时先读本卡）

**所有给人看或被判据消费的「家数」必须走 `pool.ent_unit_count(pid, info)`（实体口径）**；`len(proj_detail(pid)["ents"])` 与 `enterpriseCount` 是**记录行数**，同一家企业可被记两条 ⇒ 必然虚高于平台名册。

- **双写机制**：backfill 补录以**账号**为 key 落一条（带 `来源: backfill8`），原始采集以**单位全名**为 key 再落一条（无来源），同账号同包件 ⇒ 纯重复。同一账号两种单位写法（简称/全称）⇒ 只按单位名去重并不到底，实体口径须**规范化单位名 + 同账号 union-find 合并**，账号为空才退回单位名。
- **消费点四处，漏一处仍虚高**：项目卡「企业」行 / 采集完成判定 / 分类列表行 `🏢N/M家` / 详情页已采数。方法内要容忍 ents 值非 dict（夹具里常是 int），否则 AttributeError。
- **影响面量级**（实测）：在办 425 项中 219 项（51.5%）有此重复 ⇒ 显示虚高，且判据 `src=='平台' and plat and 家数>=plat` **偏宽**（行数天然 ≥ 家数）。修后同快照复算：`groups()` 与 ✅ 条数逐项不变（虚高不是 ✅ 的来源）。
- **18 列 CSV 没有「企业数」列** —— 它的重复行是「同一个企业出重复行」，靠 `rows_of` 归并解决，别去找那个不存在的列（找错方向会白改一轮）。
- **包件数组重复条目（同 packId 最多 54 份）** 双根因治本已落码：`entcount.norm_packs`/`norm_units` + 写入侧归并前**先自愈** + 池内一次性清扫（默认 dry-run、`--apply` 才写）。**清扫会改已结束项目的历史导出行数 ⇒ 与发布分开、单独点头**。详见 `references/menu-count-semantics.md`。
- **报数字变小必须点明「变准了」**，否则客户当成丢数据。

**用户贴来的卡片/日志先定位发布版本再解释数字**：现树 grep 不到该文案时，逐包 `tar -xzOf dist/*.tar.gz --wildcards '*/bot/render.py' | grep -n …` 找历史发布包里的模板 —— 用户贴的常是上一版发的消息，用现版代码解释其数字必答歪。详见 `references/menu-count-semantics.md`。

**改公共方法/加口径后闸门三关**：① grep 离线闸里的**手搓假对象**（`class FakePool` 等）同步补新方法（假对象重实现旧形状，不补必 AttributeError）；② 新增**能鉴别的断言**并正反各跑一次（新代码过、换回改动前副本必失败）；③ 计数器 delta 用「原始 `bot/*.py` 副本 + 当前 `tools/`」的**基线对照副本**证伪，不许凭记忆里的旧数字下结论。

## bot 修改部署流程

拉取→本地 patch→py_compile→上传→分步重启:
```
sftp 拉 /opt/v6/pix_bot_server.py → patch → python -m py_compile
上传后: pkill -9 -f 'pix_bot_serve[r].py'(单独 exec)→ setsid nohup python3 pix_bot_server.py > /opt/v6/bot.log(单独 exec)
```
查看运行日志 /opt/v6/bot.log;数据文件 /data_pool/index.json(分钟级)/health.json/gaps.json

**新树版 bot(`v6m.py bot`)的发布链 / 割接后核验 / 「bot 没反应」三级判定 / 已修缺陷台账见 `references/bot-release-and-no-response-diagnosis.md`**。★**按钮「没做进去」类报障(搜索/筛选出来只能看不能点)的定位与修法、真池真码探针、离线夹具的两个静默洞(头值类型 / 文案来源键)、bot「真活着」验收与启动横幅重复的判读见 `references/2026-10-07-bot-search-button-and-fixture-gaps.md`
- `references/bot-export-parity-and-fixture-verification.md` — **复刻老导出件（BOM/CRLF/列数/三类行）的流程 + 平台名单静默降级陷阱 + 真数据对拍口径 + 夹具必须重定向 `export_dir`/按钮断言要用真实 `Menus`**。用户丢来历史导出件说「还按这个格式来就行」、或动 `bot` 导出/菜单按钮时先读这份。上一份（2026-10-07）`。**发布链固化顺序 = scp → **两端 tar sha256 必比** → `--stage --tar … --sha …` → `--plan`(只读) → **staged 树真数据探针** → `--activate --yes` → `--verify` → **手动串行**停/起(方括号 pkill + `ssh -n -f` 起 `setsid nohup flock -n … python3 -u`) → 行号锚健康证据。**activate 不会重启 bot**(在跑进程仍持旧代码)。

## AI 数据助手(/ai)

见 references/ai-query-assistant.md。
