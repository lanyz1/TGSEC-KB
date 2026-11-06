## 缺口闭环的唯一杠杆

- 平台公开面（`dataplatform/api/findList`）**只有**企业名/统一信用代码/报名时刻，**无账号、无包件、无审核状态**
  ⇒ 每企业「通过/驳回包件矩阵」只能由**企业活票**采集；token 寿命 ≤3h。
- 所以采网全部杠杆 = **排序优先级（缺口账号 rank=0）+ 轮次频率 ÷ token 寿命**；
  缺口账号不在 `miss_accts` 时靠 `force_accts` 提序（只改排序、不进 `match_name` ⇒ 零污染）。
- 缺口家必在**竞价开始/结束**窗口再次登录 ⇒ 那个窗口就是收网时刻，盯紧它。
- 明细：`references/platform-authority-vs-token-fields.md`、`references/2026-10-09-rail-probe-and-p1e-forceaccts.md`、
  现成探针 `scripts/rail_liveness_probe.py`。

