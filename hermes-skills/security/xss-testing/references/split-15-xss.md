## 十四、XSS测试检查清单

### 14.1 信息收集与攻击面枚举
- [ ] 枚举全部输入点：URL参数/POST body/JSON字段/Header/Cookie/Path/Hash/文件名/上传文件内容
- [ ] 识别技术栈：框架（React/Vue/Angular/Svelte/AngularJS）、库版本（jQuery/DOMPurify/Bootstrap）、SSR模式
- [ ] 识别全部上下文类型：HTML/属性/JS/URL/CSS/Markdown/SVG/JSON
- [ ] 检查CSP策略头（script-src/base-uri/object-src/trusted-types）
- [ ] 检查Trusted Types是否启用及策略配置
- [ ] 检查HttpOnly/Secure/SameSite Cookie属性
- [ ] 枚举同源JSONP端点与script-src白名单域名

### 14.2 注入测试
- [ ] 基础Payload测试（script/img/svg/body/iframe）
- [ ] 事件处理程序枚举（onerror/onload/onfocus/ontoggle/onanimationstart等）
- [ ] 大小写/编码/注释/空白符/斜杠/全角字符绕过
- [ ] 20+上下文逐一构造对应闭合payload
- [ ] Polyglot通用payload测试
- [ ] Markdown/富文本编辑器注入
- [ ] 文件上传回显XSS（文件名/SVG内容/HTML内容）
- [ ] JSON字段XSS与Content-Type变换测试
- [ ] URL Path与Hash片段DOM XSS测试
- [ ] Referer/UA/XFF等头注入测试
- [ ] WAF绕过（Hackvertor编码矩阵、HPP、Chunked、Content-Type混淆）
- [ ] AI生成多态payload变体测试（XSSGAI/LLM）

### 14.3 框架与DOM专项
- [ ] grep危险Sink：dangerouslySetInnerHTML/v-html/{@html}/bypassSecurityTrust/innerHTML/eval
- [ ] source→sink数据流追踪（hash/postMessage/storage/URL）
- [ ] postMessage监听器origin校验审计
- [ ] AngularJS沙箱逃逸（{{}}表达式）
- [ ] CSTI客户端模板注入检测（{{7*7}}等）
- [ ] DOM Clobbering测试（id/name属性劫持）
- [ ] 原型污染测试（__proto__/constructor.prototype）
- [ ] SSR/Hydration JSON序列化注入（</script>逃逸）

### 14.4 高级绕过与利用
- [ ] CSP绕过：unsafe-inline/unsafe-eval/strict-dynamic/data:/JSONP端点
- [ ] Script Gadget链（jQuery data-*、Angular表达式、框架库gadget）
- [ ] Trusted Types绕过（宽松策略/策略名碰撞/DOM clobbering）
- [ ] mXSS测试（命名空间混淆/rawtext breakout/深度嵌套/二次解析包装器）
- [ ] DOMPurify版本审计（<3.4.x是否存在已知绕过）
- [ ] Service Worker/Web Worker注册与劫持测试
- [ ] Blind XSS（后台/日志/工单/客服系统）
- [ ] Cookie窃取/BeEF hook验证
- [ ] XSS→CSRF→ATO链验证（改邮箱/加管理员等敏感操作）
- [ ] 日志XSS→管理员ATO链（JSON编码错配）

### 14.5 验证与收尾
- [ ] 多浏览器验证（Chrome/Firefox/Safari/Edge解析差异）
- [ ] 记录触发条件与上下文（截图/请求/响应）
- [ ] 存储型XSS测试后清理注入数据
- [ ] 测试痕迹清理（临时文件/WebShell/注入内容）
- [ ] 输出漏洞报告：影响面/利用链/复现步骤/修复建议

