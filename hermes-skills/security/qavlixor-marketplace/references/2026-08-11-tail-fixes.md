# 2026-08-11 会话尾部修复补充（售后按钮溢出 / 发货模板持久化 / SSH 弹框 / 插键 find 坑 / 精度 / 动态段 500）

## 1. "保存后消失 / 切页丢失" 类 bug 排查顺序（重要）

**先 grep 组件注释里的"待接 / 持久化 / 纯前端 state"标记，再查 API 链路。**

- 本次发货模板（/seller/shipping-settings）"新建后切页消失"的 root cause 就写在组件注释里：
  `// 后端持久化待接: 数据存前端 state, 保存按钮按"待接"处理。`——纯前端 state，保存只改内存，切页/刷新即丢。
- 排查顺序：① 读组件顶部注释与数据初始化（useState 硬编码 = 没接后端的高危信号）② 查有无对应 API ③ 浏览器实测（新建→切页→回来）。
- 修复模式：DB 加 Json 列（`Store.shippingDefaultsJson Json?`，db push 自动迁移）→ 新建 GET/POST API（requireRole seller + resolveSellerStore 收窄归属，sanitize 限长限条数）→ 前端 useEffect 进入时 GET 回填（有数据才覆盖默认），新建/编辑/删除/设默认每次变更立即 POST。
- 注：`prisma.store.findUnique({ where: { name } })` 报 TS2322（name 非唯一字段）→ 用 `findFirst({ where: { name } })`。

## 2. 长语言按钮溢出修复模式（法/西/葡文案撑出卡片）

- 症状：flex 按钮区文案长（如 "Confirmer l'accord de remboursement"），按钮被撑出卡片边界。
- 修复：按钮区容器加 `flexWrap: "wrap"`；按钮加 `style={{ minWidth: 0, whiteSpace: "normal", lineHeight: 1.35 }}`。
- 全站排查面：卖家端所有"确认/保存"双按钮卡片底部（售后处理面板已修，其他页遇到同款直接套）。

## 3. SSH 弹密码框（用户被打扰过）

- **禁止用系统 ssh 命令直连生产服务器**（会弹 GUI 密码框打断用户）。
- 一律 paramiko（execute_code，密码硬编码脚本内），或 deploy.py 自带链路。

## 4. 插翻译键脚本的 find() 坑 + 语言区实际顺序（TS1117 / 全错位）

- 错误写法：`src.find(anchor)` 每次从文件头找，**永远命中第一个语言区**→ 6 个键全插进同区 → TS1117 duplicate。
- 正确写法：`[...re.finditer(r'"seller\.feedback\.submitted":', src)]` 收集全部出现位置，逐个 `line_end` 后插入对应语言的值。
- ★★★ **语言区实际出现顺序 = es → fr → pt → ru → zh-CN → en**（2026-08-11 实测行号：es 198 / fr 2290 / pt 4382 / ru 6475 / zh 11354 / en 12347）。**每次插键前必须先 `grep -n "锚点键" lib/translations.ts` 看实际出现顺序**，按出现顺序一一对应语言值——按想当然的顺序（zh→en→es→fr→pt→ru）插会把 6 个语言值全部错位。
- 错位症状（用户实测报的）：英文界面空提交提示显示**俄语**、中文界面显示**葡语**（"comentário"被动态翻译成"评论内容"）——比没翻译更隐蔽，因为各语言界面都能"显示"只是全错。
- 修正方式：`grep -n` 拿到 6 个键的行号 → python 按行号把每行替换为正确语言值（`lines[idx] = f'"键名": "{值}",'`），不要 re 匹配替换。
- 插错后先 `git checkout lib/translations.ts` 回滚再重插。

## 5. 余额/金额精度（Decimal→Number 浮点尾数）

- 症状：余额显示 196.39999999999998（Decimal(196.4) 直接 Number() 丢精度）。
- 修复三层：① API 层 `Number(Number(x).toFixed(2))`（根因层）② 显示层 `toFixed(2)` 兜底（余额面板/结账通道/错误消息）③ 运算本身（DB Decimal 加减）不受影响，只修转换/显示。
- 排查面：所有 `Number(wallet.availableAmount)` / `Number(row.xxx)` 的转换点。

## 6. Next.js 动态段参数名不一致 → 全站 500（含残留恢复）

- `app/api/orders/[orderNo]/...` 与 `app/api/orders/[id]/...` 并存 → 启动即 `You cannot use different slug names for the same dynamic path ('id' !== 'orderNo')`，**全站 500**。
- 恢复三步：① 本地改名统一参数名 ② **手动删服务器残留旧目录**（deploy.py archive 解压不删多余目录）③ **清服务器 .next 后全量重建**（增量构建缓存残留旧路由，光 restart 不够）。
- 新路由创建前先 `find app -type d -name "*[orderNo]*"` 检查同路径段是否已有别的参数名。

## 8. Server Component 严禁 onClick（买家 /account 全站 500，digest 排查法）

- 症状（用户实测）：买家账户页（/account）打开即"页面加载出错了 1248223131"，清缓存/强刷无效——因为错误发生在**服务器渲染阶段**，与浏览器无关。
- 根因：`components/buyer/BuyerAccountCenter.tsx` **没有 "use client"（Server Component）**，但退出登录 `<a>` 加了 `onClick`（清 localStorage）→ RSC 序列化事件处理器报 `Event handlers cannot be passed to Client Component props`，digest = 用户看到的错误码。
- 排查法：**用户报的错误码就是 Next digest** → `pm2 logs tiktok-marketplace --lines 60 --nostream | grep -B2 -A12 '<digest>'` 直接拿到组件与元素形状（{href, onClick, data-i18n, style, children} 指向具体标签）。
- 铁律：**无 "use client" 的组件文件里禁止任何事件处理器**（onClick/onChange/onSubmit 一律报此错）；事件处理要么放 "use client" 子组件，要么去掉。
- 本例替代方案：登出清 localStorage 标识改由**下次登录时覆盖**（登录成功写新 qx_account + 迁移旧 qx_cart），登出残留无害（游客走 guest key 不串号）——Server 组件做不了的事情不要硬做。

## 9. Excel 交付安全验证（用户"你给我下木马？？？"事件）

- 用户对交付文件的安全性高度敏感（发现"宏代码"立即喊停并要求解释）。**任何 Excel/可执行文件交付前必须自证干净**。
- 事实基础：openpyxl 从零生成的 `.xlsx` **天然不含宏**（xlsx 是无宏格式，宏只能存在 .xlsm/.xls 的 vbaProject.bin 里）。
- 交付前验证命令（必做）：
  ```python
  import zipfile, re
  z = zipfile.ZipFile(path); names = z.namelist()
  bad = [n for n in names if re.search(r"vba|macro|externalLink|activeX", n, re.I)]
  # bad 为空 = 干净；有 vbaProject.bin = 带宏，立即停手查来源
  ```
- 2026-08-11 事件复盘：我 cp 的 .xlsx 到桌面后**同时刻**出现同名 `.xlsm`（含 Synaptics.rar 宏木马下载器：docs.google.com/dropbox 下载 → \System32\Synaptics\Synaptics.exe 释放执行 → 注册表 VBAWarnings=1 关宏警告），我的 .xlsx 消失——**来源不是我的工具链**（openpyxl 写不出宏），疑为并行 AI 工具或机器上已有恶意软件动的手。
- 澄清/处置套路：① 先验证**源文件**（我生成的）干净（zip 结构无宏）② 验证**目标位置**文件（桌面 .xlsm 确实含恶意宏——用户没有冤枉文件）③ 对比时间戳（.xlsm 出现时刻 = 我的复制时刻）④ 删恶意文件 + 重放干净文件 + 建议用户 Defender 全盘扫描/查计划任务启动项。
- 警惕：用户环境有**并行 AI 工具**（用户会引用其回复，如"我去代码库里找真正的模板定义"），该工具可能对用户机器上的文件做过处理——涉及文件被改/消失时把它列为嫌疑。

## 10. 收银台尾部修复（按钮风格 + 已支付拦截）

- 收银台底部按钮统一平台胶囊风格：`返回` = `.button.secondary`（白底灰边），`更换支付方式` = `.button`（黑底白字）。
- 坑：`.payc-foot a { color:#667085; }` 的灰色文字规则特异性高于 `.button`，会压掉黑按钮白字——加 `.payc-foot a.button` 系列规则单独覆盖（次按钮/主按钮分别定义）。
- 已支付订单拦截：收银台"更换支付方式"显示条件 = `view.kind === "order" && view.refs?.[0]?.ref && view.refs.every(ref => ref.status !== "已支付")`（refs[].status 来自订单 paymentStatus，330 行构建）。订单列表"去支付"已按 statusKey==="unpaid" 过滤、后端 createOrderIntent 已对 paid 订单抛"订单已支付或已关闭"——收银台按钮是唯一漏网点。
- 批量商品 Excel 模板（openpyxl 生成，双 sheet：商品数据 16 列 + 填写说明；SKU 明细格式 `规格名|编码|价格|库存;` 分号分隔；必填列红底；示例行浅灰底）——会话产物目录可复用。

## 7. 其他本日速记

- 支付死循环修复模式：收银台"返回"不再跳列表（会与"去支付"互跳死循环），改跳订单详情 + 详情页 `?changePay=1` 显示通道选择（USDT/余额/其他），余额补付走独立 API（原子条件扣减 updateMany + 订单转 awaiting_shipment + syncPaymentForOrder）。
- 购物车账号隔离：localStorage key 按账号分 `qx_cart:{email}`（guest 兜底），登录写 `qx_account` + 旧 key 迁移，登出清除。
- 结算运费：商品自定义运费（shippingNote 正则拆 `自定义运费：首件 X + 续件 Y USDT，满 Z 包邮`）优先于店铺模板；模板取 `isDefault` 优先（此前取第一个启用模板会挤掉按重量默认模板）；计算 = 首件/首重 + 续件/续重 × (数量-1)，满门槛包邮。
- 商品草稿回填：品牌独立存 Product.brand 字段（原来只拼标题拆不回）；运费方式从 shippingNote 正则拆回 shipFeeMode（tpl/custom/free）；存量旧草稿 brand 空时从标题启发式拆前缀。

## 11. 会话尾部补充（订单勾选设计 + 截图贴错页排查）

- **卖家端订单管理勾选（checkbox）只有 `status === "待发货"` 的订单显示**——设计如此（勾选用途=批量导出/取消；**批量发货已删**，见 §12）。用户报"运输中/已收货/已完成/已关闭 tab 里订单选择没有"时**先确认是设计再决定改不改**，不要当 bug 修；用户若想要这些状态也能勾选（如批量导出），问清用途再实现（可选方案：导出按当前 tab 全量，不需要勾选）。
- **用户报 UI 问题时截图可能贴错页**（本次：文字说账号设置页通知按钮白色，贴的图却是订单管理页状态 tab）。排查套路：先 vision_analyze 截图确认红框内容，与文字描述不符时①实测文字所指页面（实测 3 个保存按钮全黑正常）②回复里说明截图与描述的差异，请用户重新截图确认——比直接改代码强。
- 账号设置页通知偏好：保存按钮 `.btn primary` 黑胶囊；开关 `.tg`（关=灰底#E5E5EA深黑圆点/开=绿底深黑圆点，2026-08-11 用户"人眼看不清白圆点"已从白改 #1D1D1F）；实测全正常时先让用户强刷排除旧 CSS 缓存。

## 12. 会话最后三拍（全选文字 / 开关圆点 / 批量发货全删）

- **批量发货全删（用户拍板 2026-08-11）**：删 `app/seller/batch-ship/`、`app/api/seller/batch-ship/`、`lib/batch-ship-service.ts`、`components/seller/SellerBatchShipList.tsx` + 订单管理页页头"批量发货"按钮 + 批量操作栏"批量发货"按钮。**保留**勾选体系与批量导出/批量取消（它们是独立功能，用户没让删）。删完注意：`.next-build` / `.next-dev` 缓存里残留已删路由的 type 引用 → `rm -rf .next-build .next-dev` 再 tsc，否则报 TS2307。翻译键（seller.batchShip.* / seller.nav.batchShip）留着无 UI 引用，无害可不删。
- **表头全选加文字**：`<th style={{width:88, textAlign:"center"}}>` 内 checkbox + `<span data-i18n="seller.orders.selectAll">全选</span>` 并排（inline-flex gap 5 + whiteSpace nowrap）；翻译键 6 语言按 §4 语言区顺序插入。
- **通知开关圆点可读性**：`.sap .tg::after` 圆点 `background:#fff` → `#1D1D1F`（关=灰底黑点、开=绿底黑点，.on::after 同改）。用户原话"人眼看不清楚，把圆换成其他颜色别用白色"——白色圆点在浅灰底上对比度不足。

## 13. 另见（同会话）

- **万邦 onebound 直营店铺货**（用户问"还记得万邦那个自动上货调的 API 吗"）：`lib/importers/onebound.ts`（item_get 适配器）+ `/ops-direct` 私密铺货页 + `scratchpad/fill-aliexpress.mjs`（速卖通主力）→ **refs/2026-08-11-onebound-directstores.md**
