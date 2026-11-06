# README 只保留最近一次更新 — 实操配方

用户口径：「只要最近一次更新了什么就行 其他不用显示了」。2026-10-19 实测：README 582 行 → 348 行，历史 256 行压掉，明细转 `docs/updates/`。

## 三个历史堆积点（缺一处就不算收干净）

1. 顶部 `- 2026-xx-xx：...` 连续 bullet 列表
2. `## 〇、本轮更新了什么`（到 `## 一、这是什么` 为止）
3. `## 十、融合批次`（到 `## 十一、` 为止）

## Python 改块（按锚点，从后往前）

```python
import pathlib
p = pathlib.Path('/root/TGSEC-Qtzuu/README.md')
lines = p.read_text(encoding='utf-8').split('\n')

# 1) 定位
i_top = next(i for i,l in enumerate(lines) if l.startswith('- 2026-'))
i_top_end = i_top
while i_top_end+1 < len(lines) and lines[i_top_end+1].startswith('- 2026-'):
    i_top_end += 1
i_note  = next(i for i,l in enumerate(lines) if l.startswith('**👉 本轮更新说明'))
i_sec0  = next(i for i,l in enumerate(lines) if l.startswith('## 〇、本轮更新了什么'))
i_sec1  = next(i for i,l in enumerate(lines) if l.startswith('## 一、'))
i_sec10 = next(i for i,l in enumerate(lines) if l.startswith('## 十、融合批次'))
i_sec11 = next(i for i,l in enumerate(lines) if l.startswith('## 十一、'))
i_upd   = next(i for i,l in enumerate(lines) if l.startswith('**更新说明文件：**'))

# 2) 必须从后往前替换，否则索引漂移
lines[i_upd:i_upd+1]    = [UPD_LINE]
lines[i_sec10:i_sec11]  = SEC10.split('\n')
lines[i_sec0:i_sec1]    = SEC0.split('\n')
lines[i_note:i_note+1]  = [NOTE]
lines[i_top:i_top_end+1] = [TOP_BULLET]
p.write_text('\n'.join(lines), encoding='utf-8')
```

切片替换时保留原分隔符：`§〇` 段末尾保留一个 `---`，`§十` 段末尾保留空行，否则下一节会贴上来。

## 各块该写什么

**顶部 bullet（1 条）**
```
- 2026-10-19：**报告包 11 份 → 12 课 + 当日四源/CVE/77169 吸收** — <4~5 个最硬点用 · 分隔>；CASE-INDEX **127→139**。详见 [INGEST](domains/INGEST-YYYYMMDD-PACK.md)
```

**§〇 本轮更新（只本轮）**
```
## 〇、本轮更新了什么（YYYY-MM-DD）

### <主项名>（YYYY-MM-DD）
<体量与处理结果一句话>
- **手法 A**：一句话链路
- **手法 B**：一句话链路
- **其余 N 课**：每条 3~8 字，用 · 串一行

账本：[INGEST](...) · 详情：[UPDATE](...) · CASE-INDEX **X→Y**

### 当日其余吸收（同日）
- **四源**：... → 落到哪
- **CVE 两批**：... 纠正了哪几处
- **整站情报**：篇数 / CVE 数 / 新增数
```

**§十 融合批次（1 条 + 一句指路）**
```
## 十、融合批次

### YYYY-MM-DD · <批次名>（N 份 → M 课）

- M 课落 `domains/{...}/case-lessons/`，CASE-INDEX **X→Y**
- 本机技能库同步：A 新卡 + B 处旧卡增量（列名）
- 硬闸：原文不入库；明文口令 / TOTP 种子 / bot_token / 源站 IP / 客户 PII 零落库
- 账本：[INGEST](...) · 详情：[UPDATE](...)

> 历史批次（YYYY-MM-DD 及更早）不在 README 展开，见 [`docs/updates/`](docs/updates/) 与 `git log`。
```

## 自检

```bash
cd /root/TGSEC-Qtzuu
grep -n '2026-10-1[0-8]\|2026-0[1-9]' README.md   # 只应命中「历史批次」提示行
wc -l README.md                                    # 应显著下降（本次 582→348）
grep -n '^## ' README.md                           # 节序完整，§〇..§十四 不重不漏
```

提交信息：`docs(readme): keep only latest update block (YYYY-MM-DD); history moved to docs/updates + git log`
