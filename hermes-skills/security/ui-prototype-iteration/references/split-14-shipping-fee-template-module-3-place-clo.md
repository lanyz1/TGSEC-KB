## Shipping-fee template module (3-place closed loop, verified)
Mainstream parity pattern (Shopify template reuse / TikTok Shop product-bound templates / 淘宝 首件+续件+满额包邮):
1. **Sidebar menu** (商品订单 group, box icon) → dedicated management page: template table (名称/计价规则/满额包邮/状态(默认|启用)/使用商品数/操作 编辑·复制·删除), 新建模板 modal (名称 + 计价方式 radio 包邮|按件计费 → 首件/续件/满额 inputs + 设为默认 checkbox), delete risk modal (关联商品自动改用默认模板 warning).
2. **Product publish step 4 运费设置**: three mutually-exclusive radios — 包邮 / 运费模板 (dropdown of store templates) / 自定义运费 (首件+续件+满额) — each reveals its own conditionally-shown block (`tplSelBox` / `feeBox`); hint text switches per mode.
3. **Ship page**: read-only line "运费模板: 包邮模板(订单商品采用包邮,买家免运费)".
4. Cross-links: publish page hint points to the template page ("修改模板后全店生效"); demo data stays consistent across all three places.
5. **New-template modal (upgrade, user: "太简陋了")** must be a full form, not 3 inputs: 模板名称 + **适用地区 chips** (9 region pills 全球/北美/欧洲/东南亚/中东/大洋洲/日韩/南美/非洲, checkbox inside pill, `.chip:has(input:checked)` = black border + tint — no-JS selection styling) + **计价方式 3-way radio** 包邮 / 按件计费 (首件+续件+满额) / **按重量计费** (首重 ≤1kg + 续重每 500g + 满额) + 设为默认 checkbox.
6. **运费试算器 (fee calculator)** inside the new-template modal — mainstream TikTok/Temu touch: two inputs (数量 + 订单金额) → live `<b id="calcResult">` fee; qty mode `first + more×(q-1)`, weight mode treats qty as kg → `first + more×ceil((q-1)×2)` (500g steps), `cap>0 && amt>=cap → 0`. Recalculate on radio switch AND on every input (`oninput`).
7. Region/pricing/fee-calculator names must not collide across the two template modals (publish-page selector uses `tplSelBox`; creation modal uses `tplFeeBox2`/`tplQtyBox`/`tplWtBox` + `tpltype2` names) — or radio groups and boxes will cross-wire.

