## 12c. 商品页交互失效根因(Swiper 中断 ready 回调)⭐

症状: 商品页 200、渲染正常(倒计时/販賣量可见), 但点「立即搶購」/任何按钮无反应、不跳下单。curl 检查 HTML/JS 结构、静态资源全 200 都正常——**必须真实浏览器抓 console**(headless Chrome + CDP, 见 `browser-js-debugging` 技能)。

- **根因**: pro_show 的 `$(document).ready(function(){ new Swiper('.main-swiper', {...thumbs: {swiper: '.thumb-swiper'}}); ...; $cnmallOrder.on('click', showCheckout); })` —— Swiper 初始化抛 `TypeError: Cannot read properties of null (reading '$el')` → **整个 ready 回调中断** → 后面所有按钮绑定(showCheckout)从未注册 → 点击无反应
- **Swiper thumbs 时序坑**: thumbs 传**选择器字符串**时, 若缩略轮播未先初始化 → 内部访问 $el 为 null。**必须 thumb 先 `new Swiper('.thumb-swiper', ...)` 得实例, 主轮播 `thumbs: {swiper: thumbSwiper}` 传实例**
- **修复模式**: 轮播(及其他第三方库)初始化整体 try/catch + `document.querySelector` 元素存在性检查, 保证业务绑定代码必定执行
- 附带修复: `<script src="fp.min.js" onload="generateFingerprint()">` 调用了从未定义的函数(实际采集逻辑在后续 async IIFE 自行执行)→ 去掉无效 onload 属性, console 归零
- **CDP 实测确认**: 点击前后对比 `mainContent.hidden` / `checkoutContent` 可见性(页内切换不跳 URL, 别只看 location); ERRORS(0) + DOM 状态变化 = 修复完成
- 这类"页面能渲染但交互死"的问题用 CDP 一次定位(错误+行号+调用栈), 肉眼排查效率低十倍

