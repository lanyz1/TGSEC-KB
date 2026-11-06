# 上下文预算与巨型卡分册（2026-10-17 实测）

## 1. 问题口径

「技能太多会不会调不到」要拆成三件事，别混：

| 现象 | 本质 | 处置 |
|---|---|---|
| 名字不在索引 | 裸名撞名、被覆盖、frontmatter 缺失 | 修 name/dir、补 frontmatter |
| 名字在但加载即爆 | 单卡 SKILL.md 体积 > 上下文窗口 | 按 H2 分册到 references |
| 加载过又丢 | 压缩触发 `[SKILL_PRUNED]` | 按名重载 `skill_view` |

`skill_view(name)` 是按名精确读文件；2,137 张卡全在索引里时，数量本身不造成「调不到」。真正的固定开销是索引占用的上下文。

## 2. prompt-size 实测（2,137 卡，snapshot 重建后）

命令：

```bash
rm -f /root/.hermes/.skills_prompt_snapshot.json
/usr/local/lib/hermes-agent/venv/bin/hermes prompt-size --json
```

结果：

- system prompt：196,869 chars / 267,788 bytes
- skills index：**181,063 chars / 248,802 bytes**
- security：**171,056 chars（95%）**
- tools：30 个 / 45,534 bytes
- context：200,000
- 索引 token 估算（CJK 1 token/字 + 非 CJK/4）：**约 6.7–8 万**

索引构成：name+description，每条平均约 55 chars description；security 是绝对大头。

## 3. 巨型卡拆分账

| 卡 | 拆前 | 拆后 SKILL.md | refs |
|---|---|---|---|
| sinian-omnipotent | 728 KB | 21 KB | 9（522 KB）|
| offensive-windows-boundaries | 568 KB | 4 KB | 9（538 KB）|
| offensive-windows-mitigations | 531 KB | 14 KB | 9（498 KB）|
| offensive-crash-analysis | 410 KB | 10 KB | 7（382 KB）|
| offensive-basic-exploitation | 355 KB | 3 KB | 8（333 KB）|

校验：5 张原卡逐 H2 块 Counter 比对，missing=0 / extra=0；YAML 全过。

## 4. 踩过的坑：二次分册丢正文

第一遍把 `offensive-crash-analysis` 的 Day1–6 大块搬进 references，第二遍从「已拆过的 SKILL.md」重新分册时只看到剩余小块，重建逻辑删除旧 refs → **Day1–6 约 290KB 被删**。

修复：从 `skill_backup_20261017_v2.tar.gz` 取回原卡，按原 H2 块一次性重新分册；再逐块 Counter 校验。

规则：**分册永远从原始 SKILL.md 开始；已有 `references/part-*.md` 时脚本默认拒跑**。

## 5. 验证片段

- 原块规范化：`'\n'.join(line.rstrip() for line in block.strip('\n').splitlines())`
- 目标块池：新 SKILL.md（排除 `## 分册索引`）+ 每个 ref 按 H2 切块
- `Counter(original) == Counter(target)` 才算过；只做 `in` 子串检查会被尾随空行/短标题骗出假阴性。
- `skill_view('offensive-basic-exploitation')` 返回 `linked_files.references` 8 项，与磁盘一致。

## 6. 索引还能怎么压

- 拆 references **不改变索引**（索引只读 frontmatter）。
- 同族合并成 router（如 122 张 `re-*` → 10 张、73 张 `hunt-*` → 8 张）可减条目，但内容合并风险高。
- names-only 降级：Hermes 已有 category demotion（`compact_categories`），目前只由 coding posture 触发；security 长尾降级估算 181K → ~55K chars，省约 5 万 token，代价是丢描述。
- 不建议为了索引体积盲删卡；先量 `prompt-size`，再决定是拆卡、合卡还是降级。
