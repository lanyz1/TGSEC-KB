# 买家申请售后页 i18n 修复 + 下拉选项语言跟随模式（2026-08-10 #134-135）

## 场景
买家申请售后页 `/account/orders/[id]/aftersale`（BuyerAfterSaleRequestForm + page）切语言问题：
- 切英文：问题商品下拉里的中文商品标题不翻、textarea placeholder 不翻
- 切中文：label/按钮/eyebrow 显示英文或需二次刷新（裸中文兜底补译 10-15s 慢）

## 根因
1. **裸中文兜底（applyBareChinese）排除 select/option/textarea/placeholder**（排除列表含 input/textarea/select）——下拉选项和 placeholder 永远不翻，必须走正规键或组件内翻译
2. 表单 label 全是裸中文无 data-i18n → 靠兜底补译（慢、需刷新），且"二次刷新恢复"是因为 SSR 中文原值兜底
3. 问题商品下拉选项直接用中文商品标题，没用传入的 itemTitleI18n（商品 7 语言译文）

## 修复模式（可复用）

### ① 下拉选项随语言切换（组件内模式）
```tsx
const [lang, setLang] = useState(currentClientLanguage());
useEffect(() => {
  const handler = (event: Event) => setLang(normalizeLanguage(String((event as CustomEvent).detail)));
  window.addEventListener("qavlixor-language-change", handler);
  return () => window.removeEventListener("qavlixor-language-change", handler);
}, []);
const options = items.map((item) => ({
  value: `${item.title} · ${item.sku}`,           // 提交值保持原文完整
  label: truncate(itemTitleI18n?.[item.title]?.[lang] ?? item.title),  // 显示用译文
}));
```
注意：`setLang` 必须用 `normalizeLanguage()` 转类型（直接 `String(...)` 会 TS2345——LanguageCode 联合类型不接 string）。

### ② placeholder 键化
`<textarea ... data-i18n-placeholder="buyer.afterSale.descriptionPlaceholder" />` + 键 6 语言。

### ③ 新翻译键插入流程（6 语言）
1. 服务器 GLM 翻译：`translateToAllLanguages({ [zh源]: zh源 })` 逐键调用
   - **断点续传**：结果写临时 JSON（`writeFileSync('/tmp/keys.json')`），每键成功即写盘；重跑时 `existsSync` 读回跳过已完成
   - **超时重试**：单键失败重试 3 次（间隔 3s）——GLM 单条 ~11.7s，45s TIMEOUT 常超时
2. 本地插入 translations.ts：**6 个 const 语言对象（zh/en/es/fr/pt/ru）各插一份**（zh 插中文原值，其余插译文）——不要只插 zh（getTranslation 各区独立，fallback zh 会让其他语言显示中文）
   - 定位：正则 `const <name>: TranslationMap = \{` → 配平 `{}` 找结束 → 在 `};` 前插
   - 验证：`grep -c '"key"' lib/translations.ts` 应为 6
3. 组件/页面加 `data-i18n` / `data-i18n-placeholder`
4. tsc + 部署 + 服务器 getTranslation 抽查 en/es/ru

## 同会话相关
- **买家登录页找回密码**：LoginSubmitForm 加 forgotPassword（复用 /api/auth/forgot-password + /reset-password，与卖家端同链路）；`slog-forgot` 样式在 `app/seller-apple.css` 的 `.slog .slog-forgot`（必须确认页面在 .slog 容器内才生效）
- **form-translate 传对象**（#135）：`fields` 传数组会被 `Object.entries` 转成索引键 0/1 → 返回 `{0:…}` 前端按源文本查找永远 miss；必须传 `{ [文本]: 文本 }` 对象。账号设置页/运费模板页两处同修
- **售后工单 "Requested" 残留**：存量 reason 串含英文片段（历史数据），词典预置单词秒翻（客户端词典后台自动拉取，无需部署）

## 验证注意
- 浏览器实测订单/售后页常遇 404：**订单归属店铺/买家 ≠ 登录测试账号 → 权限隔离 404 属正常**；改用服务器 getTranslation 抽查 + 代码逻辑确认 + 用户实测
- 订单详情页 2608101012180453460 属于 Tourwin Store（非 qa-seller-1 的 EchoSail）——跨店测试数据要分清归属
