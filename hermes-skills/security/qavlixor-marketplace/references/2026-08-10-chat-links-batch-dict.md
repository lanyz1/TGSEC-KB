# 2026-08-10 会话 #153-160：消息商品卡片链接 / data-i18n 键缺语言区 / 批量词典预置 / 侧栏重构

## 1. 卖家端消息商品卡片链接 404（ChatWindow 角色分流）

**症状**：卖家端"买家消息"列表页 + 单独聊天界面，点商品卡片直接 404。

**根因**：`components/chat/ChatWindow.tsx` 商品卡片链接写死 `/products/${payload.productId}`（买家端商品页）。卖家端点击时：商品已下架/删除 → 买家端页 404。

**修复**：
```tsx
<Link href={role === "seller" ? `/seller/products/${payload.productId}` : `/products/${payload.productId}`} ...>
```
**坑**：商品卡片在独立组件 `MessageCard({message, onPreview})` 里——不在 ChatWindow 组件作用域，`role` 不可见。必须给 MessageCard 加 `role: ChatRole` prop，并在两处调用点 `<MessageCard ... role={role} />` 传入（ChatWindow 88 行有 role prop，但 MessageCard 33 行没有）。TS 报 `Cannot find name 'role'` 就是这原因。

**通用规则**：卖/买共用组件的链接必须按 role 分流；卖家视角一律跳卖家端页面（编辑页能打开下架/删除商品，买家端页会 404）。

## 2. data-i18n 键缺语言区 → 切语言不翻（availableNote2 案例）

**症状**：`与提现处一致，可直接申请提现`（资金中心）切英文不翻。

**根因**：键 `seller.funds.wallet.availableNote2` 只在 zh 区有值（translations.ts 11200），其他 6 语言区缺失 → `getTranslation(en, key)` 返回 undefined → LanguageSync 不替换 → 永远中文。

**排查模式**：
```bash
grep -c '"seller.funds.wallet.availableNote2"' lib/translations.ts   # <7 就是缺语言区
grep -n '"seller.funds.wallet.availableNote2"' lib/translations.ts    # 看哪些区有
```
**修复**：按语言区"锚点键的值"插键（见 #3），补齐 6 区。注意同区相邻键（availableNote）往往同样缺失，一起查一起补。

## 3. ★插翻译键正确方法（python 按语言区锚点值定位）

**错误做法**：循环 `re.search('"seller.nav.funds": "[^"]*",')` 插 7 次 → **每次都命中同一个锚点**，7 个键全插同一位置 → JSON 重复键（后者覆盖前者，所有语言显示最后一个值）。本会话实测踩过：7 个 settingsDev 键挤在 es 区 196-202 行。

**正确做法**：语言区内的键名相同、**值不同**——用"该语言区该键的**值**"做锚点：
```python
lang_by_value = {"Centro de fondos": "es", "Centre des fonds": "fr", "Central de fundos": "pt",
                 "Центр средств": "ru", "资金中心": "zh-CN", "Funds Center": "en"}
for v, lang in lang_by_value.items():
    m = re.search(re.escape(f'  "seller.nav.funds": "{v}",') + r'\n', src)
    src = src[:m.end()] + f'  "seller.nav.settingsDev": "{vals[lang]}",\n' + src[m.end():]
```
**ar 区注意**：translations.ts 的 `seller.nav.*` 键**只有 6 个语言区**（es/fr/pt/ru/zh/en），ar 区历史缺失整组导航键（ar 界面侧栏本来就是中文/兜底，非本轮引入）。ar 区也没有阿拉伯字符锚点可插——settingsDev 等新键 ar 缺失属历史一致问题，可接受。

## 4. 服务器词典预置脚本（UiTranslation 批量入库）

**正确姿势**（本会话踩坑后定型）：
- 脚本存 `.mjs`，用 **node 直接跑**（tsx 对顶层 await + import 混合可能报 ERR_AMBIGUOUS_MODULE_SYNTAX）
- **@prisma/client 必须动态 import**：`const { PrismaClient } = await import('@prisma/client')`（静态 import 在 node 22 报歧义）
- **模型属性名是 `uiTranslation`**（不是 uITranslation！）——用 `Object.keys(p).filter(k => /translation/i.test(k))` 确认
- **字段是 `source`**（@unique，不是 sourceText）——`findUnique({ where: { source } })`，找不到用 `findFirst` 会报"无此字段"
- i18nJson 7 语言键：en/es/fr/pt/ru/ar/zh-CN

**批量 GLM 翻译**：5 词/批 + `AbortSignal.timeout(60000)` + temperature 0.1；43 词 9 批 ~2.5 分钟。**长任务用 nohup 挂后台**：`nohup node _q.mjs > /tmp/q.log 2>&1 &`，用 `ps aux | grep _q.mjs` 确认启动、`tail /tmp/q.log` 看进度（完成打 `DONE n ok, m fail`）。paramiko exec_command 等 nohup 输出会超时——正常，重连检查即可。

## 5. 卖家端侧栏重构（PortalShell sellerNavGroups）

`components/PortalShell.tsx` 45-49 行数组，改分组结构即可（URL 不变）：
- 店铺运营：工作台-入驻资料-通知中心（账号设置移走）
- 客户服务：只留售后工单+买家消息（反馈移走）
- 资金管理：只留资金中心（余额划转隐藏，页面仍在 /seller/transfer 可直达）
- **新分组"设置与开发"**（key: seller.nav.settingsDev）：账号设置 + 反馈与建议

新分组名必须插翻译键（7 语言，见 #3 方法）。实测验证：`document.querySelectorAll('.console-group')` 逐个读 innerText 对照。

## 6. 语言切换器图标

`components/LanguageSwitcher.tsx` 68 行 `<span className="language-switcher-globe">文</span>` → 改 `🌐`（"文"在英文界面突兀，且会出现在混合扫描结果里）。

## 7. 运费模板"复制"删除

SellerShippingTemplates.tsx：235 行按钮 + 130-133 行 `openCopy` 函数，两处一起删（无其他引用）。操作列剩：编辑 | 设为默认 | 删除。

## 8. 批量词典预置清单（本轮已入库，供核对）

- T0（20 词）：已退款/待接/已选/剩余/待审核/已通过/已禁用/加余额/已缴净额/未缴差额/未完结订单/商家处理中/同意退款/拒绝退款/强制退款/已上架/已下架/已删除/待支付/未付款
- 第二批（43 词）：待揽收/运输中/已签收/已确认到账/已确认收货/待人工打款/待财务确认/拆单/打款/驳回/导出/开启/重试/结算/取消/删除/加载中/已完成/运费/优惠/订单/金额/异常/全部/手续费/已驳回/草稿/确认取消订单/应付总额/应付金额/商品金额/申请金额/预计打款/单据金额/冻结余额/真实订单/审核清单/当前关联工单/直营店清单/生成校验订单/处理提现/商家已退款/平台强制退款
- 单轮散词：退款原因/同样/处理记录/问题描述/证据材料/同意退款/已介入处理/余额划转保证金/占用可提现/申请退还后释放/保证金/已缴足应缴额/已转回余额/正常/已同意/退还
