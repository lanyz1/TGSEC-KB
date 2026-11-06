## AppleSelect 下拉替换(原生 select → 苹果风白面板,2026-08-05 首轮 9 文件 21 个)
组件 `components/seller/AppleSelect.tsx`:**受控**下拉(**无 disabled prop**),API `{value, onChange, options, ariaLabel, style}`,options=`{value,label}[]`,style 透传根 div;内部 label span 自带 `data-i18n-raw`(词翻译豁免)。替换规则(下轮直接照做):
1. 受控 select:options 由 JSX option 推导 `{value,label}[]`(无 value 的 option → label=value);onChange 原样传 setter/处理函数。
2. **非受控 select(无 value/onChange 纯展示):组件内加 `useState` 包装**,默认值 = 原首个 option 值(SellerWithdrawRequestForm 3 个、SellerFundsCenter 结算月份均此模式)。
3. option 上的 `data-i18n`/`data-i18n-dynamic`/`data-i18n-map` 一律丢弃,保留中文 label。
4. `className="inp"` 删除(组件自带样式);`style` 原样透传;`aria-label` → `ariaLabel`。
5. onChange 需类型断言的原样包箭头函数:`onChange={(v) => setX(v as LogisticsEvent["status"])}`。
6. ⚠️ 无 disabled prop:`fieldset disabled` 对 AppleSelect 不生效(OnboardingWizard locked 态下拉仍可开,提交逻辑不受影响,属已知限制)。
7. 替换后遗留未用 prop(如 BuyerAfterSaleRequestForm 的 itemTitleI18n)不报错——tsconfig 仅 strict,无 noUnusedLocals。
8. 验证:`grep -rn "<select" <本次文件>` 0 命中 + `npx tsc --noEmit` EXIT 0。
逐文件清单/下轮待改文件见 `references/appleselect-native-select-migration.md`。

