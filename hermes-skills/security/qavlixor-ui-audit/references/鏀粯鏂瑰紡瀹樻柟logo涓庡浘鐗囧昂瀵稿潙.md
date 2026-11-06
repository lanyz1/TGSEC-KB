# 支付方式官方 logo 与图片尺寸坑(2026-08-13)

## 需求背景
用户要求充值/提现支付方式图标用"真实品牌官方 logo 图"(明确不要手绘 SVG 拼品牌色,也不要"高度 auto"显示)。范围:买家端账户中心充值/提现弹窗 + 卖家端资金中心充值/提现表单——`BuyerBalancePanel` / `SellerChargePanel` / `SellerWithdrawRequestForm` 共用 `components/PaymentLogos.tsx` + `public/payment-logos/`。

## logo 下载源(大厂 CDN 挡 curl)
- paypalobjects.com / usa.visa.com / mastercard.com / gstatic.com 等大厂 CDN **挡无浏览器 UA 的 curl**(403 / AccessDenied / 返回 HTML 错误页且文件非空)
- 可用源:① 品牌官方开放 CDN(developer.apple.com 的 applepay.svg 可下)② **Wikimedia Commons `Special:FilePath` 按文件标题直接取文件,对 curl 友好**:`https://commons.wikimedia.org/wiki/Special:FilePath/PayPal.svg`、`Visa_Inc._logo_(2021%E2%80%93present).svg` 等
- 下载后必须验证有效 SVG:`grep -q "<svg"` 通过才收(HTML 错误页也是非空文件,只查字节数会误收)

## 图片尺寸三坑(本 case 三轮返工,用户三次反馈)
1. **img 引用无内在尺寸的 SVG(只有 viewBox 无 width/height,如 cryptologos 的 usdt.svg)→ style 用 `height:auto` 时浏览器渲染 0×0**(getBoundingClientRect 全 0,complete=true 已加载)——**必须给固定高度**:`{height: size, maxWidth, width: "auto", objectFit: "contain"}`。首版 v2 固定 height 正常 → v3 改 height:auto 变 0×0(USDT + Visa 一起中招)→ 用户要求回 v2 效果。
2. **固定尺寸方盒 + overflow:hidden 会裁切横向 logo**:图标盒 `width:38px` 固定时,PayPal(76×48≈1.58:1)26px 高≈41px 宽、Wise(4:1)26px 高≈107px 宽 → 全被 overflow 裁掉一部分 → 盒改 `min-width:38px;max-width:118px` + 移除 overflow:hidden(`.pm-logo2` 卖家端样式)。
3. **objectFit contain + 固定 height + maxWidth**:超宽 logo 的元素盒被 maxWidth 压窄但高度固定,内容 contain 居中完整显示——**验证用 `img.complete` + `naturalWidth>0` 判断加载,别用 rect 猜显示**(rect 返回元素盒 34×26,实际图片 34×8)。

## 验证要点
- 无头检查:充值/提现弹窗里 `img[src*='payment-logos']` 的 complete=true + naturalWidth>0
- 卖家端默认英文界面(按钮是 "Recharge" 不是 "充值");买家端弹窗需先点开按钮再查
- 卡组(Visa/MC/Amex 三连排)缩小横排(高 14px 左右)放图标盒,别让总宽超盒

## 用户偏好(三次迭代确认,勿回退)
- 不想要手绘 SVG(simple-icons path 拼品牌色)
- 不想要高度 auto(0×0)→ 固定高度显示效果
- 其余 logo(Wise/卡组/ApplePay/GooglePay)确认后"别动"——改 USDT/PayPal 时不要顺手动其他的
