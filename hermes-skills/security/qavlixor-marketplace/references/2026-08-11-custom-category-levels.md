# 类目自定义扩展到二三级（2026-08-11）

## 背景
发品表单类目级联（一级/二级/三级/四级 AppleSelect）原本**只有四级有「➕ 其他」**（customMode）
→ 用户要求二三级也能自定义新增（走审批）。

## 改造点（components/SellerProductForm.tsx + PATCH API）

### 1. state 扩展
```ts
const [customMode, setCustomMode] = useState(false);  // 任一级选「➕ 其他」时进入输入
const [customLevel, setCustomLevel] = useState(0);    // 2/3/4 = 该级自定义（0=无）
```

### 2. extraCats 按父级分级（已审核通过的自定义类目）
```ts
// /api/seller/categories 已通用：返回所有 active 自定义类目 + parentSlug
const extraSecond = extraCats.filter(i => i.parentSlug === selectedRoot.slug);
const extraThird  = extraCats.filter(i => i.parentSlug === selectedSecond.slug);
const extraFourth = extraCats.filter(i => i.parentSlug === selectedThird.slug); // 原四级逻辑
```
二/三/四级 options 各并 extra + `{ value: "__custom__", label: "➕ 其他" }`。

### 3. 选择函数分支（selectSecond/selectThird 对齐 selectFourth）
```ts
if (slug === "__custom__") { setCustomLevel(2); setCustomMode(true); return; }
// 非 custom：先查 extraCats（选到已审核自定义类目 setCategory(extra.name)），再查静态树
```

### 4. 提交 payload（关键：完整路径 + 父级按层级）
```ts
// customPath = [root, second, third].slice(0, customLevel-1).concat(customCat) join(" / ")
const finalCategory = customMode && customCat.trim() && customPath ? customPath : category;
const customParentSlug = customLevel === 2 ? selectedRoot.slug
  : customLevel === 3 ? selectedSecond.slug : selectedThird.slug;
// payload: { category: finalCategory, customCategory: { name: customCat, parentSlug: customParentSlug } }
```
- 后端 ensureCategory 已支持任意层级（parentSlug 挂靠；普通店 pending 审批、直营店 autoActive 免审）
- 三级自定义示例：`电脑办公 / 3D打印设备`（二级自定义时无三级/四级参与）

### 5. PATCH API 补 customCategory（原来只有 POST 有）
- `app/api/seller/products/[id]/route.ts`：解析 customCategory{name,parentSlug} →
  `category: customCategoryName || normalizeCategoryName(...)` +
  `syncProductToPrisma(nextProduct, nextOperation, scope.storeId, customCategoryParent)`
- 不补的话编辑已上架的自定义类目商品会回退到静态类目。

## 验证
发品 → 二级/三级选「➕ 其他」→ 输入类目名 → 保存 → 类目显示完整路径；
管理端审核通过后全站卖家在该层级下拉直接可选（不必再手输）。

## 坑
- customPath/extra 计算放渲染区（400+ 行），提交 handler 闭包引用——render 后执行无 TDZ 问题。
- 已审核自定义类目选中时 setCategory(extra.name)（slug 唯一，ensureCategory update 不丢父级），
  提交不传 customCategory 也能正确挂载。
- 一级不提供自定义（14 个一级类目是平台底盘，档位/保证金按一级算，自定义一级会破坏 tier 映射）。
