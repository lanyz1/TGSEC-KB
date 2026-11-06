---
name: deliverable-packaging
description: "Use when delivering big files or dumps to a chat."
version: 0.1.0
tags: [delivery, telegram, large-files, packaging, report, 分卷, 大文件投递, 投递, 战利品交付, tg, TG投递, 投递到tg, 分卷压缩, 大文件分卷, 发文件, 交付文件]
---

# 战利品/报告交付打包（大文件分发 · 网盘链接 · 使用说明）

把大件交付物（数据 dump / 整库 / 报告）送到聊天用户手上时用。核心事实：**Telegram 机器人单文件硬顶 ~50MB**（63MB 实发被拒 `Request Entity Too Large`；48MiB 分片稳定通过；文本/CSV 的 `tar | zstd -10` 实测压缩到 16.9%）。

## 交付形态决策

1. **<50MB**：直接回复里 `MEDIA:/abs/path`（zip 优先，附 md5）。
2. **大包要发到聊天**：`tar | zstd -10` 打包 → `split -b 48M` 分片 → 后台脚本逐片 `hermes send` 连发（本技能 `scripts/send_parts_via_hermes_send.py`，验 `"success": true`、失败退避重试、收尾自动发清单）+ `terminal(background=true, notify=true)`。
3. **大包要下载链接**：GoFile 上传（`scripts/gofile_upload.py`：免账号、大文件 OK、返回 downloadPage；**服务端回读 md5 核对**再给链接）→ 聊天发链接+md5+取件说明。备选：pixeldrain / bashupload（0x0.st 上限 512MB，装不下就拆）。
4. **报告类**：MD 源文件 + `scripts/md2docx.py` 转 DOCX（纯 python-docx，无需 pandoc；标题/表格/列表保留）两版一起发。

## 收件人「怎么打开」必附（会被问）

- 分片合并：Windows `copy /b dump_part-*.part full.tar.zst`；Mac/Linux `cat dump_part-*.part > full.tar.zst`。
- `.tar.zst` 解压：7-Zip 解两次（先 zst 再 tar）；或 `zstd -d` + `tar -xf`。
- **百万行 CSV 别用 Excel**（104 万行硬顶+卡死）→ 推荐 DuckDB 单文件直查（`select * from 'x.csv' limit 100`）或导 SQLite；小文件 Excel 导入编码选 UTF-8。
- SQLite 库 → DB Browser for SQLite（免费 GUI）。

## 交付内容口径（本用户偏好）

- **实体数据默认给全字段档案，不做单列裸表**：先发纯号码列会被追问「其他信息呢」——直接出 ID+身份+资金 全字段版（单列版可另附）。
- 体量先说清：样本 vs 全量、哪些物理不可整搬（TB 级）、哪些可按需切片；承诺「全量」前先算片数与压缩后体积。
- 附 md5；命名带日期+内容摘要；中文文件名可直发。
- 大包传网盘后提醒尽快转存（GoFile 免费档长期不取会被清）。

## Pitfalls

- `hermes send` 遇超限返回 `error: No deliverable text or media remained...` + warning `Request Entity Too Large` → 降低分片（48MiB 稳），不要重试同尺寸。
- 分片连发：片间 sleep 3-5s；单片失败退避 15s 重试 ≤3 次（实测偶发一次即过）；发送脚本日志落盘（`*.send.log`）。
- 打包前剔除重复/派生文件（如 JSON 导出已含在 DB 里就不再进包）。
- 压缩选型：zstd -10 快且好（3GB→529MB/40s）；xz 更小但慢数倍，按时间预算取舍。
- 发送任务必须 background+notify；完成后自动发清单消息（把「合并/解压命令 + md5 + 片数」写进去）。
- 别把超限原因误判为平台故障：先降片重试，再谈替代通道。

## Support files

- `scripts/send_parts_via_hermes_send.py` — 归档 → 48MB 分片 → hermes send 连发 + 重试 + 清单（泛化自 2026-10 实战）。
- `scripts/gofile_upload.py` — GoFile 免账号上传 + md5 核对，打印下载页。
- `scripts/md2docx.py` — Markdown → DOCX（python-docx，标题/表格/列表）。
