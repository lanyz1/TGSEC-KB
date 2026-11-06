# Amazon UK 商品页采集（browser 工具）

2026-08 实测。Amazon 反爬严格但 browser 无头栈可过；@url 上下文提取会失败（no content extracted），必须 browser_navigate 进页面。

## 步骤
1. `browser_navigate` 首次可能超时（Operation timed out）——别急，直接 `browser_snapshot` 看页面实际已加载。
2. 首次会弹 cookie 对话框，点 Decline（`@e79` 附近，ref 每次变，按快照找）。
3. 用 `browser_console` 单行表达式提取（**多行箭头函数会报 Unexpected end of input**）。

## 选择器（2026-08 实测有效）
```js
标题:        document.querySelector('#productTitle')?.textContent.trim()
价格:        document.querySelector('#corePrice_feature_div .a-offscreen')?.textContent  // 不是 .priceToPay！
评分:        document.querySelector('#acrPopover')?.getAttribute('title')   // "4.4 out of 5 stars"
评价数:      document.querySelector('#acrCustomerReviewText')?.textContent // "(118)"
品牌店:      document.querySelector('#bylineInfo')?.textContent.trim()     // "Visit the BAMBULAB Store"
五点卖点:    Array.from(document.querySelectorAll('#feature-bullets li')).map(e=>e.textContent.trim())
图片:        Array.from(document.querySelectorAll('img[src*="images-amazon"]'))
             .map(i => i.src.replace(/\._[^.]*_\./,'.'))   // 去缩略图标记拿原图
             .filter((v,i,a)=>a.indexOf(v)===i).filter(s=>!s.includes('pixel'))
ASIN:        location.pathname.match(/dp\/([A-Z0-9]{10})/)?.[1]
卖家:        '#sellerProfileTriggerId' / '#merchantInfoFeature_feature_div'（"Sold by Bambu Lab United Kingdom"）
```

## 要点
- 图片 URL 必须 strip `._[^.]*_.` 缩略图标记（如 `._AC_UX500_.`）才是原图；下载时 Referer 带 `https://www.amazon.co.uk/`。
- 价格选择器 `.priceToPay .a-offscreen` 在部分页面为空，回退 `#corePrice_feature_div .a-offscreen` 和 `.a-price-whole`。
- 商品信息.txt 结构：前半 Qavlixor 模板 16 列（价格 GBP→USDT 换算），后半 Amazon 原始数据（ASIN/链接/价格/评分/评价数/卖家/配送/五点卖点原文/图片清单）。五点卖点原文可直接当上架素材。
- 2026-08 三个拓竹套装：A1 mini+LED Kit £169（B0GQMJ8QQT）、A1 Combo+LED Kit £345（B0GQMN8VLS）、P1S Combo £499（B0CHDS1DMC），均比官方店贵 £20~30（LED Kit + Amazon 渠道溢价）。
