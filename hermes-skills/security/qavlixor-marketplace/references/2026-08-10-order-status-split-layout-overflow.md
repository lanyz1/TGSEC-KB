# 2026-08-10 会话 #161-3：订单状态筛选拆分 / 切语言布局溢出扫描 / patch 锚点错位

## 1. 订单管理状态筛选拆分（"运输中+已收货合并应分开"）

`app/seller/orders/page.tsx`：
- 拆分前：`OrderFilter = "all"|"pending"|"shipping"|"afterSales"|"done"`，shipping 匹配 `运输中||已签收`，done 匹配 `已完成||已关闭`
- 拆分后：新增 `"received"|"closed"`；shipping 只匹配 `运输中`，received 匹配 `已签收`，done 只匹配 `已完成`，closed 匹配 `已关闭`；tab 列表 7 个（全部/待发货/运输中/已收货/退款售后/已完成/已关闭）
- `displayStatusOf` 本身早就分开（运输中→"待收货"、已签收→"已收货"）——用户报的只是**筛选合并**，先查清再改
- tab 渲染用 `data-i18n={seller.orders.filter.${tab.key}}` —— 新增/改名键必须同步

**翻译键"改值+新增键"的 python 脚本模式**（与纯插键不同——这次是既有键值要改 + 新增键）：
```python
fixes = {  # lang: (旧shipping值, 新shipping值, received值, 旧done值, 新done值, closed值)
  "es": ("En tránsito + Recibido", "En tránsito", "Recibido", "Completado + Cerrado", "Completado", "Cerrado"),
  ...
}
for lang, (ship_old, ship_new, recv, done_old, done_new, closed) in fixes.items():
    pat = re.compile(r'  "seller\.orders\.filter\.shipping": "' + re.escape(ship_old) + r'",\n')
    m = pat.search(src)
    src = src[:m.start()] + f'  "seller.orders.filter.shipping": "{ship_new}",\n  "seller.orders.filter.received": "{recv}",\n' + src[m.end():]
    # done 同理
```
用**旧值**做锚点（键名相同、值不同——值才是语言区的唯一标识），一处正则只命中一个区，6 区循环安全。验证：`grep -c '"...received"' lib/translations.ts` = 6。

## 2. 切语言布局溢出扫描方法论（"切换语言后整个框超出背景"）

**检测脚本**（浏览器 console，切最长文本语言后跑）：
```js
new Promise(r => setTimeout(() => { localStorage.setItem('globalmart-language','ar'); window.dispatchEvent(new CustomEvent('qavlixor-language-change',{detail:'ar'})); r('switched'); }, 800))
  .then(() => new Promise(r => setTimeout(() => {
    const doc = document.documentElement;
    const overflow = [...document.querySelectorAll('body *')].filter(el => el.scrollWidth > el.clientWidth + 8 && el.scrollWidth > 300)
      .slice(0, 12).map(el => ({cls: String(el.className||'').slice(0,35), sw: el.scrollWidth, cw: el.clientWidth, text: (el.textContent||'').trim().slice(0,25)}));
    r({docSW: doc.scrollWidth, docCW: doc.clientWidth, overflow});
  }, 16000)));
```
- **先看 docSW vs docCW**（页面级横向滚动=背景撑破）；`docSW === docCW` 时只有元素级溢出（裁剪/视觉问题），也要修
- 语言用 **ar 阿语**（文本最长最易溢出）；等 16s 让兜底翻译跑完
- 实测 7 页（主页/订单/资金/详情/消息/购物车/登录）只有 3 处元素级溢出：
  1. **商品标题溢出卡片** `.market-product-title`（两处 CSS 定义 1412 + 7656！只改一处另一处覆盖）→ `-webkit-line-clamp: 2` + overflow hidden（注意两处定义都改）
  2. **支付渠道条** `.ftb-badges` `flex-wrap: nowrap` → `wrap`（PayPal/VISA/AMEX 徽章 1069px 挤 400px 容器）
  3. **会话列表预览** `.lst`（ChatList 用了 className="lst" 但 **CSS 里没有 .lst 定义**→长文本不截断）→ 加 `.buyer-portal .lst, .seller-portal .lst { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }`
- 其他 nowrap 大多配 ellipsis（安全）；`grep -n "white-space: nowrap" app/globals.css` 后逐个核对是否配 overflow hidden

## 3. patch 锚点错位教训（本会话 3 次踩坑）

- **SellerOrderExportButton.tsx**：old_string 只含 `import { Modal }...` + 函数签名，patch 把新 import 插进了 18 行处的 `FIELDS` 数组中间（匹配到文件中另一个相似片段）→ 文件结构乱 → **read_file 确认后 write_file 整文件重写**（比继续 patch 快）
- **globals.css 两连错**：①`.buyer-portal .market-product-title` 的 patch 匹配后残留旧属性（old_string 只到 `min-height: 42px;` 没带完整块）→ 新块插入后旧属性悬空 ②修复时**猜测**下一段类名 `.buyer-portal .market-product-price` 不存在 → 又造出空选择器 → 再删
- **教训**：①old_string 必须带**完整块边界**（属性全部 + 闭合 `}`）②修复 CSS 时不要猜相邻选择器名，先 `sed -n` / read_file 看实际内容 ③大文件多次 patch 失败后直接 write_file 重写整个文件
- **TSX 批量小替换**（两处 `<MessageCard ... role={role} />`）用 `sed -i 's/.../.../g'` 一次搞定 + `grep -c` 验证次数

## 4. 售后批量按钮"无法点击"（用户问为什么有）
- `SellerAfterSalesList` 批量同意退款/升级平台 enabled 条件 = 仅 status="商家处理中" 且未 locked（`selectedActionable` 过滤）——勾选已退款/已关闭工单按钮禁用是**状态限制**不是 bug
- 用户质疑后建议删除"批量升级平台"（单条处理面板已有升级选项），未最终拍板——答复用户时给选项让用户选，不擅自删
