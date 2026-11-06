## Batch & export module standard (user-mandated, applies to EVERY page)
User rule, hard requirement: all batch operations and export dialogs across every page must follow the 商品管理页 (product-list) pattern. **NEVER stub a modal-grade action with a toast** — user explicitly caught this ("批量发货怎么没有下载模版", "批量导出也没有导出弹窗", "批量取消也没有风险提示", "不要偷懒") and made it an execution rule.
- **Batch upload / batch ship**: 3-step modal — ① 下载模板 (Excel 模板 + 示例数据 buttons) ② 上传文件 (drag-drop `.upload` area, format/size hint) ③ 校验结果 (success/warning/fail pills + line-level error details in red box) → confirm button
- **Batch export**: export-setup modal — 格式 (Excel .xlsx / CSV radio) + 范围 (当前筛选结果 vs 全部, with counts) + 字段勾选卡 (`.fld-grid` of checkbox chips, 7–8 fields) → 导出 (async-task toast: "任务已提交,完成后可在消息中心下载")
- **Destructive batch ops** (批量取消/批量删除/升级仲裁/批量退款): risk-confirmation modal with `.risk-box` (red-tinted panel listing consequences: auto-refund, cancellation-rate impact, lock-during-arbitration, audit log) + required reason dropdown where relevant + danger confirm button
- Reuse one `batchbar` component + one export-modal shape everywhere; only field lists differ per domain
- Every page's batch/export live under the same markup: `batchbar` (已选 N 项 + sep + actions + 取消), `modal-export-*`, `fld-grid` fields

