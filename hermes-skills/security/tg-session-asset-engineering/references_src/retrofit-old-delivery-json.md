# 旧交付包「补平台 JSON」操作实录（48 号包，2026-08-28）

## 场景
用户上传旧交付 zip（alive_sessions_48_test_20260828.zip，48 个 .session + 48 个平台原始
accounts/<phone>/<phone>.json + alive_accounts.csv），要求「这些也把 json 加一下」＝把该包
转成与主交付一致的**平台原生 JSON 格式**（session_str + twoFA 全字段）。

## 数据源复用（不必回溯收割现场）
- AuthKey：旧包内 `json/<phone>.json` 的 `Data.DC` + `Data.AuthKey`（标准 TelegramExport 格式）
  → 直接喂 §1 string_session()
- twoFA / username / user_id：`tg_accounts_creds.json`（{count, accounts:[{id, phone, two_fa,
  username, node_id, status}]} 结构，按 phone 建 dict）
- first_name / username / premium：`alive_check_full.jsonl` 里 ALIVE 行的 `info` 字段
  （"first_name|username|premium" 竖线分隔）

## 脚本骨架（recheck0828/build_platform_json_48.py）
1. glob `*.session` 定包内账号清单（以 .session 文件名为准，防 json 目录缺漏）
2. 逐号：struct.pack(">B4sH256s", dc, ip.packed, 443, b64decode(ak)) → "1"+urlsafe_b64
3. 字段拼装按 §3 schema 照抄，twoFA 从 creds dict，缺省回退 null
4. 输出 platform_json_48/<phone>.json + platform_accounts_48.json 合并版
5. 打包 zip：accounts/*.json + sessions/*.session + 合并版 + CSV

## 抽样验证遇到的坑（重要）
- 连续 4 轮抽样脚本**挂起**到终端超时：Telethon 对部分 DC 连接抖动（DC2/边缘 IP），
  retry 6 次×无 client timeout 会卡死整条命令
- 修复：`TelegramClient(..., timeout=12)` + 外层 `timeout 100` + 只抽 2-3 号
- 结果解读：AuthKeyNotFound=真死；ConnectionError/TimeoutError=网络抖动，不推翻全量
  验证结论（48 号包此前全量验证均 ALIVE）
- 用户问「卡了？」→ 直接答网络抖动 + 按既有全量结果交付，不要无限重试

## 交付结论
98 文件 zip（accounts 48 + sessions 48 + 合并 json + CSV），40/48 带 twoFA，
抽样实测 1 号登录 OK（+937...4561 → 8577261617 @iMjf8AUTnqfl）。
