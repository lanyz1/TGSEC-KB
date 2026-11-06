## 六、DOM XSS深度：Source-Sink审计方法论

### 6.1 DOM XSS特点
- 服务器不可见：payload只存在于URL fragment/postMessage/window.name/storage
- WAF/输出编码/服务端过滤全部失效
- SPA路由（hash路由/history路由）放大了攻击面
- **2026年最常见XSS变体**，是审计重点

### 6.2 Source → Sink 完整数据流清单
```
URL源: location.hash → 剪枝 → 元素id匹配 → DOM操作（常见路由库漏洞模式）
postMessage源: event.data → 未校验event.origin → innerHTML/eval
storage源: localStorage.getItem() → 二次渲染（存储型DOM XSS）
网络源: fetch响应 → .json() → 动态渲染
window.name源: 跨页面持久化 → 新页面读取
```

### 6.3 DOM XSS自动化检测工具链
```bash
# Burp DOM Invader（最强DOM XSS检测）
# 设置：Proxy -> Settings -> DOM Invader -> Enable
# 功能：自动标记source/sink、postMessage劫持检测、canary注入

# Retire.js（检测老旧易受攻击JS库）
# 浏览器扩展，识别已知漏洞库版本

# Snyk / npm audit（供应链层）
npm audit --json | jq '.vulnerabilities | keys'

# 语义化搜索
rg -n "location\.|document\.referrer|postMessage|localStorage|sessionStorage|window\.name" --type js | rg "innerHTML|eval|write|href|src|location"

# 动态分析
# Puppeteer/Playwright + 自写sink探针（注入canary，监听sink调用栈）
```

### 6.4 手动审计五步法
1. **枚举source**：全站搜`location.*`/`document.URL`/`referrer`/`postMessage`/`window.name`/`storage`
2. **枚举sink**：全站搜`innerHTML`/`eval`/`document.write`/`setAttribute`/`href=`/`location=`
3. **建立数据流**：source到sink之间是否经过编码/校验（白名单/replace/正则）
4. **测试绕过**：对编码/校验点构造绕过（双编码、Unicode、突变、原型污染）
5. **验证触发**：DevTools中修改location.hash/postMessage模拟，Console看执行

