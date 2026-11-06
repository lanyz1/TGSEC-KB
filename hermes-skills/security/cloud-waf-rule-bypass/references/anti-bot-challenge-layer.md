# 反机器人质询层(200 + JS 质询页):识别、无效矩阵、文档导航穿透

云 WAF 的两层别混:**规则集层**(403 拦截页 —— 按 Host/payload 记账,见 SKILL.md §1–§3)
与**质询层**(200 + JS 质询页 —— 要你执行它的 JS 换 cookie)。打错层 = 白烧一整轮。

## 1. 识别指纹(阿里云 BB 防护实测)

- 状态码 **200** + `Content-Type: text/html` ⇒ 只看状态码会把质询页当"放行"
- 页面内嵌 `renderData`(隐藏表单/textarea)+ **大段混淆 JS**(实测单页约 66 万字符)
- 厂商标记 `<meta name="aliyun_waf_bb">`;首次响应 `Set-Cookie: acw_tc` / `aliyungf_tc` / `ssxmod_itna(.2)`
- 质询页 URL 带 token 参数(`?refer__<rand>=` / `?timestamp__<rand>=`),**每次导航都变,且与完整 URL 绑定**
  ⇒ 回放到**另一个** URL 仍被质询。**但它不是「一次性」** —— 连它绑定的那条 URL 原样回放是有效的,见 §5

⚠ **永不 print 质询页正文**:一次 66 万字符冲爆上下文,后面几轮全在"1 行输出"里瞎猜。
判定只输出状态码、`Content-Length`、是否含 `renderData`、cookie 名。拆 JS 先落盘,再按偏移读。

## 2. ★ 一条 A/B 判它挂在什么维度(比换出口重要得多)

同一出口、同一秒、同一 URL,只改请求形态:

| 发法 | 结果 |
|---|---|
| 浏览器**文档导航**(new_tab / 地址栏 / `<a>`) | **放行**,拿到源站真实响应(实测 `{"code":400,"msg":"Invalid encrypted request"}`) |
| 同页 **XHR / fetch** | **再次被质询**(即使该页刚刚已过质询) |

⇒ 拦截挂在**请求形态**(navigation vs subresource/fetch)上,**不是 IP 信誉、也不是 header 指纹**。
先做这一步再谈换出口:同一 IP 下导航放行 ⇒ 换出口/扩出口池是无用功。

实测无效(全部仍被质询,别再逐个试):`Origin`/`Referer` 指向真实前端、
`Sec-Fetch-Dest: document`+`Sec-Fetch-Mode: navigate`+`Sec-Fetch-Site`、`X-Requested-With`、
Telegram/移动端 UA、**X-Forwarded-For 轮换**、HTTP/1.0、`Accept-Encoding: identity`、
把 token 挂到**另一个** URL 回放(连同它绑定的那条 URL 原样回放则有效,见 §5)。

### 2.1 ★ 例外:方法白名单 `HEAD` / `OPTIONS`

同一路径逐方法打一遍,只有这两个免质询(其余全质询):

| 方法 | 结果 |
|---|---|
| `HEAD` / `OPTIONS` | **直达源站**,且**不需要后缀**、不改路径 |
| `GET POST PUT DELETE PATCH PROPFIND MKCOL LOCK UNLOCK COPY MOVE SEARCH REPORT VIEW CONNECT` | 全部 200 质询页 |
| `TRACE` | Tengine 405(到不了质询层) |

- **用途 (a) 通用绕过**:拿源站错误体/指纹,不必加后缀(后缀会改路径,见 §3)。
- **用途 (b) oracle**:批量 `OPTIONS` 扫候选路径 —— 谁回应用层响应谁就存在/在白名单。
- ⚠ **发不了业务请求**:`OPTIONS` 被 Spring 默认处理器吃掉(200 空体),`X-Http-Method-Override` 实测不生效。
- 判据:响应是 **JSON 应用体**还是 **HTML 质询页**;只看状态码会被 200 骗。

### 2.2 ★ 浏览器侧先查 CORS 预检,别先改信封

跨域页面发带**自定义头**的请求必先走 `OPTIONS` 预检;源站不认就回 `403 Invalid CORS request`,
浏览器只报 `TypeError: Failed to fetch`、axios `status: 0`。

```bash
curl -i -X OPTIONS https://target/api/x \
  -H 'Origin: https://front.example' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: x-encrypted,x-encrypt-key'
# 403 Invalid CORS request ⇒ 页内打不通,改命令行;同时解释了前端自身 status 0
```

⚠ 把 `status: 0` 读成"我们的头/加密不对"是本类目标最贵的误判 —— 它与信封无关。

## 3. 后缀白名单:能到源站,但拿不到业务面

- 质询**只对"无后缀"路径**发起;追加静态后缀(.css/.js/.txt/.xml/.json/.svg/.ico/.jpeg…)直穿源站
- 例外:`.zip/.rar/.bak/.jar/.java` 被 Tengine 直接 **405** ⇒ 不是"后缀全放行"
- ⚠ 后缀法只用于读源站错误体/指纹:它同时改写路径,Spring Security 的 `permitAll` 匹配的是原路径
  ⇒ 追加后缀后 `/login`、`/captchaImage` 变 401/404,**永远到不了业务 handler**
- 矩阵参数 `;` 有两种命运,别混:
  - `/login;.css`(分号后无 `=`)→ Spring `StrictHttpFirewall` 拦成 **500 Whitelabel** ⇒ 见 500 就停,别再试变体
  - `<真实路径>;x=.js` → **WAF 按后缀放行 + Tomcat 剥离分号** ⇒ 后端收到**真实路径**。
    仍不能承载真实调用(白名单路径统一 500),**但响应类别本身就是免费的分层 oracle**:

| `;x=.js` 的响应 | 结论 |
|---|---|
| 源站 400(应用自定义文案,如 `Invalid encrypted request`) | 路径已还原、WAF 已放行,**该路径要求体加密** |
| **500 Whitelabel** | 路径已还原,且**命中过滤器白名单**(未被要求加密) |
| **容器原生 404**(Tomcat `HTTP Status 404 – Not Found`,正文含真实内部路径) | 已到容器,**应用自己的前端控制器 / Servlet Filter 被整个跳过** ⇒ 见下方「非 Spring 栈」 |
| 200 质询页 | 这一发没绕过,形态无效 |

### 3.1 非 Spring 栈(Servlet / JFinal / Struts)上这招更值钱

那里没有 `StrictHttpFirewall`,所以 `<真实路径>;x=.js` **既不改后端收到的路径、也不触发 500**,
后端落到 Tomcat DefaultServlet:

- **免费的存在性 oracle**:免 token、任意深度、任意文件名都能问 —— 原生 404 = 不存在,200 = 该静态文件/JSP 存在
- **`.jsp` 会被 JspServlet 真的执行**(实测 `/<x>.jsp;x=.js` 回 200 + 渲染出的页面正文)
- 原生 404 / 500 正文自带**内部真实路径 + 容器版本**(实测泄露 `/<context-path>/druid/index.html` 与 `Apache Tomcat/8.5.100`,
  另一栈回 `Powered by JFinal <ver>`)⇒ **一发请求同时拿到 context-path 与容器/框架版本**,比翻 DNS/CT 快得多
- 判据:响应是**容器自己的 404 页**就是这条路;回 `renderData` 质询页说明这一发形态无效

## 4. 有效通道:文档导航

```python
# browser_exec 内:用导航发 GET,从渲染出的文档里读源站 JSON
new_tab("https://target/app/merchant/info/1")
wait_for_load()
print(js("document.body.innerText.slice(0,600)"))
```

- **只对 GET/能塞进 URL 的请求成立**。要 POST/自定义头时,思路是 CDP `Fetch.enable` +
  `continueRequest` 改写导航请求(改方法、塞 body 与头)—— **本库尚未实测成型,别当结论用**,
  先用 GET 面把能拿到的拿完。
- 质询页 cookie(`acw_tc`/`ssxmod_itna`)搬进 Python 脚本**不能直连**;直连的凭据是 §5 的 URL token。
- 成功判据:响应体是**应用层 JSON**(Spring `{code,msg}` / 业务体),不是 HTML 质询页。

## 5. ★★ 把浏览器当 token 铸造机:铸一次,Python 打一轮

质询层的凭据不是 cookie、也不是 header,而是**质询 JS 跑完后改写进 URL 的那个 token**。
它与 cookie 不同 —— **它可以字节级回放**。

```python
# ① 铸:真浏览器导航一次(browser_exec 内)。这一步同时把质询解开了
goto_url("https://target/任意路径")
wait_for_load(); time.sleep(3)
tok_url = js("location.href")   # ← 已被改写成 https://target/任意路径?timestamp__<rand>=<token>
print(tok_url)                  # 取回这条完整 URL 存起来

# ② 打:纯 requests 原样回放,不带任何 cookie
s = requests.Session(); s.trust_env = False    # 环境代理会毁掉直连,先关
r = s.get(tok_url, timeout=20, verify=False)   # 200 + 源站真实业务体
```

实测结论(阿里云 BB 质询层):

- **回放成功**与 UA 无关(浏览器 UA 换成 curl/requests 照样过)、**无需任何 cookie**、
  **数分钟内持续有效**(无短 TTL)
- **回放失败只有一种主因:URL 不是那一个** —— token 与完整 URL(路径 **+ 查询串**)绑定;
  实测用 `/` 的 token 打 `/zzz`、打 `/?a=1` 均 100% 重回质询页
- ⇒ 工作流定型:**逐 URL 铸一次(≈5s/URL,浏览器)→ 收 token → Python 侧对该 URL 无限次打**。
  想带上新的查询串/payload 变体要**重新铸**(查询串也参与绑定),别复用
- 回放后程序化判据:响应体含 `renderData` / `_waf_<hex>` 标记 ⇒ 仍是质询页(页很大,按 §1 的禁令**别 print 正文**);
  否则按源站响应处理

⚠ **并发上限会让 oracle 静默失真**:同一路径并发 ~10 时,本该干净的 404 改回 **HTTP 200 + 0 字节** ——
既不报错也不是 429。⇒ 枚举期间每 N 条重打一条**已知基线 URL**(如根路径),基线响应类别一变就停;
否则「N 条零命中」只是限流的自画像。低并发 + keep-alive + 熔断退避 + 命中即时落盘。
