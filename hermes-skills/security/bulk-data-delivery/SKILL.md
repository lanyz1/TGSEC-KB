---
name: bulk-data-delivery
description: "Use when delivering big data files. Chunking, hosts, MD5."
version: 0.1.0
tags: [delivery, telegram, gofile, zstd, split, md5, 分卷, 大文件, 投递]
---

# 大体积数据交付（聊天通道 + 网盘 + 分卷）

长任务产出几十 MB ~ 几 GB 数据包时的标准交付流程。目标：交付物完整可校验、对方能一步步打开、不刷屏。

## 通道能力（实测）

- Telegram Bot API 单文件上限 ~50MB。63MB 实测被拒，报错形如 `Request Entity Too Large`（媒体发送失败警告里出现即超限）。**48MB（50,331,648B）分片实测稳定通过**。
- 回复内直接发：`MEDIA:/abs/path`。脚本化批量发：`hermes send --to telegram:<chat_id> --json "MEDIA:<path>"` → 解析输出 `"success": true` 判成功；失败隔 15s 重试（实测偶发单次失败重试即过）；chat_id 用 env `HERMES_SESSION_CHAT_ID`。
- 超 50MB 的大包 → 网盘直链（用户偏好：“直接把压缩包做成下载链接”）。GoFile 实测 554MB 上传 35–40s。

## 标准流程

1. **打包结构**：优先一个 `.tar.zst` 装**原始文件**（用户一次解压到位）。`tar -cf - files | zstd -10 -T0 -o out.tar.zst`（3GB→529MB 实测 40s）。
2. **打包后必验**：`zstd -t <file>`（完整性）；`tar --zstd -tf <file>`（清单核对条目数）；`md5sum`。
3. **分片**：`split -b 48M -d --additional-suffix=.part <archive> <prefix>-` → 给用户的合并指令按平台写全：
   - Windows（同目录 cmd）：`copy /b <prefix>-*.part <archive>`
   - Linux/Mac：`cat <prefix>-*.part > <archive>`
4. **发送脚本**（Python + `subprocess hermes send --json`）：循环分片、解析 success、每片约 4s 间隔、失败重试 3 轮；**全部发完再发一条 manifest**（片数 / 合并命令 / 整包 MD5 / 内容摘要）。脚本挂后台 + notify；日志落盘（含每片字节数）。
5. **网盘（GoFile）**：
   ```bash
   SRV=$(curl -sk https://api.gofile.io/servers | python3 -c "import json,sys;print(json.load(sys.stdin)['data']['servers'][0]['name'])")
   curl -sk -F "file=@<path>" "https://$SRV.gofile.io/contents/uploadfile" -o resp.json
   # resp.json → data.downloadPage = 分享链接；data.md5 必须与本地 md5sum 一致（服务器侧校验）
   ```
   免费档提醒用户尽快下载/转存（闲置会被清）。
6. **交付消息**：链接 + MD5 + 解压/打开步骤（Windows-first：7-Zip 对 `.tar.zst` 解两次）+ 内容清单（文件名/行数/大小）。大数据文件给打开建议：百万行 CSV 别用 Excel（卡死）→ DuckDB / SQLite `.import` / DB Browser；Excel 友好 CSV 用 **utf-8-sig BOM**（实测中文表头不乱码）。

## Pitfalls

- 别预先盲目拆小（“先拆 32MB 图稳”）——先发一发 ~48MB 探针测真实上限，失败再降级。
- 发送日志必须逐片确认成功再宣布“完成”；manifest 的 MD5 用整包（不是单片）计算。
- 分卷命名用 `-00/-01` 数字后缀（`split -d`），保证字典序 = 拼接序；`copy /b *.part` 按字典序拼，命名不对会拼错。
- 已压缩文件再套 tar.zst 不增值（双层压缩陷阱）；要么只装原始文件，要么直接发原始分片。
- 交付大 CSV 时把行数与字段清单一起写进消息（用户会核对行数=真实性）。
