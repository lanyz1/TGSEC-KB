## 四、CSRF Token绕过矩阵（深化）

### 4.1 Token验证方式与绕过对照表

| Token验证方式 | 绕过方法 | 实战优先级 |
|-------------|---------|-----------|
| 仅检查Token存在性 | 发送任意值 | ★★★★★ |
| Token可预测（时间戳/ID/MD5/固定随机源） | 预测/重放历史值 | ★★★★ |
| Token绑定Cookie但未绑定Session | 同时设置Cookie与表单Token（双提交缺陷）| ★★★★★ |
| Token绑定Cookie且绑定Session但未绑定User | 用自己的Token替换 | ★★★ |
| Token可重复使用（未一次性失效） | 捕获后重用 | ★★★★ |
| Token仅在Cookie中 | Cookie注入覆盖（子域/CRLF/Tossing）| ★★★★ |
| Token在GET参数/URL | 直接GET CSRF+Referer泄露 | ★★★★ |
| Token通过AJAX Header发送但CORS放行 | CORS读取Token（第九章） | ★★★★ |
| 空Token通过 | 删除Token字段 | ★★★★ |
| 仅校验Token长度/格式 | 等长任意值 | ★★★★ |
| 仅校验Token签名前半段/前缀 | 截断/前缀伪造 | ★★★ |
| Token校验仅针对POST方法 | HEAD/OPTIONS/GET/方法覆盖绕过（5.4节） | ★★★★ |
| Token校验仅针对特定Content-Type | 换Content-Type绕过 | ★★★ |
| Token在多步流程中仅首步校验 | 直接跳转后步（5.5节） | ★★★★ |

### 4.2 Token泄露通道全景
```
1. XSS漏洞 → 直接读取Token（meta/DOM/接口响应）
2. CORS错误配置 → 跨域fetch读取Token（第九章9.1）
3. JSONP接口泄露Token（callback参数包裹Token响应）
4. Token在URL中 → Referer/日志/历史记录泄露
5. 302重定向链 → Token随Location头/Referer外泄
6. 错误页面/调试接口回显Token
7. 统计/埋点接口（前端上报页面HTML含meta token）
8. Service Worker劫持 → 截获请求头中的Token（第十二章）
9. 共享缓存/CDN缓存差异 → 缓存投毒读取带Token页面
10. 子域页面（父域Cookie+同站token读取接口）→ 通过CORS或同站上下文读取
```

### 4.3 Token绑定的三重校验维度（审计要点）
```
高级审计时对Token逐项验证"绑定维度"：
A. 是否绑定Session？（换Session验证）
B. 是否绑定User？（换用户Token验证）
C. 是否绑定请求方法/路径？（换方法/路径验证）
D. 是否一次性？（重放验证）
E. 熵是否足够/随机源是否安全？（统计采集1000个样本分析）
任意一项"否"即存在对应绕过面，组合多项缺陷可形成完整利用链
```

### 4.4 双提交Token Cookie边界场景
```
场景A：表单Token=从Cookie读取 → 服务端仅比对"Cookie中Token==表单Token"
  → 若攻击者可设置目标域Cookie（子域接管/CRLF注入/Cookie Tossing/HTTP与HTTPS混用），即可注入攻击者已知值
场景B：Angular风格（XSRF-TOKEN Cookie + X-XSRF-Token Header）
  → 前端JS自动从Cookie读值放Header；攻击者先注入已知Cookie值 → 浏览器自动带正确Header → 绕过
场景C：Token=<REDACTED>, 服务端密钥)
  → 需密钥；若HMAC验证存在"长度差异攻击/算法混淆/时序"缺陷则可绕过（见8.3节）
```

### 4.5 多步表单CSRF与Token传递（新增）
```
多步业务流程（注册→验证→完善资料、改密→确认→完成、购物车→结算→支付确认）的Token薄弱点：
1. 仅第一步校验Token，后续步骤只校验Session → 直接构造后步请求
2. Token在步骤间通过URL参数传递 → Referer/日志泄露+GET CSRF
3. Token存于hidden域但页面间可被预测/固定
4. 各步Token独立但共享同一Session且可被"重放前步Token"
5. 步骤回退/跳转（直接POST到第N步）绕过中间校验

实战Payload（跳过中间步骤直达状态改变步骤）：
<form action="https://target.com/checkout/step3-confirm" method="POST">
  <input type="hidden" name="order_id" value="12345">
  <input type="hidden" name="confirm" value="1">
</form>
<script>document.forms[0].submit();</script>
<!-- 若step3仅依赖Session中的order上下文且不校验Token → 直接生效 -->

多步自动推进（iframe依次提交各步）：
<iframe name="f1" style="display:none"></iframe>
<iframe name="f2" style="display:none"></iframe>
<form action="https://target.com/flow/step1" method="POST" target="f1">
  <input type="hidden" name="a" value="1">
</form>
<!-- 若服务端把步骤状态存Session，攻击者构造step1→step2→step3连续提交 -->
```

