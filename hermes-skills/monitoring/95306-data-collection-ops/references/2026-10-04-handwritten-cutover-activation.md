# 2026-10-04 手搓版上线割接（入口 + 树 + current 软链）

## 发布包真值

| 包 | tar sha256 | 文件 | tree_hash | 关数 |
|---|---|---|---|---|
| **`v6rel_20261003j`(已上线)** | `6e29d198d68bb526c7c5a8fdccdbddca812809627aa985cd546c19d55c6d3845` | 54 | `05d4ffb59e96cfe1` | **9(①-⑨,含判定自检)** |
| `v6rel_20261003i`(试点用过) | `9b1ca92ef79eb5a7ce584b3cd838e54a2a8581f372a41e51fced56fe918db074` | 53 | `05d4ffb59e96cfe1` | 9 |
| `20261003h`(历史) | `85ed57c130ce0ac0c60695d2cc89fdba5e86fe197af2f1d6b58c9d66ae86c330` | 53 | `05d4ffb59e96cfe1` | 8 |
| `20261003g`(历史) | `d66fa7a7ee6b53a4eda484816bb70109f8b8e62eb55d01d397fe9b2dfb9cfd51` | 51 | `eda95ff0afcaeab3` | — |
| `20261003c`(历史) | — | — | `088153f875bad5ae` | — |

- `20261003i` 相比 `h` 多出来的是:launcher v2(入口 + `/opt/v6/lib/<rel>` + `current`)、`fleet_deploy.py::do_activate` 改为"铺刚验过的那棵树"、**⑨ 关**。
- **`j` 相比 `i` 只多 `deploy/deployutil.py` + 判定修复 ⇒ `tree_hash` 不变**:该指纹只覆盖 `collector/` 包。**推论(判"要不要重新激活全队"用这条)**:`tree_hash` 相同 ⇒ 采集代码逐字相同,即使各台 `current` 指向的 rel 名不同(先上的 11 台指 `i`、后补的宁波指 `j`),**不必为改工装再停机一轮**。
- **三处解释器 tree_hash 全同**:本机 3.11.15 / 主控 3.10.12(UTC) / 采集机 3.12.3(CST+0800) ⇒ 包内容不随解释器变。

## 激活前只读基线(必不可少)

- `tools/probe_fleet.py` 经主控跳转(本机→主控 12971→采集机),产物 `D:\渗透\95306_recon\fleet_baseline_20261004_all.txt`(599 行):**12/12 台应答、线上 md5 全 `081bd8780bd65f39495cc8dcdb216b16`、全 Python 3.12.3、零失败**。
- 基线里逐台还取到 unit(`ExecStart`/`Environment=V6_SHARD`)、crontab、资源、产物目录(`/tmp/targets` 930 项/579M)、日志源。
- **落点对账**见 SKILL.md「上线割接」节;写侧 helper 全 `atomic_json`,四个落点名逐字对齐,`[paths]` 同址。

## 试点激活实录(上海 `8.133.188.178`)

`fleet_deploy.py --rel v6rel_20261003i --activate --host 8.133.188.178 --yes` 输出链:
`before`(老入口 `081bd8780bd6`,MainPID,NRestarts=0)→ `backup`(`/opt/v6/collector.py.bak_v6rel_20261003i`,90,487B)→ `lay`(bot/collector/conf/deploy/master/tools)→ `link`(`/opt/v6/lib/v6rel_20261003i`)→ `install`(launcher,md5 `723eb134d50f`,2286B)→ `hash 05d4ffb59e96cfe1` → `active` → `journal`。

- 停机窗口 **<1 秒**(旧进程 00:54:50 停、新进程 00:54:50 起),`NRestarts=0`。
- **第 1 轮零异常**:审计流水 40 页/4000 行、快照新增 500 行、包件清单新增 7 个项目、公告映射 2980 条、竞价状态 466 个项目、请求 104(业务 58/数据 46)、预算剩 562。
- 心跳与统计已更新(`/tmp/v6_heartbeat.json` 182B、`/tmp/v6_cstats.json` 90B)= 主控健康检查读的两个文件在动。
- 线上口径生效的**日志锚点**(判"接手成功"看这三行):
  - `状态播种: seen ← seen_st (2000 条已处理的票，防重跑)`
  - `状态播种: acct_cool ← cool_acct (5 账号，其中 0 个按线上口径冻结到次日)`
  - `注意: 线上 cool_st 有 5 张票在冷却中（取票时会跳过）`

## 全量激活 → 宁波误回滚 → 修复 → 终局

`--activate --yes`(不带 `--host`)对 12 台全量执行:

| 台 | 结果 |
|---|---|
| 11 台 | `install` `723eb134d50f` + `hash` `05d4ffb59e96cfe1` + `active` ⇒ 直接上线 |
| 宁波 `114.66.40.208` | **`auto_rollback`** —— 装好、新手搓版真跑起来了,却被判失败回滚 |

**根因(工装判定踩噪声)**:`do_activate` 拿 `systemctl is-active` 的**整段 stdout** 与 `"active"` 等值比较;该台 unit 文件改过但未 `systemctl daemon-reload` ⇒ systemd 从那时起往输出里混一行:

```
active
Warning: The unit file, source configuration file or drop-ins of v6collector.service changed on disk. Run 'systemctl daemon-reload' to reload units.
```

⇒ `st["active"].strip() != "active"` 成立 ⇒ 判「不 active」⇒ 自动回滚。**该台手搓版其实跑得完全正常**(`[boot] tree_hash=05d4ffb59e96cfe1`、`状态播种 acct_cool ← cool_acct (2 账号，1 个冻结到次日)`、`rail 流水: 1 页 / 20 账号 → 本机票 3 → 池 3`、第 1 轮已在采集)。**不是机坏了,是判据把它判坏了。**

**修法(三处 + 一条闸)**:
1. 新增 `deploy/deployutil.py::active_ok(out)`(21 行):**按行精确匹配状态字** —— 噪声行天然被忽略,`inactive`/`failed`/`activating`/`unknown` 都不等 `active`,不会误放行。一处实现、激活与回滚两处调用。
2. `fleet_deploy.py` 两处命令加 `2>/dev/null`;判定改 `if not active_ok(st["active"])`。
3. **⑨ 关加「判定自检」正反控**:夹警告输出必须仍判 active、`inactive`/`failed` 必须判否;真机 12 台全打印 `判定=True/False/False`。

**回归**:重打 `20261003j` ⇒ 本机 9 关全「可以上」⇒ 12 台 `--stage` 全绿 ⇒ **宁波补激活,阶段列表不再出现 `auto_rollback`**。

**误回滚的定性姿势(下次直接照做)**:宁波回滚是干净两步(老入口 90,487B 拷回 + `current` 删除),机器回到老生产态(日志恢复老格式 `[KTY-NB1-4H-76890] 轮询开始`)。**先看 journal**:若能看到 `[boot] tree_hash=…` 与手搓版自有日志行,则是「起来了但被判失败」⇒ 修工装 + 单台 `--host` 重激活,**不要**去源码里找"为什么起不来"。

## 终局(只读 `--verify` 实测,12/12)

| 判据 | 结果 |
|---|---|
| `tree_hash` | 12× `05d4ffb59e96cfe1`(全同) |
| 入口 | 12× 2286B = launcher(md5 `723eb134d50f`) |
| `current` | 11 台 → `v6rel_20261003i`、宁波 → `v6rel_20261003j`(采集代码同 hash) |
| 服务 | 12× `active`、12× `NRestarts=0`、异常台 0 |
| unit | 一个字没改(`ExecStart=/usr/bin/python3 /opt/v6/collector.py`、`Environment=V6_SHARD=<n>`) |

回滚一条命令(单台加 `--host`):

```bash
ssh -i ~/.ssh/v6_master_key -p 12971 root@207.57.167.92 \
 'cd /tmp/v6rel_20261003j/v6rel_20261003j/deploy && python3 fleet_deploy.py --rel v6rel_20261003j --rollback --yes'
```

## 回滚安全性核对(为什么敢上)

1. 老生产载入 state = **整字典 `json.load` + 逐键 `s.get()`**、保存 = 整字典 dump ⇒ **容忍未知键**(新增键不会让它崩)。
2. 手搓版新增的 13 键**不与线上 25 键撞名**;实测激活后 25→38 键,`acct_inv` 437 / `seen_st` 2000 / `cool_st` 5 / `bid_skip` 175 / `cool_acct` 5 等**类型与规模原样**。
3. 手搓版对线上键**只读**(`prodstate.py`)+ 同语义增量写 `enroll_ops`(`audit.py`);`rail_pool`/`bid_skip` 两边同语义(rail 票池 / 跳过集合)。
4. 老入口有完整备份(`collector.py.bak_<rel>` 90,487B),`--rollback` = 拷回 + 指针切回,两步自证。

## 仍待放行

- 真网联调(联网探针会建会话/烧票,`login`/`serviceTicket` 路径)另批。
- 采集机 crontab 里老 `audit_harvest_cn.py`(每 10 分钟)未停 —— 属动生产,须单独批准;它可能与手搓 `collector/audit.py` 双写同名辅助态。

## 交付物(均在 `D:\渗透\95306_recon\` + 桌面同名份)

- `95306_割接执行记录_20261004.md`:时间线 / 逐台状态表 / 自证日志 / 回滚命令 / 遗留(81 行)。
- `95306_激活与回滚清单_20261004.md`:**可直接粘的激活与回滚命令**,标注已执行,保留为操作手册(92 行)。
- `95306_手搓版vs线上_差异对比_20261003.md`:累计 **77 处**修复(705 行 / 60,795B / md5 `5573894b9de20f05b94534e88e6350b5`),内含第 77 处 = 本轮判定噪声 bug。

## 本机写这类中文交付文档的坑(踩过)

- **差异文档是 CRLF**(Windows 侧反复编辑过):多行 `patch` 的 `old_string` 必须按 `\r\n` 拼 —— 用 `\n` 拼会静默不匹配(单行修改照样成功,极易误以为整批都成了)。动手前先 `raw.count(b"\r\n")` 判换行风格。
- **判写入成功不许用工具返回值的真值**:`patch()` 返回 dict(恒为真),`if patch(...)` 永远打印成功 —— 实测因此漏报「第 77 处小节没插进去」。改用 `r.get("success")`/`r.get("diff")`,并**再 grep 一次锚点字符串**独立复核。
