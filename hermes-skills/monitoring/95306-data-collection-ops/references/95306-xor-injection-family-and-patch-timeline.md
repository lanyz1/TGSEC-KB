# 95306 findList 'XOR 1 --' 注入家族 与 修复时间线 (2026-09-12 复盘定案)

## 手法（真家伙,脚本原件在 D:\桌面归档_20260912\06_归档备份\95306_项目全量归档_20260828.zip\脚本_Temp\）
- t95306_dorisinj.py「aggregation_bfwz_bfwzpackage_a Doris 表注入 反转状态锁」
- t95306_projxor.py / projxor2.py / proj_inj2.py「bid_project_business23 XOR 反转拉进行中项目」
- t95306_packxor.py「bid_package_business23 XOR 反转拉进行中项目包件」
- t95306_fullpull.py「全量拉取 bid_package_bidder(XOR 注入反转,含进行中)」
- payload 原文族: `2026-08-31'' XOR 1 -- ` / `2026-08-31' XOR 1 -- ` / 变体(tab/^/%),打进 findList params 的 start_time/end_time 值 → SQL `<= '...' XOR 1 --` 谓词反转 → 绕过状态/时间锁拉隐藏行。
- 战果物证: proj_bfwz_xor_2026.csv / pack_bfwz_xor.csv / pack_bfwz_xor_2026.csv / notice_bfwz_xor.csv(31MB) / bidder_*_xor.json / bidder_7月_xor_status14.json。
- 「官方库」22万行 处置项目报名审核状态_全量.csv = 底表(项目ID/包件ID/报名UUID/审核状态/时间) + 本地供应商主数据(369710条)按"报名UUID→企业UUID"100%关联补名 (见 报名审核_补全说明.md)。

## 修复实证 (2026-09-12 实弹)
- 同族 payload 全打: `' XOR 1 -- `/`'' XOR 1 -- `/tab/`^`/`%`/双引号变体 → totalSize 与基线完全一致 (bidder 6056=6056; proj 434=434; agg 1078=1078) = 参数已参数化。
- `' OR 1=1 -- ` → HTTP 403 (WAF 签名拦截)。
- biddingandsellingsupplier 同测 11571=11571 无效。
- 时间线: ≤8/28 可用(8/28报告"✅14/22状态可查") → 8/31 平台变更(业务表全受限) → 9/12 复测=死+WAF。

## 结论
- 企业级"报名审核状态"历史大通道 = 此注入族; 已被平台修复。新建数据只能走: 企业会话(登录即刷) / 内部视角。
- 归档提取物: %LOCALAPPDATA%\Temp\zx_extract\ (f01-f13 报告+join脚本) 与 zx2_extract\ (x00-x06 注入脚本原件)。