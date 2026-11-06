## Product-list table patterns (verified on 商品管理页)
- **Row sorting**: `<th data-sort="price" onclick="sortBy('price',this)">`; rows carry numeric `data-price/data-stock/data-sales` + ISO `data-updated`; `sortBy()` reorders DOM rows, toggles `sort-asc/sort-desc` classes (▲▼ via CSS `::after`). **PITFALL: `parseFloat()` on a date string (`"2026-07-31 09:12"`) silently parses to `2026` (year), so all rows compare equal and sorting appears dead.** Gate on pure-numeric regex: `/^-?\d+(\.\d+)?$/.test(av) && /^-?\d+(\.\d+)?$/.test(bv)` → numeric compare, else `localeCompare` (ISO dates sort correctly as strings).
- **Row ⋯ menu**: `.op-menu > .op-btn("⋯") + .op-drop` absolute dropdown; `toggleMenu(btn,e)` stopPropagation + close others; one document-level click handler closes all. Keep 1-2 primary actions visible as links (下架/编辑), push 预览/复制商品/删除 into the menu.
- **Stock warning synced to stepper**: `.stk-warn` line under `.qty`; 0 → red 数字 + "缺货", <10 → orange 数字 + "仅剩 N 件"; `qty()` rewrites number color AND warn line on every +/- click (set in initial HTML AND in the JS path).
- **Batch bar**: appears on row check — price/stock inputs + black `.b-act` apply buttons, 批量上架/批量下架/批量删除 + 取消; neutral `#FAFAFC` bg, never the accent color.
- **Rejected/已驳回 status**: dedicated filter tab + row-level red reason line under the title ("驳回:标题含违禁词…") — mirrors TikTok Shop/Temu; never hide rejection reasons behind the edit page.
- **Entry-point parity**: page-head buttons = 导出 CSV / 批量上传(Excel)/ 发布新品; 复制商品 lives in the row menu.

