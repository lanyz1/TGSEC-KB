# 文档口径 vs 本机实测：一次逐条对账（2026-10-22）

用户问「这个说明和本机的一致了吗」时的完整打法：不读旧产物、不引用别人汇报，**每条声明现场跑一次**。下面是对账清单、抓到的四处错、以及给其他 AI 的同步话术模板。

## 一、对账清单（照着跑，10 条）

| # | 声明 | 命令 | 本轮实测 |
|---|---|---|---|
| 1 | 卡数 | `find ~/.hermes/skills -name SKILL.md \| wc -l` + `sqlite3 arsenal.db "select status,count(*) from skills group by 1"` | 2146（372 启用 / 1774 归档） |
| 2 | 索引体积 | `stat -c %s ~/.hermes/arsenal/arsenal.db` | 342,605,824 B |
| 3 | 重建耗时 | `/usr/bin/time -v python3 arsenal_build.py`（后台跑，别等前台 180s） | 70.75s |
| 4 | 查询延迟 | `skill_find "宝塔 面板 密码 忘了" --top 1` ×3 | 0.40–0.42s，TOP1=`bt-panel-pentest` |
| 5 | 删卡数 | 备份 tar 顶层目录数 + `ls ~/.hermes/skills/security \| grep -c detail-pack` | tar 32 个目录（31 detail-pack + laravel），磁盘 0 |
| 6 | 停用名单 | `load_config()['skills']['disabled']` 长度 | 1805（= 1774 归档 + 31 张已删卡残留名） |
| 7 | 门禁 | `SKILL_FIND_NOLOG=1 python3 post_rebuild_gate.py` | full · 30/30 · 94/96 · 96/96 · 16/16×3 · 7/7 · 7/8 |
| 8 | 索引==磁盘 | `gate_last.json` 的 `total` / `disk` | 2146 / 2146 |
| 9 | 可达率 | `SKILL_FIND_NOLOG=1 python3 full_reachability_audit.py`（~10 min，`REACH_OUT` 改路径） | TOP1 1899 · TOP3 2067 · TOP10 2122 / 2146（98.88%，24 MISS） |
| 10 | 仓库卡数 | `git ls-files \| awk -F/ '$NF=="SKILL.md"' \| wc -l` | 1110 真卡（15 伞形 + 1095 domains） |

## 二、抓到的四处错口径（都已修进 `705bc9ab`）

1. **「全库可达 2146/2146」——假的。** 实测 TOP10 2122/2146 = 98.88%，24 张 MISS（`about-security` / `web-sec` / `hunt-idor` / `hunt-oauth` / `http-parameter-pollution` / `windows-ad` …）。连文档自己写的「≥99%」都没到。旧审计文件里也是 27 条 miss，从来不是全通。
2. **「仓库跟踪 1160 张 = 伞形 15 + domains 1145」——计数口径错。** `git ls-files | grep -c 'SKILL.md$'` 把 50 个 `references/upstream-*-SKILL.md` 转储算进来；真卡 1095（domains），合计 1110。同一份文档另一段又写 1095，自相矛盾。
3. **「docs/learning 里 283 个 SKILL.md 全是符号链接、克隆机悬空」——数量与状态都错。** 实际 283 个符号链接里只有 90 个名为 `SKILL.md`；案卷机上 0 悬空（目标都在），克隆机上才悬空。
4. **验收命令指向不存在的文件。** 说明让跑 `~/.hermes/arsenal/full_reachability_audit.py`，本机只装了老名 `full_reachability.py`。装栈步骤没有完整性检查，漏装无人发现。修法：0/n 步拷贝后逐个 md5 比对，打印「工具栈 N 个文件全部到位」。

## 三、给其他 AI 的同步话术（三版，按场合挑）

**A. 极简三行（已在新仓库上的机器）**

```bash
cd TGSEC-Qtzuu && git pull origin master
bash scripts/apply-arsenal-20261022.sh
cat ~/.hermes/arsenal/gate_last.json   # ok:true + tier
```

**B. 整段可粘（给别的 AI 执行）** 必须含六段：拉取（含 divergent 恢复）→ 跑脚本（幂等、6 步明细）→ 验收（`ok=true`、`total==disk==find`、`tier=full|portable` 语义）→ 两条红线（别灌 `domains/`；`portable` 不许当 full 汇报）→ 要 full 基线就搬 82MB 包（`export-arsenal-library.sh` + `--diff` md5）→ 可引用基线数字（2146 / 342MB / 65–80s / 0.3–0.7s / 98.88%）。

**C. 群里三句话**：仓库地址 + 换代 commit + 「`git pull && bash scripts/apply-…`，末行必须 `GATE OK`；`GATE OK（portable…）` 也算过但不是 full 基线」+ 文档路径。

## 四、报告模板（被问「一致了吗」时）

1. 先给结论：**几成一致 + 几处水分**，别铺垫。
2. 「实打实一致的」用 bullet 列数字，每条注明是现场跑的还是读文件的。
3. 「对不上的」逐条：声明值 → 实测值 → 为什么错 → 修法。
4. 最后一句给动作（「要我改文档并提交吗」→ 直接改 + 推 + 报 commit）。
