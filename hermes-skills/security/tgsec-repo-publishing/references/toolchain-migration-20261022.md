# 工具链迁移包实战：检索栈入仓（2026-10-22）

一次性把「本机脚本」变成「别人能跑的发布包」的完整账。以后发布同类包照抄这个形状。

## 发了什么（commit `2808b425` → `cf35f568`）

| 路径 | 内容 |
|---|---|
| `tools/arsenal/` | 12 文件：9 个 py（build / find / gate / keeper / build_termdf / selftest / route_eval / trim_scan / full_reachability_audit）+ 2 个 eval json + README |
| `scripts/apply-arsenal-20261022.sh` | 幂等 6 步升级（装栈 → 备份 → 删卡 → 搬 refs → 写 disabled → 重建+门禁），`--no-purge` 跳过清磁盘 |
| `docs/UPGRADE-20261022-ARSENAL.md` | 旧克隆升级指南：变更表 / 脚本法+手工法 / 验收表 / 回滚 / 9 条坑 / 可粘提示词 |
| `docs/updates/UPDATE-2026-10-22.md` §四 | C 批明细：删 32 张 / 停 6 张 / 回收 ≈325MB / 盲测 10→12 |
| `README.md` | 顶部 bullet、§〇 新子节、§十 改「三批」、§十二 加升级命令与链接 |

## 抓出的三个真 bug（都是假 HOME fixture 跑出来的）

1. **漏 helper**：`arsenal_build.py` 末尾 `subprocess.run(sys.executable, "build_termdf.py")`；只拷三个主脚本 → 别人首次重建 `no such table: term_df` + gate traceback。修：升级脚本按 `*.py` 全拷；gate 缺表时改为 `probs.append` 而不是抛栈。
2. **硬编码路径**：四个脚本全是 `/root/.hermes/...`。修：`ARSENAL_SKILLS` / `ARSENAL_DIR` / `ARSENAL_DB` / `ARSENAL_ROUTE_EVAL` 环境变量，默认值不变；升级脚本 export 之，`selftest.py` 调子进程改用 `sys.executable`。
3. **门禁污染检索日志**：三 phase 评测的 `subprocess.run` 漏了 `env={**os.environ, "SKILL_FIND_NOLOG": "1"}`，每跑一次门禁往 `query.log` 灌几十条假检索。修后实测：gate 跑完 `query.log` 仍 9 行。

## 假 HOME 验收（可复现）

```bash
bash <skill>/scripts/fake_home_fixture.sh /tmp/fh
HOME=/tmp/fh HERMES_SKILLS=/tmp/fh/.hermes/skills \
  ARSENAL_DIR=/tmp/fh/.hermes/arsenal ARCHIVE_DIR=/tmp/fh/archive \
  bash scripts/apply-arsenal-20261022.sh --no-purge
```

必须看到：`0/6` 列出 12 个文件 → `1/6` 备份 2 张 → `2/6` 已删 2 张 → `3/6` 搬 h1 → `4/6` 写 disabled → `6/6` 建库；门禁 **FAIL**（2 张卡过不了 96 条评测）且**没有 Traceback**。

门禁失败是预期的；判定标准是「分支全走到 + 报错可读」，不是「假树上绿」。

## 验收与坑

- 真机幂等跑：`GATE OK · 2146 卡 · TOP1 94/96 · TOP3 96/96 · MISS 0 · selftest 30/30`；`query.log` 不增长。
- 从真 remote 重 clone 再跑：`git clone git@github.com:lanyz1/TGSEC-Qtzuu.git`（HTTPS 私有仓匿名 clone 报 `could not read Username`），clone 里 `ls tools/arsenal | wc -l` = 12、`bash -n` 过、executable bit 在。
- 中途 amend 导致 force-push：`082202e1 → fca9a05b`（首版）被 amend 成 `2808b425`，别的克隆 pull 会 divergent。补救：文档写 `git stash -u && git fetch origin && git reset --hard origin/master`；教训是本地 fixture 跑完再推第一次。
- 不要承诺「别人卡数=2146」：仓里没有全量卡，升级只删对方本机存在的同名卡。验收口径：索引卡数 == 磁盘 SKILL.md 数 + `GATE OK`。
