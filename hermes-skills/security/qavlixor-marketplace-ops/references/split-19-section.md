## 验证流程(改样式后必做)
1. `npx tsc --noEmit` → EXIT 0。
2. browser_console 探针复测。**探针表达式必须写单行紧凑 IIFE** — 多行/带注释会报 `SyntaxError: Unexpected end of input`。现成探针见 `templates/buyer-color-probe.js`(扫饱和橙红绿残留,过滤近黑/近白/灰/合法徽章色,只抓真残留)。
3. **探针返回空/NF 的排查**：① 页面可能已跳走（browser_navigate 后立刻探针最稳，重导航一次再探）；② 选择器要按页面真实类名（快照里的 button 文本可能带空格，`textContent.trim()` 精确匹配）；③ 复杂正则/引号嵌套会触发命令解析拦截，改用 write_file 写 python 脚本 + terminal 执行，别硬塞进命令行。
4. `/pay/[intentNo]` 收银台**原标注"仅源码核对,禁实际渲染"——2026-08-05 已实测渲染成功并修残留(commit 46497a6),C7 现在可正常打开验证**(用户主动要求"打开一个我看看"后实测)。该页是真实下单链路的正常落点,不是禁区;用户要看就走真实下单流程打开。真实下单链路见下方 C7 记录。
5. **React 合成事件坑(2026-08-06 S15 实测)**:JS `dispatchEvent(new MouseEvent('click'))` 对 React `onClick` 处理函数**不触发**(React 只认浏览器真实事件)——点 AppleSelect 菜单项等自定义组件选项时,要么用 `browser_click`(真实点击路径,先 browser_snapshot 拿 ref),要么用 `mousedown+mouseup+click` 三连 dispatch 模拟。反之,`input` 的 `value` 修改(填表单)需要 React setter 才能触发 onChange:`Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set.call(el, v)` + `dispatchEvent(new Event('input',{bubbles:true}))`。

