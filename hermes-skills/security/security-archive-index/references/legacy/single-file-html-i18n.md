<!-- archived from /root/.hermes/skills/security/single-file-html-i18n/SKILL.md on 2026-10-21 -->

---
name: single-file-html-i18n
description: >-
  测绘引擎·Single-file HTML i18n breaks JS/CSS; AI agent handoff too.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/single-file-html-i18n`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/single-file-html-i18n/…')`，不要相对 `references/legacy/` 解析。

# single-file-html-i18n（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/single-file-html-i18n/`

溯源（仅标记）：`hermes/software-development`

---

# Single-file HTML Bulk Text Replacement (i18n / 换语言 / 批量文案替换)

对单文件 HTML 应用(内联 CSS + `<script>` 的单文件原型)做全站文案替换(中文→英文、术语替换、品牌词替换)时,**批量替换几乎必然破坏 JS 和 CSS**。本技能是检测、修复、验证的完整方法论。典型场景:单文件原型全站英文化(1366 个串/2373 处,3 轮替换)。

## 何时用
- 用户要求把单文件 HTML 原型全站换语言/换文案
- 需要把原型效果"原样"交给另一个 AI 代理(Claude Code 等)实现 → 见第 6 节交接模式

## 1. 替换方法
1. **先扫描再替换**:正则提取全部 CJK 串(`[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+`),Counter 统计,按出现次数排优先级,分批映射。
2. **映射表长串优先替换**(`sorted(M, key=len, reverse=True)`),否则短 key 会吃掉长串内子串。
3. **绝不映射单字**(如 `'单'→''`、`'个'→''`、`'与'→'and'`):会破坏"订单/工单/键盘"等复合词,且不可逆。只映射完整词/短语。
4. 标点单独一轮(`。→.` `、→, ` `「」→"` `—→-` `…→...` `（）→()`),同样全局替换。
5. 每轮后重新扫描残留(CJK 正则),按当前状态(不是原始扫描)建下一轮映射——碎片(`人信息已` 等)要还原上下文再翻。

## 2. 破坏模式(替换的副作用,必查)
| 破坏 | 形态 | 后果 |
|---|---|---|
| JS 成员访问点后插空格 | `document. getElementById`、`s. classList. toggle` | 大多合法但可疑;最致命的是**选择器字符串**被破坏 |
| 选择器字符串破坏 | `querySelectorAll('. view')`、`'. modal-mask'` | **SyntaxError: '. view' is not a valid selector** → 初始化中断 → 按钮失灵/曲线图不画/hash 路由不切换(症状:导航点了没反应、页面默认显示第一个 section) |
| CSS 选择器破坏 | `. card{`、`.st. green`、`.tbl .ops` → 合并 `.tbl.ops` | 样式全失效/后代选择器失效 |
| 撇号截断字符串 | 映射值含 `'`(如 `Today's`)插入单引号 JS 字符串 | 语法错误(本会话未发生,但高危) |
| 粘连 | 碎片拼接成 `charactersCountcharacters`、`ordersHistoryOrder`、`AllTypes` | 文案难看 |

## 3. 检测
```python
# JS 破坏:点后空格
re.findall(r'[a-zA-Z0-9_$]\. [a-zA-Z_$]', js)          # 字母.空格字母 = 被破坏的成员访问
# JS 字符串里的小写+大写粘连(排除 id/选择器/函数名)
re.findall(r"'[^']{5,70}'", js)  # 再筛 [a-z]{2}[A-Z][a-z]{2,}
# CSS 合并的后代选择器
re.findall(r'\.[a-z][\w-]*(?:\.[a-z][\w-]*)+', css)     # .a.b → 需拆 .a .b(同元素多类除外)
# 残留 CJK
re.findall(r'[\u3000-\u303f\uff00-\uffef\u4e00-\u9fff\u2014\u2026]', html)
```

## 4. 修复
1. **script 块内 `. ` → `.`**(只对 script 块,别碰 HTML 文本区的英文句点+空格)。替换后检查 `e.g.` 类文案例外。
2. **CSS 选择器重建**:` \. ` 模式与点后空格全部还原;后代关系(`.tbl .ops`)与同元素多类(`.btn.primary`/`.pm-item2.on`)必须区分——**维护同元素多类白名单**,其余合并的拆开。
3. **粘连清理**:逐条 replace 修复(先看上下文再翻,不要猜)。
4. 修完 `node --check` 提取的 script 验证**语法**;语法过了还要浏览器实测**运行时**(无效选择器是运行时错误,node 查不出)。
5. **注入新 `<script>` 块的坑(本会话翻车两次)**:往已有多 script 的单文件加 JS 时,(a) 把裸 JS 字符串插在第一个 `</script>` 之后会被浏览器当 HTML 文本,**不执行**(`window.你的变量 === undefined`,UI 却正常渲染,极具迷惑性);(b) `find('</script>')` 找到的第一个结束标签不一定是你以为的块(文件可能头部小 script + 主 script 并存)→ 插入点落进主 script 内部,再包 `<script>` 标签会把主 script 截断/残留裸文本。对策:永远把**完整 `<script>...</script>` 块插到 `</body>` 之前**;验证用 `window.变量 !== undefined` + 实际调用函数,别只看 UI。
6. **切回英文用 reload 的前提**:HTML 源码必须保持单一语言(英文),中文只在运行时替换——若把中文写死进源码,reload 方案失效。

## 5. 验证(必须全做)
1. `node --check` 语法 ✓
2. 浏览器实测核心函数:`show('funds')` 路由切换、`drawChart()` 曲线图、点按钮弹窗
3. console 零 JS 错误(挂 `window.onerror` 钩子收集,注意 navigate 的历史异常是残留,reload 后重查)
4. **file:// 缓存坑**:浏览器反复加载旧版(修复不生效的假象)→ 用 `location.href='file:///...?_='+Date.now()+'#/route'` 强刷
5. 数字完好性抽查(金额 `8,916.35` 不能被破坏)

## 6. 交接给另一个 AI 代理(Claude Code 协作模式)
用户让"另一个 AI 代理照做我的原型"时,单给部署说明不够——它会在自己架构里自由发挥,效果走样。正确产出**三件套**:
1. **基准文件**:可交互的单文件 HTML 原型 = 最终裁决(冲突时以它为准)
2. **UI 基准规格.md**:精确 token(:root 全部变量)、组件规格表(padding/圆角/色值/字号逐项)、逐页结构/交互/英文文案、验收标准(逐页对照基准截图)
3. **实施指令.md**:三条红线(不许发挥 UI/冲突时基准优先/职责=后端对接)、变更流程(UI 改动永远发生在基准文件,代理只同步 UI + 接后端,不重设计)、常见坑清单(它以前犯过的)

判断标准一句话:**"基准文件里长什么样,你的代码里就必须长什么样;后端的事你负责,UI 的事基准说了算。"**

**巡检清单要随包交付**:修复过程中把"修复前 → 修复后"逐条记成对照文档(按页面分节),并附给代理的自查正则(`innerText` 扫 `[a-z]{2}[A-Z][a-z]{2,}` 粘连,要求 0 输出)。代理若从旧版基准抄过文案会带同款 bug,让它自查而不是你逐页复查。验收代理截图的方法见第 8/9 节与 `references/screenshot-verification.md`。

**规格必须逐页详细(简略页 = 漏页)**:用户问"你是不是把入驻资料这几页给漏掉了"——不是真漏,而是规格里该页只有 1-3 行描述(相对资金中心一整页详规格对比强烈)。每页都要逐字段:页头/副标题文案、区块顺序、演示数据值(含姓名/金额/单号)、状态徽章、按钮与操作、弹窗、交互规则(校验/倒计时/联动)。素材直接从基准 HTML 提取:按 `id="view-xxx"` 切 section,正则 `>([^<>]{2,90})<` 拉可见文本逐行入规格。补全后再问"还有哪页简略"时,自己先按字符数排序检查一遍(如 861 字符的 §4.16 vs 1 万字符的页面 HTML)。

**数据源也是照抄对象(不只样式)**:代理最常在演示数据上翻车——图表样式/算法全抄对,但把数据换成当前日期/自造数(销售趋势图横轴出现当天 8/1、8/2,末端值 60 vs 基准 410,而网格比例恰好一致,极具迷惑性)。对策:把基准图表 JS **原样导出**(数据常量 + drawChart + fitChart 整段,`templates/` 或独立 .js),命令"整段复制勿重写";若接后端,只允许替换数据源,渲染规则照抄(日期锚点/切片取法/prev=当前×0.87/末端标注=原始值)。验收用 console 核 SVG 结构:`svg.querySelectorAll('line'/'path'/'circle'/'text').length` + 最后一个 `<text>` 值,判定数据是否基准。

## 7. 运行时中英切换(toggle 引擎,别做纯中文副本)
用户偏好:**"直接做成中英文可切换的不就行了吗"**——一个切换按钮 > 另存一份纯中文文件。
- HTML 源码保持单一语言(如英文),`<script>` 开头注入引擎 + 词典 `{EN: 中文}`
- 切中文 = **运行时替换** DOM 文本节点 + input placeholder(子串匹配,单词边界 `(^|[^A-Za-z])<escapedKey>([^A-Za-z]|$)`,**长 key 优先**让复合串赢过组成部分)
- 切回英文 = **`location.reload()`** 恢复源码(无需反向词典,无漂移)
- `localStorage` 记忆;`DOMContentLoaded` 后 `setTimeout(applyLang, 50)` 自动应用
- 顶栏 `.select` 加 `onclick="toggleLang()"`,按钮文字 `English` ↔ `简体中文` 翻转
- **演示数据(商品名/地址)必须进词典**,否则切中文后残留英文;`Type-C` 这类 token 要整串优先,否则 `Type`→`类型` 误伤成 `类型-C`
- 完整引擎见 `templates/i18n-engine.js`;验证:各路由 h2/状态徽章翻译、双向切换、reload 恢复无混合残留

## 8. 像素级交接补充(规格"描述"≠"代码")
用户抱怨"设计 token 对得上但页面还是不一样"——三大**无声差异**(规格文字里没写就必走样):
1. **字体栈**:body 必须 `-apple-system, BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei", sans-serif` + `-webkit-font-smoothing:antialiased`——最大差异源,整体观感全靠它
2. **全局重置**:`*{box-sizing:border-box;margin:0;padding:0}`、`html,body{height:100%}`、button/input/a 默认值、`svg{width:17px;height:17px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}`
3. **图标**:内联 SVG stroke-width **1.8**,禁止图标库(lucide 等)
对策:把基准文件完整 CSS **原样导出**成独立 .css 交给代理 `diff` 逐字节对齐;禁止"按描述重写",命令"复制 HTML 结构(含内联 style)"。

## 9. 代理截图验收(无 vision 工具时)
OCR + 像素分析验证代理的截图是否照抄基准(比它自报"改好了"可靠):
- OCR(`rapidocr-onnxruntime`)提取截图文字 → 与基准页面提取的可见文本逐条对照,输出「基准原文 | 它做的 | 判定」**铁证对照表**
- PIL 像素分区:黑底品牌区深色像素占比(应 ~30%+)、左/右半平均色判断两栏布局是否缺失
- 典型"没照抄"证据:自创文案(基准没有的按钮/链接)、布局缺区、演示数据被换成当前日期/自造数据(如销售趋势图横轴出现当天日期)
- 判定明确:**是代理的问题不是规格问题**(文案逐字写死它还发明,说明没读基准)→ 交付「逐字修正对照表」让它逐条改,命令"直接复制基准 HTML,禁止自己写文案"

## 支持文件
- `references/bulk-replace-breakage-recipe.md` — 本会话完整破坏形态、修复脚本片段、白名单示例
- `templates/i18n-engine.js` — 运行时中英切换引擎(词典 + TreeWalker 替换 + reload 恢复)
- `references/screenshot-verification.md` — 无 vision 的代理截图验收(OCR+PIL 代码)与像素级规格补充要点
- `references/demo-data-and-script-injection.md` — 日期切换器(DASH_DATA+setDay)、演示数据联动规则(客单价×单数/涨幅/待结算/图表同源)、注入 `<script>` 块的两个坑、从基准 HTML 重建全部交付文件
