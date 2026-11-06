## 新坑速查 → 详见 refs/（按日期归档）
/#订单号时间戳根因+生产psql直查+改单号同步纪律→refs 2026-08-13-test-order-time-fix
/批量上传模板16列+恶意xlsm警告→refs 2026-08-11-batch-upload-template
/#169商品审核通知+补键脚本定稿法+.btn样式→refs 2026-08-10-product-review-notify
/#172-192→refs 2026-08-11-pay-deadloop-routesegment
#193-197 flexWrap/余额精度/插键区序/已支付拦截→refs 2026-08-11-tail-fixes
#198onebound铺货→refs onebound-shelf.md
#199删号/密码重置→refs 2026-08-11-account-deletion
#200保证金死锁(草稿计入应缴)→refs 2026-08-11-deposit-deadlock
#201类目二三级→refs 2026-08-11-custom-category-levels
#202上品工具+木马→refs 2026-08-11-auto-shelf-tool|2026-08-11-malware
#203-205客服三波→refs 2026-08-12-support-chat-stock-sku|support-chat-iteration|support-agent-admin
/#206客服角色页UI方案A→refs 2026-08-13-staff-create-roles-ui
/#2026-08-14订单生成真实化+时区三件套+扣库存+通知补发+待结算eta+翻译铁律→refs 2026-08-14-real-order-gen-timezone-stock
#165见refs late-session
#167代充不发通知/通知角色/动态import prisma→refs 2026-08-10-admin-transparency
#166+通知16类型清单见refs 2026-08-10-notification-types(PREF_GROUP分组/触发场景/DB分组查询脚本/给用户做类型一览HTML模板)
①切语言一步到位（SSR 固化→data-i18n/语言监听/LanguageSync refresh 兜底）
②时区偏移（前端传 Unix 毫秒时间戳，禁 toISOString 依赖浏览器时区）
③售后 history actor 是中文标签（判 `=== "买家"` 不是 "buyer"）
④售后证据 CDN 白名单（cdn.qavlixor.com 需放行）
⑤部署包禁止 git 跟踪（自我包含 → tar.gz 解压 EOF）
⑥校验订单定时创建（ScheduledOrderJob/Item + cron 每分钟 + 按 storeId 分组 + CRON_SECRET 内联）
⑦SKU 上限 20 + trim-over-sku 存量收敛（保留订单引用；按钮保留可点+点击提示，禁隐藏入口）
⑧物流 lastEvent 17TRACK JSON 兜底乱码
⑨布局"太靠两侧"= 贴边问题（space-between + padding），不是改居中
⑩translations.ts 插键语言区顺序 zh→en→es→fr→pt→ru→ar，锚点必须用语言特定值（禁裸键名 replace），插前查键号占用、插后验 7 处分布
⑪data-i18n-raw = 跳过翻译（动态中文值禁用它，改 DynamicText；排查页面不翻译先扫它）
⑫按钮/链接漏 data-i18n 标记（同页同类元素一个有标记一个没有 = 漏标典型）
⑬纯文本元素漏交互链接（商品/店铺名没包 Link = 点击无效；数据缺跳转字段如 CartItem.storeSlug）
⑭i18n 数据字段已随查询返回但渲染层漏用（commodityI18n 纯文本 td；查数据源字段→看页面是否消费）
⑮动态统计值"数字+单位"禁止 getTranslation 拼接整段给 DynamicText（查词典失败），数字裸渲染+单位 data-i18n 分离
⑯动态词典源串必须与页面实际渲染值逐字符一致（含 \n/全角标点）——补词典前先生产 JSON.stringify 实际值；解析文本含换行用 `[\s\S]*` 禁 `.*`（rma 时间线二次不翻根因）
⑰搜索匹配池只含中文标题 → 其他语言搜不到；拼入 item.i18n.title 各语言（Object.values 加入 haystack），商品 i18n 全量无需回填

