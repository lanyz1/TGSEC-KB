# 对外分发与干净机器安装（2026-10-22 实测）

## 1. 干净 HOME：从 clone 到能检索

空目录 `HOME=/tmp/fh4` 首跑 `bash scripts/apply-arsenal-20261022.sh --no-purge`：

```
FATAL: 技能树不存在：/tmp/fh4/.hermes/skills
RC=0        # 注意：这是管道 head 的退出码，别当成功
```

补丁（apply 脚本第 0 步）：

```bash
mkdir -p "$HOME/.hermes"
if [ ! -d "$SK" ] || [ "$(find "$SK" -name SKILL.md 2>/dev/null | wc -l)" -eq 0 ]; then
  echo "[i] 安装位为空，先用仓库伞形卡 bootstrap"
  bash "$REPO/scripts/sync-hermes-skills.sh"
fi
```

补完实测（`/tmp/fh5`，空 HOME）：

```
[*] will install 15 skills
校验：工具栈 11 个文件全部到位（md5 一致）
GATE OK（portable，173 条基线不适用）· 索引 15 卡 / 磁盘 15 张 SKILL.md
APPLY_RC=0
```

## 2. portable 与标题/正文词召回

15 卡库上旧逻辑把「标题词 3/8」判成门禁红——基线词是全量库语料，小库根本凑不出来。修法：

```python
if tried >= 4:
    facts.append(...)
    if ok < tried * 0.75 and tier == "full":   # portable 只记录
        probs.append(...)
```

全量库回归不变：`30/30 · core 94/96 · TOP3 96/96 · 标题词 7/7 · 正文词 7/8 · RC 0`。

## 3. 导出包体积：85MB → 41MB

原包（`--exclude` 之前）内含：

- `skills/.curator_backups/2026-10-20T11-20-43Z/skills.tar.gz` — 41MB，**旧 2178 卡快照**
- `skills/.curator_ledger.jsonl` — 11.8MB 操作账本

修法（`scripts/export-arsenal-library.sh`）：

```bash
tar czf "$TAR" -C "$(dirname "$SK")" \
  --exclude='.curator_backups' \
  --exclude='.curator_ledger.jsonl' \
  --exclude='*.pkl' \
  --exclude='__pycache__' \
  "$(basename "$SK")"
```

实测：`42,888,112 B`（tar.gz）/ `42,888,219 B`（.gpg），包内 2146 张；剩余仅 `skills/.curator_state`（小状态文件，可留）。

## 4. 加密分发包

```bash
gpg --batch --yes --passphrase "$P" -c hermes-skills-<ts>.tar.gz
# 产物：*.tar.gz.gpg + PASSPHRASE.txt + *.gpg.sha256
```

解包验证（不要只看 gpg 退出码）：

```bash
gpg -q --batch --passphrase "$P" -d hermes-skills-*.gpg | tar tzf - | awk -F/ '$NF=="SKILL.md"' | wc -l
# 2146
```

## 5. 精简库导入全量包（164 卡 → full）

```bash
git fetch origin master && git reset --hard origin/master   # 不要 git pull
sha256sum -c hermes-skills-*.gpg.sha256
gpg -d hermes-skills-*.gpg | tar xz -C ~/.hermes             # overlay，私有卡保留
python3 ~/.hermes/arsenal/arsenal_build.py
SKILL_FIND_NOLOG=1 python3 ~/.hermes/arsenal/post_rebuild_gate.py
```

判定：`tier=full`、`skipped=0`、`ok:true`、**`total == disk`**（约 2146 + 私有卡，不是 2146 本身）。

## 6. 给对方的整段话术（能直接转发）

```
1) cd <仓库>; git fetch origin master; git reset --hard origin/master; git rev-parse --short HEAD
2) bash scripts/apply-arsenal-20261022.sh
3) cat ~/.hermes/arsenal/gate_last.json   # ok:true 且 total==disk；tier 两种都算过
4) 红线：domains/ 不灌进 ~/.hermes/skills；portable 不许当 full 汇报
```

要 full 再加：`sha256sum -c` → `gpg -d | tar xz -C ~/.hermes` → 重建 → 门禁 `tier=full`。

## 7. 仓库卡数口径（别再报错）

| 口径 | 数字 | 说明 |
|---|---|---|
| `git ls-files | grep -c 'SKILL.md$'` | 1160 | **多 50 条** `references/upstream-*-SKILL.md` 资料转储 |
| 真卡（`.claude/skills` 15 + `domains` 1095） | 1110 | `awk -F/ '$NF=="SKILL.md"'` |
| `find . -name SKILL.md -type f` | 1110 | 加 `-type f` 排掉软链 |
| 安装库 | 2146 | 启用 372 / 归档 1774 |

所以：**仓库 ≠ 安装库**。仓库给 1110 张（含 1095 知识库），安装库另有 1858 份 `references/legacy/*.md` 案卷，仓库里 `legacy/*.md` = 0。
