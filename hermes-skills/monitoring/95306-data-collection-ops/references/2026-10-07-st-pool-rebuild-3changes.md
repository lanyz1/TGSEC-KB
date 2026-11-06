# ST 池「最小改造 3 处」落地记录(2026-10-07)

基于 `references/2026-10-07-st-pool-live-test.md` 的实测结论,对 `D:\95306c` 做**三处最小改造**。
状态:**三处改造已全部上线**(主控割接 + 12 台 active + bot 静默重启);
上线 8 关流程与「生产侧验证配方」见 `references/release-rollout-and-verification.md`。

## 改造① 票寿命:淘汰线 → 新鲜阈值

- 旧语义:`rail.ttl_min = 45`(分钟)当**淘汰线** ⇒ 票池实测票龄 min/中/max = 4.9 / 28.9 / 49.9 分钟,而票实测能活 **1–3h**
  ⇒ **中位数票只用到一半寿命就被删**(237–241 张活票里被白扔的是补存量缺口的唯一工具)。
- 新语义(两档):
  - `ttl_min = 45` = **新鲜阈值**:未超 ⇒ `stale=False`,优先用、不必验活;
  - `ttl_max_min = 180` = **真淘汰线**:只有超 180 分钟(或 `st=="dead"`)才 `_evict`;
  - 中间地带超 `ttl_min` ⇒ `stale=True`,**必须 `probe` 验活**才可用。
- `candidates` 条目增 `"stale"` 字段 + **两趟稳定排序**(先按 `at` 倒序 = 新鲜优先、再按 stale 布尔),同档内新鲜票排前。
- 落码位点:`collector/tickets.py`(`__init__` 读 `ttl_max_min`、新增 `is_stale(at, now=None)`、`_evict` 按 `ttl_max_min`)+ `conf/collector.ini`。
- **★改语义必须在 conf 注释里写明「票寿命实测小时级」的理由**,否则后人看到 45 会当成淘汰线改回去。

## 改造② 名册接存量缺口(含第三处真 bug:读盘主键)

### 真 bug:`gapgen.projects()` 按 `info["projId"]` 读盘

判决实验(同张参与者活票、两个 pid 各拉一次 `getBuyPackageList`):

| pid 取值 | 结果 |
|---|---|
| **池目录名**(`07391c54…` / `f8535b01…` / `f14dc219…`) | `操作成功`,rows = 1 / 2 / 1 |
| `info.projId`(`736bd8e3…` / `badcd25e…` / `b77e9eef…`) | `code=100 系统服务异常,请联系技术支持!` |

⇒ **平台只认池目录名**。真池实测:**14,379 个带 `项目信息.json` 的目录里 325 个「目录名 ≠ info.projId」** ⇒ 旧代码按 `projId` 读盘时这批**全部读空**。

修法:`projects()` 挂 `_dir` = 池目录名;`pid` 一律走 `pid_of(p)` / `pid_of(info)` 取目录名;
**量测口径同样必须按目录名、绝不可按 `info["projId"]`,也不可用 `bidStarttime` 当窗选器。**

### 结构性返工:棘轮不许豁免 ⇒ 真拆模块

`struct_check` 报 gapgen **文件 >400 行 + `gen()` >50 行** ⇒ 存量缺口逻辑整体外移 **`master/gapstock.py`(123 行,`class StockMixin`)**:

- `plat_roster()` 读 `plat_enroll_map.json` → `{projCode: {"ents": [企业全名…], "day": 公告日}}`,**读不到返 `{}`(fail-closed,不许当空名单静默放过)**;
- `stock_gaps(projects)` = 名单内、池里的**待补名 + 已结束项目**;
- `merge_stock(names, projects)` 供 `gapgen.gen()` **一行调用**。

`gapgen.py`:`class GapGen(StockMixin)` + `gen()` 一行 `n_stock = self.merge_stock(names, projects)`;旧存量段**整段删除**(留着 = 重复实现 + 撑爆 400 行)。
拆开的三条理由:① 400/50 棘轮;**② 这段有独立风险面**(读平台名单 + 企业名归一 + 读盘上限),拆开可单独夹具覆盖;**③ 坏了只表现为「存量缺口没进名册」,绝不拖垮在网缺口主链**。

### 名额与命名空间

- `conf/master.ini`:`stock_max_names = 400` / `stock_scan_max = 600` —— **存量缺口只占独立名额,在网项目名额永不被挤**(夹具断言「在网占位键保留 = True」)。
- **★两条派活腿(orch / backfill)必须各用各的远端名册/产物文件名**(曾共用同一 ctx 路径 ⇒ 互相覆盖的真撞车)。backfill 腿专属:`/tmp/bk8_bf_ctx.json` / `bk8_bf_result_%d.json` / `bk8_bf_stats_%d.json` / `bk8_bf_%d.log`。
- 归一落点复用生产同源函数:**`bot/render.py::match_plat_units(units, plat_names, plat_times=None)` → `(matched, pending, extra)`**(纯 stdlib ⇒ cron 级 `master/gapgen.py` 可安全 import)。

## ★③ 排队优先:先补上一个「有闸无门」的真洞

**发现(实测)**:`Guard.note_acct_risk → escalate → freeze` 这条账号冻结链**全库无人调用**;
`tickets.candidates` 里的 `acct_cooled` 门 ⇒ **闸门一直空着**;而 `collector/gapfill.py::_run_loop:168` 把
平台风控响应当「票死了」**静默丢弃**(不记平台风控、不冷账号)。后果:同一张坏票**每轮重打**、配额白烧、风控升级。

**修法**:

1. 新增 `GapFill._note_risk(tok, uid)` —— **票级必须计**(多票连击才判平台风控,单张坏票不算)+ **账号级必须计**;
2. `_run_loop` 里 `if stat == "risk" and self._note_risk(tok, uid): log(…) ; break` = **风控即收手**(本轮不再烧配额)。

**★通用判据(新卡级教训)**:给系统加任何「冷却/冻结/限额/退避」类闸门时,**先 grep 那个记账函数有没有调用者**;
「有闸无门」(闸门存在、触发点缺失或结果被上层静默丢弃)在本系统已出现一次,形态极隐蔽——闸门代码看着完全正常。
改闸门必须**同时接上「触发点」与「收手动作」**,并用夹具断言「坏票不再被当 alive 处理」。

## 真池只读验收(零写)

沙箱树 `/tmp/sbx_tree`(现役树 + 本地改动)跑 `sbx_accept.py`,读真池 `/data_pool`,**不调 `gen()`/`save()`、不写任何生产文件**:

```
① 带项目信息.json 的池目录 = 14379
★ 目录名 != info.projId 的项目 = 325 个   ⇒ 旧代码按 projId 读盘时这批全部读空
② 平台名单(含企业名单) = 515 项目 / 池里有目录 345 / 无目录 170
③ 存量缺口 = 18 家企业 / 22 个点位      ← 与上一轮 stock_scan3.py 的「22 条 / 18 家」完全吻合(两套独立算法互证)
★ 点位 pid 全是真存在的池目录 = True / 形状干净 = True
★ merge_stock 并入 18 条;在网占位键保留 = True
写入生产文件 = 0
```

- 点位里出现 **沈阳沈吉再生资源回收有限公司(3 个点位)、锦州双赢废旧物资回收有限公司** —— 正是沈阳铁道 108 次项目真差集那两家;归一假阳性「河南帆辰」已消失 ⇒ 端到端语义对。
- **口径提示**:`plat_enroll_map` 顶层 622 条目,其中**只有 515 条带企业名单**(其余 `企业数=0`)⇒ 报「622」是条目数,报「515」才是可判缺口的口径,两个数必须说清是哪一个。

## 闸口基线(改完必跑)

`offline_master 133/133`(原 108 + 新增 25)｜`offline_run 59/59`｜`offline_cli 7/7`｜`offline_bot 110/110`｜`offline_ui 178`｜`offline_repack 25/25`｜
`struct_check` 新增/变大 **0**｜`bind_audit` 未绑定裸名 **0**｜`compileall OK`

夹具:`tools/offline_master_cases_c.py`(4 用例:`case_pid_dir` / `case_stock_gaps` / `case_gapfill_risk` / `case_ticket_ttl`),
宿主 `tools/offline_master.py` 用 `CC.bind(**kw)` 注入 + 用例登记。
**夹具写法约束**:① 用例函数 ≤50 行(超了就把桩类提到模块级)② `GapFill` 构造期要读 `store.targets_dir` ⇒ 桩必须提供该字段(字段缺失 = 构造函数直接炸,与逻辑无关)③ 夹具模块含 `globals().update(` 时 `bind_audit` 自动跳过(宿主注入 idiom)。

## 已上线 + 生产侧证据(逐条都不是自证)

| 改造 | 生产侧硬证据 |
|---|---|
| ①② | `gapgen` 首轮 cron 日志出现新模块**自有前缀** `[gapstock <ts>] 扫 N 项目 ⇒ … 待补 / … 家 / … 个点位`,并写出名册 + 覆盖产物;条数与沙箱只读验收、独立量测脚本**逐数吻合** |
| ② | 名册条目 pid 全为**池目录名**形态(含那个「目录名 ≠ info.projId」的目录)⇒ 主键修复真生效,而不是「文件到位」 |
| ② | 采集机侧 `journald` 打出「缺口 ctx: 名单 N(生成于 <主控那轮的时间戳>)」+ 采集机名册文件与主控同刻产物**字节一致** ⇒ 名册真流到采集端 |
| ② 命名空间 | 采集机上出现 backfill 腿**专属**名册文件(~35K),派活腿整轮 12 分片全触发+回写 ⇒ 两腿不再共用 ctx |
| ③ | 新记账路径随采集机 `systemctl restart v6collector` 生效 |

★ **轮转类分发别误判**:名册按 shard 轮转推送,**某台机器上还是上一轮的名册属正常节奏**,不是分发断了 —— 要验证就看已走到自己窗口的那台,或等下一轮。

## 遗留
- 可选:α 端到端活票真拉一次(会花平台 GET 配额;判决实验已证「池目录名 pid ⇒ 操作成功」,且名册已在采集端被读出,增量价值有限)。
- 未修但已知:`coverage()` 的 `end=True` 两条判据都依赖 `bidStarttime`,而 13,937 个「已结束」目录里只有 1,302 个带 bst ⇒ **~12,635 个永远定不了稿、每轮重拉**(配额漏桶,单独议题)。
