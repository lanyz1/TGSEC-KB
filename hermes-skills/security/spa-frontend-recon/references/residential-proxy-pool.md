# 住宅代理池工作流(解决 IP 风控,博彩/风控严格目标必备)

来源: AQ777(gz778.aq777c1.vip)渗透实战 — 批量注册/登录测试后 IP 被 `login.ip.restricted` 整体风控,免费公共代理质量差且大多被目标已知黑名单拦截,用户提供住宅代理 xlsx 后打通。

## 触发场景

- 目标返回 `login.ip.restricted` / `register_ip_restricted` / `us_forbidden_login_error`(IP 级或账号级风控)
- 需要规模化枚举/注册/测试,但单个出口 IP 很快被拉黑
- v2rayN 只有 1 个节点(或节点 IP 被目标拉黑)无法轮换

## 住宅代理资源格式(用户交付物,常见)

用户提供的"住宅节点"通常是 xlsx 表格,两种典型列结构:

**类型 A(直连住宅)**:
```
出口IP地址 | Socks5-代理地址 | Socks5-端口号 | Socks5-代理账号 | Socks5-代理密码 | 备注 | ...
72.13.252.60 | q0_1746307169.ga6x.com | 30801 | q0_1746307169-ddcn-92228633052160 | c6f8d10e | 美国
```

**类型 B(S5 中转)**:
```
出口IP地址 | 中转后代理地址 | 中转后端口号 | 中转后代理账号 | 中转后代理密码 | ...
72.245.135.169 | 14.119.66.81 | 30901 | l1_1773388338-rdf-91191211826212 | cef99674
```

关键:**每个账号 = 一个独立出口 IP**(同一中转地址 host:port 配不同账号即不同出口)。表头行决定列索引,解析时先找表头(含"出口IP地址"/"Socks5-代理地址" 或 "中转后代理地址")再取数据行,否则行结构不同会错位。

## 步骤

### 1. 解析 xlsx(无 openpyxl 时用标准库 zipfile+XML)

```python
import zipfile, re, xml.etree.ElementTree as ET
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def read_xlsx(fp):
    out = []
    with zipfile.ZipFile(fp) as z:
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in root.findall('m:si', NS):
                out.append(''.join(t.text or '' for t in si.iter('{...}t')))
        # 遍历 xl/worksheets/sheetN.xml, 单元格取值: 先查 m:v, 再查 inline m:is, t='s' 时查 sharedStrings
    return out
# 表头定位列 → 逐行提取 (exit_ip, host, port, user, pwd)
```

### 2. 验证代理(pysocks,支持认证)

**curl --socks5 带认证经常 CONN_FAIL,用 Python pysocks 更可靠**:

```python
import socks, ssl
s = socks.socksocket()
s.set_proxy(socks.SOCKS5, host, port, username=user, password=pwd)
s.settimeout(15)
s.connect((target_host, 443))
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
ss = ctx.wrap_socket(s, server_hostname=target_host)
# 手动拼 HTTP/1.1 请求(Connection: close),读响应
```

每个代理先查出口 IP(`https://api.ipify.org` 经代理)确认与声明一致,再测目标 `whitelabel` 是否返回 `"success":true`(通过风控)vs `login.ip.restricted`(该出口也被拉黑)。

### 3. 代理池轮换客户端

- 可用出口列表 + 失败黑名单(近期失败 IP 30s 内跳过)
- 每次请求 `POOL.next()` 轮换;连接失败/超时/被风控 → `mark_fail` 换下一个
- 重试 3 次
- 所有请求头(Merchant/Device/UA/Origin)与直连一致,加密链逻辑不变

### 4. 教训

- 免费公共代理(proxyscrape 等)对风控严格目标基本无用:延迟高、多数连不上、IP 池被目标标记 — **用户明确表示不要用垃圾免费代理**
- 住宅代理验证出口 IP 与声明一致才算可用;本案例 13 个节点 7 个可用(6 个超时/认证失败)
- 账号被锁(`us_forbidden_login_error`)是**账号级**锁定,换 IP 无效,需换账号;IP 级限制(`login.ip.restricted`)换 IP 有效
- 换 IP 只解决 IP 风控,不解决账号锁定 — 批量测试要账号池 + IP 池双轮换
