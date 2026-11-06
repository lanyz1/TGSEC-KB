# 段间状态传递模型（代码形状 + 判定算法）

## 一个函数拆完长什么样

原：
```python
    def write_gaps(self):
        <一大段顺序代码，>50 行>
```

拆后（类内方法示例；类外普通函数把 `self.` 去掉、形参照传）：
```python
    def write_gaps_p1(self):                       # 段：缩进必须与原方法一致
        <原正文第 1 块，逐行搬运>
        return locals()

    def write_gaps_p2(self, gaps):                  # 形参 = 本段需要的前序状态
        <原正文第 2 块>
        return locals()

    def write_gaps(self):                           # 替身：函数名/签名/装饰器位置不变
        """（原函数体按顶层语句边界切为 2 段；段间状态经 __S__ 显式传）"""
        __S__ = {}
        __S__.update(self.write_gaps_p1())
        if '__ret__' in __S__:
            return __S__.pop('__ret__')
        __S__.update(self.write_gaps_p2(gaps=__S__.get('gaps')))
        if '__ret__' in __S__:
            return __S__.pop('__ret__')
```

约定：
- 写回一律 `__S__.update(<段>(…))`；读取一律 `__S__.get('name')`（**不要** `__S__['name']`）。
- 形参一律**惰性**传：`x=__S__.get('x', x)`（`self`/`cls` 直传）。**不要**写死 `x=x`：段内若对这个参数名重绑（`cls_dir = os.path.join(pool, cls_dir)`、`path = f(path)` 之类），重绑值不会回流，后段仍读到原参数值 ⇒ 静默算错，症状常常出现在**另一棵树**的自测桩里。
- 方法：`self.<段>(…)`，形参表不重复塞 `self`。

## 返回值贯通

段内原文：
```python
        if not files:
            return None
        ...
        return d
```
改为：
```python
        if not files:
            __ret__ = None
            return locals()
        ...
        __ret__ = d
        return locals()
```
（缩进取该行自身的缩进；只动本段作用域内的 return；跨多行 ⇒ 拒绝拆。）
`finally` 里另有一个 return 的情形也自然正确：先 `__ret__ = A` 再被 `finally` 里改写成 B 并 `return locals()`。

## `_piece_locals(text)`：段自身作用域的函数级局部名

1. 解析 `ast.parse("if 1:\n" + text)` —— 段正文本身就是一个合法 suite，加个 `if` 头就不用先去掉公共缩进；此时 text 第 k 行 ↔ AST 第 k+1 行。
2. 递归遍历，**不进入** `FunctionDef / AsyncFunctionDef / ClassDef / Lambda / 各种推导式` 的函数体；但顶层遇到的 `def/class` 的**名字**要计入（它绑在本段作用域）。
3. 计入：`Name(ctx=Store/Del)`、`arg`、`Import/ImportFrom` 的 `asname` 或首段包名、`ExceptHandler.name`。
4. 遇到 `global/nonlocal` 列出的名字 ⇒ 从集合里**去掉**。

要点：`if/for/with/try/except` 块内的赋值**是**函数级局部名 —— 漏了它，段就会去读同名模块全局。

## 调用点要传哪些名字

```
need = (段正文里出现过的标识符 ∩ 此前可绑定集合) − 本函数形参
此前可绑定集合 = 形参 ∪ 前序各段的 _piece_locals
```

- **不要把 `need` 并回「此前可绑定集合」**：那会把「全局名」变成幻影依赖，后段 `__S__.get` 拿到 `None` 或直接 `KeyError`。
- 段正文里出现的标识符可用正则粗提（`[A-Za-z_]\w*`）再与集合求交；宁可少传（走全局）也不要凭空多传。

## 长度核对（别自己造新违规）

```
段产出行数 = 1（段头 def 行） + 切片跨度 + 1（return locals()） + 签名换行数
```
⇒ 段跨度上限应比「函数上限」留 3–4 行余量，不要刚好等于函数上限。
单条语句跨度本身就超过段上限时：**拒绝拆**，不要让它独占一段。

## 批量驱动验收判据（每条）

拆分成功 ∧ `py_compile` 通过 ∧ 目标棘轮条消失 ∧ 无新增超限 ∧ **该树自测桩 rc=0 且输出含「通过」**；任一不过 ⇒ 还原 pristine、把候选另存 `rejected__<rel>.cand`。

- 按路径前缀选自测桩（例如 `master/`→master 桩、`bot/`→bot 桩、`collector/`→采集桩）。
- 驱动本身要能承受单条失败：备份用**首次接触即固定**的 pristine 语义，避免中途状态被当成还原点。
- 失败候选务必落盘，验尸靠它，不靠重跑复现。
