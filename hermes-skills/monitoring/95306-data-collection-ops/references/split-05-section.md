## 参考文件

- `references/2026-10-09-backfill-fanout-and-freshness.md` — 补采腿三件套落地实证：扇出 8.9×／P1d 新鲜度加权（rail 行无企业名）／探针六坑／回滚清单。
- `references/2026-10-09-rail-probe-and-p1e-forceaccts.md` — ★rail 探针四坑（缺秒/主控直打/错 ctx/欠采样）+ `user_types` 是白名单的订正 + P1e `force_accts` 排序优先（零污染）。
- `references/2026-10-09-platform-api-boundary-and-probe-pitfalls.md` — ★平台 `findList` 字段/ funcId 家族/参数的真实边界（无包件无审核⇒矩阵必须靠活票）+ `buy_time`=必然登录（收网窗口）+ 探针四坑（`rail_rows` 返元组/旧树 import/票龄符号/欠采样）；且含**缺口快线 gapfast.py 检测器（纯只读，已自测）+ 包装脚本启用/停用命令**。

