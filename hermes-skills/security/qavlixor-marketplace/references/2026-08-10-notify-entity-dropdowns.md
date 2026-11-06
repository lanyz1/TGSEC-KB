# 2026-08-10 下午会话：#116-122（通知偏好/主体变更/下拉体检/AppleSelect 最终形态）

## ★#116 AppleSelect 最终形态（翻译与点击跟随两全）

**演进史**（踩坑完整路径）：
1. 初版：label/选项纯文本 → LanguageSync 裸中文兜底 textContent 替换 → **React fiber 文本节点被销毁** → 点击选项后 React 更新写到脱离 DOM 的旧节点 → **label 永远显示替换残留值（"看起来点不动"）**
2. 中间态：label 改原文 + `data-no-translate` → 点击跟随了但**翻译丢了**（切语言 label 不跟随——用户又报）
3. **最终态（三件套共存）**：
   - `t()` 组件内翻译（`translateDynamicValue(lang, text, "operation")`——语言事件 `qavlixor-language-change` 驱动 state）
   - `key={active?.value}` —— 值变化强制 React **重建 span 节点**（绕开 fiber 断链）
   - `data-no-translate` —— LanguageSync 不碰（防替换）
4. 选项按钮 span 同样 `data-no-translate` + `t(item.label)`；onChange 传**原文 value**（提交数据不受翻译影响）

**关键教训**：LanguageSync 的 `textContent` 替换对任何 **React 受控文本节点**都可能断链——受控组件内部文本要么加 key 重建、要么 data-no-translate + 组件内翻译，**不要裸文本交给兜底**。

## #117 通知偏好接入（"待接"→完整链路）

- 存储：`User.notifyPrefsJson`（`{order, aftersale, fund}`——system 锁定不可关）
- API：`/api/seller/notify-prefs` GET/PUT（未登录 401）
- 发送过滤：`lib/notification-service.ts` 的 `notify()` 里 `isNotifyAllowed(recipientEmail, role, templateKey)`——templateKey 归类（order_*/shipment_*/payment_*→order；after_sale_*→aftersale；deposit_*→fund；未归类/change_request_result→永远发）；关闭分组**直接不产生记录**（返回 null）
- 前端：SellerAccountSettings 通知偏好卡片——开关 state 化 + saveNotifyPrefs 调 PUT + "待接"标签删除 + opacity 恢复

## #118 店铺主体变更接入（"提交变更（待接）"→完整审核链路）

- 提交 API：`/api/seller/change-requests` 支持 `requestType="entity"`——newValue=JSON 字符串（entityType/country/licenseNumber/address/representative/contactPhone）；校验：JSON 可解析 + entityType 字符串或数组 + currentValue 对比（"内容未变"拦截）+ 待审核去重 + 长度≤1000
- 管理端审核：`app/api/admin/change-reviews/[id]/route.ts` 三分支（nickname/storeName/entity）——entity 通过时解析 JSON 更新 SellerAccount 6 字段（businessLicenseNumber 有 unique 约束，冲突会报错）
- 管理端列表：AdminChangeReviews TYPE_LABEL 加 entity + `entitySummary()` 把 JSON 摘要为"类型/执照号/法人"（防表格显示原始 JSON）
- 前端：主体卡片"提交变更"按钮 → Modal 弹窗 6 字段（预填当前值、必填校验）→ 提交后 pendingEntity 显示"变更审核中"禁用按钮
- 翻译键：`seller.account.entityModalTitle` 等 7 语言（补键后务必 check-translations）

## #119 删卖家昵称（界面精简类改动的正确姿势）

- UI 层：SellerAccountSettings "卖家个人信息"区 displayName 输入框 + label 删除（data-i18n 键保留无害）
- 逻辑层：saveProfile 的 nickname 变更队列删除（changeQueue 只留 storeName）、pendingNickname 删除、提交后回滚逻辑只留 storeName
- **数据层保留**：displayName 数据仍被聊天体系使用（message-repository 买家真实名/peerNameFor 🎮 兜底）——**删 UI 字段绝不连数据机制一起删**
- 输入即翻 collect 数组同步只留 storeName

## #120 下拉体检 + 固定词预置词典模式

- 方法论：全站 grep `<select`（原生）+ `AppleSelect`（自定义）→ 逐处读 options 来源（data-i18n/data-i18n-dynamic/裸中文/英文/动态）→ 分类（✅键/⚠️补译/❌未预置）→ 输出 HTML 报告（D:\跨境商城\会话产物\）
- **固定词预置模式**（让下拉选项秒翻）：批量 `translateToAllLanguages`（**每批 2-4 个词**——6 个以上会 Node 超时崩溃）→ upsert UiTranslation（scope=dynamic, note 标注来源）→ 客户端切语言立即命中
- 本次预置：售后（补发商品/物流未收到）、通用（请选择/本月/差额转回/全额转回）、发货（发货仓/默认发货仓/默认发货时限/默认物流公司）、闭店 4 原因、运费模板名 3 个（含金额的混合文本 GLM 也能正确翻）、发货时限（今天 18:00 前/24 小时内/48 小时内/3 天内）
- 仓库名（深圳仓/香港仓/广州仓）是卖家动态数据——补译通道自动处理，无需预置

## #121 卖家侧栏店铺名跟随语言

- 根因：PortalShell profile 卡 `data-i18n={identityTitleKey}` 且 `identityTitleKey = portal === "seller" ? undefined : ...` → 卖家端无键永不翻译
- 修复：卖家端 strong 换 `<DynamicText as="strong" value={liveIdentity.title} kind="store-name" />`（词典查 store-name 类，账号设置页"输入即翻"翻过的店名立即显示；未翻过走补译）

## #122 硬编码短命提示（"通知偏好已保存"不翻译的根因）

- 根因：这类 setMessage 提示 **3 秒自动消失**，裸中文兜底补译要 10-15 秒回填——提示早没了，永远看不到译文
- 修复：**直接加翻译键**（6 键 × 7 语言 GLM 生成）+ `getTranslation(currentClientLanguage(), key)` 替换——切语言即时生效
- 键：prefsSaved/prefsSaveFailed/entitySubmitted/entityRequired/entitySubmitFailed/closeSubmitted
- 验证：服务器 `getTranslation(lang, key)` 直测各语言值（比浏览器快且稳）

## 通用教训

1. **翻译键插值**：GLM 批量翻译分批（2-4 词/批），value 必须传中文原文（传 "x" 会静默失败）
2. **AppleSelect 交互验证**：is-active 是 value 真相（label 可能被外部替换）——点击后查 is-active 而非 label
3. **提示语/状态文本**：能加键就加键，不要依赖兜底补译（时序不可控）
4. **"待接"占位**（通知偏好/主体变更）接入时：存储→API→前端→（如涉及）发送/审核链路，四层一起打通再交付
