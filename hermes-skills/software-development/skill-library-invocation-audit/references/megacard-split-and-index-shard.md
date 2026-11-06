# 超长卡拆主卡 + 索引/全文分片（2026-10-21 实测）

目标：单卡正文 ≤12K 字符；目录索引 ≤12KB/片；全文按需 ≤12K 字符/片。

## 0. 备份

```bash
mkdir -p /root/backups
tar czf /root/backups/skills_pre_split.tar.gz -C ~/.hermes/skills <relative SKILL.md paths>
cp ~/.hermes/config.yaml /root/backups/config.premerge.$(date +%s).yaml
```

拆卡前把目标 SKILL.md 打进 tar；不要只依赖 git。

## 1. 量账：字符，不是字节

`hermes prompt-size --json` 的 `skill_md_bytes` 是 UTF-8 字节。中文约 3 字节/字符，**12KB 字节 ≈ 4K 字符**。按字节设 12KB 预算会拆出 1.2KB 空壳路由；按 30KB 字节选目标会漏掉 26.7K 字符的 ASCII 重卡。

```python
n = len(open(path, encoding='utf-8').read())   # 字符数，选目标用这个
```

- 拆目标：`n > 15000` 字符。
- SKILL.md 预算：`12000` 字符。
- 全文二次分片阈值：`full.md > 20000` 字符，片预算 `12000` 字符。

## 2. 拆 SKILL.md

1. 保留 frontmatter + H1 + 开头段。
2. 按 `^## ` 切节，跟踪 ``` / ~~~ fence，代码块内不切。
3. 从第一节起累计，超过 12,000 字符就停；其余节原样写 `references/full.md`。
4. 若第一节本身 >12K：在 `###` 或编号列表项边界再切；绝不能只留 1KB 引言。
5. SKILL.md 末尾插：

```markdown
## 全文导航（已拆分）

主卡保留前 N 节；其余 M 节在 `references/full.md`：

- 标题 1
- 标题 2

加载：`skill_view(name='<name>', file_path='references/full.md')`
```

验证：原 H2 标题集合 = 新 SKILL.md + full.md 的 H2 集合（Counter 等值）；字符数守恒（新 SKILL + full ≈ 原文 + 导航开销）。

## 3. 目录索引分片

触发：`references/index.md` >20KB。

1. 取所有 `- **name**` 条目行，按原顺序每 ≤12KB 字节切一片。
2. 写 `index-part-01.md`…，每片头写“第 i/M 片（n 张，首条→末条）”。
3. master `index.md` 只写片名、首尾条目、条数。
4. **改目录卡 MERGED-INDEX 块**：旧 `index-a-c.md` 等字母片已删除，块内必须改成 `references/index.md`（或列全新片名）。
5. 验收：各片条目合计 = `## 归档子卡（已合并 N 张）`；全库 1,856 条 0 重复；每条 `references/legacy/<name>.md` 存在；master 里的片路径全部存在。

本次：59 片，单片最大 11.8KB；`security-archive-index` 624 条 → 21 片。

## 4. full.md 二次分片

触发：nav 指向的 `full.md` >20K 字符。

1. 按 `^## ` 切 full.md；从第一节起打包，≤12,000 字符/片。
2. 写 `references/parts/part-01.md`…，每片头写“第 i/M 部分”。
3. 写 `references/parts/index.md`：`- 第 i 片：首节 → 末节 — references/parts/part-0i.md`。
4. **不重写原 nav 列表**，只在 nav 末尾追加：`> 全文较大（N 字符），已分 M 片：references/parts/index.md；整包仍可读 references/full.md。`
5. 单节 >12K 时独立成片；`parts/index.md` 标明“超长单节独立成片”，不要谎称每片都 ≤12KB。

本次：18 张、62 片；`pentest-execution` 86.6K 字符 → 8 片。

## 5. 验收清单

```bash
/usr/local/lib/hermes-agent/venv/bin/hermes prompt-size --json > /root/ps_final.json
```

- enabled 359（361 启用 − 2 张平台限定）；索引 38,608 bytes；system 46,919 chars。
- 启用卡最大正文 14,738 字符（没有 >15K 的）。
- 60 张拆卡、59 个索引片、18 张全文分片/62 片。
- 1,856 条归档：0 重复、0 条 legacy 路径缺失、目录计数全对。
- 所有启用卡 frontmatter `yaml.safe_load` 通过。
- 实弹：`skill_view(主卡)`、`skill_view(主卡, 'references/parts/index.md')`、`skill_view(目录卡, 'references/legacy/<name>.md')` 三者都能读。

## 6. 坑

- `skill_view(file_path=...)` 必须带 `.md`，不带后缀只返回目录条目。
- `skill_view(目录卡, 'references/index.md')` 只返回 master；读条目还要再指 `index-part-NN.md`。
- 目录卡 description 为 `>-` 多行 YAML 时，把“含 N 张”追加到最后一个缩进行，不要 `rstrip('"')` 硬拼；改完 `yaml.safe_load` 复验。
- 不要对已拆过的 SKILL.md 再跑一遍拆卡；从 tar 里的原卡重来，否则会丢第一遍移走的块（旧卡分册脚本同坑）。
- 145 处原卡自带的 `references/*.md` 历史悬空引用不是本轮造成，不要伪造文件去填；报告里单列。
- `hermes skills list` 与 `prompt-size` 的 enabled 数会差 1–2（平台限定），别追平。
