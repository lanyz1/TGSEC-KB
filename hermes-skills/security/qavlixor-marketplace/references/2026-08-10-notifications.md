# 通知中心功能扩展（#127，2026-08-10）

卖家端通知中心新增：多选 + 删除全部 + 服务端分页。完整模式（后续同类列表页可直接复用）。

## 改动文件

1. **`app/api/seller/notifications/delete/route.ts`（新建）**——删除 API
   - POST `{ ids: string[] }` 删除选中；`{ all: true }` 删除当前卖家全部
   - 校验：`currentEmail()` 未登录 401；`deleteMany` 带 `recipientEmail`（只能删自己的）
   - 返回 `{ ok, deleted }`

2. **`app/seller/notifications/page.tsx`**——服务端分页
   - `searchParams.page`，每页 10 条（同 `/seller/transfer` 余额划转模式）
   - 查询 `take: 500` 全量 → 内存过滤分类 → `slice` 分页（通知量小，无需 DB offset 分页）
   - `page/totalPages/totalCount/tab` 组装成 `pagination` prop 传给组件
   - **翻页链接保留 tab**：`/seller/notifications?tab=order&page=2`（all 时无 tab）

3. **`components/seller/SellerNotificationList.tsx`**——组件
   - 多选：`selected: Set<string>` state；每行复选框（`stopPropagation` 防触发 Link 跳转/已读）
   - 批量条：`selected.size > 0` 时显示（已选 N 条 / 删除选中 / 取消选择）
   - 全选：底部"全选"复选框（当前页 `pageIds.every` 判断）
   - 删除：`router.refresh()` 刷新（列表在服务端）
   - 分页栏：`pagination ? 显示 : null`（**pagination 可选 prop**——admin 端共用组件不传，兼容）

## 关键坑

- **组件被 admin/notifications/page.tsx 共用**：`pagination` 必须可选，否则 admin 页 TS2741
- **data-i18n 键缺失会显示空白**（`getTranslation` 返回 undefined 时 `element.textContent !== value` 仍赋值）：新按钮文案要么先加键要么**裸中文兜底**（不要写不存在的键）
- **"删除全部"用 `window.confirm`**（浏览器原生弹窗，不进翻译体系——可接受）
- 分页文案"1 / N 页 · 共 X 条"：混合文本走裸中文兜底拆翻（"条"首次补译 10-15s）

## 复用模式

列表页加"多选/批量操作/分页"三步走：
1. 服务端：searchParams.page + PAGE_SIZE + count（参考 `/seller/transfer/page.tsx` 与通知页）
2. API：POST 批量删除/操作，必须带 `recipientEmail`/归属校验
3. 组件：selected Set + 批量条 + 全选 + 分页栏（pagination 可选兼容多端共用）
