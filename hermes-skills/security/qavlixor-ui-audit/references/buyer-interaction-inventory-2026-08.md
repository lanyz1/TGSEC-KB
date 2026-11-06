# 买家端全部页面交互元素全量清单（2026-08-07 功能层审计）

源码驱动产出（app/ 根路径 + components/buyer + PortalShell + chat/* + 共享组件 + middleware.ts）。页面文案带 data-i18n 键属全局机制，清单不重复标注。

## 全局（layout + PortalShell BuyerPortalShell + middleware）
- 顶部导航链接：账户→/account、订单→/account/orders、消息→/messages（ChatUnreadBadge 未读角标，15s 轮询 /api/chat/unread，未读增加响提示音）、收藏→/favorites、购物车→/cart（CartBadge localStorage 计数角标，>99 显示 99+）、商家入驻→/seller/register
- 顶部搜索表单：q 参数 GET /search?q=…（空关键词=全部商品）
- LanguageSwitcher：7 语言下拉，写 localStorage + 派发 qavlixor-language-change 事件；点外部关闭
- 页脚链接组：About/Contact/Terms/Privacy + Refund Policy/Shipping Policy/Orders/Messages + Merchant Policy/Seller Login/Seller Register；信任徽章条纯展示
- IdentityGuard：bfcache 恢复时登录身份 cookie 变化 → 强制刷新
- middleware：/account、/checkout（**payment-restricted 放行**）、/favorites、/messages 前缀要求 buyer 角色会话（cookie 篡改/过期=未登录），否则 302 → /login?next=<原路径>；/cart、/products 公开；商家/管理员会话不能访问买家端

## 首页 /
- 轮播 BuyerHeroCarousel：3 幻灯片，自动 6s 轮播；左右箭头‹› + 圆点切页；每页主/次按钮各 1 → 类目筛选页
- Tab 商品集（热卖精选/新品上架/为你推荐）：纯前端切换 3 组商品网格
- 促销瓷片 4 块（今日秒杀/新店首发/新人精选专区→/products；办公室升级→类目页）
- 「猜你喜欢」→「全部商品」链接 → /products
- ProductCard（全站复用）：图/标题→/products/[id]；店铺名→/stores/[slug]（无 slug 不渲染链接）；「加入」→ /cart?product=<id>；心形收藏（icon 变体只做添加；401 → 跳 /login?next=当前页）
- 边界：无已上架商品时网格为空（无空态文案）

## 商品列表 /products
- 侧栏「全部类目」→ /products；类目树：中间级=三角箭头展开/收起 + 类目名链接跳 ?category=slug 筛选；叶子=筛选链接；选中路径自动展开高亮
- 价格筛选表单：从/到输入（decimal）+ 确认 → GET /products?category&sort&minPrice&maxPrice；非法数字忽略
- 排序 5 项链接（推荐/销量/价格低→高/评分/新上架）：保留类目+价格参数
- 分页（每页 32）：上一页/下一页（首尾页禁用态 span）+ 页码（含省略号分隔）；保留筛选参数
- 边界：空结果显示「该类目暂无在售商品。」；非法 category=未选中；page 超界收敛

## 商品详情 /products/[id]
- 面包屑：Home + 类目链（可点）→ 商品名
- ProductGallery：主图点击开灯箱（Esc/遮罩/×关闭，锁滚动）；灯箱‹›切图 + 键盘←→；缩略图条点击或 hover 切主图；单图无缩略图/灯箱箭头
- ProductBuyBox：SKU 规格按钮组（按索引选中，各自记忆数量；库存 0 规格标 soldout 可点但购买禁用）；数量步进器 −/+（下限 1，上限=该 SKU 库存，输入框只留数字，失焦/回车夹取，非法回退）；「立即购买」→ /checkout?product&sku&qty（下架/库存0/店主本人禁用，href 变 /products）；「加入购物车」→ localStorage 后跳 /cart；「收藏/已收藏」labeled 变体可切换（401 → 登录页）
- 店铺卡：「进入商家店铺」→ /stores/[id]；「联系商家」→ /messages/new?product=<id>（店主本人隐藏）
- 本店推荐 4 个 + 底部为你推荐商品卡
- 锚点 Tab：商品详情/规格参数 → #pdp-detail / #pdp-spec
- 边界：不存在/下架 → 404

## 购物车 /cart
- ?product&sku&qty 入口：自动加购并 replaceState 清参；qty 夹取 [1,99]；商品下架 → 404
- 全选 checkbox + 每行 checkbox（失效商品禁用）；「清除失效商品」（有失效项才出现，/api/products/validate 标记 已删除/已下架）
- 步进器 −/+ + 数字输入（只留数字 6 位，失焦空值回退，下限 1；无效商品禁用）
- 「删除」；「去结算」（无选中禁用）→ 写选集 → /checkout?cart=1；「继续购物」→ /products
- 汇总：小计/运费恒 0/应付；跨店「将生成 N 个订单」
- 边界：空购物车空态；校验请求失败静默忽略

## 结算 /checkout
- 页头 Continue Shopping → /products；步骤条 4 步展示
- 直访无参：兜底第一个在售商品；无在售 → 「暂无可结算商品」+ 去选商品/返回个人中心；商品不可用 → 「商品不可用」空态；?cart=1 只结算勾选集（无选集=全量）
- 收货表单：收件人/国家下拉(US/CN/GB/AE)/详细地址（必填 3 项）；门牌号/邮编/电话选填；邮箱必填；订单备注 maxLength 500；预填登录邮箱+默认地址
- 支付方式 6 单选（USDT 默认/ PayPal/ Wise/ Card/ Apple Pay/ Google Pay）
- 「Place an order · N USDT」：非 USDT → 跳 payment-restricted?method&back；USDT → POST /api/checkout/orders → 跳收银台 payUrl；校验失败提示；提交中禁用
- 「Cancel」→ router.back()；汇总卡「返回购物车」
- 边界：cart 模式提交时勾选已空 → 提示回购物车；下单成功只移除已购项；跨店自动拆单

## 结算成功 /checkout/success?orders=
- 订单号链接 → /account/orders/[orderNo]；未付显示「去支付」（POST /api/pay/intents 后跳收银台，失败显示错误）；「查看全部订单」→ /account/orders
- 边界：orders 参数空 → 空白卡片

## 支付风控 /checkout/payment-restricted?method&back
- 「返回结账 · 切换支付方式」→ back（仅站内 / 开头且非 //，否则回落 /checkout）；「继续逛逛」→ /products；纯静态提示页，无需登录

## 收银台 /pay/[intentNo]
- 金额（含识别尾数）+ 倒计时每秒刷新 + 收款地址 + 网络 + 本地币折算参考（/api/currency/rates）
- 「复制金额」「复制地址」：剪贴板，成功显示已复制 1.5s
- 5s 轮询支付状态；已确认 → 2.5s 后自动跳 doneUrl（可点「查看结果」）；过期 → 「重新生成支付金额」（POST renew 替换 URL）
- 折叠「已按其他金额转账？填写 TXID 走人工确认」：TXID（≥12 字符校验）+ 钱包选填 + 提交凭证
- 页脚「返回」按 kind 回 /account/orders 或 /seller/funds
- 边界：intentNo 不存在 → 404

## 搜索 /search?q&page
- 类目命中 pill（≤8）→ 类目筛选页；模糊结果每页 32；上一页/下一页 + 当前页/总页数
- 边界：无结果空态「没有找到相关商品」；page 超界收敛

## 店铺页 /stores/[id]
- 非店主：「收藏店铺 ☆/★」StoreFavoriteButton（401/403 → 提示「请先登录买家账号」不跳转）；「联系商家」→ /messages/[slug]（自动建店铺会话）
- 店主：「管理我的店铺」→ /seller；所有人「继续逛商品」→ /products
- 商品网格每页 32 + 上一页/下一页
- 边界：店铺不存在 404；无在售空态；店主隐藏收藏/联系

## 收藏夹 /favorites?tab=products|stores
- Tab 商品/店铺；商品行 → /products/[id]，店铺行 → /stores/[slug]
- 「移除」→ Modal 确认（取消/移除，成功 reload；Esc/遮罩/×关闭）
- 边界：空态「暂无数据」；未登录 middleware 拦截

## 登录 /login
- 邮箱 + 密码（PasswordInput 小眼睛明文切换）；「登录买家中心」→ POST /api/auth/login（body 带 role: buyer），成功跳 ?next= 或服务端 entry；「Sign Up」→ /register

## 注册 /register
- 邮箱 + 邮箱验证码 + 密码（≥8 位提示）+ 昵称（仅买家）
- 「发送验证码」：邮箱空禁用；POST /api/email-verification/send
- 协议勾选（/terms、/privacy 新窗口）；未勾选点注册 → 「请先阅读并勾选同意平台协议。」
- 「创建账号」：未勾选禁用；POST /api/auth/register（含 emailCode）→ /account；「Log in」→ /login

## 买家中心 /account
- 「编辑资料」→ /account/profile；「全部订单」→ /account/orders
- 订单状态 4 宫格（待付款/待发货/待收货/退款售后 → 对应筛选页），数量角标
- 余额卡 BuyerBalancePanel：「充值」→ Modal（金额 type=number min=1，非正数提示；方式下拉 5 项）→ POST /api/buyer/recharge → 跳收银台 payUrl；「提现」→ Modal（金额+方式+收款账户 maxLength 190，空提示；手续费 1.5%/最低 1 USDT）→ POST /api/buyer/withdrawals → 成功显示单号 reload；遮罩/取消关闭（busy 不可关）
- 资金记录（最近 10 条展示）；最近 5 笔订单表 + 「查看」；「为你推荐」商品卡
- 侧栏导航（我的账户/订单/售后/收藏/资料/地址/安全）+「退出登录」→ /api/auth/logout

## 我的订单 /account/orders?status=
- Tab 全部/待付款/待发货/待收货/已完成；商品名 → 商品页；「查看」→ 订单详情；待付款行「去支付」；部分退款显示「已退 X USDT」
- 边界：空态「暂无数据」；非法 status 回落全部

## 订单详情 /account/orders/[id]
- 「返回订单列表」；店铺名 → /stores/[slug]；商品 → /products/[id]；「联系商家」→ /messages/[orderNo]
- 待付款：倒计时「剩余 HH:MM:SS 将自动关闭」（超时提示）+「去支付」+「取消订单」（二次确认：确认取消订单/再想想）
- 待收货：「确认收货」（仅 delivered/receipt_confirmed 可用）
- 售后资格内：「申请售后」→ /aftersale；售后中：「查看售后」→ /account/rma
- 五步进度条；金额/物流/收货/付款信息展示
- 边界：非本人/未登录/不存在 → 404

## 申请售后 /account/orders/[id]/aftersale
- AppleSelect：售后类型（部分退款/全额退款/补发商品/物流未收到）+ 问题商品（订单商品列表）
- 金额 number（默认 min(总额,10)）+ 问题说明 textarea；凭证 1/2/3 上传（FileUploadButton，png/jpeg/webp/pdf）
- 「提交售后申请」：说明空或金额≤0 → 提示；成功跳回订单详情；「返回订单」
- 边界：资格不符 → redirect 订单详情；非本人 404

## 退款售后 /account/rma
- 售后卡：关联订单（Order.id→orderNo 映射，勿直接渲染 id）、商品行、证据图新窗口、处理记录时间线
- 「申请平台介入」（仅已拒绝/超 72h 未处理）：说明选填 + 证据上传 + 确认按钮 → POST /api/aftersales/[id]/escalate
- 「补充证据/说明」（未完结卡）：说明与图片至少一项 → POST /api/aftersales/[id]/evidence
- 边界：空态「暂无数据」

## 收货地址 /account/addresses
- 「设为默认」（非默认行）PATCH；「删除」→ Modal 确认
- 「新增收货地址/收起」（无地址自动展开）；表单：收货人必填 + 电话（区号随国家联动、仅数字 ≤15 位、<4 位提示）+ 国家下拉（其他=手输）+ 省市联动（切国家清省市、切省清市）+ 邮编 + 详细地址（失焦「自动识别」国家省市）+ 设为默认 checkbox
- 「保存地址」：必填缺失提示；成功收起置顶；「自动识别」按钮

## 个人资料 /account/profile
- 「更换头像」→ 隐藏 file（png/jpeg/webp ≤8MB）→ /api/uploads + /api/account/avatar
- 昵称/手机号/默认语言下拉 + 邮箱只读；「保存修改」→ POST /api/account/profile
- 「注销账号」→ 展开面板：密码 + 输入 DELETE + 确认注销 → POST /api/account/deactivate → 跳 redirectTo

## 安全设置 /account/password
- 原/新/确认密码（均小眼睛）；「保存修改」：新≠确认 → 提示；成功清空三框

## 消息 /messages（买家）
- ChatList：搜索框（联系人/主题/最后消息过滤）+ Tab 全部/未读/工单 + 会话列表（未读角标 99+，纠纷/工单标签）
- ChatWindow：消息流（气泡/图片/订单卡/日期分隔/已读未读回执/失败点击重试）；图片点击全屏预览
- ChatComposer：Enter 发送（Shift+Enter 换行，输入法组合不触发）；图片按钮上传（JPG/PNG/WEBP ≤8MB）；买家无常用语
- ChatContextPanel：智能摘要/咨询商品（查看商品）/关联订单（查看订单详情）；买家不可见快捷操作
- 轮询：消息 4s、列表 10s；收到新消息响提示音并标记已读
- 边界：未登录 → /login?next=/messages；无会话/未选中空态

## 消息会话 /messages/[id]
- id 解析顺序：会话 id → 订单号（自动建订单会话）→ 店铺 slug；均失败 404；打开即已读

## 新建会话 /messages/new?product=<id>
- 未登录 → login；无 product → /messages；自动建商品会话（自己店商品/无有效卖家 → 回 /messages 不 404）→ redirect 会话页

## 联系我们 /contact
- 主题下拉 4 项 + 姓名（必填）+ 邮箱（正则校验）+ 参考号选填 + 留言（≥12 字符）+ 蜜罐 Company
- Submit → POST /api/contact，成功清留言；上方政策内容展示

## 政策页 /about /terms /privacy /refund-policy /shipping-policy /merchant-policy
- PolicyPageView 纯静态，无可交互元素

## 全局错误页
- 「刷新页面」reload /「重试」reset + 错误编号

## 内部/隐藏页
- /preview、/preview/checklist：导航索引（纯链接）；/ops-direct：仅 admin（否则 404），直营店管理+一键铺货
