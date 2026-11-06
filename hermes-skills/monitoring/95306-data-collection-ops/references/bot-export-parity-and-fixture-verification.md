# 老式导出件复刻 + 离线夹具/真池验证（bot 侧）

## 何时用
- 用户丢来一份历史导出件（CSV/XLSX）说「还按这个格式来就行」⇒ 任务是**复刻那份文件的形状**，不是重新设计表。
- 要把老正本（pix_bot_server 快照）里的产出逻辑移植进新树出口（菜单/导出按钮）。
- 给 bot 的菜单/导出按钮写离线夹具断言。

---

## A. 复刻老格式：先量字节，再找权威产出者

1. **量样式件**（不要用肉眼看表头就动手）：
   - BOM：`open(p,'rb').read()[:3] == b'\xef\xbb\xbf'`（Excel 双击不乱码靠它）
   - CRLF：`raw.count(b'\r\n')` 与 `raw.count(b'\n')` 相等且 = 行数
   - 列/行：`csv.reader(open(p, encoding='utf-8-sig', newline=''))` → 列数 = `len(rows[0])`
2. **找权威产出者**，不要照样表反推逻辑：老正本快照 `D:/渗透/95306_recon/mec_snapshot/pix_bot_server.py`（融合「报名总表」约 `:691`；联系方式 helper `sup_profile` 约 `:2955`）。逐字读实现后移植，产出才能与用户认的那份逐字一致。
3. **数据源三件套**（`/data_pool`，只读）：
   - `<pool>/<pid>/pack_map.json` → `enterprises[账号]`：`账号 / 单位 / 报名时间_平台 / 时间 / 包件[]`；包件字段 `packId / packCode / packName / 保证金 / 报价模式 / 物资条数 / 审核状态`。
   - `<pool>/企业档案/<企业名>.json`：常缺联系人。
   - `<pool>/供应商/<企业名>.json` → `法人 / 联系人 / 手机号`（联系方式真源；用样表里的真实值自证一次再接线）。
4. **平台权威名单真源** = `<pool>/plat_enroll_map.json`（线上口径，**按 projCode 键**，由 `sync_plat_enroll.py` 产）；`plat_enroll.json`（手搓，**按 pid 键**）通常不存在。`pool.proj_plat_ent_names(pid, info)` 依次试 `pe[str(pid)]`、`pe[info["projCode"]]]`。
5. **落盘**：只写 `export_dir`（`/opt/v6/exports`），**绝不写 `/data_pool`**；文件名沿用 `报名总表_<项目编号>.csv`。

---

## B. 静默降级 = 本类任务最大坑

- `proj_plat_ent_names()` 在「`info` 缺 `projCode`」或「名单里没这个项目」时**返回 `[]`，不抛异常** ⇒ 产出整体退化成**全 `🔹平台外`**，而且行数还会**变多**（无包件企业也成行）—— 表头/编码/联系方式全对，**看起来就是格式对了**，极难自察。
- **判据**：导出后先看状态分布 `Counter(r[0] for r in rows[1:])`。`✅已采 == 0 且全 🔹平台外` ⇒ **先查平台名单覆盖与 info 键，不要去改格式代码**。
- **一般化规则**：凡产出依赖「查表命中 / 未命中走兜底分支」的 helper，**夹具全绿 ≠ 真池取到数**。必须真数据对拍（C 节）才能宣布移植完成。

---

## C. 真数据对拍（主控上只读）

1. **复制现役树到 /tmp**：`cp -a /opt/v6/lib/v6rel_<rel> /tmp/regtest`，把新模块塞进 `/tmp/regtest/bot/`；**production 树一字不动**。
2. 驱动脚本用**真 conf**：`Conf('/tmp/regtest/conf/master.ini')` → `Pool(conf)` → 新导出函数，输出落 `/tmp/regout`（不落 `/data_pool`）。
3. **对拍口径**：与 `/data_pool/汇总/报名总表_<projectCode>.csv`（历史产出）比 —— 表头逐字相等 + 行**多重集**差（`Counter(map(tuple, rows))` 相减）+ 状态分布 + 同企业逐列差异统计。
4. **差异归因顺序**：① 数据漂移（时点快照、回填覆盖 `时间`/`报名时间_平台`）→ ② 数据源覆盖范围 → ③ 才怀疑代码。把①②当代码 bug 改会越改越错。
5. **抽样必须两边都覆盖**：名单内项目 ≥1、名单外项目 ≥1 —— 才能真验证 `✅已采 / ⏳待补 / 🔹平台外` 三类行都出得来。**行数与老产出相同 + 表头一致 = 移植可信的最强证据**（例：两个名单内项目 33/33、80/80 逐行一致）。
6. **覆盖范围差异不是 bug**：线上名单只覆盖近期项目（数百个量级）；老产出里常有一大半项目不在名单内 ⇒ 那些项目产出会全 `🔹平台外`。要补跑 `sync_plat_enroll` 回填，代码侧无法凭空造名单。**汇报时要如实说清哪些项目受影响。**
7. **按钮真实路径也要验**：`export(pool, pid, info=None)` 依赖 `proj_detail()["info"]` 自带 `projCode`，否则同 B 的静默降级。
8. **有意增强要点名**：保留「平台外 + 无包件企业成行」这类比老正本更全的行为时，要在交付里点名差异与条数，别让用户自己发现行数不一样。

---

## D. 离线夹具纪律（bot / 菜单 / 导出）

- **夹具 conf 必须把 `export_dir`、`pool_summary_dir` 一起 patch 到临时目录**：生产 ini 写的是 `/opt/v6/exports`；不 patch 时夹具真的往生产形状路径写（Windows 上生成 `D:\opt\v6\...`），**零污染闸会抓** —— 这是真隐患，不是理论风险。顺手把 `save`、`offset_file` 等所有产出类路径一起重定向。
- **按钮断言要用真实 `Menus`**：
  `from bot.menus import Menus` → `Menus(conf, router, cmds=cmds, pool=pool, render=render, push=push, compat=None)` → `mn.act_xxx(cid, pid)`。
  `act_*` / `menu_*` 挂在 **`Menus`** 上，`Commands` 没有这些方法（`cmds.act_entscsv` → AttributeError）。
- **独立小池夹具**（不污染宿主假池 —— 宿主假池还要给后面的分类/推送断言用）：
  `shutil.copyfile(conf.path, ini)` + `patch_ini(ini, {"paths": {"pool": pdir}, "bot": {"index_file": ..., "type_file": ..., "export_dir": ...}})`。
  桩 JSON 形状：`index.json` = `{"projects": {pid: {projName, projCode, stage, live}}}`；`proj_types.json` = `{projCode: "竞卖"}`（**按 projCode 键**）；`plat_enroll.json` = `{pid: {"count": N, "names": [...]}}`（**按 pid 键**）。
- **`jdump` 不建父目录** ⇒ 写 `企业档案/`、`供应商/` 这类分类子目录前先 `os.makedirs`。
- **断言要覆盖「数据/文案来源键」**，不只「按钮存在 + 回调对」：真池把键改名时夹具会全绿，而按钮静默显示 UUID。
- **测「格式」就断字节层**：BOM、CRLF、列数、表头逐字、状态标注顺序，别只断逻辑分支。

---

## E. 工具坑

- `search_files` 的正则里带 `(` / `)` 会被改写成 `(?:...)` 并报 `rg: regex parse error: unclosed group` ⇒ 用**字面词 alternation**，括号一律不带。
- 长 `ssh` / `scp` 命令容易撞 600s 前台上限被转后台 ⇒ 命令内自己 `tail` + 落盘日志，再分次读。
