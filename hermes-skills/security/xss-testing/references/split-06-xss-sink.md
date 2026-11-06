## 五、现代框架XSS与危险Sink审计

### 5.1 框架默认防护与逃生舱口
现代框架默认自动编码，XSS几乎只发生在"逃生舱口"（raw HTML插入API）——**审计时不用扫描所有插值，直接grep危险API即可**：

| 框架 | 默认防护 | 逃生舱口（危险Sink） |
|------|---------|---------------------|
| React | JSX自动转义所有插值 | `dangerouslySetInnerHTML`、`href={userInput}`(javascript:)、`React.createElement`动态标签名 |
| Vue | `{{ }}`自动转义 | `v-html`、动态组件`<component :is>`、`template`字符串编译、`$eval` |
| Angular | 插值与属性绑定自动消毒 | `bypassSecurityTrustAs*`系列、`[innerHTML]`、动态组件工厂 |
| Svelte | `{expr}`自动转义 | `{@html}`、动态组件 |
| AngularJS(1.x) | 沙箱（已废弃） | 模板表达式沙箱逃逸（见5.4） |

**grep审计命令（代码审计核心动作）：**
```bash
# React/Vue/Angular/Svelte 危险Sink全局搜索
rg -n "dangerouslySetInnerHTML|v-html|{@html}|bypassSecurityTrust|\[innerHTML\]|innerHTML\s*=|outerHTML\s*=|document\.write|eval\(|new Function|setTimeout\(['\"]|location\.(href|assign|replace)\s*=" src/ --type ts --type js
# 动态URL属性
rg -n "href=\{|\:href=|v-bind:href|target=\"_blank\".*href"
# 动态属性名/事件
rg -n "setAttribute\(|addEventListener\(.*user|\[[A-Za-z]+\]" src/
```

### 5.2 React危险模式
```jsx
// 危险：用户可控HTML直接渲染
<div dangerouslySetInnerHTML={{ __html: userInput }} />
// 修复：先DOMPurify再渲染
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(userInput) }} />

// 危险：javascript: URL（React不会阻止href协议）
<a href={userInput}>link</a>
// 修复：协议白名单校验
function safeUrl(u){ return /^(https?:|mailto:|#)/.test(u) ? u : '#'; }

// 危险：动态标签名（React.createElement(userTag)）
React.createElement(userControlledTag, {...})

// 危险：SSR/Next.js hydration JSON注入
// RSC/SSR将initial state序列化为内联<script>，若JSON未转义</script>即可逃逸
// 检测：页面源码中搜"self.__next_f"或__NEXT_DATA__的<script>包裹内容
// payload思路：值中注入 "</script><script>alert(1)</script>"
```

### 5.3 Vue危险模式
```vue
<!-- 危险：v-html直接渲染 -->
<div v-html="userHtml"></div>

<!-- 危险：用户可控模板编译（等于任意代码执行） -->
new Vue({ el: '#app', template: '<div>' + userProvidedString + '</div>' })  // NEVER DO THIS

<!-- 危险：动态组件名 -->
<component :is="userControlledName"></component>

<!-- 已知漏洞：CVE-2024-6783 Vue 2模板编译器特定指令模式XSS -->
<!-- Vue 2已EOL，建议审计时标注迁移Vue 3 -->

<!-- URL属性 -->
<a v-bind:href="userUrl">link</a>
```

### 5.4 Angular/AngularJS危险模式
```typescript
// Angular(2+) 危险：绕过安全管道
this.sanitizer.bypassSecurityTrustHtml(userHtml);       // [innerHTML]配合
this.sanitizer.bypassSecurityTrustScript(userScript);
this.sanitizer.bypassSecurityTrustUrl(userUrl);
this.sanitizer.bypassSecurityTrustResourceUrl(userUrl); // iframe src

// Angular 1.x 沙箱逃逸（经典payload，按版本选择）
{{constructor.constructor('alert(1)')()}}
{{_l.constructor.prototype.valueOf=1,toString=1}}
{{a=toString().constructor.prototype;a.charAt=a.trim;$eval('a,alert(1),a')}}
{{$on.constructor('alert(1)')()}}
{{[].pop.constructor('alert(1)')()}}
// SVG变体（{{ }}被过滤时）
<svg><animate onbegin=alert(1) attributeName=x dur=1s>
```

### 5.5 Svelte危险模式
```svelte
<!-- 危险：{@html}直接渲染用户HTML -->
<div>{@html userHtml}</div>
<!-- 修复：DOMPurify.sanitize后再渲染 -->
<div>{@html DOMPurify.sanitize(userHtml)}</div>
```

### 5.6 客户端模板注入（CSTI）与通用检测
**CSTI检测payload（在插值位置输入）：**
```
{{7*7}}
${7*7}
<%= 7*7 %>
{{constructor.constructor('alert(1)')()}}
```
**验证链**：`{{7*7}}`返回49 → 模板引擎表达式执行 → 尝试`constructor.constructor`构造器链 → 任意代码执行。

**框架版本指纹→已知漏洞匹配：**
| 框架/库 | 已知漏洞 | 检测特征 |
|---------|---------|---------|
| AngularJS 1.x | 沙箱逃逸（多版本CVE） | `ng-app` + `{{...}}` |
| Vue 2 | CVE-2024-6783（模板指令XSS） | `v-bind` 特定模式 |
| jQuery <3.5 | CVE-2020-11022/11023（htmlPrefilter） | `$(userHtml)` / `.html()` |
| Bootstrap 3 | CVE-2025-1647（DOM clobbering XSS） | data-toggle/自定义事件 |
| DOMPurify <3.4.x | 2024-2026 mXSS系列（见第七章） | innerHTML渲染用户内容 |

### 5.7 框架XSS审计方法论（实战步骤）
1. **识别框架版本**：`package.json`/`manifest`/JS特征（React 17+无`React.createElement`痕迹，Vue挂载点`#app`）
2. **grep逃生舱口API**（见5.1命令），逐一审查数据流
3. **追踪source→sink**：URL参数/hash/postMessage → 状态管理（Redux/Pinia）→ 渲染
4. **检查SSR/Hydration边界**：序列化JSON的`</script>`逃逸、hydration不匹配导致的DOM重解析
5. **审计第三方组件库**：富文本编辑器（Quill/Tiptap）、Markdown渲染器（marked/showdown，注意XSS选项是否开启）
6. **验证**：构造对应框架语法的polyglot，在浏览器DevTools Console观察sink触发

