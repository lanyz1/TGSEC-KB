# 2026-08-10 模板弹窗翻译修复（#123-126）— data-i18n 与 React 渲染竞争的完整坑

场景：运费模板"编辑/复制"弹窗切语言后仍显示中文。层层排查出 **3 个独立根因**，均为可复用模式。

## 根因 1：data-i18n 元素被 React 重渲染覆盖回中文

**现象**：弹窗内 label（data-i18n 键）切语言时 LanguageSync 已替换成目标语言，但弹窗的"输入即翻"（切语言触发 setNameI18n → 整窗重渲染）把已替换文本覆盖回 JSX 原值（中文）。

**为什么观察者没兜住**：MutationObserver 的 characterData 分支只监听金额文本（moneyTextSources/hasMoneyToken），data-i18n 元素的文本变化不触发 → React 覆盖后永不再替换。

**修复**（components/LanguageSync.tsx observer 内）：
```ts
if (mutation.type === "characterData") {
  const target = mutation.target;
  if (!(target instanceof Text) || !target.parentElement?.closest(".buyer-portal, .seller-portal, .admin-portal")) return false;
  if (moneyTextSources.has(target) || hasMoneyToken(target.nodeValue ?? "")) return true;
  // 关键：data-i18n 元素文本变化（React 覆盖回中文）→ 再次触发应用
  return Boolean(target.parentElement?.closest("[data-i18n], [data-i18n-placeholder], [data-i18n-title], [data-i18n-aria-label]"));
}
```
**无循环**：applyLanguage 替换后值相同（`element.textContent !== value` 判断）不再触发 characterData。

## 根因 2：form-translate API 传数组 → 返回索引键 0/1（真凶）

**现象**：输入框值（模板名/适用范围）翻译后永不显示。服务器实测：POST `{fields: ["包邮","通用"]}` 返回 `translations` 键为 `0,1`。

**根因**：`fields` 参数类型是 `Record<string, string>`，前端传数组 → `Object.entries(["包邮","通用"])` 得到 `[["0","包邮"],["1","通用"]]` → translateToAllLanguages 返回键=输入 key（"0"/"1"）→ 前端按源文本 `nameI18n["包邮"]` 查找永远 miss。

**修复**：前端必须传"键=文本"对象：
```ts
fetch("/api/i18n/form-translate", { method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ fields: Object.fromEntries(keys.map((k) => [k, k])) }) })
```
⚠️ 检查过 **SellerAccountSettings.tsx 也有同款 bug**（fields: keys 数组）——搜 `form-translate` 全站确认调用方式统一。

## 根因 3：输入即翻时序（先切语言再打开弹窗 → form 为空）

**现象**：语言事件触发时弹窗未开（form.name=""）→ applyNameTranslation 空转；打开弹窗预填后无事件再触发 → 输入框值不跟随。

**修复**：useEffect 依赖 form 值（预填/变化自动补译）：
```ts
useEffect(() => {
  ...
  if (formRef.current.name || formRef.current.scope) applyNameTranslation(nameLang); // 依赖变化时补译
  const handler = ...;
  window.addEventListener("qavlixor-language-change", handler);
  return () => window.removeEventListener("qavlixor-language-change", handler);
}, [form.name, form.scope]); // ← 关键：依赖 form 值（nameI18n 更新不触发——form 不变，无循环）
```

## 根因 4（同轮）：AppleSelect label 翻译与"点不动"两全

上轮为修"点不动"（#104 fiber 断链）把 label 改成原文渲染 → 丢翻译。恢复 `t()` 组件内翻译 + **保留 `key={active?.value}` 重建节点** + data-no-translate。三个要素缺一不可：
- `key={active?.value}`：值变化强制 React 重建 span（绕开 LanguageSync textContent 替换导致的 fiber 断链）
- `data-no-translate`：LanguageSync 不碰 label
- `t()`：组件内查动态词典（语言事件驱动），词典 miss 显示原文

## 顺带：词典预置（切语言秒翻清单）

发货设置弹窗 3 下拉 label 词：默认仓（有）/今天 18:00 前（补）/手动记录（补）/24 小时内/48 小时内/3 天内（补）。固定选项词一次性 GLM 翻译入库（uiTranslation.upsert，scope='dynamic'），避免补译通道 10-15s 延迟。

## 验证方法

- 服务器直接 POST form-translate（传对象）→ 确认返回键=源文本、ar 值正确（如 包邮→شحن مجاني）
- 浏览器：切 AR → 打开编辑弹窗 → label 与输入框值都跟随
- 检查全站同款 `fields: keys` 数组调用（grep form-translate）
