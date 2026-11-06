# 2026-10-09 rail 探针四坑 + P1e force_accts（缺口账号排名优先）

## 一、探针四坑（每一个都让我白跑一轮）

| # | 现象 | 真因 | 正确姿势 |
|---|------|------|----------|
| 1 | `rows=0 fail=0`（每片都空，不报错） | 时间串只到分钟 `%Y-%m-%d %H:%M` | **必须带秒** `%Y-%m-%d %H:%M:%S` |
| 2 | `code=-2 appId不存在` | 在**主控**直接 POST；生产 rail 查询走 RelayExec（经采集机出口） | 探针**在采集机上跑** |
| 3 | ctx 只有 `accts/gen_time/gen_ts/names`，`base=http://`、`referer` 空 | 读错了 ctx 文件：`/tmp/bk8_ctx.json` 是陈旧文件 | **生产 ctx = `/tmp/bk8_bf_ctx.json`**（conf `[backfill] ctx_file`），含 `params.{base,referer,user_types,...}` |
| 4 | 24h 单窗只翻 3 页 ⇒ 11 个账号全 0 命中（连已采到的都 0） | `rail_size=500`/页，24h 实际上万行 ⇒ 严重欠采样 | **分片扫**（每片一个窗、各自页 1..N）；比对命中率再下结论 |
| 5 | `AttributeError: 'list' object has no attribute 'get'` | `rail_rows()` 返回 **`(rows, fail)` 元组**，直接迭代拿到的是内层 list | `rows, fail = w.rail_rows(st, en)` **先解包** |
| 6 | 探针里新字段恒为空（如读到 `force_accts=0`，误判“名单没生效”） | 采集机上 `import master.bk_worker` 命中的是 `/opt/v6/current` **旧树**；生产真正跑的是 `/tmp/bk_worker.py` | 探针用 `importlib` **显式加载 `/tmp/bk_worker.py`**，并打印所用文件路径自证 |

自证铁律：探针必须打印**响应信封**（`code/msg/data类型/len`）+ 行键 + 现场参数值（base/referer/func/size/skip）；
只要信封不是 `code=0 操作成功`，后面所有「0 命中」都不算证据。

复用姿势：`BK_CTX=/tmp/bk8_bf_ctx.json python3 -u probe.py`（探针靠环境变量取 ctx，别硬编码）；
加载纪律：探针**显式加载生产文件**——采集机上用 `importlib` 加载 `/tmp/bk_worker.py`（生产真身），主控上从代码树加载；
**别用裸 `import master.bk_worker`**（采集机上会落到 `/opt/v6/current` 旧树，读到旧行为、新字段恒空）。加载后打印文件路径自证。
可直接复用现成脚本：`scripts/rail_liveness_probe.py`（票龄→token 存活率 + 缺口账号盯守，只读）。

## 二、订正：`user_types = "03,3"` 是**白名单**，不是跳过表

```python
ok = lambda r: (r.get("token") and str(r.get("login_status")) == "1"
                and str(r.get("user_type")) in self.user_types)   # 只采 03
```
⇒ 企业登录票就是 `ty=03`（实测 d168988 `2026-10-09 14:33:20 ty=03 login_status=1`）。
**旧认知「watch_skip_types=03,3 跳过了企业票」是错标，已作废**——别再去"修"这个参数。

## 三、真因：缺口账号不在 `miss_accts` ⇒ 额度里靠抽签

- `miss_accts` 来自 `/data_pool/gaps.json` 的「缺账号」；`miss_map` 来自「缺企业」。
- P1 只把 2 家账号级缺口排进 0 档；`d168988 / m168988 / SXXHFS888` 只在**企业名**里
  ⇒ 它们的票 `rank=2`，与全部新鲜票同级，在 `1275` 额度里抽签；
- 实测该票 **3 小时内 token 已死**（`user/info → code=100 系统服务异常`）⇒ 抽不到就永远漏。

### P1e 修法（最小面）
```
conf [backfill] force_accts = hcxd<PHONE-REDACTED>,SXXHFS888,qikai1989,d168988,m168988
backfill.build_ctx(): "force_accts": [x.strip() for x in conf.get_str("backfill","force_accts","").split(",") if x.strip()]
bk_worker.pick_cands(): gap = 0 if (uid in miss_accts or uid in force_accts) ...
```
只改**排序**，不进 `match_name` ⇒ 非缺口企业的名字不会被误判为命中 ⇒ **零数据污染**。
回滚：三份 `.bak_<ts>_p1e_forceacct`（bk_worker/backfill/master.ini）一行 cp 复原。

## 四、口径备忘
- `rail_rows()` 列键：`userid / token / user_type / login_status / login_time / username / address / login_device ...`
  （**无企业名** ⇒ 企业名只能靠有效 token 调 `user/info` 拿 `dwhz`）。
- token 寿命很短（实测 ≤3h）⇒ 补采只能「**实时接住**」；所以**排序优先级 + 轮次频率**才是采集率杠杆。
- 缺口家「报名时刻」（平台权威源）≠ 登录时刻，不能直接当对窗锚点。但它是**「该企业必然登录过」的信号**
  （买标书就得登录）；我方表 `报名时间`（包件提交）与 `buy_time` 差值 ≈ 同会话内完成度（实测 38 分钟）。
  字段归属与取数路径详表见 `references/platform-authority-vs-token-fields.md`。
- 票龄算法：`age = now - login_time`（**算反了会得负值**）。实测 rail 45 分钟窗有 **1200+ 行**、最新票龄仅 **1~2 分钟**、
  且相当比例 token 当场存活 ⇒ 平台登录流量很大 ⇒ 缺口票落在 `rank=2` 抽签里基本抽不到 ⇒ **必须 rank=0**。
- 长流程轮询纪律：判活/判完成用 `ssh 采集机 'pgrep -f x.py >/dev/null && echo RUN || echo GONE'`，
  **ssh 超时 / 空输出绝不能当作 DONE**（否则误判完成、拿到空结果）；链路抖动要重试，不要中断整条取证链。

## 五、两条腿的 ctx 必须分清（我为此白跑两轮）

| 腿 | cron | ctx 文件 | 生成方 | 消费方 | 结构 |
|----|------|----------|--------|--------|------|
| **orch 腿** | `2-59/5`（每 5 分钟，跑得最勤） | `paths.ctx_file` = `/tmp/bk8_ctx.json` | `v6m.py gapgen`（`8,18,28,…` 每 10 分钟） | 采集机上 `tools/gap_once.py`（**它自己就做 rail 收割**） | `{gen_ts, gen_time, names[{full,norm,pids,stock}], accts{账号:报名时刻}}` |
| **backfill 腿** | `15,45` | `[backfill] ctx_file` = `/tmp/bk8_bf_ctx.json` | `backfill.build_ctx()`（每轮重建） | 采集机上 `/tmp/bk_worker.py`（`bk_worker.Worker`） | `{miss_names, miss_map, miss_accts, stale_map, user_types, force_accts, …}` |

★ 两条腿的 ctx **文件名与结构都不同**，worker 代码也不同（`gaps.py`/`app.gap` vs `bk_worker.Worker`）⇒
只改一边的 ctx 不会影响另一边；我最初把 `/tmp/bk8_ctx.json` 当成「陈旧文件」是错的（那是 orch 腿现役文件）。
**P1e 目前只注入 backfill 腿**（足够：rank=0 + ≤30 分钟轮次 vs token ≤3h）；改 orch 腿需动 `gapgen`，收益小、风险大，不要顺手改。

## 六、缺口账号↔企业名映射：出处是我方历史采集表（权威，非推断）

项目表（`企业包件表_18列_*.csv`）**本就带 `登录账号` 列**（表头：`企业全称,统一信用代码,登录账号,项目ID,…`）。
因此「某账号是谁」可直接查历史表，不要靠猜：

```bash
grep -h "$acct" /data_pool/*/企业包件表*.csv | awk -F, '{print $1" | "$3}' | sort -u
```

2026-10-09 实测（武汉84 `ON002026092916314988`，平台 12 家 = 已采 6 + 缺口 5 + 新报名 1）：

| 账号 | 企业全称 |
|---|---|
| `d168988` | 济南东照盛金属材料有限公司 |
| `m168988` | 济南天勤锻造有限公司 |
| `SXXHFS888` | 山西鑫和丰硕再生资源有限公司 |
| `hcxd<PHONE-REDACTED>` | 宁夏鸿宸鑫达工贸有限公司 |
| `qikai1989` | 重庆霖澜海商贸有限公司 |
| `fybz789` | 武汉松叶包装印务有限公司（已采） |

⇒ 这 5 家名字都在 `miss_names`（缺企业）里 ⇒ 命中后走名字分支拿 `miss_map` 点位，
P1e 的**排名优先 + 既有名字匹配 = 完整闭环**；`force_accts` 只影响排序，不进 `match_name` ⇒ 无误归属风险。
