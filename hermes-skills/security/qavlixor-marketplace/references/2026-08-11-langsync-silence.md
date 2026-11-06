# 三端切页卡顿：LanguageSync 自循环 + 静默期修复（2026-08-11）

## 症状
买/卖/管理端（三端共用 LanguageSync）点击页内按钮切换页面时明显卡顿。

## 根因（调试路径）
1. 全局 `MutationObserver.observe(document.body, { subtree, childList, characterData, attributes })`（LanguageSync.tsx ~823 行）
2. 切页 = 整个页面 DOM 替换 → 大量 mutations → `scheduleApply()`（rAF 合并一次）→ `applyLanguage()`
3. `applyLanguage` 非默认语言分支做 **5 次全树遍历**：data-i18n 替换 / placeholder / aria-label / title / applyDynamicElements / applyConsoleAutoLanguage / applyBuyerCurrency / `applyBareChinese`（TreeWalker 全文本节点 + 词典查询 + `reportTranslationMiss` 网络上报）
4. **自循环**：写入 `textContent` → 触发 characterData mutations → observer 回调 `shouldApply` 检查（data-i18n 元素为 true）→ 再 scheduleApply → 再全树遍历 → 再写……2-3 轮叠加
5. 每轮还带词典查询 + 未命中上报（网络），页面大时每轮几十 ms

## 修复（2026-08-11，模块级变量，不破坏翻译功能）
```ts
// 模块级
let applyingSilence = false;
let applyingSilenceTimer = 0;

function applyLanguage(language: string) {
  applyingSilence = true;
  window.clearTimeout(applyingSilenceTimer);
  applyingSilenceTimer = window.setTimeout(() => { applyingSilence = false; }, 300);
  // ...原有逻辑
}

// observer 回调第一行
const observer = new MutationObserver((mutations) => {
  if (applyingSilence) return;   // 静默期内不重新调度，切断自循环
  ...
});
```
效果：切页只跑 1 轮翻译扫描（该扫的照扫，翻译功能不受影响）。

## 同类警示
- 任何"Observer 监听 DOM + 回调写 DOM"的组合都要防自循环（写入时置静默 flag / 或写前比较值相同则跳过——后者防不住 observer 触发本身，必须用静默期）
- LanguageSync 是全局组件：性能问题三端同时出现，排查先看全局组件再猜页面

## 相关历史
- 已修：通知铃 AudioContext 手势预热（`pointerdown/keydown` 一次性监听预热 ctx + resume，否则 Chrome 自动播放策略静音）+ 打开面板已读清零时同步 `prevCountRef.current = 0`（否则新通知比较失真漏响）
- 轮询 30s（60s 改的，响应更及时）；`!document.hidden` 才轮询/响铃
