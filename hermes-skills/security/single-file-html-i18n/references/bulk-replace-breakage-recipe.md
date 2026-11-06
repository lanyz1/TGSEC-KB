# Bulk-replace breakage recipe (2026-08, Qavlixor 全站中→英)

真实案例:单文件 2,600 行原型(内联 CSS+JS)全站英文化,1,366 去重中文串 / 2,373 处。
3 轮映射表替换后,CJK 残留 0,但 JS/CSS 被严重破坏,出现"按钮失灵、曲线图消失、hash 路由不切换"。

## 症状 → 根因
- 症状:导航点击无反应、`#/funds` 显示 Dashboard、曲线图空、按钮"点了没反应"
- 根因:script 初始化时 `document.querySelectorAll('. view')` 抛
  `SyntaxError: '. view' is not a valid selector` → 初始化中断 → 后续全部不执行
  (事件绑定/曲线图调用/hashchange 监听)。函数声明已提升所以不报"未定义",
  但函数内部同样抛错 → 表现为"点了没反应"。
- 次级坑:手动调用 `drawChart()` 报 `Cannot access 'sales30' before initialization`(TDZ)
  —— 因为 script 中途抛错,`const sales30` 那行从未执行。不要被 TDZ 误导,先修中断点。

## 破坏的精确形态
- JS 成员访问:`document. getElementById` / `s. classList. toggle`(点后空格,955 处)
- JS 选择器字符串:`'. view'` / `'. modal-mask'` / `'. nav-item'`(点后空格)
- CSS 选择器:`. card{` / `.st. green` / `body. auth-mode`(点后空格);
  修复时误合并成 `.tbl.ops`(后代)→ 需按白名单拆回 `.tbl .ops`
- HTML 文本区**没被破坏**(英文句点+空格、金额 `8,916.35` 完好)——修复时别全局扫,只动 script/CSS 块

## 关键修复步骤(顺序)
```python
# 1. 只修 script 块
i = html.find('<script>') + len('<script>'); j = html.rfind('</script>')
js = html[i:j].replace('. ', '.')   # 点后空格全还原
html = html[:i] + js + html[j:]

# 2. CSS 选择器:点后空格还原(删除 `\. ` 的点后空格)
css = re.sub(r'\. ([a-zA-Z][\w-]*)', r'.\1', css)

# 3. 后代合并拆分(.a.b → .a .b),同元素多类白名单保持:
# .btn.primary/.st.green/.tg.on/.pm-item2.on/.msg.me/.step.on/.nav-item.active
# /tl-item.done/.pay-opt.on/.net-opt.on/.ch-opt.on/.sf-step.cur/.pm-logo.* 等
# 特例拆后代:.pm-item.on .ok / .tl-item.done .dot / .field.has-err .err-msg
#          / .sf-step.cur .n / .tabs button.on .cnt / .op-menu.open .op-drop

# 4. 验证
node --check extracted.js    # 语法;运行时错(无效选择器)node 查不出,必须浏览器实测
```

## 检测正则(替换后必跑)
```python
js_broken = re.findall(r'[a-zA-Z0-9_$]\. [a-zA-Z_$]', js)          # 点后空格成员访问
css_merged = re.findall(r'\.[a-z][\w-]*(?:\.[a-z][\w-]*)+', css)    # 合并选择器
glued = re.findall(r"'[^']{5,70}'", js)                              # 字符串粘连(筛 [a-z]{2}[A-Z][a-z]{2,})
cjk_left = re.findall(r'[\u3000-\u303f\uff00-\uffef\u4e00-\u9fff\u2014\u2026]', html)
```

## 粘连清理样例(先看上下文再翻)
`charactersCountcharacters`→`characters` / `ordersHistoryOrder`→`orders · Order History`
/ `Allcharacterssection`→`All Fields` / `2026year7month31day`→`Jul 31, 2026`
/ `hoursinShip`→`h to ship` / `transferredRefund`→`refunded to original method`
/ `PaySuccess`→`Payment Successful` / `BulkCancel`→`Bulk Cancel`
/ `SelecteduseThisAddress`→`Address selected`

## 验证清单(浏览器)
1. `show('funds')` → view-funds active
2. `drawChart()` → svg 有 path/line(注意选择器写 `#chart path`,不是 `#chart svg path`)
3. 点按钮 → 弹窗 `.show`
4. `window.onerror` 钩子 → reload 后 `__log` 空(此前 navigate 报的 exception 是历史残留)
5. file:// 缓存:`location.href='file:///...?_='+Date.now()+'#/route'` 强刷,否则永远看到旧版
