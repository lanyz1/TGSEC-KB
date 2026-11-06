# 苹果风状态卡片 4 宫格（SVG 图标）模式

> 来源：C12 /account 我的账户首页订单状态 4 宫格重新设计（commit c5677ae）
> 用户反馈"▤▣▱▭ 文字符号图标粗糙"→ 换 SVG 线性图标 + 圆形图标容器。

## 结构（app/account/page.tsx 实现参考）

### 1. SVG 图标定义（组件文件顶部，与全站线性图标风格一致）
```tsx
const statusIcons: Record<string, React.ReactNode> = {
  unpaid: (
    <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor"
         strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="4" width="18" height="16" rx="3" />
      <path d="M3 10h18M8 4v6" />
    </svg>
  ),
  unshipped: (/* 包裹 */),
  shipped: (/* 对勾圆环 */),
  rma: (/* 刷新环 */),
};
```

### 2. 卡片 JSX（关键样式内联 + hover 走 CSS 类）
```tsx
<a className="dash-stat" style={{ display:"flex", flexDirection:"column", alignItems:"center",
     gap:8, padding:"16px 8px", borderRadius:14, position:"relative", transition:"background .18s ease" }}>
  <span className="dash-stat-icon" style={{ display:"inline-flex", alignItems:"center", justifyContent:"center",
       width:48, height:48, borderRadius:"50%", background:"#F5F5F7", color:"#1D1D1F" }}>
    {statusIcons[item.statusKey]}
  </span>
  <em style={{ fontSize:13, fontWeight:600, color:"#1D1D1F", fontStyle:"normal" }}>{label}</em>
  {count ? <b style={{ position:"absolute", top:10, right:"calc(25% - 14px)", fontSize:11, fontWeight:600,
       background:"#FF3B30", color:"#fff", borderRadius:999, minWidth:18, height:18, padding:"0 5px",
       display:"inline-flex", alignItems:"center", justifyContent:"center" }}>{count}</b> : null}
</a>
```

### 3. hover CSS（globals.css，buyer-portal 作用域）
```css
.buyer-portal .dash-stat:hover { background: #F5F5F7; }
.buyer-portal .dash-stat:hover .dash-stat-icon { background: #000; color: #fff; }
```

## 要点
- 图标必须 `stroke="currentColor"` → 颜色由容器 color 控制，hover 黑底白图自动生效
- 徽章（待办数）用系统红 `#FF3B30`、999px 胶囊、绝对定位右上
- 文字符号（▤▣▱▭♥★）全站禁用——这是旧式占位图标标志
- 图标容器 48px 圆形浅灰 = 苹果系统设置图标风格
