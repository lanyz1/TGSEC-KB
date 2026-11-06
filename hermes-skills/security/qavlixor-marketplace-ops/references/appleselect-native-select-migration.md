# AppleSelect 原生 select 迁移(2026-08-05 首轮:9 文件 21 个,tsc EXIT 0)

## 组件 API(components/seller/AppleSelect.tsx)
- **受控组件**:`{ value: string; onChange: (v: string) => void; options: {value,label}[]; ariaLabel?; style? }`。style 透传到根 div。
- 视觉:白底触发按钮 + 白面板圆角阴影 + 选中项黑底圆角白行;触发按钮与菜单项的 label span 自带 `data-i18n-raw`(词翻译豁免)。
- **无 disabled prop**;`fieldset disabled` 对组件不生效(OnboardingWizard locked 态下拉仍可点开,提交按钮/后端校验不受影响,只读态不彻底属已知限制)。

## 已完成清单(9 文件 21 个)
| 文件 | 数量 | 关键点 |
|---|---|---|
| components/SellerProductForm.tsx | 6 | 四级类目级联 ×4(aria-label→ariaLabel;第四级含 extraFourth 已审核自定义类目 + `__custom__` 触发 customMode)+ 发货时限 + 运费模板(无 value option→label=value;width 220/340 透传) |
| components/seller/SellerWithdrawRequestForm.tsx | 3 | **全非受控** → 组件顶加 `useState("USD")`/`useState("Chase Bank (JPMorgan)")`/`useState("USD")`(bankCurrency/bankName/wiseCurrency,默认=原首个 option);maxWidth 200 透传 |
| components/seller/onboarding/OnboardingWizard.tsx | 3 | 注册国家/签发国家(value="" 占位"请选择"保留、data-i18n 丢、width 240;options 含条件追加已存值)+ 偏好语言(languages.map code/label) |
| components/seller/AfterSaleActionForm.tsx | 2 | 退款/拒绝原因,直传 setter,width 220 |
| components/seller/BuyerAfterSaleRequestForm.tsx | 2 | 售后类型 + 问题商品(option 的 data-i18n-dynamic/data-i18n-map 随 option 移除;`itemTitleI18n` prop 类型保留、调用方不变、未用不报错) |
| components/seller/SellerFundsCenter.tsx | 2 | 结算月份(非受控→`useState("本月")`,width 180)+ 退还类型(受控,onChange 包 `as "difference" \| "full"`) |
| components/seller/AdminLogisticsUpdateForm.tsx | 1 | 物流状态,onChange 包 `as LogisticsEvent["status"]` |
| components/seller/AdminWithdrawalForm.tsx | 1 | 处理状态,onChange 包 `as Withdrawal["status"]` |
| components/seller/SellerAccountSettings.tsx | 1 | 闭店原因,直传 setter |

## 已知仍含原生 select 的文件(下轮目标)
- components/seller/SellerFulfillmentForm.tsx:127(carrierPreset,该文件已 import AppleSelect 并用于发货仓/发货时限)/153(deliveryWindow)。
- 其余全库扫:`grep -rn "<select" app/ components/ --include="*.tsx"`(注意:不含受 AppleSelect 影响的 9 文件)。

## 坑
- **patch 工具对 CRLF 文件 diff 显示整文件重写**(见 SKILL.md 环境坑:patch 会把 LF→CRLF,git diff --stat 被 autocrlf 归一化隐藏)。改完 `git diff --stat` 核对改动行数,异常先查行尾。
- **search_files 工具对中文路径 IO error**:用 terminal + grep(中文路径加引号)。
- **tsconfig 仅 strict**(无 noUnusedLocals/noUnusedParameters):替换后遗留未用 prop/变量不报错,别为此加 `void` 或删 prop 类型。
- **无 value 的 option(纯文本 `<option>文案</option>`)在 AppleSelect 里 value=label**——`["部分退款","全额退款",...].map(label => ({value: label, label}))` 是标准写法。
