# 数字同源 + 一条命令灌库（2026-10-22 实测）

触发：用户问「推送到仓库了没 简介改了吗」「排查到其他机器的问题了吗 要怎么给其他机器说呢」。

## 一、简介数字：四处同源 + About 单列

改卡数时这四处必须一起改，只改 README 会被追第二遍：

| 位置 | 锚点 | 改什么 |
|---|---|---|
| `README.md` | 顶部 bullet / `## 〇、本轮更新了什么` / `## 十、融合批次` / 标题 | 本轮数字链（如 `2178→2146→2204`）+ 新增一节吸收小结 |
| `START.md` | 顶部更新 bullet 列表 + `**规模体感：**` 行 + `**本轮更新（日期）：**` | 虚数换实测（见下）；补当天 bullet |
| `docs/updates/UPDATE-<date>.md` | 文末追加 `## 六、…` | 本批明细 + 门禁数字 + 脱敏口径 |
| `docs/UPGRADE-<date>-<topic>.md` | 标题、§0 一句话、§2 变更表「卡数」行、§3 验收示例、正文 `别死记 <N>` | 全部换成新基线；示例要写 `total/enabled/disabled/tier/ok` |

仓库 **About 描述**：SSH deploy key 只能推代码，本机无 `gh`/token 时改不了。别装作已改，交付时给一句可粘贴文案（例：「面向 AI + 人的授权安全知识库：1,168 张域卡 / 149 实战课，按攻击面组织，含检索栈与重建门禁」）。

### 实测测量命令（不许估）

```bash
cd /root/TGSEC-Qtzuu
echo "domains_files=$(find domains -type f | wc -l)"          # 29,829
echo "domain_cards=$(git ls-files | awk -F/ '$NF=="SKILL.md"' | grep -c '^domains/')"  # 1,153
echo "umbrella=$(find .claude/skills -name SKILL.md | wc -l)"  # 15 → 合计真卡 1,168
echo "case_md=$(find domains -path '*case-lessons*' -name '*.md' | wc -l)"  # 149
echo "domain_dirs=$(find domains -maxdepth 1 -type d | wc -l)"  # 31（含 domains 自身，报 30）
```

注意：`find -type d` 结果含 `domains` 自己；`case-lessons` 里含各域 `README.md` / `REPORTS-*-INDEX.md`，报「实战课 149」前先确认口径（要精确就用 `reconcile_case_index.py`）。

## 二、`scripts/import-arsenal-package.sh`（一条命令灌库）

用法：`bash scripts/import-arsenal-package.sh <pkg.gpg> <PASSPHRASE.txt>`；env：`HERMES_SKILLS`（默认 `$HOME/.hermes/skills`）、`BACKUP_DIR`（默认安装位父目录）。

四步：

1. **校验包**：`gpg -d | tar xz -C $TMP`，数 `SKILL.md` 与 `.disabled.json` 条数；解不开直接 FATAL（口令错/包坏）；seed=0 只 WARN（提醒 core96 会掉 88/96）。
2. **备份旧库**：有卡才 `mv` 成 `skills.bak-<时间>`（省磁盘，不做 copy）；空安装位跳过。
3. **解包**：`gpg -d | tar xz -C $(dirname $SK)`，再数一次卡数。
4. **装检索栈 + 重建 + 门禁**：直接调 `scripts/apply-arsenal-20261022.sh`，最后从 `gate_last.json` 打印 `total/disk/tier/skipped/ok`。

**假 HOME 首装实测**（必做，真机已升级只会走幂等分支）：

```bash
HOME=/tmp/t9 HERMES_SKILLS=/tmp/t9/.hermes/skills BACKUP_DIR=/tmp/t9 \
  bash scripts/import-arsenal-package.sh <pkg.gpg> <PASSPHRASE.txt>
# 输出末行：total=2204 disk=2204 tier=full skipped=0 ok=True / IMPORT_RC=0
```

## 三、验包（换机器前后都能跑）

```bash
bash scripts/verify_package_clean.sh <pkg.gpg> <PASSPHRASE.txt> 2204 '154\.219\.127\.' secret_literals.txt
# cards=2204 expect=2204 ip_hits=0 literal_hits=0 seed=1805
# sha256=<...>
# PKG_CLEAN
```

`secret_literals.txt` 放已知泄漏字面量（每行一个，精确匹配），**放 `/root/audit-<date>/` 不入仓**。

## 四、worker 仓库对齐（易漏的一步）

库同步完 ≠ 仓库同步完。两台 worker 实测：库已 2204 全绿，仓库 HEAD 却停在 `ef5287ca`（落后 `bd0bc76a`、`4a9106ab`…）。对齐脚本（口令从本机既有脚本提取，不手打）：

```bash
export SSHPASS=$(grep -oP "export SSHPASS='\K[^']+" /root/audit-<date>/probe60.sh | head -1)
for H in <host1> <host2>; do
  sshpass -e ssh -o StrictHostKeyChecking=no root@$H \
    'cd /root/TGSEC-Qtzuu && git fetch -q origin && git reset --hard -q origin/master && echo "$(hostname) HEAD=$(git rev-parse --short HEAD) dirty=$(git status --porcelain|wc -l)"'
done
# 期望两行同一短哈希 + dirty=0
```

## 五、给其他机器的可复制提示词（骨架）

结构固定，不要写成设计文档：① 拉仓库 + 断言 HEAD；② 分 A（有包 → full）/ B（只有仓 → portable）；③ 一条判据 `ok:true 且 total==disk`；④ 红线（`domains/` 不进 `~/.hermes/skills`；自有 IP/密钥不入卡/文档/commit；口令不抄进文件）；⑤ 故障对照表（seed 缺 → 88/96；技能树空 → FATAL；`pull` divergent → fetch+reset；`dirty 1` = `.tgsec-bootstrapped`；`skill_find.py` 不存在 → 检索栈没装）；⑥ 回三行：HEAD / total·disk·tier·ok / 跳过条目。

用户偏好：**整段能直接转发**，别给「方案 A/B 设计说明」；末尾一句「就这些」。
