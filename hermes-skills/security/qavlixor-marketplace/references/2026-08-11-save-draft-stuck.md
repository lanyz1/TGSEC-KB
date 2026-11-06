# 2026-08-11 保存草稿"点击无反应"修复（#181）

## 症状
卖家端发布商品最后一步点"保存草稿"（或提交审核）无任何反应。

## 排查过程
- 浏览器实测完整流程（登录→发布→填标题品牌→走完 4 步→保存草稿）：保存本身正常（落库+跳转商品列表+品牌字段也存上）——主链路没坏。
- 真实用户"无反应"两个根因：
  1. **fetch 无超时无 catch**：网络异常/请求挂起时 `setSaving(true)` 永不复位 → 按钮 `disabled={saving || !title}` 永久禁用 → 点击无反应（最符合症状）。
  2. **校验失败提示在侧栏"完成度"区**：原 `notice` 只渲染在 aside-card，表单校验不通过（SKU 编码/价格缺项、参数名格式）时红字在页面右侧，按钮位置看不到 → 用户以为没反应。

## 修复（components/SellerProductForm.tsx）
1. submit 的 fetch 加超时 + catch，saving 永不卡死：
```ts
const response = await fetch(url, { ..., body: JSON.stringify(payload), signal: AbortSignal.timeout(30000) }).catch(() => null);
if (!response) { setSaving(false); setNotice("保存失败，请稍后重试。"); return; }
```
2. 底部按钮容器改 `flexDirection: "column"`，按钮行上方加红色 notice 就近提示（侧栏 notice 保留，双处显示）：
```jsx
<div style={{ display: "flex", flexDirection: "column", gap: 8, padding: "16px 20px", borderTop: "1px solid var(--border)" }}>
  {notice ? <div className="hint" style={{ color: "#d70015", fontWeight: 600, margin: 0 }}>{notice}</div> : null}
  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
    ...按钮...
  </div>
</div>
```

## 踩坑
- 给按钮行包新 div 时 JSX 闭合数错 → TSC 报 `Expected corresponding JSX closing tag for 'form'`；修复后再多一个 `</div>` 也要删（原结构一个容器 div 变成 column+row 两个，旧闭合保留了一个多余的）。
- 排查顺序：①按钮 disabled 是否卡 true（saving 状态、fetch 有无 catch）②按钮上方有没有红字 notice（校验拦截）。

## 通用规则
- 所有表单提交 fetch 必须带 `AbortSignal.timeout(30s)` + `.catch(() => null)`，`setSaving(false)` 覆盖所有退出路径。
- 操作按钮的失败提示就近显示（按钮行上方），不要只放在页面角落。

## 附：清理测试商品数据（生产 DB）
- 直接 DELETE Product 会撞外键（ProductVariant/ProductImage/ProductOperationMetric 引用）→ 先删子表再删主表：
  `productImage.deleteMany → productVariant.deleteMany → productOperationMetric.deleteMany → product.delete`
- 服务器上跑 prisma 脚本用 sftp 写 `_q.mjs` + `node _q.mjs`（动态 import Prisma），避免 shell 转义中文/引号问题；schema 变更后若报 client 字段错误先 `prisma generate`。
