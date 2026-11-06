## 二、检测方法论

### 2.1 Token机制识别
检查请求中的CSRF Token字段：
| Token位置 | 常见参数名 |
|---------|---------|
| 表单隐藏字段 | `csrf_token`、`_token`、`csrfmiddlewaretoken`、`authenticity_token`、`__RequestVerificationToken`、`csrf` |
| HTTP Header | `X-CSRF-Token`、`X-XSRF-Token`、`X-CSRF-TOKEN`、`X-Anti-CSRF-Token`、`Authorization`（误用场景） |
| Cookie | `XSRF-TOKEN`、`csrftoken`、`csrf-token`（Angular等框架自动从Cookie取值放入Header） |
| URL参数 | `?token=xxx`、`&_csrf=xxx`、`?state=xxx` |
| meta标签 | `<meta name="csrf-token" content="...">`（页面内嵌，可被CORS/JSONP读取） |

**Token有效性测试矩阵（进阶）：**
```
1. 删除Token → 是否拒绝？（应拒绝，接受=漏洞）
2. 替换为其他用户Token → 是否拒绝？（应拒绝，接受=Token未绑定用户）
3. 替换为其他会话Token → 是否拒绝？（应拒绝，接受=Token未绑定Session）
4. Token长度太短/全相同字符 → 是否拒绝？（长度校验缺陷）
5. Token仅校验格式（正则/长度）不校验值 → 等长任意值可过
6. Token可预测（时间戳+用户ID MD5、随机数种子固定、线性递增）
7. 空Token/空字符串是否通过？（部分框架`if(token)`判断缺陷）
8. Token在GET与POST中均可使用？（GET CSRF + Referer泄露面）
9. 把Token从Header移到Body、Body移到Cookie、Cookie移到GET参数是否仍通过？（校验位置绑定缺陷）
10. Token在OPTIONS/HEAD/GET请求中是否也校验？（方法条件校验，见5.4节）
```

### 2.2 Referer/Origin检测
```
1. 正常Referer: https://target.com/path → 通过
2. 删除Referer → 是否拒绝？（只校验"存在性"=可被no-referrer绕过）
3. Referer为空 → 是否通过？（data:/blob:/sandbox iframe Origin为null场景）
4. Referer为http://（降级） → 是否检查？
5. Referer为子域名 → 是否通过？（同站应通过）
6. Referer为target.com.attacker.com → 是否通过？（前缀/包含匹配缺陷）
7. Referer为attacker.com/target.com（路径含） → 是否通过？（包含匹配缺陷）
8. Referer为<EMAIL-REDACTED> → 是否通过？（@解析host为attacker.com）
9. Origin头为空/缺失时 → 是否通过？（仅当Origin存在时校验=伪造删除Origin）
10. Origin为null → 是否通过？（iframe sandbox/srcdoc/data: URL）
11. Origin与Host不匹配时是否拒绝？
```

### 2.3 SameSite Cookie检测
```
检查所有Set-Cookie头的SameSite属性：
- 无SameSite属性 → 现代浏览器默认Lax（Chrome 80+/Firefox 87+/Safari 16.4+），但老浏览器/APP内WebView可能是"无限制"
- SameSite=Strict → 跨站一律不携带，需同站Gadget/子域接管/SW绕过
- SameSite=Lax → 跨站顶级导航GET携带，POST/AJAX不携带；可被2分钟窗口/方法覆盖绕过
- SameSite=None → 必须Secure，所有请求携带=无防护，直接普通CSRF
同时检查：Domain属性是否为父域（父域Cookie可被子域页面携带）、Path是否为/、是否带__Host-/__Secure-前缀
```

### 2.4 自定义Header检测
- 依赖`X-Requested-With: XMLHttpRequest`（jQuery自动添加）：form提交不含此Header → 可作为校验信号；绕过见6.x/7.x
- 依赖`X-CSRF-Token` Header：跨站JS无法设置（触发预检），但CORS错误配置/Flash/SW劫持/DNS Rebinding可绕过
- 注意：**校验逻辑是否"Header存在即可"**（不校验值）——某些实现`if(req.headers['x-requested-with'])`即放行，`fetch`加任意值即可过

### 2.5 Fetch Metadata（Sec-Fetch-*）检测
```
2023起浏览器在请求中自动附加（JS不可伪造）：
- Sec-Fetch-Site: same-origin / same-site / cross-site / none
- Sec-Fetch-Mode: navigate / no-cors / cors / websocket
- Sec-Fetch-Dest: document / empty / image / iframe / json ...
- Sec-Fetch-User: ?1（顶级导航用户激活）

测试要点：
1. 目标是否校验Sec-Fetch-*？（现代框架如.NET 11自动拒绝cross-site+非安全方法）
2. 反向利用：旧浏览器/代理剥离/WebView/命令行工具（curl）不发送这些头 → 若服务端"缺失即放行"，可直接构造裸请求
3. 检查服务端是否对Sec-Fetch-Site: cross-site但Sec-Fetch-Mode: navigate（顶级导航）放行 → GET型CSRF仍有空间
```

