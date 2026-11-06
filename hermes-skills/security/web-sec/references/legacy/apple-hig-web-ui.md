<!-- archived from /root/.hermes/skills/security/apple-hig-web-ui/SKILL.md on 2026-10-21 -->

---
name: apple-hig-web-ui
description: >-
  测绘引擎·Use when designing web UIs — user prefers Apple HIG style.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/apple-hig-web-ui`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/apple-hig-web-ui/…')`，不要相对 `references/legacy/` 解析。

# apple-hig-web-ui（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/apple-hig-web-ui/`

溯源（仅标记）：`hermes/creative`

---

# Apple HIG Web UI 设计(用户首选风格)

触发:用户要设计/重做 Web 界面、管理后台、dashboard;或对风格方向犹豫("帮我设计/重做一套")。

## 用户口味(强信号,来自多轮否决)
- ✅ **Apple HIG**:浅色系统灰底 `#F5F5F7` / 纯白、系统字体栈(`-apple-system` + PingFang/微软雅黑)、大标题(页面 24px+ 粗体)、**胶囊按钮**(border-radius:999px)、克制的单一强调色、细分割线 `rgba(0,0,0,.07)`、充足留白、卡片圆角 14-16px、阴影极淡或不要
- ✅ 本用户最终选定 **A2 纯白极简**:纯白底 + 黑色主按钮 + 蓝 `#0071E3` 仅作链接/点缀、浅灰侧边栏 `#F9F9F9`、选中菜单项浅灰底 + 黑粗体(无左色条)
- ❌ 被否决过的方向(别再主动给):科技风(发光/渐变/网格线 → "AI 味太重")、传统深色侧栏+浅内容 SaaS("太老套")、TikTok 黑粉风("不满意")
- 状态语义色必须用 **Apple 系统色**:绿 `#34C759`、蓝 `#007AFF`、橙 `#FF9500`、红 `#FF3B30`、灰 `#8E8E93`;徽章 = 浅底(系统色 10-15% 透明度)+ 深色文字(如绿底文字 `#248A3D`、红底文字 `#D70015`),胶囊圆角

## 配色/风格选择工作流(用户要求"出样图对比")
1. 用户对风格犹豫时**不要只给色卡**——直接做对比样图页:4 套完整方案,每套用**真实组件渲染同一张完整页面**(侧边栏全菜单+顶栏+KPI+图表+待办+表格)
2. 每套样图用 `transform:scale(.36~.52)` 缩略图排列(2x2 或 1x3),底部标注方案名 + 定位一句话 + 核心色值
3. 默认选中一套(高亮边框 + ✓ 标),用户回复字母(A/B/C/D 或 T1/A1 等)即定稿
4. 定稿后**用 CSS 变量全局套用**:改 :root 令牌即可全站换肤,组件零改动

## 多页面原型模式(单文件 SPA,用户偏好)
- 单个 HTML 文件放桌面:所有页面是 `<section class="view" id="view-xxx">`,hash 路由 `#/route` + `show()` 切换;刷新保持路由
- 无壳页面(登录/注册/入驻流程/审核状态)用 `body.auth-mode` 隐藏侧栏+顶栏,内容区全屏
- CSS 变量 = 设计令牌(:root 定义颜色/圆角/字体/阴影),之后所有微调都只碰令牌或局部
- 数据/交互演示也要做:筛选、排序、弹窗、倒计时、批量操作条、行内「⋯」下拉菜单,用户会逐个点
- 验证:浏览器打开遍历所有路由无报错,交互用 console 实测后再交付

## 陷阱(本会话踩过的)
1. **SVG 图表窗口缩放不重绘/错位**:viewBox 写死(如 760x240)时,缩放窗口只等比拉伸,而且 hover 坐标按写死宽度算会错位。修复:监听 `resize` → 读容器 `clientWidth` → 更新 viewBox 宽度 → 整图重绘;hover 坐标换算必须用动态宽度变量(不能引用常量 W)
2. **表格日期排序无效**:`parseFloat("2026-07-31 09:12")` 解析成 `2026`(同年全相等)→ 排序纹丝不动。修复:排序前用正则 `/^-?\d+(\.\d+)?$/` 判断是否纯数字列,纯数字走数值比较,日期/文本走 `localeCompare`(ISO 格式字符串字典序=时间序)
3. **操作列链接与图标按钮不对齐**:flex 容器要加 `align-items:center`
4. 一行 4+ 个操作链接会挤 → 高频操作(编辑/下架)平铺,低频(预览/复制/删除)收进「⋯」下拉
5. 修改 HTML 后用浏览器验证时可能命中旧缓存 → 用 `location.reload()` 或 console 直读 DOM 确认,别只看 snapshot

## 逐页迭代工作流
- 用户说"挨个页面调"时:先列页面清单 + 每页预判要调的细节,让用户挑起点(或建议从首页开始定组件基调)
- 每页先做视觉/结构细节(间距、字号、对齐、冗余清理),再做主流平台对齐(见下)
- 主流跨境平台(TikTok Shop/Shopify/Temu/亚马逊)商品页的共性差距清单:批量改价/上下架/删除、审核驳回原因行内展示、Excel 批量上传+模板下载、导出设置弹窗(格式/范围/字段勾选)、更新时间列+表头排序、库存缺货/低库存警示、多 SKU 价格区间、复制商品

## 存量 UI 苹果风巡检(audit 模式,2026-08 三端逐页实战)
给已有页面(非新设计)做苹果风审计时的固定手法——探针量测 + CSSOM 枚举,不要靠肉眼猜:
1. **探针表达式写单行紧凑 IIFE**(多行/带注释会报 `SyntaxError: Unexpected end of input`),量 `getComputedStyle` 的 borderRadius/fontWeight/fontSize/color/backgroundColor/borderColor/boxShadow。
2. **改样式不生效先 CSSOM 枚举**(`[...document.styleSheets].forEach(sh=>{try{[...sh.cssRules].forEach(r=>{if(r.style&&el.matches(r.selectorText))console.log(r.selectorText, r.style.borderRadius, r.style.getPropertyPriority('border-radius'))})}catch(e){}})`)—直接看到"谁赢、为什么输":同 !important 比特异性,同特异性比文件顺序。比盲目加 !important 快。
3. **⚠️ 重置块 !important 军备赛**:全局表单重置块(如 `[scope] button,...{border-radius:8px !important}`)会压掉胶囊按钮。解法 = 提特异性:`grep` 元素祖先链拿包裹类写 `[scope] .wrapper button{999px !important}`;**若按钮 class 本身含 `button` 字样(如 `button secondary cct-x`),重置块列表里可能有 `.buyer-portal .button`(同 important 同特异性靠后赢)→ 写 `button.cct-x`(含元素选择器 0,2,1)+ bg/color/border/border-radius 全属性 !important**。
4. **⚠️ `<Link>` 渲染成 `<a>`**:`button.类名` 前缀选择器不命中 Link 型按钮,必须补 `a.类名` 变体与 button. 并列。
5. **⚠️ 饱和色探针有"近白浅粉盲区"**:按 max-min<45 过滤近白的探针会放过浅粉/浅橙底(`#fff0f3`/`#fff8f9`/`#fff7f5` 的 max-min 只有 8-18)。浅粉系专项探针:`r>245 && b<245 && (r-b)>8`;**且必须同时扫 `borderColor`**(浅粉残留常是分隔线/边框如 `#ffe3e9`,`backgroundColor` 扫不到)。每次巡检跑两遍:饱和色 + 浅粉系(含 border)。
6. **⚠️ 字重白名单**:全站只应出现 400/500/600/700;扫到 800/850/900/950 即 AI 生成乱入值(旧主题残留),逐处清回 600/700。
7. **⚠️ 全局裸类名残留**(`.main`/`.button` 等无作用域前缀):会给页面无差别命中(如 `.main{padding:34px 0 56px}` 撑高卡片)。卡片莫名超高先 CSSOM 枚举查 padding 来源,再局部归零。
8. **⚠️ sticky top 影响初始渲染位置**:两栏 sticky 布局顶部不对齐时,先查 sticky 元素 `top` 值是否 > 内容起点(header+padding)——sticky 的 top 在未滚动时就把元素推到"距视口顶 top 值"处。改小到吸顶目标位(如 header 下方 18px)即可,别加 margin 硬调。
9. **⚠️ 全局 `h1{font-size:clamp(...)}` 顶爆标题**:列表/详情页标题大得离谱时,先 CSSOM 枚举看是否命中全局 clamp,再局部覆盖小字号,别只调字重。
10. **分组控件(stepper/分段)整体圆角靠容器 `overflow:hidden` 裁切内部元素**,不给内部逐个设圆角;旧式残留特征 = 按钮浅灰底 `#f7f7f7` + 方角 + `#ddd` 边框,苹果风一律白底 + 悬停 `#F5F5F7` + 中性 `#E8E8ED`。

## 交付
- 单文件 HTML 放桌面 → `open_preview` 给用户看;每轮改动后刷新预览 + 简短说明"这轮改了什么"
- 浏览器验证 console 无错再交付;交互改动用 console 实测(触发点击/排序/筛选并断言结果)

## 支持文件
- `references/apple-design-tokens.md` — A2 纯白极简完整令牌集 + Apple 系统色对照,可直接照抄
- Apple HIG 风同样适用于 **A4 印刷图册/报价图册**(封面深空黑居中大标题、单一 `#0071E3`、价格黑色、`@page{A4;margin:0}`):完整版式令牌见 `ai-product-catalog` §4b,无头逐页溢出验证脚本见其 `scripts/verify_catalog.py`
