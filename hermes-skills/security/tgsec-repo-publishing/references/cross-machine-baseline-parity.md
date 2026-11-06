# 跨机基线复现（同一套卡，两台机器分数不同）

2026-10-22，`<IP-REDACTED>` 灌完全量库后 core96 只有 `88/96 · 94/96 · MISS 2`，本机同库是 `94/96 · 96/96 · MISS 0`。以下是定位全过程，方法论比结论更值钱。

## 症状对照

| 机器 | 卡数 | 索引 | core96 TOP1 | TOP3 | MISS | 正文词 |
|---|---|---|---|---|---|---|
| 案卷机（本机） | 2146 | 342.6MB | 94/96 | 96/96 | 0 | 7/8 |
| <IP-REDACTED>（旧包） | 2146 | 344.3MB | 88/96 | 94/96 | 2 | 7/8→5/8 |
| <IP-REDACTED>（补 seed 后） | 2146 | 344.3MB | 94/96 | 96/96 | 0 | 7/8 |

同一份 `eval_core.json`、同一份 `skill_find.py`、同一批 2146 张卡（4 张抽样 md5 完全一致）。

## 三步判决（顺序不要反）

### ① 排除使用加权 `use_count`

`skill_find.py` 打分有 `s += min(10, log1p(use_count)*2)`，且排序键含 `-use_count`。先用**副本**清零验证：

```bash
cp ~/.hermes/arsenal/arsenal.db /tmp/db0.db
python3 -c "import sqlite3;c=sqlite3.connect('/tmp/db0.db');c.execute('UPDATE skills SET use_count=0');c.commit()"
cd ~/.hermes/arsenal && ARSENAL_DB=/tmp/db0.db SKILL_FIND_NOLOG=1 \
  python3 route_eval.py eval_core.json skill_find.py --phase none | tail -2
```

本次结果仍是 `94/96 · 96/96 · MISS 0` → `use_count` 不是原因。
（`ARSENAL_DB` 确实被 `skill_find.py` 读取：指到不存在的路径会直接 traceback，可用来确认 env 生效。）

### ② 把索引库整体搬到对方跑（分离「库内容」与「运行环境」）

```bash
scp ~/.hermes/arsenal/arsenal.db root@<host>:/tmp/local.db
ssh root@<host> 'cd ~/.hermes/arsenal && ARSENAL_DB=/tmp/local.db SKILL_FIND_NOLOG=1 \
  python3 route_eval.py eval_core.json skill_find.py --phase none | tail -2'
```

远程用本机 db 跑出 `94/96 · 96/96 · MISS 0` → **问题在建库内容，不在 Python/SQLite 版本**。
（之前怀疑过 SQLite：本机 3.53.1、远程 3.45.1，FTS5 trigram 行为可能不同——这一步直接排除了它。344MB 传输几十秒，比猜快得多。）

### ③ 逐字段对差

```bash
python3 scripts/db_parity_diff.py /root/.hermes/arsenal/arsenal.db /tmp/local.db
```

输出：2146 vs 2146 行、名字集合零差、**1768 行有字段差异**，第一条差异就是：

```
cursor-ide-ops  status  A='enabled'  B='disabled'
```

status 直方图：本机 `enabled 372 / disabled 1774`，远程 `enabled 2140+ / disabled 6`。

## 根因

`arsenal_build.py`：

```python
DISABLED = set(load_config().get("skills", {}).get("disabled") or [])
status = "disabled" if name in DISABLED else "enabled"
```

归档名单只存在于本机 `~/.hermes/config.yaml`，**不随导出包走**。新机器上 2146 张全 enabled → `SKILLFIND_BOOST=1.15` 对几乎所有卡生效 → 区分度消失 → 排名被拉平。

## 修法（已推 `9b9e6c8c`）

`arsenal_build.py`：

```python
SEED = os.path.join(ROOT, ".disabled.json")
if os.environ.get("ARSENAL_IGNORE_DISABLED_SEED") != "1" and os.path.exists(SEED):
    DISABLED |= set(json.load(open(SEED, encoding="utf-8")))
```

`scripts/export-arsenal-library.sh` 打包前生成 seed（优先 `hermes_cli.config.load_config()`，退回 yaml 读 `~/.hermes/config.yaml`），写 `skills/.disabled.json`；tar 会自然带上。

验证：远程 `python3 arsenal_build.py` 末行 `"enabled": 372, "disabled": 1774, "legacy": 1856` → `post_rebuild_gate.py` 出 `GATE OK（full）· 94/96 · 96/96 · MISS 0 · 改动 0 张`。

## 教训

- 基线分数是**库 + 状态 + 代码**三者的函数；只搬卡不搬状态，full 基线不可复现。
- 「同库不同分」优先怀疑**索引内容**，用「把 db 搬过去跑」一刀切开环境变量，比逐项猜版本快一个数量级。
- 导出包验收除了卡数，必须验 `enabled/disabled` 两个数；只看 total==disk 会漏掉这类问题。
