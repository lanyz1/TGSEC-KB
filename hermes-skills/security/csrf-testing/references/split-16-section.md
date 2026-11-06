## 十四、自动化工具链

### 14.1 Burp Suite
```
- Engagement tools → Generate CSRF PoC：一键生成可复制HTML PoC（含Token去除警告）
- CSRF Token handling（Session handling rules）：Repeater/Intruder自动提取并更新Token
- Match and Replace：批量改Token/Referer/Origin测试绕过
- 403 Bypasser插件：方法覆盖/路径规范化自动测试
- CSPT2CSRF扩展（Doyensec官方）：扫描前端CSPT→CSRF链
- 自定义Python扩展：自动提取Token并构造跨域fetch PoC
```

### 14.2 专用工具
| 工具 | 用途 |
|------|------|
| XSRFProbe | CSRF自动化检测（Token绕过/Referer缺失/方法覆盖） |
| OWASP ZAP（+CSRF插件） | 主动扫描CSRF，配合AI插件 |
| Burp CSRF PoC Generator | 快速生成PoC |
| SameSite测试沙箱（samesite-sandbox.glitch.me） | 验证浏览器SameSite行为 |
| Chromium/Firefox headless + Playwright | 多浏览器自动化验证PoC（Cookie携带行为差异） |
| Cookie-Editor/BrowserStack | 多浏览器Cookie行为对比测试 |
| Strix / XBOW / Shannon | AI驱动检测扫描（13.3节） |

### 14.3 XSRFProbe使用
```bash
# 基础扫描（需登录Cookie）
xsrfprobe -u https://target.com --cookie "session=xxx"

# 深度分析模式
xsrfprobe -u https://target.com/api -c "cookies.txt" --skip-analysis

# 输出HTML报告
xsrfprobe -u https://target.com --raw http-request.txt -p
```

### 14.4 多浏览器验证矩阵（必做）
```
同一PoC必须在以下环境验证：
- Chrome/Edge（最新）：Lax默认+2分钟窗口语义
- Firefox（最新）：Lax默认+宽泛的Lax+POST例外（与Chrome窗口规则不同）
- Safari（含iOS）：ITP强限制第三方Cookie，SameSite=None也受限
- 无头浏览器模拟老浏览器/WebView（UA/无SameSite支持）
- curl/httpx（非浏览器）：验证"无Sec-Fetch-*头"是否被服务端放行
```

