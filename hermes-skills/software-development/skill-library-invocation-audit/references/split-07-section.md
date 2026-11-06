## 修复、提交与同步（本机 + 仓库双树）

本机 `~/.hermes/skills` 与发布仓 `domains/**/SKILL.md` 是**两套独立文件**：本地拆完 ≠ 仓里修好。2026-10-17 实测本地 5 张巨卡拆完，仓库仍有 7 张 >200KB（含 2 张本地没有的 sinian 供应商卡）。

1. **双树量体积**：`find ~/.hermes/skills -name SKILL.md -size +200k` + `find <repo>/domains -name SKILL.md -size +200k`；两边都归零才算完。
2. **按名映射仓库路径**：`git -C <repo> ls-files | grep -E '/(<card>)/SKILL\.md$'`。仓库是域布局（`domains/<域>/.../<卡>/SKILL.md`），不要假设与 `.hermes` 同路径。
3. **仓库独有巨卡**：本地没有的供应商卡也要拆；直接从仓库原文件拆，拆前用 `git show HEAD:<path>` 留原字节。
4. **同步本地分册**：复制 `SKILL.md` + `references/`，保留仓库原有 `scripts/` 等目录；核对页脚署名 `@TGSEC社区 · @TGSEC-Qtzuu 整理`——本地拆卡常把它丢掉，必须补回。
5. **mode 归一**：`cp` 会把 644 带成 755；`chmod 644` 后 `git show --summary` 查 `mode change`，有就 amend。
6. **提交与验收**：`git add -A` 后按 `git diff --cached --name-only | wc -l` 核对真实文件数（`git status` 对未跟踪目录只显示 1 行）；commit → `python3 /root/tgsec-guard/scan_push.py <repo>` → 有 amend 必须重扫 → push → `git ls-remote origin refs/heads/master` == `git rev-parse HEAD`，工作树 0 残留。
7. **留档**：审计全文 `docs/SKILL-AUDIT-<date>.md`；同日更新说明 `docs/updates/UPDATE-<date>.md`（在尾部 `@TGSEC` 署名行前插入；`patch` 对全角空格易失配，用 Python `rfind(marker)` 更稳）。

逐卡映射、体积与校验命令见 `references/repo-sync-oversized-cards-20261017.md`。

- 跨机语义：pull ≠ 技能更新——pull 完要重跑 sync 才装进各 agent 目标目录（旧死目录要留回退）。
- 推库口令与推后三件验收（三方针齐平 / 反向克隆+旧对象 404 探针 / 落盘）见 security-kb-ingest `references/push-guard-acceptance.md`。

