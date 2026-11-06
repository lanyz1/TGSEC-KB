## 9. 拦截分层 = 免鉴权面的判决依据
同站点不同路径会落到**不同层**，按返回值分层即可推出「谁跳过了前置过滤器」：
```
400 Invalid encrypted request  ⇒ 被信封/前置过滤器拦（没进鉴权）
401 / {"code":401}            ⇒ 跳过过滤器，进认证层（需票据）
Spring 404 / 无 handler 404   ⇒ 跳过过滤器，无此 handler
Whitelabel 403 / {"status":403,"error":"Forbidden"}
                              ⇒ 前置 ACL **或信封闸**（app 级；改 XFF/X-Real-IP 也不动 ⇒ 别当 WAF 层）
                                ★ 判据 = 「明文 403 + 信封 200」配对出现 ⇒ 就是信封闸，不是白名单/不是被封
整齐 401（全端点同码同句）      ⇒ **通道已通、票死了** ⇒ 停止改通道/换形态/换出口，去重新登录取新票
                                分层口诀：挑战页=WAF 层 / 400·403=信封层 / 整齐 401=身份层
应用 JSON                     ⇒ 真业务响应
200 + 0 字节(无 Content-Type)  ⇒ 静态资源处理器 / 兜底：**不存在的路径也回 200+0**（`/system/**` 尤其）⇒ 不是「读到文件」，判可读必须与「已知存在的文件」对照
挑战页(renderData / ≈110310B) ⇒ 还没进应用 ⇒ 本次任何应用层结论作废，重试后再读
```
★ **先拿乱写路径定 catch-all 档，再读其他路径**：同一台可能两种取向 —— catch-all=403 时「401 = permitAll 成员」（**白名单 oracle，可直接扫免票路由**）；catch-all=401 时「401 什么也没证明」，须靠 404 判白名单。**跳过负对照就把 401 读成「端点存在」是最常见误判**。
★ **后缀形态不能用来判 permitAll**：`/getInfo`→RuoYi 401 而 `/getInfo.json`→Spring 403（后缀让请求匹配不上 permitAll 规则）⇒ 后缀只用来「穿 WAF 看框架层」，判白名单必须「无后缀 + 导航重试」。
```
⇒ 只有「跳过过滤器 + permitAll」的路径才是免鉴权面；用该法把 `/common/**` 收敛到**唯一个** `POST /common/verifyAuthToken`（其余 `/common/*` = 401，其余全路径 = 400）。
★ **方法（GET/POST）是独立变量：`Request method 'POST' not supported` 不等于端点不可用** —— 该文案说明请求**已进控制器且鉴权已过**（否则回 401/403）⇒ 换 GET 重打（信封类带 `?encryptParams=<密文>`）即可。实测一批 RuoYi 风格业务读端点（商品/订单/商户信息/余额）**全部 GET-only**，把它们读成「打不通」会白丢整片读面。

## 10. 差分扫的假命中陷阱
用「与参考行前 N 字相同」判「无差异」时，**动态段（页面时间戳、随机 id、`?alichlgref=` 签名）会让同页被判成差异** ⇒ 28 条枚举全被打上假 ★。做差分前先归一化（剥时间戳/动态段）或只比对**结构性关键字**（如错误类名、msg 字段）。

## 11. 导航重试纪律（挑战页不是判死依据）
- ★ **同一路径连续导航，前几发仍回挑战页，第 2–3 发才出真响应**（实测：`/captchaImage` 第 3 发、`/system/user/list` 第 2 发；同轮 `/manager/`、`/swagger-ui/index.html` 直接吃挑战页而 `/admin/`、`/dist/`、`/web/` 出真响应）⇒ **单次挑战页不足以判「路径不存在 / 被拦」**。
- 判死前同路径至少 3 发；仍全为挑战页才可判死，或换「后缀白名单」形态复核。重试代码见 `references/pass-channel-recipes.md`。
- ★ **回跳参数 = 挑战已解的证据**：导航通过后 final URL 会被追加 `?refer__1720=` / `?encode__1715=` / `?md5__1713=`；**看到这些参数就说明这次响应是真的**，没看到则应先怀疑本次仍是挑战/未完成解算。
- ★ **页内 fetch/XHR 是否免质询是逐『页面宿主』属性，必须实测**：多数实例上即使同一标签页已解过挑战、cookie 齐全，页内 fetch 照样回挑战页；但**在目标自己的页面里**发 XHR 时，页面脚本会给请求 URL 自动追加 `?md5__1713=<token>` ⇒ 直接 200 真数据。判定顺序：先试「目标自己页面内 XHR」，失败再退回导航读/车辆改写；**别因为某页页内 fetch 失败就断定整条路不通**。
  ★★ **同一 host 上「导航放行」与「页内 XHR 放行」是两件独立的事，必须分开实测**：实测有 host 是**导航已解出真页面（拿到 `{...}` 应用文案），页内 fetch 与页内 XHR 却仍双双吃 ≈110310 挑战体**（该台没有页内豁免属性）⇒ 这种台**唯一通道就是铸签重放**（§1 票行）。**判据 = 看页内请求的响应体是不是挑战体，而不是看导航成不成功**；导航成功只证明该 host 的 doc 面放行。别再为它重试页内通道/车辆改写。
- ★ **令牌与出口 IP 绑定**：铸票出口 ≠ 回放出口 ⇒ 整齐 401/挑战。用环境变量把出口固定进每次运行（`XVIP_SOCKS=host:port python probe.py`）；同族的**页面域与接口域可能各自只有不同出口可达**（实测：页面源域仅经本机代理出口可达、接口域经跳板出口可达）⇒ 为「页面源」与「接口」分别固定出口并分别验证。

## 12. Cloudflare non-interactive 挑战：正面求解 + clearance 复用（实测通路）
- **指纹**：`403/429` + 响应头 `Cf-Mitigated: challenge`；挑战页 `Just a moment...` / `请稍候` / `cType: 'non-interactive'`；**cloudscraper 对 managed challenge 无效**（~0.8s 静默 403 返，别烧轮次）。
- **通路线**：真 Chrome（`--headless=new` 亦可）经**跳板 socks5 出口**正面求解：non-interactive 挑战几秒内**自动解**，无需交互。
  1) 启动：`chrome --headless=new --remote-debugging-port=<p> --user-data-dir=<tmp> --proxy-server=socks5://<跳板> --user-agent="<常规 Chrome UA>" --no-first-run --disable-gpu`（**受管后台**起，勿 nohup）。
  2) **代理是否生效必须实测**：CDP 导航 `http://myip.ipip.net/` 读出口 IP（同机两实例曾「一个好一个坏」，重开即可，别去雕代理参数）。
  3) **原生 CDP（websocket-client ~100 行）**：`/json/list` 取 page `webSocketDebuggerUrl` → 同步 `send`（靠 id 匹配回执）→ `Emulation.setUserAgentOverride`（**去 HeadlessChrome** + 给 `userAgentMetadata`）→ `Page.addScriptToEvaluateOnNewDocument` 注入 stealth（`navigator.webdriver` 等）→ `Page.navigate` → **每秒轮询 `document.title`**：含 `稍候`/`Just a moment` = 还在解；变真标题 = 已过。**DrissionPage 4.1.1.x 对 Chrome 154 的 CDP ws 404（不兼容）⇒ 直接用 websocket-client，别在库上烧轮次。**
- **clearance 复用（机外 HTTP）**：过挑后 `Network.getCookies` 导出 **`cf_clearance`** ⇒ `requests`/`curl` 带 `Cookie: cf_clearance=...` + **与铸挑同出口** + 同款 UA ⇒ 200（含被挑战路径）；**绑定 IP**（换出口立失效）。
- **CF 下 POST 优先序**：①「已过挑页面」的**页内 fetch**（页面宿主豁免，clearance 会话内同源 XHR 通常不再挑）；② 页内 fetch 被挑 → 真**表单提交**（`form.submit()`，走导航面）+ `Page.addScriptToEvaluateOnNewDocument` 覆盖 `window.alert`/`history.back`（防弹窗阻塞与回退丢页）；③ 都不可用才考虑「导航车辆 + Fetch 改写」。
- **配额现实**：CF 对**数据中心出口**（跳板/云主机）的「非浏览器」请求配额极低——数发密集探测即进 `429+challenge`；**批次要小、间隔 ≥8s、批间冷却**。
- ★ **页内 XHR 也计配额（修正「页内不受限」的旧说法）**：真 Chrome 页内 fetch 连发 ~4 发即吃 `429 + challenge`（导航面更宽但同样计费，不是无限）⇒ 批内 8s 间隔、被挑后**在同 tab 重导航刷新会话**再重试即可恢复；9 项以上的矩阵拆两批跑。
- ★ **CF 静默空体（200 + 0 字节）**：对「携带 clearance 的非浏览器客户端」CF 可不报错地回 **200 空体**（伪装成应用空响应）⇒ 判读前先对照「真浏览器通道下同请求的形态」，别把静默挡当成应用行为（实测：curl+clearance 内页 200+0，同时真 Chrome 页内同请求 17334B 完整页）。
- ★ **反调试站（disable-devtool 系）过法**：页面检测到 CDP 后 `location.replace('https://example.com')`（症状：导航「成功」但 tab 停在 example.com / 目标页秒跳；被踢的旧 tab 已污染不可复用）。**顺序：attach → `Network.setBlockedURLs(["*disable-devtool*"])` → 新开干净 target / 再导航**；`alert`/`history.back` 用 `Page.addScriptToEvaluateOnNewDocument` 覆盖。此类前端防护对 CDP 零阻力，别因它判「页面无法自动化」。

- ★★★ **本机直连（无跳板）也能全站放行——只要「真 Chrome 指纹 + 正常 UA」（实测）**：CF non-interactive 挑战对 headless=new + CDP 的本机 Chrome **0 秒自动解**，之后**全站放行——连随机编造的 404 路径也直透源站**（对照：curl 直连只放行页面/静态后缀，跳板只放行精确白名单路径）。定型启动参数：`--headless=new --remote-debugging-port=<p> --user-data-dir=<纯英文路径> --no-first-run --no-default-browser-check --user-agent="<常规 Chrome UA>" --lang=zh-CN --window-size=1366,850`；**不显式传 UA 时 headless 默认带 `HeadlessChrome` 字串** ⇒ 必被 Turnstile/CF 指纹拦 ⇒ UA 必须显式给。**通道矩阵铁律：同目标并行测「跳板 / curl 直连 / 本机浏览器」三通道的放行粒度（全站 vs 精确路径 vs 仅静态），取全放行者作主通道**；某通道 403 只说明该通道不行，别据此给目标判死。
- ★★★ **过挑后的主战工具 = 浏览器上下文 fetch 客户端**（POST 优先序①的工程化；实测 GET+POST 全片可打）：Playwright `connect_over_cdp` 连已过挑 Chrome → 在**已停在目标域的 tab** 里 `page.evaluate` 发 `fetch`——请求由页面宿主发出 ⇒ 免挑战、带全指纹、POST 可用。三条工程坑：① `redirect:'follow'` 且**回显 final URL**——`manual` 模式会把 302 显示成 `status 0`，把跳转藏掉；final URL 常泄露真实路由（实测跳转暴露后台路径）。② 二进制响应（验证码图等）**不能用 `text()`**（PNG 被转坏）⇒ 检 `content-type: image/*` 走 `arrayBuffer()` → 分块 `btoa` 回传 base64、Python 侧解码落盘。③ 每次调用重连 CDP、按目标域选 tab（一浏览器多任务防打错站）。模板：`scripts/cdp_fetch.py`。

## 13. 信封加密 API × 挑战 WAF：密码学在 Python 侧，传输在页面侧
目标 API 自带信封（请求 `encrypt-key` 头 + 密文体，响应按**响应头** `encrypt-key` 解密）**又**在挑战 WAF 之后时，**不要把信封重实现到页内 JS**：
1. **先判页面 WebCrypto 够不够用**：页面侧常缺算法原语（实测 `subtle.importKey` 不认 `RSAES-PKCS1-v1_5`、无 AES-ECB）⇒ 页内加密是死路，**别在页内试参数名/曲线/填充**，直接换分工。
2. **分工固定** = 「Python 造密文 → 页面只负责发 → Python 解密」：Python 侧用 `cryptography` + 从 bundle 复刻的信封实现造 `encrypt-key` 与密文体 ⇒ 把两者**当字符串参数传进页内 `fetch`**（`page.evaluate` 里只做发请求这一件事）⇒ Python 侧用响应头 `encrypt-key` 解出的 key 解响应。
3. **判「信封被受理」的唯一硬判据 = 响应能用我方解出的 key 解开**（HTTP 200 + 密文体）；解不开 ⇒ 那是服务端自己的错误包，与信封无关。
4. **`encrypt-key` 与 body 必须成对**（服务端用 ek 里的 key 去解 body）⇒ 错配组合得到的 500 / `Invalid padding bytes` **只证明配对错，不证明明文错** ⇒ 别据此改算法或换密钥。
5. **密文类响应禁止小切片**：日志用的 `slice(0,N)` 会截断密文 ⇒ 假 `Invalid padding bytes` ⇒ 全量取体（≥30–64KB）再解。
配方（可复制代码）见 `references/pass-channel-recipes.md` §2.7。

## 支持文件
- `references/pass-channel-recipes.md` —— 可复制配方（导航读 / 导航车辆+Fetch 改写 / **信封通道（Python 加密＋页面投递＋Python 解密）** / cookie 罐 / 票据语义 / 求解器提取 / 假 oracle 清单）。
- `scripts/acw_ticket_http.py` —— **票 + 纯 HTTP 回放器**：吃「`path<TAB>票<TAB>method`」清单，逐条打印真响应并自动标 ★ACW（票失效）。铸票仍由浏览器做，脚本头注释写了步骤与两条铁律。
- `scripts/cdp_fetch.py` —— **浏览器上下文 fetch 客户端**（过挑战后打受保护端点）：`cdp_fetch.py METHOD PATH [BODY|@file] [CTYPE|-] [HEADERS_JSON|-]`；自动 redirect-follow 并回显 final URL、二进制响应落盘 `*.bin`。前置 = headless Chrome(CDP) 已停在目标域。
