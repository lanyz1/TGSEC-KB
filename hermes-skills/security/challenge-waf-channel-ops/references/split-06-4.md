## 4. 求解器资产优先级
挑战页把求解器写进 `localStorage['_waf_<id>']`：值 = **URL 编码**的混淆 IIFE + 尾部 `||<时间戳>`。`decodeURIComponent(v.split('||')[0])` 即得可执行 JS，在真浏览器（或 Node+jsdom 垫片）里 `eval` 复用其铸造逻辑 —— 比从外链那个 ~174KB 混淆脚本手抠算法**短一个量级**。
- ★ **只为「过闸取数」别碰求解器**：铸票 + HTTP 回放（§1 首行）已够；逆求解器只在「必须机外零浏览器跑通整链」时才值得投轮次。
- ★★ **POST 铸票 = 票据通道的天花板（已实测，别再重试）**：票**只能由导航铸，而导航恒 GET** ⇒ 发不出 POST 的票。三路封死：GET 票发 POST ⇒ 挑战页；`Fetch.continueRequest` 把导航 method 改成 POST ⇒ **Chrome 直接拒绝改导航方法**；真表单 POST（导航型）⇒ final URL 被反爬接成 `?alichlgref=` 降级，且 **WAF 重放会把请求体复位成原始表单值**（改写后的体到不了应用，见 `references/pass-channel-recipes.md` §2.6）。⇒ **需要 POST 时不要再写第 N 个导航/表单/方法改写变体**：走「跨源 XHR + 白名单 Origin」（§1 首行，实测可 POST），或该实例的页内 XHR 豁免。

