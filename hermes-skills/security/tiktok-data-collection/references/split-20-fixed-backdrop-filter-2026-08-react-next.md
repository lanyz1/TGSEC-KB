## ★前端弹窗 fixed 定位被 backdrop-filter 劫持(2026-08 实测,通用 React/Next 坑)
- **症状**:弹窗(overlay + fixed inset-0)打开后\"卡在页面内容流里\"——不浮层、不居中、遮罩只盖一小块、关不掉的样子(用户原话\"提现框卡进去了\")。实测 overlay rect = 父卡片尺寸(如 943×198)而非视口(1249×1277)
- **根因**:CSS 规范——**祖先元素有 `backdrop-filter`(或 filter/transform/perspective/contain)时,该祖先成为后代 fixed/absolute 元素的 containing block**。本项目 `.tf-glass` 类自带 `backdrop-filter: blur(8px)`,弹窗恰好在 tf-glass 卡片(钱包页 header)内部渲染 → fixed 以卡片为基准
- **判别**(CDP):`[...document.querySelectorAll('*')].filter(e => getComputedStyle(e).position==='fixed')` 逐个看 `getBoundingClientRect()`——rect ≠ 视口尺寸 = containing block 被劫持;再沿 parentElement 链找 `getComputedStyle(ancestor).backdropFilter !== 'none'`
- **修复**:React **`createPortal(<弹窗/>, document.body)`** 渲染到 body 下,彻底脱离卡片链。改完验证:overlay rect 恢复全屏 + `document.querySelector('.tf-glass.max-w-md').getBoundingClientRect()` 居中(centeredX/centeredY 偏差 <5px)
- **检查清单**:页面内所有条件渲染弹窗(bind-dialog / withdraw-dialog / 任何 modal)若有 fixed overlay 且可能挂在带 backdrop-filter 的卡片下,**一律 Portal**——同类隐患一次修完,别等用户挨个报
- 部署时注意:该修复改的是 .tsx 渲染结构,typecheck + 本地 CDP 验证后走常规部署即可

