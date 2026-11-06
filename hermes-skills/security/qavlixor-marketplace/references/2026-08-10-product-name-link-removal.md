# 商品名跳转删除 + JSX 中文注释 TS 解析坑（#129，2026-08-10）

## 一、卖家端订单管理商品名跳转编辑商品（用户拍板删除）

**需求**：用户明确"点击商品名字会跳转编辑商品，全部删掉，这个功能不好"——订单管理里商品名不再可点击。

**位置（共 2 处，列表 + 详情都要查）**：
1. `components/seller/SellerOrdersTable.tsx`（订单列表）——`<Link href={`/seller/products/${item.productId}`} ...>` 包 DynamicText → 改 `<span>`（保留 maxWidth/ellipsis 截断样式）
2. `app/seller/orders/[id]/page.tsx`（订单详情 93 行）——同款 Link → span

**要点**：
- 改 Link → span 时**闭合标签也要改**（`</Link>` → `</span>`），漏改即 TS 报错
- 保留 `DynamicText`（多语言翻译不能丢）
- 全站排查同类跳转用 `grep -rn "seller/products/${" app/seller/ components/seller/`
- 售后列表/详情无此跳转，不用改

## 二、★JSX 表达式内中文注释引发 TS 连锁解析错误（坑）

**现象**：`{item ? ( {/* 2026-08-10 商品名不再跳转编辑商品（用户拍板删除该功能） */} <span>...</span> ) : (...)}` ——把含**全角括号**的中文注释放进 JSX 表达式后，`npx tsc --noEmit` 报**连锁错乱**错误：
```
SellerOrdersTable.tsx(151,19): error TS2657: JSX expressions must have one parent element.
SellerOrdersTable.tsx(169,35): error TS1005: ')' expected.
SellerOrdersTable.tsx(169,184): error TS1382: Unexpected token. Did you mean `{'>'}` or `&gt;`?
SellerOrdersTable.tsx(171,31): error TS17002: Expected corresponding JSX closing tag for 'div'.
SellerOrdersTable.tsx(337,1): error TS1128: Declaration or statement expected.
```

**关键特征**：报错行号**全部错乱**（151/169/171/174/337 都报，且与实际问题行无关）；git diff 看改动完全正确、cat -A 无隐藏字符——就是注释本身触发解析器进入异常状态。

**修复**：删掉该注释（或改用不含全角标点的英文注释）→ TSC=0。**这是验证过的修复路径**。

**教训（此类"报错行号错乱"的通用排查顺序）**：
1. 先怀疑**最近改动的 JSX 表达式内注释/字符串**（尤其含全角字符的）——直接删掉重试
2. 再查 `</X>` 闭合标签是否配对（Link→span 类替换漏改闭合最常见）
3. git diff + cat -A 确认无隐藏字符/意外替换
4. 最后才考虑行尾（CRLF/LF 混合 git 会警告，但一般不致语法错）

**后续约定**：JSX 表达式内（`{cond ? ( ... ) : ...}` 中间）**不放中文注释**；注释放表达式外或 JSX 元素属性区，或只用纯 ASCII。
