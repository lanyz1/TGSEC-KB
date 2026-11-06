## 支付启用链路(USDT TRC20 主通道,2026-08 验证)
- .env 配 `USDT_TRC20_ADDRESS=<T开头34位地址>` + 可选 `TRON_API_KEY`(不配走公共节点) → 充值订单 HTTP 200
- 返回 `mode:"onchain"` + `expectedAmount` 含**校验尾数**(如 100.9272)→ 精确金额自动匹配到账(60 秒轮询 `USDT_SCAN_SECONDS`),用户无需提交凭证
- 未配任何网关时充值 503 `payment_not_configured`(前端显示禁用态)——这是防白嫖设计,不是 bug
- **未开通通道的前端提示(2026-08)**:`GET /api/wallet/methods` 返回 `{methods:{PAYPAL:false,USDT:true,VISA:false}}`(gateway.paymentMethodsStatus,凭证配齐自动变 true 无需改代码)→ 前端点击不可用通道按钮时提示而非等充值才报错;**用户文案偏好:简短中性,不要推销/引导式**——"该通道正在开通中,请先使用 USDT 充值"被否,最终定稿 **"该通道暂无可支付方式"**(en: "No payment method available for this channel yet")。提示用页面内联错误条,不置灰不加角标(用户明确不要)
  - **★点击必须保留视觉反馈**:不可用通道被点后**蓝框/选中态必须跟随过去**(用户\"蓝色的框不跟随,一直定死\"反馈)——选中 + 同时弹提示,而不是拦截选中只弹提示。充值按钮再拦一道(selected 不可用通道点\"立即充值\"同样提示,不发请求)
  - **★错误提示要渲染在所有 step**:错误提示条若只写在 step=pay 视图,form 页点击会\"没反应\"(状态设置了但无渲染位置)。任何表单页的点击反馈错误必须在该视图内联渲染(按钮下方)
- **★支付信息结构化卡片(2026-08 用户\"优化一下样式\")**:USDT 链上转账的 payInfo 一长串文字(地址+金额+说明混排)用户难看清——后端 `ChargeResult` 加 `payDetail?: {address, amount, currency, network}`(usdtGateway 返回;recharge route 透传 `payDetail ?? null`),前端 mode==='onchain' && payDetail 时渲染两卡片:① 地址卡(label+等宽 font-mono 地址+**复制按钮**,复制后变\"已复制\"2s,navigator.clipboard);② 金额卡(text-2xl 大字+右角\"金额含校验尾数/自动匹配到账\"小字);非 onchain/无 payDetail 走原 payInfo 纯文本兜底

