## 五、SameSite Cookie语义与跨浏览器绕过

### 5.1 Site判定与浏览器语义差异（2026现状）
```
"Site" = scheme + eTLD+1（公共后缀+一级），与端口/子域无关
- https://app.example.com → https://api.example.com = same-site
- https://example.com → http://example.com = cross-site（scheme不同）
- 无SameSite属性默认Lax：
  Chrome/Edge 80+（2020-02）、Firefox 87+（2021-04）、Safari 16.4+（2023-03）
  Chrome on iOS 用WebKit不强制新默认；APP内WebView/老浏览器无默认限制
- Safari ITP：第三方Cookie默认封禁+7天清除，SameSite=None Cookie在Safari也受限（需CAPTCHA/Storage Access API）
```
**跨浏览器差异是攻击者的机会窗：** 同一PoC在Chrome失败、在Firefox/老浏览器/WebView可能成功，务必多浏览器验证。

### 5.2 SameSite=Lax绕过
```javascript
// 1. GET型操作顶级导航（Lax允许）：改GET、或接受GET+body
window.open('https://target.com/api/delete?id=123');
location.href = 'https://target.com/api/delete?id=123';

// 2. Lax+POST 2分钟窗口（Chrome专用，最高价值）
// 机制：若Cookie是"最近（≤2分钟）跨站POST响应中设置"的，Lax会额外放行一次跨站POST
// 利用：先用跨站POST让目标Set-Cookie（如搜索/登录/埋点接口反射写入cookie），
//       2分钟内立即发起CSRF POST → Cookie被携带
// 第一步（跨站form，诱导目标写入cookie）：
//   POST https://target.com/login → 响应Set-Cookie: session=xxx; SameSite=Lax
// 第二步（2分钟窗口内的CSRF POST）：
//   form自动提交到敏感接口 → Lax例外放行携带Cookie

// 3. 方法覆盖（_method=GET，6.x详述）：浏览器发POST（Lax阻止），路由层视为GET
//    Symfony/Laravel/Express/Rails 常见 `_method` 隐藏参数

// 4. 同站Gadget（Strict/Lax通用最强绕过）：找到同站任意JS执行点
//    - 同站XSS / DOM open redirect（客户端重定向构造目标URL，被视为普通请求而非导航）
//    - 子域名XSS（cookie Domain=父域时）
//    - JSONP回调（同站可执行攻击者控制JS的接口）
//    - 子域接管（sibling subdomain takeover：DNS挂靠/悬空记录）
//    PortSwigger经典思路：同站DOM型open redirect作为Gadget，让浏览器发"普通同站请求"

// 5. Cookie注入覆盖（不阻止Set-Cookie）：
//    把受害者Session覆盖为攻击者已知会话 → CSRF操作使用攻击者会话（=Login CSRF变体）

// 6. 跨站WebSocket握手（CSWSH，见11.1节）：WS握手GET在部分实现/旧浏览器不受SameSite限制
```

### 5.3 SameSite=Strict绕过
```javascript
// Strict下任何跨站请求不携带Cookie，需破坏"跨站"前提：
// 1. 同站Gadget：子域XSS/JSONP/DOM open redirect（5.2-4）
// 2. 子域接管后成为"同站"来源
// 3. Service Worker劫持（Chromium issue 429585229：SW拦截fetch()转发时Strict/Lax Cookie被不当包含）
// 4. 点击劫持组合：诱导用户在已打开的target.com页面内点击（同站触发）
// 5. 老浏览器/WebView不执行Strict语义
// 6. 若登录态在非Cookie载体（Authorization Header/Web Storage+JS请求）→ SameSite完全无效，直接CSRF其API
```

### 5.4 方法条件校验绕过（POST-only token检查）
```
大量框架/自研代码只对POST校验Token（GET留给读操作）：
1. _method=GET：form提交_method=GET，路由层当GET处理 → Token校验被跳过
   <form action="https://target.com/api/change-email" method="POST">
     <input type="hidden" name="_method" value="GET">
     <input type="hidden" name="email" value="<EMAIL-REDACTED>">
   </form>
2. HEAD-as-GET：后端把HEAD路由到GET handler（无Token校验），HEAD跨站可发
   <img src="https://target.com/api/change-email?email=<EMAIL-REDACTED>">
   // 某些框架接受HEAD作为GET的响应头模式——若操作副作用在GET handler内则生效
3. 用OPTIONS/TRACE探路：若OPTIONS也执行handler副作用（罕见）
4. 直接改GET：`POST /api/x` → `GET /api/x?params...`，Token校验仅绑定POST即失效
```

### 5.5 SameSite=None与Partitioned（CHIPS）
```
- SameSite=None必须Secure：站点若为兼容第三方把认证Cookie设为None → 全部跨站请求携带 → 普通CSRF全通，优先级最高先测
- Partitioned Cookie（CHIPS）：分区存储，第三方嵌入场景不携带——主要影响"嵌入iframe内的第三方服务"
  测试：若目标把认证Cookie标记为Partitioned，则攻击者站内嵌iframe发起的跨站请求不携带该Cookie（天然防CSRF），需转向顶级导航/同站Gadget
```

