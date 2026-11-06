<!-- archived from /root/.hermes/skills/security/webapp-rebuild-from-recon/SKILL.md on 2026-10-21 -->

---
name: webapp-rebuild-from-recon
description: "重建丢失源码的Web应用: 源码包+架构+API文档。触发: 恢复源码, 源码丢了, 复刻系统, 一模一样。"
version: 1.0.0
license: MIT
platforms: [windows, linux, macos]

---

> 归档卡：原目录 `/root/.hermes/skills/security/webapp-rebuild-from-recon`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/webapp-rebuild-from-recon/…')`，不要相对 `references/legacy/` 解析。

# 从 Recon 逆向重建 Web 应用(源码恢复/复刻)

用户丢失源码时,从线上站点完整逆向重建:前端保真 + 后端行为等价。交付 = 可运行源码包 + 架构分析 + API 文档(用户画像:破解/渗透成功后常要求"一模一样"复刻部署)。

## When to Use

- 用户说"这是我自己的网站,源码丢了/被删了,帮我恢复"
- 逆向/渗透完成后的"交付源码包"阶段(用户要能自己跑起来)
- 需要把黑盒站点还原成可部署的同构系统

## 工作流

1. **完整 recon 先行**(见 spa-frontend-recon / spa-api-discovery / web-cms-pentest):
   - 全量抓页面(商品/落地页/成功页/404/信息页)+ 内联 JS + 外部 JS/CSS + 数据 JSON
   - 枚举并**实测每个接口**(GET/POST 都 curl 一把,拿真实请求/响应),产出 API 契约
   - 识别框架指纹(路由格式/CSRF 机制/框架特征,如 XunRuiCMS `index.php?s=模块&c=控制器&m=方法`)
   - **枚举/扫描适可而止**:用户偏好采样够用即可,不要全量扫完(如商品列表扫一段确认结构就停)
2. **定技术栈**:优先**原生 PHP8 + SQLite**(零依赖,`php -S` 即可跑);若目标是开源框架二开,可模拟其路由格式保 URL 兼容
3. **实现后端**:路由分发 → 每个接口按契约实现 → 推断建表(表名对齐线上特征,如 dr_*)→ seed 数据(注意**线上 API 参数里的 id 要与 seed 一致**,如接口查 id=61,自增成 1 会查不到)
4. **前端保真**:抓到的 HTML 转 PHP 模板,动态数据 PHP 注入;静态资源 CDN 统一本地化(含站内相对路径 `/static/xxx` 与绝对 CDN URL 两种都要处理)
5. **数据资产导入**:地区库/字典从线上抓的 JS 文件解析入库(JS 树 → 扁平表,记 parent_id,两个接口格式可互相支撑)
6. **端到端验证**:每个接口 curl 实测 + **完整业务链路走通**(如下单→订单号→成功页),中间接口 200 不算完成
7. **打包交付**:源码包 + README + API 文档 + 部署说明(nginx/Apache rewrite 规则,伪静态如 `/slug` → index.php)

## 环境准备(Windows)

```bash
# PHP Windows 版(windows.php.net 302 到 downloads.php.net)
curl -L -o php.zip "https://downloads.php.net/~windows/releases/php-8.3.33-nts-Win32-vs16-x64.zip"
# php.ini 启用: extension=sqlite3 / pdo_sqlite / mbstring / curl / gd
# 本地跑:
D:/tools/php83/php.exe -S 127.0.0.1:8080 -t <站点目录>
# php -S 直接 serve 静态文件 + 把路由请求交回 index.php
```

## Pitfalls(实测)

- **HTML→PHP 模板转换用脚本做,转换后必须 `php -l` 验证**:
  - 子串碰撞:`tcskuData: {` 含子串 `skuData: {`,直接 `str.find` 会替换错对象 → 用正则 `(?<!tc)skuData: {` + 括号深度配对
  - 正则替换生成 PHP 代码时会产生 `$pro[\'id\']` 反斜杠残留 → 只在 `<?php ... ?>` 段内清理反斜杠,**别动 JS 里合法的 `\'` 转义**
  - 模板内嵌 PHP 变量(meta og:title 等)用 `json_encode()` 输出,注意 HTML 属性引号
- **路由命名**:`s=模块&c=控制器&m=方法` → 模块文件 `modules/{s}.php`,函数名 `{c}_{m}()`(如 c=show&m=index → `show_index()`,不是 `pro_show()`);c 缺省时 c=模块名;写错名字会"方法不存在"
- **JS 变量文件解析**:`var linkage_tw =[{...}];` 等号后可能无空格 → 正则 `var \w+\s*=\s*(\[.*\]);`
- **CSRF 复刻**:对齐目标行为(cookie+字段双校验,POST 成功后刷新 token);下单类接口防刷保留(目标限速,重建也限)
- **Windows 原生 curl 写中文路径失败**(`D:\渗透\...` No such file)→ 先下到英文 ASCII 路径再 cp
- **订单/业务数据走明文 GET 的复刻**:参数格式(如 `ordata[sn]=`)要与线上一致,前端 JS 依赖该格式跳转

## Verification

- [ ] 全部页面模板可渲染(商品页/成功页/信息页/404)
- [ ] 每个 API 契约接口 curl 实测与线上响应结构一致
- [ ] 完整业务链路端到端走通(下单→订单号→成功页显示)
- [ ] 静态资源全部本地化无外链(或明确保留的 CDN 白名单)
- [ ] 交付含 README + API 文档 + 部署说明

## References

- `spa-frontend-recon/references/xunruicms-cod-zengda.md` — zengda.shop(长安COD/XunRuiCMS)全站逆向+重建完整案例:API 契约、SKU 结构、地区库导入、表结构推断、重建坑
- `spa-frontend-recon` / `spa-api-discovery` — recon 前置方法论


---

## 外部库增量（2026-10-11 分享包）

## Pitfalls

- **SFC 里 `find('</template>')` 会命中「被注释掉的模板块」内的 `</template>`** ⇒ 模板切片用 `rfind('</template>')`；同理 `<template>` 段界判定不得用首个匹配。
- **`v-if` + `v-for` 写在同一元素上 ≠ 原厂 `v-if ? Fragment[keyed]{ v-for, 空态 }`** —— 同元素写法会把空态（`.none` 暂无数据）掉成父级顶层兄弟，条件不成立时仍渲染（实测 +6832 字节）。回填时必须按原厂把「列表 + 空态」包回同一 `<template v-if>` 分支内。(实测)
- **块级 DOM 收拢 / 搬移修复器的落点偏移必须剔除前导空白**：正则带 `\s*`（形如 `\s*<div class="none"`）时，`m.start()`/`m.end()` 之外的 `lead = len(m.group(0)) - len(m.group(0).lstrip())` 不可省，且使用前 `assert out[nstart:nstart+4] == '<div'` —— 漏掉前导空白会把起点落到标签名中间 ⇒ 深度/括号配对从半截标签开始、静默返回 None（实测「配对失败」的真根因就是它；同族偏移基准错见静态属性回填的 BASE 自校准）。(实测)

- **HTML→PHP 模板转换用脚本做,转换后必须 `php -l` 验证**:
  - 子串碰撞:`tcskuData: {` 含子串 `skuData: {`,直接 `str.find` 会替换错对象 → 用正则 `(?<!tc)skuData: {` + 括号深度配对
  - 正则替换生成 PHP 代码时会产生 `$pro[\'id\']` 反斜杠残留 → 只在 `<?php ... ?>` 段内清理反斜杠,**别动 JS 里合法的 `\'` 转义**
  - 模板内嵌 PHP 变量(meta og:title 等)用 `json_encode()` 输出,注意 HTML 属性引号
- **路由命名**:`s=模块&c=控制器&m=方法` → 模块文件 `modules/{s}.php`,函数名 `{c}_{m}()`(如 c=show&m=index → `show_index()`,不是 `pro_show()`);c 缺省时 c=模块名;写错名字会"方法不存在"
- **JS 变量文件解析**:`var linkage_tw =[{...}];` 等号后可能无空格 → 正则 `var \w+\s*=\s*(\[.*\]);`
- **CSRF 复刻**:对齐目标行为(cookie+字段双校验,POST 成功后刷新 token);下单类接口防刷保留(目标限速,重建也限)
- **Windows 原生 curl 写中文路径失败**(`D:\渗透\...` No such file)→ 先下到英文 ASCII 路径再 cp
- **订单/业务数据走明文 GET 的复刻**:参数格式(如 `ordata[sn]=`)要与线上一致,前端 JS 依赖该格式跳转

## 前端工程重建（只有 dist 时：反编译回 `.vue` 工程）

后端重建之外，客户常在同一单里要「可 `npm run build` 的前端原工程」。**dist 里有 Vite `manifest.json` 就能机械重建，不要重写**（实测：356 页面落盘 / SFC 全绿 / 构建绿）：

```
manifest.json → 源文件树蓝图 + .vue→chunk 映射
chunk         → 渲染函数反编译 → <template>
chunk         → setup() 体抽取   → <script setup>
vendor chunk  → 导出名→真 API 名 两级表回填
主包 index.<hash>.js → 应用运行时(store/api/router/i18n) → src/runtime/*.ts
```

六道闸（顺序固定）：`sfc_check` 全绿 → `vite build` 绿 → **页面 chunk 体积从几 KB 空壳跳到几十 KB** → 抽验页面 `<script setup>` 是真业务调用 → **导出面之差**（runtime 入口导出集 vs barrel 导出集**逐名相等**）→ **生产形态真跑起来**：`npm run build` + `npx vite preview --port N --strictPort` + CDP 读数/截图。**冒烟不要用 `npm run dev`** —— 冷启上千模块 + HMR websocket 会让无头 dump 与虚拟时钟卡死，读数全是噪声。绿色构建**拦不住**五类致命缺陷：TDZ、模板悬空绑定、漏注册的 `$` 全局属性、barrel 漏转出、pinia 抢跑 —— 只有运行才现形；逐条根因/修法见 `references/vite-dist-to-sfc-rebuild.md` 第七节，卡死时的读数手段见 skill `browser-js-debugging`。
**★ 开工前先判「vendor 是否分离」——它决定整条还原路线**：数 `assets/` 里的真 vendor chunk。分离（几十个 `vendor.@vue.*.js` 之类）⇒ 走别名两跳法（vendor chunk 里真名就地加载）。**全内联**（`assets/` 只剩几个旁支库，Vue/router/pinia/i18n/Arco 全进 entry chunk，entry 到 MB 级/数万行）⇒ **entry chunk 就是应用本体**：自带权威路由表（`component: () => ax(() => import("./page.<hash>.js"), [预载依赖清单])`）、路由器实例（在导出表里）、**顶层自注册的全局守卫**（`router.beforeEach(...)`，不在导出表里）、store、权限指令、i18n。
⇒ 全内联套别让 `main.ts` 另建第二套 router/守卫（会与单体里的实例分叉），改为把单体当 app 入口、只把它的动态页面 import 重指到重建的 `@/pages/*.vue`。**也不要把同族「有 vendor 分离」那套的引导层搬过来**：别名是**每次构建**重新分配的（同族两套 dist 连同名函数体的 token 都不同），搬来的层会向单体索要不存在的语义名。`gen_router.js <distRoot> <outDir>` 可从 manifest 生成权威路由表（页数/manifest 条数/顶层数三个数对得上才算数）。做法与证据见 `references/minified-bundle-to-modules.md` 第十节。
**★ 多 SFC chunk 的页主体会「张冠李戴」**：分块组件元数据缺源路径（`file=null`）时，别名四段式（basename→dirName→chunkBase→唯一组件）无法用 `/pages/` 或名字消歧，退化成 `largest` ⇒ 页 `.vue` 里可能是**该页的子组件**（面板/图表/横幅）的体，同 chunk 的兄弟 SFC 根本没落盘。判据：模板根形状与路由页不符（出现别域 i18n key、`GridItem class="title"` 这类面板骨架）+ 工程里找不到兄弟子件文件。修法：先把该 chunk 的**全部** SFC 物化（子件四件套），再用「父引用子」重选页主体，最后用同表运行期 A/B 定案（同 DOM=误报、异 DOM=真劫持）。**判不了就不许写结论** —— 标记页只能以「未证实」进交付台账。
**★ 运行时 barrel 撞名是全内联套的必然病**：把各模块的**原始压缩别名**全量 `export {} from` 出去，必然 `Multiple exports with the same name "u"`（实测一次 116 个 esbuild 错）。barrel 只导**已定名的语义名**、每个语义名指向唯一模块；定不了名的**留 TODO 不猜**。
**Stage H 引导段（易整段丢失）**：entry chunk 的**顶层侧效语句**（`app.config.globalProperties.$x = …`、`app.provide(…)`、`app.use(…)`、`app.mount('#app')`）**不在导出表里**，只按「导出项 + 无具名导入的侧效 import」采集会全部丢掉 ⇒ 模板里 `$dataFormat/$kilobitnumberFormat/$numberFormat/$pageReset` 这类名字成悬空（实测 177 页模板直接调用）。必须单独采集这段并逐条接到 `main.ts`，缩名用该 chunk 的导出表定名（禁猜）。
**口径铁律**：重建产物**不是原厂原件**；**绿色构建 ≠ 开箱即用** —— 页面里的 `../index.<hash>.js` 在重建工程里默认是**悬空 import**（store/router/api/i18n 全在里面），必须做 Stage G：主包 → `src/runtime/*.ts` + 把页面 import 重指过去，否则再绿也跑不起来。
⇒ SFC 侧规则与坑见 `references/vite-dist-to-sfc-rebuild.md`；主包运行时还原见 `references/minified-bundle-to-modules.md`。
**★ 原厂 `index.html` 要逐字复刻，并做「同环境 A/B」**：原厂 `<title>` 常是**空**的（标题由应用按路由 meta 运行时设置）⇒ 写死静态标题会盖掉应用标题（A/B 一眼看出差）；body 尾部的同步 `<script src="./tinymce/tinymce.min.js">` 与 `DOMContentLoaded` 里注入的语言包（`/tinymce/langs/zh_CN.js` 等）也要照搬，并把原厂静态目录整份 copy 进 `public/`（Vite 原样进 dist），**否则富文本页在重建工程里直接不可用**。A/B 用两个静态服务器（原厂 dist / 重建 dist）比可测读数：`#/` 是否被守卫重定向、`document.title`、`#app` 的 innerHTML、全局对象（`typeof window.tinymce`）。**无后端时两侧都只渲染注释节点（`<!---->`）** ⇒ 空白是环境所致、不是工程缺陷，别登记成缺口；差异必须落到具体读数上才成立。
**★ 运行时还原不止「导出面/全局属性」**（都属「build 全绿但跑不起来」族）：
① **HTTP 封装（`utils/request.ts`）的鉴权头与语言头要从原厂 chunk 逐字还原**（典型 `Authorization = `Bearer ${useTempStore().token}``、`Accept-Language = useLocalStore().lang`，带 localStorage 兜底 + try/catch 防 pinia 未就绪）—— 反编译常把它退化成 `localStorage.getItem('token')`，接口全 401；改完**必须重跑全量运行期实扫**（新增跨模块导入本身就是新的运行期风险）。
② **引导期临时打点一律加 `?diag=` 闸**（改 `document.title`、`BOOT:` 日志），否则非诊断模式会覆盖页面标题。
③ **缺图标资源就手写 BMP 格式 ICO 落 `public/favicon.ico`**（无需图像库），别留 404；favicon 是否 200 也算交付闸的一条读数。

**★ 反编译必然带出的「模板属性直译」缺陷（build 全绿，只在运行期炸）**：渲染函数里的 `onClick: fn(x)` 会被直译成模板属性 `:onClick="fn(x)"` —— 模板里 `:` 是**属性绑定、每次渲染求值** ⇒ 每渲染一次真调一次。若 `fn` 内是 `router.go(0)`/`location.reload()`，就是**启动期整页重载风暴**（实测 4 ms 内 24 次，页面永远重启；症状会伪装成「主线程卡死」或「接口批量失败」，把排错带偏两个方向）。同族 `:onUpdate:modelValue="x = $event"`：渲染期无 `$event` ⇒ 每渲染把状态写成 undefined。修法 = 机械改写 `:onXxx="<直接调用>"` → `@x-x="<同表达式>"`（Vue 自动包处理函数），事件名转 **kebab**（`@value-change` 编译为 `onValueChange`，与组件 `onXxx` prop 对齐；整段小写会得到 `onValuechange` ⇒ 处理函数静默失效）。全库扫描/改写：`scripts/scan_render_attrs.js`。
**★ 同族的第二签名：反编译把箭头函数整个吞掉** —— 模板里写成 `:onClick="x.value=!x"`（原厂 render 是 `onClick:c[0]||(c[0]=o=>x.value=!s(x))`）⇒ 绑定在 **render 期求值** ⇒ 对**已解包的布尔**写 `.value`，报 `Cannot create property 'value' on boolean 'false'`。**真值一律回读原厂 chunk 的渲染函数**，模板源的正确形态是 `@click="x = !x"`（**ref 名直接赋值**：SFC 编译器自动补 `.value`；写成 `x.value` 会被再解包一次）；字面量赋值同法（`x.value='remind'` → `@click="x = 'remind'"`）。本类**成族出现**（实测 53 处 / 24 文件，另有 4 处形态复杂者如实报 UNRESOLVED 不猜），所以纪律是：全库扫 → 修复器 DRY 记数 → APPLY → **宿主/冷加载重跑把错误计数打到 0**（改前先备份 `.preev`）。用「占位普查」找缺口是不够的 —— 无占位但处理器被译错的页照样报错。
**★ store 初始 state 的形状不许压扁**：模板 `X.init.logo.black` 这类深路径在**首屏**就读（早于 `systemInit()` 等异步引导 resolve）。压成 `init: {}` ⇒ 首屏 `TypeError: reading 'black'` 白屏。默认形状从**原代码自己的兜底分支**逐字还原（原厂 else/catch 里那份 placeholder 对象就是权威形状，不算伪造）。
**★ 批量改写后必须重跑运行闸门**再对外说「可二开」—— 改写器是机械的，回归只能靠运行期读数（`scripts/scan_render_attrs.js` 未落 `--write` 时以非零码退出，可直接串进闸门）。
**★ 反编译器的“角色分流”必须是三条独立分支**：渲染函数里 `createTextVNode("…")` 是**文本**、
`createCommentVNode("…")` 是**注释**（`("v-if", true)` 属编译器占位，直接丢），
不能与元素创建共用一条分支 —— 混用会产出伪标签（`< 中文名 />`）并在构建期让 `compiler-core` 的 `genNode` 拿到 undefined 节点崩。
**注释分支还必须排在“文本节点”分支之前**：否则注释的字符串实参被文本分支吞成 `{{ "…" }}`，实参里含 `{{ $t('…') }}` 时
直接打断模板编译。同理，标签解析要追**页内局部**声明 `X = resolveComponent("van-field")`（只查主组件 `components` 表会漏，未解析组件被降级成 `<span …>`）。
改完必走闭环（重反编译 → 原地覆盖 → 重注入 → 修复链 → 构建）并给出伪标签/未解析计数对比；
合并产物先核根前缀（`cp -rf <OUT>/pages/. src/pages/`）、别 `rm -rf src/pages`（会删掉手工重建的页）；
构建前三门自检 + `driver.sh` 纪律见 `references/multi-suite-rebuild-pipeline.md` §8。

**★ 模板标签是「组件解析」的窄口 —— 五条铁律（机理/探针/代码见 `references/vue-tag-and-component-resolution.md`）**：
① **标签名合法性必须与 Vue tokenizer 同口径 = 只认字母开头**（`isTagStartChar` 只认 `[A-Za-z]`）：`_`/`$` 开头的别名直写成标签会被 tokenizer **整段吞掉**，元素消失、子节点上浮，跨节点效应表现为 codegen `Duplicate slot names found`，且报错行号是**子节点**那行、不是病灶行。收紧为字母开头，非法起始字符走可逆别名编码。
② **原生标签判定用 `@vue/shared` 的 `isHTMLTag/isSVGTag/isMathMLTag`**，不手写集合：漏一个（实测漏 `q/g/rt/use`）就把真组件当原生跳过 ⇒ 不注册 `components` ⇒ 槽模板挂到原生元素上 ⇒ `Codegen node is missing` + 静默错渲染。
③ **Vue 运行时 API 名绝不可能是组件标签**：名字表（含反编译器手写兜底表）把 `normalizeProps` 之类当组件真名 ⇒ 假组件、运行期解析失败。护栏必须落在**组件名解析的每一条路径**上（别名表路径与模块名表路径各有一处，只加一条等于没加），命中即回落别名路径。
④ **未定名组件用「可逆别名编码」标签名，禁止无条件降级成原生元素**（`<span>` 占位 + `#slot` 子节点会在构建期直接崩）；注入端对称解码还原。
⑤ **无 `<script>` / 无 setup 的页不许整页跳过**：跳过 ⇒ 组件从不注册 ⇒ 运行期 `resolveComponent` 失败、整页空白而构建全绿。改为合成最小注册脚本，且只用**权威可解析**来源（组件库 `es/` 目录名 Pascal 化 / 端口化 chunk 反向索引），解析不出的如实登记未解析清单。

**★ 「未落绑定标签 / Duplicate slot」类自写检查脚本的结论是启发式、会过时**：实测同一现象既有真病灶也有纯伪影。权威只认两个 —— ① 真 `npm run build`；② 用 `@vue/compiler-sfc` 按 vite 同参编译每页模板，抽 `resolveComponent("X")` 与 `_ctx.X` 再核对 X 是否在 `components` 键 / setup 返回 / 模块级声明里，交「解析点数 / 编译失败 / 不可解析」三个数。**片段级编译 OK ≠ 真构建 OK**（跨节点效应在片段层看不到），翻案前先把探针改成与构建同源的选项矩阵并打印 AST 父级结构。
**★ 修复器自己的 oracle 会「静默失效」——编译/解析类 oracle 一律禁止 `catch → continue`（本轮惨痛实证，最高优先）**：判「双 `.value`」的扫描器把 `sfc.parse(src,{pad:'space'})` 之后的 `compileScript()` 包进 `try{…}catch(e){continue}`，而 `@vue/compiler-sfc` 在 `pad:'space'` 下对一批文件抛内部错 `Cannot read properties of undefined (reading 'previous')` ⇒ 这些文件**从未进过扫描**，却让全量读数报出 `total_dual = 0`（「缺陷已清」）。去 pad 后的真值是 **20 文件 / 193 处**，症状 = **除首页外所有路由运行期 `Cannot read properties of undefined (reading 'value')`、`#app` 只剩 1 个元素**（原厂同路由 2715–7544 字节 / 34–42 元素）⇒ 差点把「整站白屏」当成「已清零」。三条硬纪律：① oracle 必须**显式记 `bad`/`COMPILE_THROW` 计数并打进报告**，`bad == 0` 才算这次扫描有效，否则「0 处」这个读数本身不成立；② 编译器级 oracle **不要传 `pad:'space'`**（偏移改用 AST 节点自身的 `loc`），且判 ref 二次解包必须 `compileScript(d,{inlineTemplate:true})` —— **非 inline 下 `dual` 恒为 0**，拿它当 oracle 会把真缺陷判成干净；③ **换 oracle / 改判据之后，此前所有修复器的「幂等 0」读数全部作废**，必须在新 oracle 上重跑 DRY → APPLY → 再 DRY。修完仍须回**冷加载 A/B**（页长/元素数）复核，不能只看 oracle 归零。
④ **「文件已改动」不是逐项生效**：修复器按项报结果时必须断言 `hits == 预期`（`0 命中 ⇒ FAIL、不写盘`），锚串一律从**该文件自己的文本**取 —— 同族页面的 import 别名不同（一页有 `onMounted as ze`，另一页根本没有），沿用上一页的锚点会恒 0 命中；APPLY 后逐项 `grep -c` 复核再构建（实测 5 项里 4 项未命中、脚本仍打印「生效」，一整轮白干）。
**★ prod 压缩栈 → 源码行：构建时开 sourcemap 再回源定位**（`scripts/prod_stack_to_source.cjs`）：反编译工程的报错栈只有 `chunk.js:1:COL`，`vite build --outDir distSM --sourcemap` 后用 `source-map-js` 的 `originalPositionFor` 一步得到 `<原 .vue 文件>:<行>:<列>`，再打印该 offset 前后的压缩表达式即可肉眼读出真凶（本轮即由此把 `transactionPassword/index.vue` 里的 `X.value.value` 现形）。**与 `chunk-offset-dump.js` 分工**：本脚本用于「定位到源码文件行号」，后者用于「读编译后表达式」。
**★ 静态 class/style 回填 oracle 的三条硬口径**（从原厂 render 树取静态属性、回填到模板；判据全靠 DOM 差分）：① **真值要同时取三类，且必须剔伪标签** —— ①hoisted props 对象（`e("div",Wt,[…])`）；②**组件调用** `B(k,{…})`（`k=U("van-tabs")` ⇒ tag=van-tabs，只取元素会整类漏）；③必须把 `createCommentVNode`/`createTextVNode` 出的伪标签从「元素」里剔除 —— 原厂条件分支里的 `u("v-if",!0)` 会被误判成真元素 ⇒ **按序错位**（黑名单：`v-if/v-else/v-else-if/v-for/v-slot/template/slot/component/transition/transition-group/keep-alive/teleport/suspense`；实测某页错位 26 → 加闸后 5）。style 是对象时必须转 CSS 串。② **插入点必须自校准基准 + 逐处断言** —— 模板 AST `loc.start.offset` 的基准可能是「文件绝对」或「块内容相对」，用错会把属性插进标签名中间（实测把 `<title` 插成 `<tit…`）⇒ 用首个元素实测判定 BASE ∈ {0, tplBase}，且**每次插入前断言该 off 前缀 == `<tag`**，否则不插。③ **批量 APPLY 必须分档 + 备份 + 幂等复验** —— `--maxmismatch=N` 闸、且「先 DRY 取对齐读数，只有 mismatch<=N 才 APPLY」；每批前 `cp -r src src.bak_attrsN`；APPLY 后 DRY 复跑必须 0 处才算过（高错位文件不硬 APPLY）。
**★ 修复链顺序是契约，不得调换**：`注入 → 模板结构修复 → 顶层闭合归一 → 模板属性修复 → 悬空名回填 → 模板 i18n 绑定改写 → 脚本绑定还原 → build` —— **注入会重写整个 `<script>` 段，任何模板层修复必须排在注入之后**。每个修复器都要：① 自证幂等（干跑 → `--write` → 再干跑 = 0 处/全跳过）；② 对非 `<script setup>` 页设安全闸（往非 setup 页注入 `useI18n()` 会把它提到模块作用域 ✗）。改完解析器/修复器走「回滚页面 → 重跑 → 重建」闭环，且以产物实证，不看日志看结果。
**★ 三类「静默改写」：`src` 里 grep 不到、`vite build` 全绿，只在产物/运行期炸**（① 模板 `$t('key')` 被生产构建编成 `X.value("key")`，或撞上脚本同名助手 ⇒ 崩在助手内部，报错签名完全不像；② 反编译把 `ref` 的编译后形态 `NAME.value.X` 直译进模板 ⇒ `unref` 双解包；③ 注入器把模板泄漏名错绑成 import（`defineComponent as E` / `isRef as tt` / 图标 `as w`）⇒ 原厂 `reactive` 声明被吞）。判据只有产物与运行期：**dev server 未压缩转换产物当 oracle**（dev 出 `$setup.$t(...)` 而 dist 出 `X.value(...)` ⇒ 缺陷在构建期，改模板文本躲不掉）+ **按栈偏移切 chunk 读编译后表达式**（`scripts/chunk-offset-dump.js`，报错栈第二帧是调用者）。逐条机理/修法见 `references/vite-dist-to-sfc-rebuild.md` 第十一节。

**★ 反编译模板的保真缺陷族与修复器纪律（`references/template-fidelity-repair.md`）**：除上条 `.value` 双解包外，同族还有三个 **build 全绿、只在运行期/肉眼对照里现形** 的坑 —— ① **`v-if` 守卫被吞**（原厂 render `cond?(v(),m(tag,{…})):l("v-if",!0)` 只剩 consequent ⇒ 无初值的 `ref()` 首屏求值即 `TypeError reading '<模板首字面属性>'`）；② **相邻插值文本被吞**（`n(a)+" "+n(b)` 当不了文本 ⇒ 子节点整段丢失、渲染成空 `<div></div>`）；③ **scopeId 静态提升**（`defineOptions({__scopeId})` 不够，非要 `compilerOptions.hoistStatic:false` 才把 `data-v-*` 落到 DOM，否则作用域 CSS 全失效；自证 = 同路由双侧 `#app` 长度相等且 `data-v-<id>` 各 1 次）。全局 `hoistStatic:false` 是兜底，先做**逐节点外科修法**：把该节点绑定的字面量 class 改成 **script 变量**（`<span :class="DASH_CLS">`），内联 base64 改 `:src="EE"` —— 写 `:class="'x'"` 会被常量折叠、**照样被提升**（「改了没效果」的头号原因）；产物里 patchFlag = `-1` 就是 HOISTED，先读它再判补丁是否落在活路径上。同族第二类：`data-v-<id>-s` 后缀来自运行时对**插槽 fallback 内容**的注入（原厂手写 render 走 `noSlotted` ⇒ 单页可差上百处），修法是把内容**移出 `<slot>` 的 fallback**。两类机理与实测读数见 `references/template-fidelity-repair.md` §7。三条常驻纪律：
① **批改前备份源码树，且先把输出串算完再开写句柄** —— `open(p,'w')` 立即截断，写参表达式求值抛错会把文件清成 0 字节（从备份恢复 + `find . -name '*.vue' -size -200c` 计数兜底）。
② **反编译器/代码生成器改完必须用「新旧产物逐字节 diff」自证生效**：产物完全一致 = 补丁不在活代码路径上（实测补在子节点渲染函数上无效：同形态在更早的分派分支里已被消化），不得以「我改了」当结论。**零 DOM 效果的第二成因是「结构位置错配」而非「动态化不足」**：我方把原厂静态节点放进 `v-for` 行内（列表为空 ⇒ 永不渲染），原厂它在静态同级 —— 实测 `line` 分隔符连做两批动态化零 Δ，归位到原厂位置（`.pickTime` 内、起止字段之间）一次 +184。诊断 = 在原厂 chunk 里找该 vnode **const 的定义与调用点**（定义给形态、调用点给位置）；判据 = 产物 diff 一致或冷加载 Δ 不变 ⇒ **先查结构位置，别再叠加动态化**（详见 `references/template-fidelity-repair.md` §7(c)）。
③ **A/B 差异先排除原厂自身**：原厂那侧本就空渲染或自带报错的页面不算重建回归；结构差异用「标签序列 difflib」定位（不要打印整页 HTML），模板守卫/文本/属性的真值一律取**原厂 chunk 的渲染函数原文**。
**★ 第四类：`v-else` / 三元 else 分支整块丢失**（build 全绿、DOM 少一大块）。原厂 `cond?(A):(B)` 的第二支被反编译器吞掉 ⇒ 我方模板只剩 `v-if` 分支、`v-if` 假时渲成 `<!---->`，而原厂同位置渲染**空态文案 + 空态图**（实测 FPS 页 `v-if="I.length>0"` 后的 else 地块整块消失，`<!---->` 计数 27 vs 原厂 24，正好差 3 个 `<img>`）。判据 = 数双侧 `<!---->` 与各标签计数差，再回读**原厂 chunk 渲染函数原文**确认第二支的内容；修法只能改反编译器重反编译，禁止手写补内容。
**★ 第五类：`<img src="@/assets/img/...">` 引用的源资产在重建工程里根本不存在**（`src/assets/` 为空，模板引用十几个 PNG）。原厂由打包器**内联成 base64**（<4KB 资产），所以「同字节还原」= 从**原厂 chunk 里取那段 base64 解码成 PNG 写到原路径**，让重打包再次内联 ⇒ 产物与 DOM 双双等价；不要手绘/找近似图（字节不同 ⇒ base64 长度不同 ⇒ DOM 长度差）。
**★ 第六类：反编译器在「文本节点 + 组件」混排时丢尾部组件**（build 全绿、DOM 少一整块、`d=-256`）。原厂 render 原文形态 `t("div",Ma,[V(s("SWIFT Code")+" "), d(I,{name:"info-o",…})])` —— 同一 div 里「文本 + 组件」并列时，反编译器只出文本、丢掉后面的组件（实测 `SWIFT Code` 后的 `van-icon-info-o`、上传框的 `van-icon.plus.plus` 双丢）。**判据**：`#app` 长度差 + **元素计数**（`badge=6/6`、`info_o=1/1`、`plus=2/2`）+ 逐字符 diff 落到具体节点；**修法**：先按原厂 render 原文回填模板（`fix_bankcardadd_icons.py` 式模板补丁），同型再现才动反编译器。修后 `-256 → -3 → 0`（`diff块=0`）。
**★ 第七类：`v-if` 假分支占位注释的文本是「编译模式」产物**（`d=-3`，肉眼无感但破坏逐字节保真）。原厂 chunk 带 **`__file`** 且渲染函数里是 `N("v-if",!0)` ⇒ **该产物是 dev 形态编译的**；本机 `@vue/compiler-sfc` 3.4.25 在 `NODE_ENV=production` 下编译成 `_createCommentVNode("", true)` ⇒ DOM 出 `<!---->`（**每处少 4 字节**），只有 `NODE_ENV=development` 编译才出 `"v-if"`。
⇒ **不要为了这个整套切 dev 构建**（会拉 npm `vue` 的 dev 运行时、反而降保真；实测还因裸别名导入直接构建失败）。正解 = vite 插件 `enforce:'post'` 只做**等价还原**：`/\.vue/` 的 transform 里把 `_createCommentVNode(\s*""\s*,\s*true\s*)` 换成 `_createCommentVNode("v-if", true)`。**自证读数** = 页 chunk 内 `"v-if"` 计数（0 → 5，与原厂 DOM 的 5 处一致）+ 同页 A/B `d` 归零。
**★ 裸别名导入是潜伏缺陷（prod 隐身、dev 现形）**：反编译产物里会写 `import { u } from "vue"`（原厂是 `unref as u`）。prod 构建靠 tree-shaking 把「未使用」的裸别名抹掉 ⇒ **构建全绿、缺陷隐身**；dev 构建当场报 `"u" is not exported by "vue/dist/vue.runtime.esm-bundler.js"`。交付前必扫 `import \{[^}]*\} from "vue"` 里**没有 `as`** 的单字母名并补成 `unref as u` 形态（本库实测 2 处：accountStatement / exchangeRecord）。
**★ 剩余 `d=+8/+16` 型尾差 = 我方模板空白在 condense 下活了下来**：反编译器输出的多行缩进里，**「插值/文本 ↔ 元素」边界**的空白会被 whitespace-condense 保留成 1 个空格（**「元素 ↔ 元素」边界的会被整段删掉**，所以只有前者漏字节）；diff 块形态全是 `insert` 空格 ⇒ 根治办法是让反编译器**在文本类子节点与元素子节点相邻处不插空白**（原厂 compiled children 就是无空白的精确节点表）。同族反向 = 我方注释节点带文本而原厂是空注释（`<!---->` vs `<!-- comment -->`，差 9 字节）⇒ 注释文本一律取原厂 `createCommentVNode(...)` 实参原文，禁止自行补字；**原厂该位置 `createCommentVNode` 计数为 0 ⇒ 我方那条注释是伪造的，整条删除**（别改成空注释、别留作占位）。
**★ 别名修剪器会误删「仅模板使用」的导入**（第 1 类静默缺陷，实测 -2943 字符）：`fix_vue_imports` 式脚本只扫脚本体判用途 ⇒ `import{_ as q}from"./zanwu.js"` 被当无用删掉，而模板 `<img :src="q">` 真的在用 ⇒ 空态图整块消失、DOM 差 -2943 而 build 全绿。修法 = 按**原厂 chunk 的 import 表**逐文件比对模板表达式，把缺的导入补回（脚本 `restore_tmpl_imports.py`）；**模板表达式正则必须覆盖全部形态** `(?:[:@][\w.:-]+|v-[\w:.\-\[\]]+)\s*=\s*"([^"]*)"` —— 写成 `(?::|@|v-if=…)\s*"` 会漏掉 `:src="q"`（冒号后还有属性名）而报「0 命中」。回填后必须冷加载 A/B 复测该页长度。
**★ 全量反编译/重建脚本并发或迟到完成会覆盖产物 ⇒ 判新鲜度只认 mtime**：两次 `bash xxx.sh > runN.log` 写同一输出目录时，**先检查产物 mtime 是否晚于所有日志 mtime**，再信内容（实测一份迟到的旧版日志把 `download` 写成 42 B，而盘上是修复版 999 B —— 只看日志会误判成回归）。纪律：长任务串行、或每轮换输出目录 + 落「版本戳文件」。
**★ 第四类静默改写：反编译吞掉的可能是「成员路径里的一级」**（`e.book_new()` 原文本是 `XLSX.utils.book_new()` —— 命名空间别名还在、中间那级没了，静态看像正常调用，按成员名 grep 也命不中缺失点）。判据 = **构建期的 `not exported` 告警即权威清单**（不用猜）：修前/修后各 `grep -cE "not exported" build.txt` 当验收证据；再去**包自己的 ESM 入口**核对真实导出结构（`node_modules/<pkg>/<pkg>.mjs` 里该名字挂在 `utils` 这类子对象下），**只补那一级**、带幂等护栏。反面做法：另加一层新命名空间再前缀，或改用可能被局部形参遮蔽的别名（`n.` 常就是形参名）。
**同族签名要对号入座**：`Cannot call a namespace ("t")` = 前缀丢了一级；`Illegal reassignment of import "X"` 与 `"13" is not exported by <命名空间>` **成对出现**时不是缺导入，而是**Vue 编译器生成的渲染缓存表达式被直译进了模板**（原厂 `_cache[13]||(_cache[13]=withKeys(...))` 里的 `_cache` 被认成命名空间导入）⇒ 改回 `_cache[N]`（渲染函数作用域内可用）。**构建器报的行列号是「生成后模块」的坐标**：在 `.vue` 源码里 grep 那一行必然找不到 —— 先用 `@vue/compiler-sfc` 的 `compileScript` 或 `vite` 的 `transformRequest` 把该文件转出来读原文，再动手。
**★ 反编译器的「对账注释」要抽样再清**：`<!-- 组件名待定: C -->` 这类注释的下一行**往往已经是真名**（`<Card ...>`）⇒ 只是「原混淆名 → 真名」的记账，删了才干净（实测数百处）；但形态不一的（后接闭合标签/文本，标记失去指代）必须**保留 + 登记进 TODO 台账**。批量删注释前先抽样 2–3 处定性，只删「载荷已被证明冗余」的。
**★ 门槛口径**：全路由运行期实扫五分类 —— `OK` 干净渲染 / `BLANK` 父级容器路由（无独立内容，**非缺陷**）/ 仅 `AxiosError`（mock 后端缺失，**非工程缺陷**）/ `REDIRECT` 登录跳转 / **真缺陷**。**只有「真缺陷 = 0」才叫门槛通过**；`npm run build` 绿不算 —— `.vue` 无 `lang="ts"` 时写 `ref<any>(...)` 会被当 JS 解析，构建照绿而运行期 `ReferenceError: any is not defined`。
**★ 验收只认「冷加载」，同 tab 内导航的扫描会伪绿**：SPA 换 hash 只是 same-document 导航，模块早被预热 ⇒ 同一批页面在热身扫描下逐字节一致（实测 35/35 一致），改成整页重载后却有一批页抛 `ReferenceError`、渲染退化回注释节点。**冷加载的做法：每条路由拼一个变化的查询串再导航（`?t=<i>#<route>`），只改 hash 不算**；逐路由读数必须取自冷加载那一趟，热身那趟只能用来粗筛路由清单。**路由清单必须取运行期 `router.getRoutes()` 的解析后绝对路径** —— 手拼「父前缀 + 子路径」会得到重复前缀（`/dashboard/dashboard/...`），整批页渲染空状态、读数看起来「12/13 一致」的伪绿；改完立刻删掉旧路由表与旧读数 jsonl 重生成。**CDP 的 `Page.addScriptToEvaluateOnNewDocument` 只对当前 target 生效**：`new_tab` 打开的是新 target，错误采集恒为空 ⇒ 采集器与冷导航必须同 tab（`goto_url('?cb=<n>#<route>')`）。
**★ A/B 扫描要分块 + 增量落盘**：无头 session 会在长扫描中途断线（实测两次），单次全量必丢读数 ⇒ 按索引区间分块（`N` 走 globals）+ 每块把读数 append 进 jsonl，断线只丢当前块。比对口径：`#app` 的 innerHTML 逐字节 + 长度 + 三路报错（`console.error` / `window.onerror` / `errorHandler`）计数。
**★ A/B 读数两道闸：稳定性闸门 + 有效性判定（缺一项就会把假差异写进报告）**
① **稳定性闸门**：每条路由等 DOM settle 后连读 `(#app 长度, 元素数)`，**连续两次一致**才落盘 —— 只读一次会把「渲染中途」的中间态当结论（实测同路由 6331 vs 2903，深度复测后 5338 == 5338）。
② **无效读数剔除重跑，不得当结论**：连接濒死 / 渲染进程崩溃期的读数极小（我方侧 284 B 一类）、双侧同为极小值 ⇒ 判 `INVALID` 并在台账标注分母；历史基准里本就是 bogus 的读数（两侧 `no close frame`）在首次有效读数出现后要撤掉旧结论。
③ **异常路由先复测再定性**：个别路由报大差 ⇒ 对它单独做「最多 N 次读、要求连续两次稳定」的深度复测；复测相等 = 采样噪声，不是缺陷。
④ **单 tab 复用 + 每路由回收**：每路由新开 tab 会把浏览器守护进程搞崩（渲染进程崩溃/内存）—— 改为**复用同一 tab、CDP hook 只注册一次、每路由导航到 `about:blank` 回收**，并缩小批量（每批 4~10 条）。守护进程仍卡死 ⇒ **换浏览器会话名**（新 daemon），**不 kill 任何进程**。
⑤ **A/B 服务编排纪律**：端口 ↔ 目录**一一对应**（新产物上新端口，绝不同端口换挂目录）；核对端口归属用 `PowerShell Get-CimInstance Win32_Process` 取 CommandLine（`wmic` 可能无输出），**只按 PID** 停自己起的服务，原厂/基准端口一律不动；要**就地重建被占用目录**时先记录「端口 + 目录」，重建后**按原样在同端口同目录重启**，并实测 `http=200` + 入口文件字节数 == 磁盘字节数（「恢复原状」要有读数，不是口头）。清理时 `taskkill` 在 cmd.exe 下**不能带 `MSYS_NO_PATHCONV=1` 前缀**（cmd 不认 POSIX 变量赋值，会报「不是内部或外部命令」而**静默不清**）；带管道的核对（`wc`/`grep`）走 `terminal`(bash)，`execute_code` 的 subprocess 是 cmd.exe、没有这些工具。
**扫页干净 ≠ 补完**：模板悬空名藏在未触发分支里（隐藏面板事件、`v-if` 假分支），必须再用 compiler-sfc oracle（扫编译结果里的 `_ctx.X`）单独盘一次，**「运行期真缺陷 = 0」与「oracle 悬空名 = 0」两个数同时给出才算过**。悬空名修法按用法形态分派（i18n / ref / reactive / 组件），孤儿子组件用假 manifest 驱动注入器补 `<script>`，生成物还有 `defineProps`/`defineEmits` 空 + `expose` 形参位裸标识符三处留白 —— 全在 `references/vite-dist-to-sfc-rebuild.md` 第五节与第十二节。

**★ vendor chunk 的「映射 npm」几乎是错的，默认端口化**：dist 侧导出别名（`vue-i18n` 的 `c`、`vant` 的 `F`、`vue-router` 的 `s`）与真包导出名**没有对应表**，映射到 npm 必报 `"X" is not exported by <pkg>`；端口化成 `src/runtime/*.ts` 则导出名沿用原别名 ⇒ 零猜测且可构建。唯有 `vue` 例外（别名表可由实证取得）。
**同族的静默变体（构建全绿，只有 DOM 差分能看见）：原厂内联的第三方整包被换成「同名 npm 包 + 转发 shim」⇒ 该库在页面里从不初始化**。判据 = 挂载节点只剩我方模板的空壳 —— **缺库自己加上的标记 class**（实测原厂 `class="pdf pdfjs"`、我方 `class="pdf"`），且库生成的后代 DOM（loadingBar / pageNum / viewerContainer …）一个不剩；三路错误钩子全 0、无任何报错，长度差就是全部症状。修法 = **把原厂 chunk 里那份 vendor bundle 逐字节落成 `src/runtime/<原名>.js`，原 import 别名保持不变**（`import { P as E } from "./pdfh5.7858a0e3.js"`），语义与原厂完全等价；不要用 `import * as m from "<pkg>"` + `m.default ?? m.X ?? m` 这类 shim 去凑（实测 1141 B shim 指向 npm 包 ⇒ 页面只剩空壳：同族包的入口形态/worker/CSS 差一点，库就静默不干活）。**判 shim 是否生效看 DOM 里有没有库的标记 class，不看有没有报错。**
**★ 每批修复后 A/B 必须全量重跑并与上一批读数逐路由对照**（只验触发怀疑的那条路由会放过别处退化）；读数表同时给 Δ、diff 块数、白屏数、三路错误计数。**跨批对照有前提：抽取口径必须一致**（是否含 `#app` 外壳元素、选择器、结算时长、路由表）—— 口径变过（实测某一批的抽取不含外壳）⇒ 跨批数值**不可比**，只能比**同批内 Δ**；下结论前先用一条已知 PASS 路由做口径自检（同路由同批 Δ==0、跨批却差一个量级 ⇒ 口径变了，不是回归） —— **Δ 大幅收敛后剩下的块若全是「库差异」（`--alone`/`autocorrect` 这类各版本都无的特征），就停止投入并登记，不要再改结构**。
**★ 端口化模块里没定名的 vue 别名：与真包跑「同一行为电池」取唯一匹配**（禁猜、禁按名字相似度硬套）。电池 = `__v_isRef/__v_isReactive`、调用返回类型、对象 `name/keys`，覆盖真包**全部**导出后逐位比对。实测四例：`F→vShow`（name/keys 完全一致）、`v→hasInjectionContext`（真值表逐位吻合）、`r→ref`（`r({a:{b:1}})` 内层是 reactive ⇒ 非 shallowRef；`r(()=>1)` 非 readonly ⇒ 非 computed）、`s→setupDevtoolsPlugin`。**投喂必须是真对象**（真包的 `ref/reactive/readonly/shallowRef/vnode`）：vue 的私有标志是 Symbol-keyed，手搓 `{__v_isReactive:true}` 一律无效。
**★ 电池的「判别力」三条硬约束**（跑出大量歧义时先补判别力，禁硬猜、禁按名字相似度硬套）：
① **指纹必须含 `f.name` 与 `f.length`，且所有取值都要安全字符串化** —— `'' + vnode.type` 在 Symbol 上直接抛错、被 try/catch 收成同一个 `E` ⇒ `createCommentVNode`/`createTextVNode` 这种同族永远分不开；用 `String(v.type)`（或 `v.type.description`）才恢复区分度。
② **必须有恒等判定**：`f(o) === o` 才能拆开 `markRaw`/`reactive`/`readonly`/`toRaw` 族（只看返回类型全是 object）。
③ **必须捕 `console.warn` 文案**：生命周期钩子（`onMounted` 族）行为与返回值完全一致，只有告警里的钩子名能区分；`inject`/`provide`/`resolveComponent` 同理。
**★ 先量导出面再谈映射**：别名 chunk 与真包的同名模块，其「导出总数 / 函数导出数」应逐位相等（实测两侧同为 159 / 132）= 双射成立的前提。**不要按文件名认定哪个 chunk 是 vue 运行时**：实测 `vue.<hash>.js` 只导出 1 个键，真正的 vue API 在 `@vue.<hash>.js`。
**★ 同源比对靠重建工程自己的 `public/`**：把别名 chunk 拷进 `public/`，页内一次 `import('/_probe_alias.js')` + `import('/@id/vue')`（或 `/node_modules/.vite/deps/vue.js`）同时拿到两侧 —— 普通静态服务器不发 CORS 头，跨源 ES module import 直接失败。探针文件**交付前必须删**。现成脚本 `scripts/vue_alias_battery.js`。
**★ 未解析的别名一律不许按原样写进 import**：`map.get(alias, alias)` 式回落会产出 `import { at as c } from "vue"` ⇒ 绑成 undefined、页面静默错渲染，比裸引用更难查。注入器必须「先解析后注入」，并把无法定名的清单单独报出来；构建期 `"X" is not exported by <pkg>` 就是天然护栏（构建转红是好事）。
**★ 未还原 import 的权威依据是「原厂 chunk 自己的 import 表」，不是文件里的 TODO 注释**：`import{X as Y}from"./Z.js"` 给出完整的**本地名 → (模块, 导出名)** 映射。反编译器 TODO 有**至少两种句式**（`未还原模块 ./X.js（本地名 a，导出 n）` 与 `无法验证 <pkg> 的导出（本地名 X，导出名 Y；…）`），只认第一种会整类漏掉（vant 这类全走第二种）。**标识符正则必须写 `[A-Za-z_$][\\w$]*`** —— 用 `\\w+` 会静默跳过 `$`/`$t`/`$e`/`$a` 开头的别名，症状是运行期 `ReferenceError: $t is not defined` 而 TODO 清单里明明列着该项。
**★ 反编译产物里长得像模板的文本可能只是注释载荷**：`createCommentVNode(' <span>{{ $t("…") }}</span> ')` 里的插值**不求值**，不能当「模板需要该绑定」的证据；判「活表达式」还是「注释字符串载荷」看它是否落在 `createCommentVNode(...)` 的字符串实参里。绑定需求只以脚本段的真实调用为准。
**★ 长脚本不要内联进工具调用体**：工具调用体会被上下文压缩器插入标记而截断/污染 ⇒ 一律落盘再 `exec(open(path, encoding='utf-8').read())`。**但依赖 helper 注入的 `browser_exec` 是例外**：`exec()` 会丢 helper 注入（`new_tab` 未定义 ⇒ 返回 `mine=0/orig=0` 的假一致）⇒ 必须内联，因此内联体要**保持紧凑**（≈1.5 KB 以内；不写长三引号 JS 块，JS 用单行拼接/短 `+` 串接；长逻辑拆成多次调用、中间值落盘 json 传递）—— 压缩器插标记会截断调用体，症状是 `SyntaxError: unterminated triple-quoted string literal`，那是**代码根本没执行**，别当逻辑 bug 排查。**扫源码树的 grep 一律限定文件类型**（`--include=*.vue --include=*.ts`），压缩产物/bundle 只 `-c` 计数：不带限定会把整份 `*.min.css` dump 进结果，读数被降级、真值丢失。**bundle 一律禁「内容 grep」** —— `grep -rn "component("` 会命中单行数 MB 的压缩行，把整段结果打成噪声、真值全丢（记录被降级）⇒ 先 `-c` / `files_only` 定量，再定点读窗口。**判「某字符串在不在 bundle 里」必须用带引号的精确串 + 计数**：拿短模式做 alternation（`c_w`/`c_t`/`c_b` 这类在压缩代码里满地都是）会大量误命中，直接得出「原厂也有」的假结论（实测把运行期拼出来的组件名误判成两侧都存在，白绕一轮）。**含反斜杠的脚本同样不要走 heredoc**：本机 bash 的 heredoc 会吃掉一层反斜杠（正则字符类到手变 `unterminated character set`）⇒ 探针一律 `write_file` 落盘再跑；脚本里必须表达反斜杠字面量时用 `chr(92)` 拼。
**★ 运行时 DOM 差异先怀疑依赖库版本差 —— 定版只认「原厂 DOM 判据 + 全路由读数」，不认源码考古（recipe `references/dependency-version-fingerprinting.md`，探针 `scripts/dep_version_probe.sh`）**：**未声明**的 prop 会透传成 DOM 属性、声明过的会被消费 ⇒ 原厂 DOM 出现某个「本库不该有」的属性（对象值字符串化成 `[object HTMLDivElement]`）即说明原厂那版**没声明**它 ⇒ 用 `npm pack <lib>@<v>` 逐版解包 grep 特征 prop（`package/es/<comp>/<Comp>.mjs`）把版本夹到区间，再**装回候选版 → 重建 → 全路由冷加载读数**，取总差最小者；读数变差就**回滚**（实测 4.6.0 比 4.6.3 总差多 180 字节）。特征在**所有**版本都 grep 不到（如 `van-cell__value--alone`）⇒ **不是版本差**，是原厂自研/补丁层，停止考古。改依赖前必须备份 `package.json`/`package-lock.json`，定版后**全量重测**（定版会改所有页的产物，只验触发怀疑的那条路由不算）。
**★ 真包 vue 不导出 `setupDevtoolsPlugin`** —— 它来自 `@vue/devtools-api`（pinia/vue-router 的真实依赖，装得上、导出可得），chunk 里自带该实现的证据是报错含 `enableEarlyProxy`、用法是 `{id,label,logo,packageName}` 描述符。按包判定来源，别硬塞给 `vue`。
**★ 「只导出 1 个名字、值是整包命名空间对象」的 chunk 要写 `import * as X from "<pkg>"`**：写成 `import { r as X } from "vue"` 必炸（`r` 那名字只在该 chunk 的私有导出表里存在）。判据：该 chunk 导出表长度=1 且导出值是含 100+ 键的对象。
**★ runtime 端口化产物的文件名必须每 chunk 唯一**：两个 chunk 都叫 `index.<hash>.js`，stem 截成 `index` ⇒ 同写 `runtime/index.ts` 互相覆盖、再被 barrel 覆盖 ⇒ **两个主模块全丢**（构建能过、功能静默缺失）。stem 一律取「完整文件名减 `.js`」。
**★ 路由懒加载是动态 import，必须与静态引用一起改写**：`() => import("./page.<hash>.js")` 要按 manifest 反查改指 `@/pages/x.vue`（不改则构建直接失败，改完模块数从十几跳到几百）。
**★ 反编译器的 vendor 判定是模板塌成 ~50 B 桩的根因**：判定按 import 源匹配 `vendor.@vue` 之类，套内命名不同（如 `@vue.cc2f9ce9.js`）就不命中 ⇒ 别名表空。修法 = 名表带上 `vendor`/`vendorMap`，不是换名表。
**★ mono / 单块 chunk 的主组件拿不到别名表**（实测输出 51 B 桩、`主组件别名表: (空)`）：该 chunk 的路由表、store、App 组件要**手工从 chunk 抽取再手写**（App 桩里凭猜写的 `<van-loading>` 是臆造，真渲染是 `router-view` + `show` 标志）；同 chunk 的兄弟组件走 `--comp=X --name=X` 可正常出。
**★ 多套复刻的管线手册**（逐套配方派生、`gen_runtime.js` 实参口径、注入/端口化/构建闸门顺序）见工程内 `D:/渗透/_t5/PIPELINE_tao.md`（ras-admin / otc-page 双套实证）。

**★ 第八类：原厂「注释载荷」被反编译器泄漏成活动 DOM（死标记）**。原厂 render 里 `k(\` <template #finished>…\`)` = `createCommentVNode(字符串)` ⇒ **渲染成注释节点、内容永不求值**；反编译器若把字符串里的 `<template #slot>` / HTML 片段还原成真插槽/元素，就渲染出原厂没有的 DOM（且补 scope 反而更错）。判据 = 从原厂 chunk 提取「落在字符串/模板字面量内的 `<template #slot>` 或 HTML 片段」清单（手写字符串扫描器，别用嵌套正则），逐项回我方源码对账；修法 = **还原成 HTML 注释**（与原厂一致）。**幂等守卫的正确判据是「该位置是否处于未闭合注释内」**（数 `<!--` 与 `-->` 的差），**不能用「前 8 字符有没有 `<!--`」这种窄窗口** —— 外层注释可能隔好几行，窄窗口查不到 ⇒ 二次包裹会把外层注释提前闭合、冒出孤儿 `</tag>`（实测 `bad=1 Invalid end tag`）。同族：源码里本来就是注释形态的死插槽，正确动作是**跳过**、不是再包一层。
**★ 注释载荷回填「按位置配对」会静默毁页（实测 BUILD_EXIT=1 `[vite:vue] Element is missing end tag`）**：从双侧 DOM 抽 `<!--…-->` 文本后，即使**注释条数相等**也不能用 zip 按位配对回填到源码 —— DOM 注释顺序与源码顺序可能错位，且源码里一个锚点可能对应多个语义不同的目标 ⇒ 一条 640 字符的「被注释掉的整段 DOM」被插进了错误的注释锚点，把本该活动的 `<van-field>/<van-icon>` 连同 `</div>` 全吞进注释（注释体里含 `</van-field>` 之类时 SFC 解析直接崩）
  - 正确判据三层：① 目标必须**锚点唯一**（该 `<!--文本-->` 在**模板段**内出现次数 == 目标数）；② 锚点在源码里 0 次命中时**一律 skip 并记数**，不得回落成「按位置取第 N 个」；③ 多义锚点（同一文本对多个目标，如 ` comment ` 4 处对 4 个不同目标）只允许**同语义族内按序配对**，且必须重建后冷加载复核字节账。
  - **真源必须与源码同版**：一旦某一批回填已 APPLY，之前采集的 DOM 就**不能再拿来对源码做文本替换**（源码文本已变 ⇒ 命中 0 或错配）。顺序固定：改源码 → 重建 → 重新采集 DOM → 再比对下一批。
  - **工具调用被中断（app/后端停掉）时可能有「孤儿执行」已部分落盘**：读到的文件状态可能是半成品。恢复后第一件事是跑**廉价完整性闸**（`npm run build` / `sfc` 解析）；本类崩溃点定位极快 —— 报错直接给 `file:line`，恢复手段 = 从备份 `cp` 单文件 + **幂等重放**已定档的确定性修复器（DRY→APPLY 均报 0 处即回到事故前状态），禁止手工编辑修复。
**★ 插槽 scope / 组件别名的修复器三条纪律**（三条都踩过）：① 插槽体候选扫描必须用**代码视图** = 只保留绑定表达式（`:x`/`v-`/`@`/`#`）与 `{{ }}` 插值内容、剥字符串字面量与静态属性值 —— 整段 `strip_literals` 会把属性绑定表达式一起剥（`slot_scope` 归 0）；② 代码视图**不得再对纯文本做收尾清理**（会把 `[expr]` 括号内的表达式也抹掉、候选恒空）；③ `script_declares` 必须先剥**字符串字面量**（假阳：`"payment.FPS…"` ⇒ `#cancel="payment"`）与**注释**（假阴：`// - 未找到来源的标识符: o` 让 `o` 被当已声明）。
**★ runtime 导入 key 的真源是「导入它的页 chunk 的 import 表」**（`import{KEY as ALIAS}from"./MOD.js"` ⇒ KEY 才是该模块的正确导入 key）：**不是模块文件自身**（模块不导入自己、取不到 key）、**不是名字相似度**。硬编码 `import { t as X }` 会造出 `Identifier 'X' has already been declared`（实测模块只导出 `v`，原厂用 `v as`）；`"t" is not exported by …` 是天然护栏。去重/修剪时**保留 key 与真源一致的那行**、删其余；名字已声明 ⇒ **只改模板标签、不加导入**；误删的导入要按真源补回（实测 3 处 key 改写 + 13 条补回）。
**★ 批改脚本伤害自己 ⇒ 每次 APPLY 后必须重跑三闸并留外科修复脚本**：本轮 APPLY 自造两个缺陷（重复 import、注释内二次包裹）。三闸 = ① 模板编译（`tpl_check`，`bad=0`）② 编译器 oracle（双 `.value` / 悬空名 / `COMPILE_THROW`）③ 修复器**幂等复跑 = 0 处**。修法一律写成**幂等的外科修复脚本**（如「删掉 key 与真源不符的重复行」），不要手工编辑。
**★ 第九类：纯字符串资产引用不会进 dist（图数相等 ≠ 引用完整）**。源码 `var G="./assets/x.png"`（非 `new URL`/`import`）时打包器不收它 —— 原厂是靠「文件放在 web 根 `assets/` 下、按相对路径取」成立的。修法 = 扫全库 `["']\./assets/([^"']+)["']` 并把原厂同名文件复制到 `public/assets/`（原样进 dist、路径与原厂一致）；**判据是产物「引用 → 文件」完整性检查（缺失目标 = 0），不是图数相等**（实测图数 69=69 仍缺 41 张）。**扫描正则会把 `onerror="javascript:this.src='../assets/x.png'"` 里的相对路径一并抓进来**（`../assets/` 含 `./assets/` 子串）⇒ 这类只在内联 JS 字符串里出现、原厂侧同样不存在的引用**不是缺口**，判缺口前先回原厂目录核一遍该名字是否存在。
**★ 模板段 / 脚本段边界：取 `<script>` 之前「最后一个」`</template>`**。用 `</template>\s*$` 判末界时，「模板在前、脚本在后」的 SFC 会让 `tpl` 吞掉整段 script（`tpl=(10,16257)` 与 `script:(5906,16257)` 重叠）⇒ 所有模板级修复实际改的是脚本段、静默无效。

**★ 第十类：模板临时量被写回 ctx 成员的致命族 + 五个同族保真缺口**（app-page 实证，`distA13` 前 6668 vs 原厂 21112 早崩）：
① **致命形态**：反编译器把渲染函数里的局部临时量还原成**模板里的裸标识符赋值**（`(_=u)` / `(b=…)`）。Vue 编译期为未声明标识符加 `_ctx.`，而**生产运行时 `ctx._` 是实例内部槽位** ⇒ `_ctx._ = u` 写入即毁实例指针，报 `Cannot destructure property 'ctx'/'data' of 'e'`，整页崩且与 API 层无关。判据 = 扫**模板绑定表达式**中对裸标识符的赋值（`(name=…`），剔掉字符串字面量内的假阳；**修法 = 在 `<script setup>` 顶层声明 `let name;`**（编译器改发 `$setup.name`，不再写 ctx），非 setup 页不得注入。修复器要**幂等 + 可回滚**（注入行带 `[decomp-temp]` 标记 + 独立 `rollback_decomp_temp.py`）。实测该页修后 `21112 = 21112`、d=0。
② **声明集合必须由解析器给，禁止正则扫源码文本**：跨行多重声明（`const Z = s(86),\n    D = s("86"),`）、对象字面量 / 箭头函数体里的 `;` 都会把 `[^;]*?` 式守卫截断 ⇒ 漏判已声明 ⇒ 注入重复 `let` ⇒ babel `checkLVal` 构建炸（同一坑连踩两次）。正解 = `@vue/compiler-sfc` parse + `@babel/parser`，**只收脚本顶层绑定**；递归收集会把函数体内 `var t,d,p,c,i` 也算进来 ⇒ 过度包含 ⇒ 恰好漏掉最要命的名字。
③ **声明集合必须在「回滚后的干净树」上采集**：在带注入的树上采集会把上一轮注入的声明当成既有绑定 ⇒ 命中 0 处（假阴性）⇒ 白干一轮。
④ **`v-show` / 组件 wrapper 丢失族**（build 全绿，只在 DOM 差分里现形）：原厂 `withDirectives(...,[[vShow,cond]])` 与 `h(Popup,{show:D.value,…})` 被吞掉 ⇒ 本应隐藏的元素以**裸块**渲染（实测 +79：多出 `div.top`/`div.content`）、本应带 `style="display:none"` 的元素裸渲染（实测 −39）或子节点**从 wrapper 泄漏成兄弟节点**。判据 = 标签序列 difflib 定位 + 回读原厂 chunk 的 `withDirectives`/`h(组件,{show:…)` 原文核绑定。
⑤ **相邻插值丢表达式 ⇒ 只剩空格**（实测 `div.Language` 内 `{{ i(m)+" " }}` 的 `m` 未初始化 ⇒ 渲染成一个空格、d=−1）：真值取原厂 render 原文 `Q(i(m.value)+" ",1)`。
⑥ **Vite `transformAssetUrls` 会把模板里的纯字符串 `./assets/x.png` 哈希成绝对 URL**（原厂保留相对路径 ⇒ 逐字保真会差一截）；要复刻原样就在 vue 插件里关掉该 transform。**改配置后必须回产物取证**：该页 chunk 不得再有 `src:<导入名>` / `new URL("<hash>.png", import.meta.url)`（应是字面量），同路由 DOM 该属性逐字相同；DOM 里的**带 hash 文件名**即证明对方 URL 是我方构建生成的。实测出现过「配置行已写进 `vite.config.ts`、产物照旧」⇒ 先确认本轮构建真的重跑了（产物 mtime 晚于源码 mtime，`BUILD_EXIT` **落盘后 grep**，`tail` 会截掉 exit 码），再查第二份配置文件 / 第二处 `plugins`。
⑦ **`<template>` 与 `<script setup>` 之间的块外残留不影响构建、只污染产物**：旧世代修复器把模块级字面量插错了块（实测同一文件 4~8 份重复、全库 188 处）—— SFC 解析容忍块外文本 ⇒ 构建全绿。纪律：补声明的修复器落点判定必须是「`<script setup>` 开标签之后」+ 落完自检两块之间无非空白；换代时 `grep -c` 旧标记审计历史产出（期望每文件 1 处）。
⑧ **可逆别名编码的标签会「成品化」留在源码**（别名解析被跳过，注入日志 `SKIP … 别名 _x24 -> None（未处理）` 是其信号）：源码里留着 `<C__x24 :anout=… :show="!0" />`，DOM 出 `<c__x24>` 假元素。修法 = 按**原厂 chunk 的 props 签名**回真组件（本案 `titleBlock`），细节见 `references/vue-tag-and-component-resolution.md` §2。
**★ 第十一类：丢掉的别名 import ⇒ 模块级自由变量（两种签名，修法同源）**（完整取真名流程见 `references/lost-alias-binding-rebind.md`，扫描器 `scripts/freevars.cjs`）
① **先分类**：裸别名出现在**模块顶层**（`$.configure(...)` 在 App/runtime 模块作用域，不在组件内）⇒ 一个 `ReferenceError` **打断整包挂载**，**所有**路由 `#app` 长度 0（报错签名 `assets/index-*.js:LINE`）；出现在**页面 chunk 的 setup 里** ⇒ 只有该路由渲染成空壳（长度几十字节 / 1 个元素）。顶层型**不要拿去查模板**，它不是模板缺陷。
② **权威清单两个，顺序固定**：反编译器自己的未还原台账（`_script_report.json` 式）已逐条给出「本地名 / 模块 chunk / 导出名」，两种句式都要认（`未还原模块 ./X.js（本地名 ke，导出 b）` 与 `无法验证 <pkg> 的导出（本地名 X，导出名 Y）`）——它是**全局计数、不带文件位置**，只当清单用；再回**原厂 chunk 顶部 import 表**取「本地名 → (chunk, 导出名)」全表（`import{N as $}from"./nprogress.59272c9a.js"`）。
③ **落点靠自写的 per-file 自由标识符扫描**（`scripts/freevars.cjs`）：`<script>` 段 + `@babel/parser`，自由 = 引用 − 本文件全部绑定 − 全局白名单；**不要依赖 `@babel/traverse`**（多数工程没装，会白等一轮）。**引用正则必须含 `$`**（`[A-Za-z_$][\w$]*`），否则整类漏。
④ **真名是「同一 vendor chunk 的全局常量」**：工程里任一文件已有成功的 `import { showToast as wt } from "vant"` ⇒ 固定 (vant chunk, `T`) → `showToast`，其余文件照此回填；chunk 尾部 `export{er as a, rr as b, tr as c, nr as u}` **只给公开混淆名**，真名只能来自「已成功那行」或按库语义读 chunk 实现（vue-router `u`=useRouter / `b`=useRoute：看局部函数体注入的是 routerKey 还是 routeLocationKey）。**禁按名字相似度猜**；构建期 `"X" is not exported by <pkg>` 是天然护栏。
⑤ **回填用真包真名 + 统一重命名用法**：`import NProgress from "nprogress"` 且两处 `$.configure` 一并改成 `NProgress.configure`（`replace_all`），比再造 `import { N as $ }` 好读、不新增裸别名。
⑥ **修完必须整轮逐路由冷加载复扫**：修掉顶层那条只解开挂载；页面 chunk 的下一批自由变量会在导航到各路由时逐个冒出来（实测 `$` → `Ct` → `ke` 连环），每路由落盘 (`len`, 元素数, `window.onerror` 文案) 才算收敛。

**★ 第十二类：注入/回填的绑定表达式必须过「根标识符已声明」闸（自造白屏，最贵的一类）**
把绑定回填进模板（`:src` 值、`v-if` 条件）时，**表达式里的根标识符必须是本文件 `<script setup>` 里已声明的绑定**。原厂 chunk 的别名与本方脚本**不保证同名**：原厂 `WRAP(ALIAS).routerData.bg` 里的 `ALIAS` 是它自己的 store 局部名，本方要么根本没有这个绑定、要么它是别的东西 ⇒ 实测两页注入后**整页白屏**（`#app` 只剩 122 B / 0 元素），而 `vite build` 全绿、0 报错。纪律：① 注入前逐条解析「条件根标识符 ← 本方脚本绑定」，**解析不出就不注入**（保留未接线、记进台账），绝不放一个会抛错的表达式进去；解析出的 store/ref 一律改写为**本方**变量名（本方 `X = HOOK()` 才是 store，别抄原厂字母）。② **自伤定位法（比读堆栈快）**：怀疑某次注入导致白屏 ⇒ 从「注入前备份」**只回滚该文件** → 重建 → 冷加载 A/B 看是否恢复渲染（实测回滚后两页立刻恢复 2499 B / 1918 B 真内容）。③ A/B **双侧同为极小值**（7/7、126/126 这类）判 **INVALID/BOGUS，不计通过**（正常页是 KB 级），台账分母要如实标注。④ 原厂条件分支恒 false 时，我方补的 `<template v-if>` 分支体只能是占位 ⇒ DOM 等价但属**已知语义缺口**，必须显式登记，不得写成「已修复」。

**★ 第十三类：重建源「少了 setup 尾部」⇒ 声明里的数据从未被覆盖（同一份列表在 chunk 里出现两次）**
原厂 chunk 里同一份数据常出现**两次**：组件顶部的声明（`d=c([…])`，初始值）与 setup **尾部**的重赋值（`return <hook>(()=>{st(),ot(),d.value=[…],document.title=…,S.value=…})`）——**渲染真值是后者**。只 grep 到第一处就下结论 ⇒ 永远对不上 DOM（实测我方列表 7 条 vs 原厂 8 条，且其中两条各用了错图标：1188/788 vs 原厂 1648/1384）。两条纪律：
① **收口前先做「尾部对账」**：把原厂 chunk 从 `return <hook>(()=>{` 到 render 函数之前整段，与**我方 `<script>` 的最后一行**逐行对齐 —— 重建出的 SFC 常整段丢掉这段（含 `Q.value=$ViewHeight(...)` 这类一次性赋值），而 `npm run build` 全绿、页面照常渲染，只有逐条 DOM 差能现形。
② **定位靠逐条指纹对齐，不靠总长度差**：取重复结构锚点（每条的外层 class）切条，逐条抽「文本标签序列 + 资产 base64 字节长」，按索引对齐打印 ⇒ 一步落到「第 k 条、哪个常量/字段」；回填时**常量直接从原厂 chunk 正则抽取，禁止手抄 base64**（手抄是静默失真源）。
**Hook 别名静态定名法**：在 vue 桶 chunk 里找 `export{<内部名> as <字母>}`，再找 `<内部名>=<hook工厂>("<字母>")` —— 该字母就是 Vue 内部 LifecycleHooks 键（`m`=onMounted、`bm`=onBeforeMount、`u`=onUpdated…）；桶的重导出链断了就直接定位 hook 工厂本身的定义。
**★ 断言口径升级：命中数断言拦不住「语法坏行」**：改 import 列表这类**字符串切口**时，`s[:-7]` 式切除会把语句拼成 `import { a, b } from, c } from "vue";` —— **期望子串在、命中数对、逐项断言全过，而文件语法非法**（实测直接从 build exit 1 才暴露）。纪律：① 改语句一律**整条语句替换**（正则锚定整行、整体重写），**禁止按偏移切片再拼接**；② 除命中数外必须加**形态断言**（该行须匹配预期完整正则）或**语法闸门**（紧随的构建，`BUILD_EXIT` 落盘后 grep —— `tail` 会截掉 exit 码）；三道都绿才算 APPLY 成功。

**★ 尾差收敛纪律：字节级差分驱动，禁止「全局猜测式改写」**（细节与脚本见 `references/byte-delta-convergence.md`）
① **两侧 DOM 先落盘，再字符级差分**（`difflib.SequenceMatcher` 逐 opcode，`insert/delete` 带前后 40 字符上下文，只打前 6 块）：长度差是症状，opcode 才是病灶 —— 把「Δ=−23」读到「正好缺 ` style="display: none;"`」这一步再动手。
② **判据永远是「同路由的原厂 DOM」逐站形态，不是编译规则推理**；一次性全局改写（行合并器 / 去注释器）会**过度修正** —— 同一批「多余空格」里既有真偏差、也有原厂确实渲染空格的站点（实测把 −1 削成 −6）⇒ 整改一条就重建一次、复测该路由，超削按差分回补。多出来的空格还可能来自 **i18n 词表值本身**（词表带尾随空格）而非空白文本节点，两处都要查。
③ **注释就是字节**：本类工程编译保留注释 ⇒ 原厂被注释块的文本必须**逐字回填**（从原厂 chunk 的反引号模板字面量取全文并手写反转义；压缩后 `createCommentVNode` 是别名，别用函数名正则抓），且**绝不能用 HTML 注释当我方修复标记**（标记自身进 DOM 变增量）—— 标记改走 `<script setup>` 的 `//` 注释或独立台账 json。
④ **守卫必须带唯一区分项**：同一属性/片段在文件别处也出现时，宽守卫会**静默返回「已应用」而真改动从未落地**（实测 img 的 `v-show` 被同串的另一个块挡掉，Δ 原样保留）⇒ **「已应用」不是证据，重建后必须再差分确认该字节真的出现**。
⑤ **修复器分代，换代即退役**：守卫以 MARK 存在与否判定（不得以「锚串是否还在」判定）；**撤掉旧 MARK 却仍在闸门里跑旧修复器 ⇒ 旧修复器认为自己没干过，会把注释/包裹再插一遍**（实测静态修复器在重建闸门里回填了刚清掉的注释）。闸门只跑当前代修复器的 DRY，「当前代 0 处」才算幂等通过。
⑥ **wrapper / 指令修复后必须数「开/闭标签对」**：只删重复的闭标签会留下「开 1 / 闭 2」的自嵌套，而 DOM 的属性计数照样对得上 ⇒ 残余藏在结构里（`grep -c '<X'` 必须等于 `grep -c '</X>'`，并与原厂嵌套层级对照）；`v-show` 族**同时命中普通元素与块级 wrapper**，以原厂 `withDirectives` **全集**逐条比对，别只看 `display:none` 计数。
⑦ 闸门里的观测量本身也会骗人：粗 `grep -c '\.value\.value'` 会命中 vant 的 `a.value.values`（属性名含该子串）⇒ 双 `.value` 只认 compiler-sfc oracle。
⑧ **`style` 静态属性 ≠ `:style` 绑定：只有后者走运行时 `patchStyle`，简写属性会被归一**（实测原厂 `style:{flex:"1"}` 渲成 `flex: 1 1 0%;`，我方静态 `style="flex:1"` 逐字保留 ⇒ 每处差 6 字节）；凡带简写/多值 CSS 的属性一律改 `:style` 对象绑定，再把对象序列化形态与 DOM 逐字对齐（`{height:"72vh",width:"100%"}` ↔ `height: 72vh; width: 100%;`）。
⑨ **幂等守卫的判据同样只能取自「本方文件自己的文本」**（不只是锚串）：按原厂形态假设写 `'P.value' in t` 这类守卫，而本方模板写的是 `Number(P)+"44"` ⇒ **守卫恒假**，脚本照打「已应用」却一处未写（实测 5 项里 4 项落空）。守卫/锚串一律用本方实测文本，且 APPLY 后逐项 `grep -c` 复核命中数 == 预期。

**★ 宿主型渲染层（Electron 桌面壳）不得用纯浏览器 A/B 验收**：渲染层依赖宿主注入的 `require`/`nodeIntegration`，静态服务器下**两侧都会 `require is not defined`** ⇒ 双侧读数同为 0 是 **BOGUS 不是通过**。真宿主可**离线**搭：本机 `%LOCALAPPDATA%\electron\Cache\<sha256>\electron-v<ver>-win32-x64.zip` 直接 `unzip` 即得 `electron.exe`（不必 `npm i electron`）；宿主壳 = `BrowserWindow({show:false, webPreferences:{nodeIntegration:true, contextIsolation:false, webSecurity:false, preload}})`，preload 在页面脚本前挂 `window.onerror` / `unhandledrejection` / `console.error` 钩子，`did-finish-load` 后 `executeJavaScript` 取 `#app` innerHTML 落盘并打印错误计数与栈。**判据不止字节数**：数双侧「未解析的自定义元素」（原样留在 DOM 里的 `<c_menu>` 这类非原生标签）—— 原厂 0 / 我方 7 比长度差（2751 vs 66920）更快指向「组件注册链缺失」这类结构缺口。宿主读数一律写进宿主目录，**不得写进原厂只读 dist**；宿主壳目录自建 `package.json` 且**不要 `"type":"module"`**（否则 `require('electron')` 直接炸，须改 `.cjs`）。完整宿主脚本与判据表见 `references/electron-renderer-host-verification.md`。
**★ 宿主型渲染层的「端口三件套」缺任一 ⇒ DOM 大幅缺斤**（三者互不替代，必须各跑一次）：
① **占位（`<C_*>`）→ 逐字节端口**原厂 chunk（原厂本地子组件是同 chunk 内的变量引用，丢成名字标签就永远解析不出；**普查正则必须含下划线命名 `<C_[A-Za-z_]`**，否则漏 `<C__x24>` 这类）；
② **独立的依赖闭包补齐器** —— 页面已无占位就不再进端口计划，其依赖不会被顺带 port；匹配式必须覆盖**动态** `import("./x")`（只写 `from"\./x"` 会漏 ⇒ vite `Could not resolve`，而构建失败时宿主读的仍是旧产物 ⇒ 看到「读数没变」先查构建日志）；
③ **构建后置的 CSS 补齐器** —— 端口 chunk 里的 `__vitePreload` 仍按原厂 hash 名引用 CSS，而重建工程把它们静态 import 进入口、被 rollup 合并成单文件 ⇒ **preload 失败 ⇒ 动态组件整块不挂载**（症状：`#app` 掉一万+字节、只剩 CSS 报错）。逐字节从原厂 assets 拷回被引用未产出的 CSS 即可（本类最大单项收益）。
**★ chunk 归属（`.vue` → 原厂 chunk）必须确定性评分产出，禁止多候选择一**：判据 = **i18n key 交集**，退路 = 长标识符交集并打印各候选打分；交集为 0 且无同名 chunk 的页 ⇒ **报「未能映射」，不猜**。
**★ 怀疑「某端口模块有损」时用换入实验证伪，别反复读代码**：把该文件临时换成**原厂逐字节版**重建重测 —— 读数与错误集合一字未变 ⇒ 该模块被排除，缺陷在我方胶水层（实验后回滚，保留我方 port）。

**★ 「该换哪份 dist」是取证问题，不是偏好问题**：原厂**没有构建产物**时，唯一可用的保真判据是**与 `package-lock.json` / 依赖树的一致性** —— 干净树（传递依赖只有单一版本）重建出的产物才是保真版。作业树里混入的**嵌套 `node_modules`**（外层与内层同名包版本不同，实测外层 3.4.25 / 内层 3.5.43）会让产物**多内联一份模块**（entry chunk 偏大、模块数 +2），并**级联改名全部懒加载 chunk**（vendor chunk 改名 ⇒ 引用它的 chunk 全换 hash，实测一次 87 个）—— 这种版本漂移产物**必须换掉**。取证手法 = **可逆移动该目录**（移到旁边、不删）→ 重建 → 与 from-zip 全新构建逐字节对照 → 决定后再移回去。换过 dist 必须**重打 zip 并从 zip 解出复验**，旧 zip 留备份。

## 交付形态（重建工程的最后一公里）

重建完按固定四件套交付，**每个数都由机械提取生成，不写「已完成」这类话**：
`src/` + 构建配置（可 `npm install && npm run build`）· `dist/`（已验收产物）·
`README.md`（实测读数表 / 快速开始 / 环境变量 / 目录 / 二开必做）· `docs/架构分析.md`（启动链：pinia 必须第一个 `app.use`）·
`docs/API文档.md` · `docs/TODO清单.md`（残留台账）· `deploy/nginx.conf`（history 回落 + 静态长缓存 + 反代**服务/域名**，**不写 K8s 服务名**）。

- **API 文档必须走别名表**：重建后页面调用走导入别名（`import { cmsApi as C } from "@/runtime"` 后用 `C.xxx(`），
  直接按 `xxxApi.` 提取会得 0 行；先解析 import 建 `local → original` 映射再统计 `别名.方法(`。
- **生成器验内容、不验 exit code**：提取正则不匹配时照样 exit 0 并写出 0 行的「成功」文档 ⇒ 跑完立刻 `head` + 计数断言；
  文档里的路径先两侧 `replace(/\\/g, "/")` 归一（混用 `path.join` 与字面 `ROOT + "\\"` 会把绝对路径写进交付文档）。
- **凭据零残留**：`.env` 只列键名（`cut -d= -f1`）、按形态清单扫源码，命中要**看上下文定性**（表单字段名如短信通道 `*_secret_id` 不是凭据值）；
  交付说明写明「密钥二开时全部重生成，包内原厂那套作废」。打包与验包机制（zip 分隔符、`unzip -Z1` 验收）见 skill `gitbash-windows-toolchain-ops` §9。
- 内部脚本/中间报告归 `_internal/`，包体保持干净；**交付前再跑一次全量实扫**，把「真缺陷」与「AxiosError（未接后端）」两个数都写进 README。
- **交付包必须自复现**：验收对象是「交付出去的那份」，不是「我建的这份」—— 从 zip 解到全新空目录 → `npm install` → **干净 env** 构建（显式剔除各包专属口径，如某些包只认 `NODE_ENV=development`）→ **逐文件「名 + sha256」双向 0 差异**才算过；chunk 改名不构成差异（按「去哈希名」配对 + 抽样核内容）。配方与脚本骨架见 `references/rebuilt-project-delivery.md` §6。
- **清单只认双读数**：每包写**实测 sha256 + 文件数 + zip 条目数**，并逐包满足「磁盘文件数 == `unzip -Z1` 条目数」+ CRC 校验通过；重打后同步刷新清单与桌面副本，写明「每个数来自哪条命令」，**不得沿用上一版数字**。
- **已知项要如实登记，不当缺陷也不当已修复**：原厂侧本来就坏的页（自身报错 / `#app` 缺失 / JSON 解析失败）、运行时随机同长度 id（echarts 实例 id）、纯 CSS 的 `data-v-*` 差异、console 警告类别差异 —— 写进交付文档的「已知项」，并注明与上一批读数逐条一致（既有性质、非本轮引入）。

## 老版本功能/UI 装回新代码树：对齐口径与覆盖计数

旧一代程序（单文件脚本 / 旧前端 / 旧后台）被换成新模块树后，把它那一层的按钮、菜单、回调、待输入流程装回新树，并对「一比一」给出可核查数字。五条常驻纪律（判定器实现、别名三档、对拍表见 `references/legacy-surface-parity-verification.md`）：

1. **基准只认旧版正本，不认早年快照**：正本全量扫描结果才是分母 —— 早年 dump 常只覆盖正本的一小部分，在子集上跑出的「100%」是假结论。汇报写明基准文件、行数、去重入口数。
2. **覆盖计数分三档同出，不许只报一个数**：① 键/参数位对齐（命中键，余下为空或以 `:`/`{` 开头）② 靠短前缀吞掉（`aiexp` 落到 `ai`，语义待人工确认，**不算对齐**）③ 完全没人接。判定**按原始键形**比 —— 先把参数剥掉再比对会造出一堆假警报；别名表里的键属「有意的对齐」，要一起并进基准域，否则已处理的键仍被报成缺口。
3. **测试由正本扫出的清单驱动，禁止手抄键名**：手抄必然漏（实测手抄 13 个、正本 100 个）。让测试引用同一个取键函数，逐键真点并断言「有回音、不抛错」。
4. **断言失败先分清是谁的错**：离线 harness 存记录的形态常与产品代码的发送形态不一致（harness 存 dict 而断言按下标取 ⇒ `KeyError` 看着像产品崩；记录器签名接不住 `parse_mode` 这类位置实参 ⇒ 报「参数错」）。断言里带 traceback 尾部，先问「这行代码在谁的库里」，**先修 harness 再考虑碰产品代码**。
5. **换树必做状态/配置对拍（缺失即 fail-open）**：旧程序写过的每个状态文件与新树指向逐个对拍（真身名/大小/内容骨架 vs 新树配置的路径与期望形状）。读不到文件通常不报错而是**读成空** ⇒ 「读列表判权限」的闸门恒真（授权名册缺失 = 对全网开放），同族还波及收藏、监控关键词与广播/群发。兼容层两条铁律：**路径只回落不迁移、形状只兼容不搬动**，标量类型也保。

降级映射（新层没有等价状态时）必须在注释与汇报里**写明语义不一致**，不得计入一比一。
