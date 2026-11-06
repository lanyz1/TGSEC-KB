# 仓库侧巨卡同步实录（2026-10-17）

## 为什么单独立档

`~/.hermes/skills` 与发布仓 `/root/TGSEC-Qtzuu` 的 `domains/**/SKILL.md` 是两套独立文件。
本地把 5 张 >200KB 巨卡拆完后，仓库仍有 **7 张 >200KB**：5 张同名副本 + 2 张本地根本没有的 sinian 供应商卡。
只量本地树会误判「已修完」。

## 实测体积账

| 仓库路径（`domains/.../<card>/SKILL.md`） | 拆前 | 拆后 SKILL.md | references |
|---|---:|---:|---:|
| `other/src-methods/_vendor/sinian/sinian-sinian-omnipotent` | 728,838 | 30,846 | 9 |
| `windows-post/hunter-6000/offensive-windows-boundaries` | 567,524 | 5,211 | 9 |
| `windows-post/hunter-6000/offensive-windows-mitigations` | 530,499 | 14,762 | 9 |
| `binary-pwn/hunter-6000/offensive-crash-analysis` | 409,253 | 13,392 | 7 |
| `web-attack/hunter-6000/offensive-basic-exploitation` | 354,312 | 3,639 | 8 |
| `malware-dfir/src-methods/_vendor/sinian/sinian-anti-forensics` | 367,158 | 2,090 | 20 |
| `post-exp-tools/src-methods/_vendor/sinian/sinian-data-exfiltration` | 208,203 | 2,178 | 16 |

后 2 张是仓库独有，本地 `.hermes` 没有同名目录；不要因为本地“只找到 5 张”就漏掉。

## 操作序列

### 1. 双树量体积

```bash
find /root/.hermes/skills -name SKILL.md -size +200k -printf '%s %p\n' | sort -rn
cd /root/TGSEC-Qtzuu
git ls-files | grep -E '/(sinian-omnipotent|offensive-windows-boundaries|offensive-windows-mitigations|offensive-crash-analysis|offensive-basic-exploitation)/SKILL\.md$'
find domains -name SKILL.md -size +200k -printf '%s %p\n' | sort -rn
```

### 2. 仓库路径映射

仓库是域布局，同名卡路径不等于 `~/.hermes/skills/security/<card>/`。

```bash
git ls-files | grep -E '/(<card>)/SKILL\.md$'
```

### 3. 拆分仓库独有卡

直接用围栏感知的 H2 拆分器：frontmatter + 首段 preamble 留在 SKILL.md，其余每个 `## ` 段落 `references/part-NN.md`。
复用 `skill-library-invocation-audit/scripts/split_oversized_skill.py`；它要求从**原始未拆**的 SKILL.md 起跑。

```python
# 关键：只在 ``` / ~~~ 围栏外匹配 ^## \n# 否则代码块里的注释会被当标题
fence = None
for ln in body.splitlines(keepends=True):
    s = ln.lstrip()
    if fence is None and (s.startswith('```') or s.startswith('~~~')):
        fence = s[:3]
    elif fence and s.startswith(fence):
        fence = None
    if fence is None and ln.startswith('## '):
        # 切段
```

### 4. 同步本地分册到仓库

- 复制 `SKILL.md` + `references/` 到仓库对应目录。
- **保留仓库原有的 `scripts/`、其他子目录**，不要整目录覆盖。
- 页脚署名：本地拆卡常把 `@TGSEC社区 · @TGSEC-Qtzuu 整理` 丢掉；同步时检查并补回。
- `cp` 后文件 mode 可能从 644 变 755：`chmod 644 <SKILL.md>`，`git add` 后看 `git show --summary` 有没有 `mode change`，有就 amend。

### 5. 校验

```bash
# 仓库内不再有 >200KB 的 SKILL.md
find domains -name SKILL.md -size +200k | wc -l   # 必须 0

# YAML 可解析
python3 - <<'PY'
import re,yaml,pathlib
for p in pathlib.Path('domains').rglob('SKILL.md'):
    t=p.read_text(encoding='utf-8')
    m=re.match(r'^---\n(.*?)\n---\n',t,re.S)
    if m: yaml.safe_load(m.group(1))
print('yaml ok')
PY
```

内容守恒（两类分别验）：

- 本地已拆卡 → 仓库同名副本：原卡所有行 vs 新 `SKILL.md`+refs 的行多重集，`missing` 只能是页脚/索引等故意改动行。
- 仓库独有卡：拆分后 `frontmatter + preamble + ''.join(parts)` 必须**逐字节等于原文件**，再写盘。

### 6. 提交与推送

```bash
cd /root/TGSEC-Qtzuu
git add -A
git diff --cached --name-only | wc -l          # 真实文件数；git status 对未跟踪目录只显示 1 行
git diff --cached --name-only | grep '/references/' | wc -l
git commit -m "fix(skills): 7 张 >200KB 巨型 SKILL.md 分册 + <date> 技能库体检报告"
python3 /root/tgsec-guard/scan_push.py /root/TGSEC-Qtzuu
git push origin master
git ls-remote origin refs/heads/master | cut -f1   # 必须 == git rev-parse HEAD
git status --porcelain=v1 | wc -l                # 必须 0
```

守卫扫的是**提交差**：commit 前扫不到；amend 后必须重扫。

### 7. 留档位置

- 审计全文：`docs/SKILL-AUDIT-<date>.md`
- 同日更新说明：`docs/updates/UPDATE-<date>.md`，在尾部 `@TGSEC社区 · @TGSEC-Qtzuu 整理` 前插入新节。
- `patch` 对全角空格/尾随空白容易失配；用 Python `t.rfind('@TGSEC社区')` 定位后切片插入更稳。

## 坑位

- 只量 `.hermes` 不量仓库 → 漏 2 张仓库独有巨卡。
- `git status --short` 把未跟踪的 `references/` 目录折叠成 1 行；不要用它估算文件数。
- 直接整目录 `shutil.copytree` 覆盖仓库卡目录 → 可能删掉仓库原有 `scripts/`。
- 忘记 `chmod 644` → commit 里出现 755 mode change，虽然能推但脏。
- 页脚被拆卡丢掉 → 仓库署名不一致；同步时补。
