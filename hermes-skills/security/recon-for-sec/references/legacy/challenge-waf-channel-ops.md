<!-- archived from /root/.hermes/skills/security/challenge-waf-channel-ops/SKILL.md on 2026-10-21 -->

---
name: challenge-waf-channel-ops
description: Use when 打 JS 挑战型 WAF(ACW/CF 质询)挡住时. 通道矩阵+浏览器取数与投递.
---

> 归档卡：原目录 `/root/.hermes/skills/security/challenge-waf-channel-ops`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/challenge-waf-channel-ops/…')`，不要相对 `references/legacy/` 解析。

# 挑战型 WAF：通道矩阵与浏览器作业

## 触发指纹
- 响应 **HTTP 200** 但 body 是挑战页（`renderData` / `_waf_` / 混淆脚本外链 `/<a>/<b>/<c>`）
- 长度恒定异常（如 ≈110310 / 65137 / 48753）
- curl 被挑战、**真浏览器导航却能出内容**
- 「带全 cookie、全指纹头、TLS 伪装也照样挑战」

## 0. 铁律
1. **挑战页是 200** ⇒ 判成功看 body 特征与长度，不看状态码。
2. **放行面由请求类型决定，不由路径/cookie/头决定**：只放行「顶层导航(doc)」与「后缀白名单(.js/.css/.ico/.log 等；**追加实测 `.json`/`.txt` 同样放行 ⇒ 白名单逐目标补测，别假定只有 `.js` 一类**）」。**页内同源 XHR/fetch 一律挑战** —— 即使该路径在站点自身白名单内（`/captchaImage`、`/login` 这类），即使挂上了导航票据。
   ★★★★**放行的第三个面 = 跨源 XHR，条件是 `Origin`/`Referer` 命中 WAF 白名单域**（通常是**平台自己的前端域**——它常挂在另一张 CDN 上、本身没有 ACW）：从该域页面 `fetch(接口域, {mode:'cors', credentials:'omit', …})` 实测 **200 + 真业务响应**，且**方法（含 POST）/头/Content-Type/体全可控** ⇒ **这条优先于一切票据、导航车辆、求解器方案，开工先探它**（配方见 `references/pass-channel-recipes.md` §2.5）。判据 = 回包是业务响应且无挑战特征；`credentials:'include'` 会因接口侧 CORS 拒带凭据而 `TypeError: Failed to fetch` ⇒ **永远 `omit`**（该通道不需要 cookie）。
   ★★ **但「白名单 `Origin`」≠「自填 `Origin` 头即可」**：把该通道的完整请求头（含自填 `Origin: https://<前端域>`）搬到纯 HTTP 客户端回放，多组差分**全部吃挑战** ⇒ WAF 校验的是 **TLS/浏览器指纹**，`Origin` 只是必要条件 ⇒ **这条通道只能在真浏览器上下文里发**（页内 `fetch`）；别用 curl/requests 复刻它，也别因伪 Origin 被挑战就否掉这条通道本身。
   ★★**例外（实测打通过整片读写面的首选通道）**：从**目标自己的页面**（同 ACW 部署、能真正加载出来并跑完挑战的那个域）里发出的页内 XHR，**页面脚本会自动给它的请求 URL 追加 `?md5__1713=<token>`** ⇒ 不被挑战，直接回真数据。判据是「请求由这个页面发出」，与 cookie/指纹头无关；从别的域或 `about:blank` 里发的依旧吃挑战页（本形态下这是逐**页面宿主**属性，见 §11 末条）。
   ★★**方法也是独立变量**：同一页面宿主上实测「GET 导航全过、页内 `fetch` 的 **POST** 6/6 全吃挑战」⇒ 需要 POST 时只能走「导航车辆 + Fetch 域改写」，**不要以为页面 XHR 豁免就能发 POST**。
3. **恒定响应不得当 oracle**，**框架级同错不得当成果**（见 §3）。
4. **别把一处结论当普适**：同一家族不同实例/版本对「导航车辆改 POST」的反应可以**相反**（一处降级为 `GET …?alichlgref=`，一处完全放行）。用 rewrite 回执自测，**不要凭既有笔记放弃通道**；也不要反过来假定它一定通。
5. ★★**判层靠「明文 vs 信封」的配对差分，不靠状态码**：同一 path、同一出口，连发**明文**与**信封**（`encrypt-key` 头 + 加密体）两发 ⇒ 明文 `403 {"status":403,"error":"Forbidden"}` + 信封 `200` = **闸在应用层信封**（既不是 WAF、不是 IP 白名单、也不是票）⇒ 见到 400/403 **先补一发信封对照再归因**。只看 403 就判「源站被反爬 / EIP 被封」，会把整片本来已通的面误杀成死面。
6. ★★**同一 host 上「挑战型出口」与「直通型出口」可并存** ⇒ 开工第一发是 **出口 × {明文, 信封} 小矩阵**（每出口 2 发，几分钟出结论），而不是先信「换出口对挑战型 WAF 无效」。实测同一刻同一路径：三个出口吃 ≈110KB 挑战体，跳板与直连直达应用层。§7 首条只适用于「连 `GET /` 都挑战」的实例。

## 1. 通道矩阵（按性价比选）
| 需求 | 通道 | 做法 |
|---|---|---|
| ★★★★ 任意方法/头/体（**真 POST 通道，首选**） | **跨源 XHR + 白名单 `Origin`/`Referer`** | 页面停在**平台自己的前端域**（= `Origin`/`Referer` 要填的原值，取自 SPA `baseURL` / 真抓包）→ 页内 `fetch(apiBase+path,{method,headers,body,mode:'cors',credentials:'omit'})` ⇒ 实测 200 + 真响应，**POST 可用**，无需 cookie/票据/求解器（配方 §2.5） |
| ★★读写数据 | **目标自己页面的页内 XHR** | 选同族中**能加载出来**的页面（常是 OSS/营销落地域，可能与接口域**不同出口**）→ 页内 `xhr.open(m,url,false)` 发请求，带**从 App 自身请求里抄下来的设备头**（`visitorId/visitorName/fpFromCache/requestId`）+ 有效 Bearer；token 由页面脚本自动补 ⇒ 实测整片只读面 + 写通道均 200 |
| GET 读数据 | **导航读通道** | `Page.navigate` 到目标 URL（含 JSON 端点）⇒ 浏览器把 JSON 渲染为文本 ⇒ 读 `document.body.innerText`；连 401/403 的 JSON 错误体也能读回 |
| POST 投递 | **导航车辆 + Fetch 域改写** | `Fetch.enable`(Request 阶段) ⇒ 设 path/method/body/headers ⇒ `Page.navigate` 到该路径 ⇒ WAF 视为 doc 放行、应用实收 POST |
| ★带自定义加密头的 GET | **导航 + `Network.setExtraHTTPHeaders`** | 挑战型 WAF 下**唯一能给导航注入自定义头**的路（`Fetch.continueRequest` 改自定义头 Chrome 不生效）：密文放 `?encryptParams=`，密钥/指纹头（`encrypt-key`/`visitorId`/`requestId`）由注入提供 ⇒ 实测头**真发出**（用 `Network.requestWillBeSent` 核 verify）且能穿挑战到应用层 |
| ★★★ 机外复现 / 批量提速（首选） | **票 + 纯 HTTP 客户端直发** | 真浏览器导航到该 path（解出质询）⇒ 从 final URL 取 `encode__1715=`/`md5__1713=`/`refer__1720=` 的**完整值** ⇒ 纯 HTTP 客户端把它原样追加回**同 path 同 method**（`requests.get(host+path+"?encode__1715="+票)`）⇒ **200 真业务数据**。★ **无需 cookie、无需指纹头、无需与铸票同出口**（实测无 cookie 的裸 requests 直通）；★ 票在「path+method」维度内**可重复使用**（同票连发 3 发全 200）；★ **跨 path 或跨 method 立即回挑战**（GET 票发 POST ⇒ 挑战）⇒ **每 path 铸一次**：铸票 ~6s、之后毫秒级直发，整片只读面可脚本化。
  ★★ **票绑定的粒度是 (host, path[, method])，query 不受约束** ⇒ **同一张票可复放任意 query 参数组合**（`?<票参数>=<票>&k1=v1&k2=v2`）：端点参数名/类型契约探测、字段差分对照**全放到纯 Python 侧做**，**绝不为每个参数变体重铸**（铸票 ~6s 且每次都在吃惩罚预算）。整族参数契约可由此一趟取全。
  ★★ **票参数名逐 host 不同**（实测见过 `type__1350=` / `encode__1715=` / `md5__1713=` / `refer__1720=`）⇒ 从 final URL **正则抓 `<字母串>__<4位数字>=`** 定位，别硬编码，也别假定同族各台同名。跑法见 `scripts/acw_ticket_http.py` |
| 端点存在性/鉴权层判定 | 导航读通道看 body | 401(认证层) / 403(前置过滤器) / 404 / 应用 JSON 形态各异，可据此分层 |

## 2. 改写回执 = 自证（每次必打）
输出 rewrite 记录（形如 `/login|POST|77b|hdr=1`）+ **final URL** + body 前 N 字：
- `|POST|<n>b|hdr=1` ⇒ 改写生效；
- final URL 变成 `?alichlgref=<原URL>` / body 丢弃 ⇒ **被该实例降级为 GET**，此路不通；
- 应用返回**它自己的** 403/500/JSON（不是挑战页）⇒ 已穿过 WAF，从此按应用语义推进。

**先跑一次 GET 对照组**确认改写管道本身生效，再判「WAF 降级」还是「改写没生效」。

## 3. 两种假 oracle（别把噪声当成果）
1. **恒定响应**：不带特殊头/缺头的对照与实验**同字** ⇒ 该通道零信息量，立即换通道。
2. **框架级同错**：后缀矩阵探针若对**真实路径**与**故意编造的不存在路径**返回同一个框架级错误（都 500 / 同一段 Spring Boot 错误页）⇒ 只穿了闸门、根本没落到控制器 ⇒ **停止生成后缀变体**（逐个试 `.css/.log/.ico/.jsp` 是纯烧时间）。
   ★ **后缀族一次性判死的结构性判据**：「静态后缀能过 WAF」与「框架无该后缀映射」可以同时成立且互斥（实测 `.jsp` 过 WAF 但 Spring Boot 回 `Whitelabel Error Page`）⇒ 该后缀族不能再加变体；同理，**「带信封」与「无信封对照」同字** = 该路径根本没进被测逻辑，在此路径上堆任何载荷形状都是零信息量（实测 20 种形状同字，整组结论作废）。
3. **假绕过（分号矩阵参数）**：`;x=.js`/`;a=.css` 这类形态**确实**能穿过 WAF 与**前置路径过滤器**（响应从 403 变 500，看起来「进去了」），但**开了 `StrictHttpFirewall` 的 Spring 拒收任何含 `;` 的 URI** ⇒ 恒 500（连乱写路径也 500）。**判据 = 拿同变形的乱写路径做对照**：乱写路径同样 500 ⇒ 那是过滤器解析 `;` 的通用异常，**不是「进了控制器」，更不是绕过** ⇒ 别再加 `//p`、`/p%2e`、`/P`、`/p/`、`/p%20` 变体烧时间。

### 3.4 「WAF 放行」≠「应用可达」：三层归一化不一致（通用律，先读本节再排形态变体）
同一条 URI 会被**三层各自归一化**，三者常数不同：
- **WAF**：按「路径是否以静态扩展名结尾」放行 + 路径关键词黑名单；
- **中间过滤器**：可能**先剥 `;` 矩阵参数**再匹配自己的白名单（⇒ 后缀形态被它剥、矩阵形态被它放行）；
- **框架路由**：可能**不剥** `;`（⇒ `;x=.js` 恒 `NoHandlerFound` 500），且静态后缀映射只在**开了 `use-suffix-pattern-matching` 的实例**才落到 handler（逐台配置，必须探）。
⇒ **一个形态几乎不可能同时满足三层**：后缀换到 WAF 放行却破坏路由，矩阵参数换到过滤器放行却撞框架 ⇒ 形态矩阵每加一个变体 = 同时赌三层的归一化，命中率极低。**别在形态上继续堆 `.css/.log/.ico/.jsp/;//p/%2e/后缀双层` 变体（§3 已判死）；正解是换通道或换端点。**
**一发定层的差分配方**（同一真路径，多发交叉，单发结论一律不采）：`GET <realpath>`、`GET <realpath>.js`、`POST <realpath>.js`，外加一发**乱写路径的同变形** `<bogus>.js` 做负对照 ⇒ 交叉即可读出「后缀映射开否 + permitAll 是否含 `/**/*.js` + 是否 `StrictHttpFirewall`」。**含 `;` 的 URI 全 500（连乱写路径也 500）= 通用解析异常，不是「进了控制器」。**
★ **关键词黑名单按归一化后的路径生效且对编码变体免疫**：实测 `actuator`/`heapdump`/`..`/`download`/`resource` 命中即挑战，`%64ownload`、`downLoad`、`//`、`./`、`%2f` 等 11 种变体**全部仍挑战** ⇒ 命中关键词后**停止做编码变形**，改换路径或换通道（WAF 规则列表是通用黑名单，也**不能**反过来当作「该组件存在」的证据）。

## 4. 求解器资产优先级
挑战页把求解器写进 `localStorage['_waf_<id>']`：值 = **URL 编码**的混淆 IIFE + 尾部 `||<时间戳>`。`decodeURIComponent(v.split('||')[0])` 即得可执行 JS，在真浏览器（或 Node+jsdom 垫片）里 `eval` 复用其铸造逻辑 —— 比从外链那个 ~174KB 混淆脚本手抠算法**短一个量级**。
- ★ **只为「过闸取数」别碰求解器**：铸票 + HTTP 回放（§1 首行）已够；逆求解器只在「必须机外零浏览器跑通整链」时才值得投轮次。
- ★★ **POST 铸票 = 票据通道的天花板（已实测，别再重试）**：票**只能由导航铸，而导航恒 GET** ⇒ 发不出 POST 的票。三路封死：GET 票发 POST ⇒ 挑战页；`Fetch.continueRequest` 把导航 method 改成 POST ⇒ **Chrome 直接拒绝改导航方法**；真表单 POST（导航型）⇒ final URL 被反爬接成 `?alichlgref=` 降级，且 **WAF 重放会把请求体复位成原始表单值**（改写后的体到不了应用，见 `references/pass-channel-recipes.md` §2.6）。⇒ **需要 POST 时不要再写第 N 个导航/表单/方法改写变体**：走「跨源 XHR + 白名单 Origin」（§1 首行，实测可 POST），或该实例的页内 XHR 豁免。

## 5. CDP 驱动纪律
- **拿结果必须用同步调用接口**（如 `t.call(...)`）；fire-and-forget 的 `send` 只返回消息 id ⇒ 取 cookie/响应体时会静默得到空值，白白绕远。
- 共享调试浏览器里一旦开了同家族的多个标签，**按精确 host 选页**，不要用域名家族子串（`xwallet` 会同时命中 `xwallet8` 与 `xwallet801` ⇒ 打错目标）。
- 新开标签用 `Target.createTarget`（部分实例上 `/json/new` 不灵）。
- ★**复用「现成」调试实例前先断言它真能用**：`/json/list` 里 url 写着目标域、tab 实际停在**错误页**（`location.host` 为空 / `chromewebdata`）是常态 ⇒ 页内 `fetch` 全部 `TypeError: Failed to fetch`（opaque origin），而脚本照常「跑完」并打印一批假否定。判据 = `location.host` 等于目标域 + `document.readyState`；不满足就 `Target.createTarget` 新建并重新导航，别在原 tab 硬发。**每批先打印宿主 origin 自证**，不满足则整批登记「未测」。
- ★**需要外联时自起独立实例，绝不杀已有 Chrome**：历史遗留的调试实例常**没有代理出口**（症状 = 导航一直加载/超时，如卡死的 `:9227`）⇒ 起新实例用独立 `--user-data-dir` + 新 `--remote-debugging-port` + `--proxy-server=socks5://127.0.0.1:<port>`（参数见 §12）；**杀进程必须先取得用户同意**，且旧实例可能承载着已解题的会话。起实例前先纯 HTTP 探一遍候选出口（`curl -x socks5h://127.0.0.1:<p> https://<host> -o /dev/null -w '%{http_code}'`），把已验证可通的写进 `--proxy-server`。
- ★**浏览器类脚本别在前台等**：导航/解题/页内 fetch 循环在终端前台极易撞满超时（实测 420s）⇒ 走后台 + 硬超时 + 结果落盘（`> xpN.out 2>&1`），再读文件判读；前台超时会把「还没跑完」误读成「通道不通」。
- ★ **自研「pump 型」CDP 客户端：`pump(seconds)` 只把事件喂给 `on_event`、不返回事件列表** ⇒ 要收 `Network.requestWillBeSent` / 读 `getResponseBody`，必须**覆写 `on_event` 自己攒**；写 `for e in t.pump(...)` 拿到 `None`，症状是「脚本只打表头就退出」。同理：`send` 是 fire-and-forget、必须用同步 `call` 才拿得到回执（§5 首条）。

## 6. 客户端白名单 ≠ 服务端放行面
站点 bundle 里常有免签/免认证白名单数组（形如 `pl="/,/login,/register,/captchaImage,/profile/**,/common/upload,…"`）。它是**接口清单的高价值字典**（可反查真实端点名），但**不等于服务端放行面**：实测 bundle 白名单含 `/login`，服务端仍 403。
★ **另一组更值钱、且最常被忽略的数组 = 「不加密 / 不追加签名」的 URL 列表**（形如 `ut=["/app/x/uploadCover","/app/x/file/download"]`，常与一行 `e.data instanceof FormData && delete e.headers["Content-Type"]` 同处）。这些端点是**唯一天然不要求破信封/破签名的 POST·multipart 面** ⇒ 写原语优先打它们，而不是回头改信封实现、换密钥、猜公钥。
★ **但 WAF 仍按扩展名独立拦**：同一上传端点，合法图片 → 200 + 落静态桶 URL，而 `.jsp`/`.svg`/双扩展名/穿越名 → **405 + WAF 拦页（根本没到应用层）** ⇒ **「上传落静态存储」形态下拿不到 RCE**，别在这条线上连烧轮次；写面价值应改找「其他不加密端点的业务写」或「读原语」。
★ **上传面能否当 shell：一次判决就够，别再堆扩展名变体** —— 拿**真图字节（合法 JPEG）+ 可控文件名**做一组对照：`x.jsp` / `x.jpg.jsp` / `x.jsp.jpg`。若回包 URL 是**服务端自生成的 UUID 名 + 扩白名单**（实测只放 `bmp/gif/jpg/jpeg/png`），该面即判死：文件名不进存储路径、扩展名由服务端决定 ⇒ 不必再换 Content-Type、双扩展名、穿越名。**失败语义要分层记**：`405 + WAF 拦页` = 根本没到应用层（WAF 按扩展名拦）；`500 读取图片失败 / Invalid image` = 到了应用层被**服务端图像解码**拦 —— 两者不是同一件事，混记会得出「目标封了上传」的错误结论。
★ **免签/不加密白名单端点（`ut=[...]`）的参数名只能从 bundle 挖**：白名单只给**路径**，字段名要回调用点取对象字面量（形如 `i=(t={},o={})=>r("/app/x/file/download",t,o)` 的调用者 `{fileid:t, orderid:t, type:47}`）。**参数对错的硬判据 = 错误文案差分**：字段名错回**通用异常**（`发生异常`/框架 500）；字段名对而对象不存在回**业务级文案**（`订单不存在`）⇒ 见到业务级文案即证明契约命中，此时只差一个有效对象 ID，**别再改参数形态**，改去找那个 ID（如按用户隔离的列表接口、发货/订单页）。

## 7. 侦察纪律
- 换出口 IP / 跳板对挑战型 WAF 通常无效（连 `GET /` 都挑战）—— 别浪费跳板，但同一实例可能对源站直连放行，先探。
- 低频；**处罚是阶梯的，别连发自造请求**：`Punish-Loc: keepper` + 恒定长度（如 110310）= 惩罚态 → 继续喷升级为 **200 + 空体** → 再升级为**连接被 reset（curl `000`）**。自造形态（自造 POST / 跨域 XHR）每试错一次可能升一级 ⇒ 试错必须**极低频 + 每次只换一个变量**，优先走「目标自己页面内 XHR」。
- ★ **CF（Cloudflare）系实测惩罚梯度（补）**：`200 + 挑战体（Just a moment / 请稍候）` → **`429 + Cf-Mitigated: challenge`**（数据中心出口的 CF 非浏览器请求配额极低，数发密集即中）→ **`000`/RST（连接被重置）**；**家宽与跳板出口各自独立计罚**（实测：直连内页 RST 的窗口里，跳板出口仅 429）；命中即**整批停手冷却 ≥5–10 分钟**，期间不发任何目标请求（含「换个路径/端点看看」）。
- ★★ **阶梯再上一级 = 整窗不可达，且会静默污染整批结论**：连续导航后该 host 对**所有**请求（含铸票导航本身）回 `ERR_CONNECTION_CLOSED` / Python `SSL: UNEXPECTED_EOF_WHILE_READING`；窗口内换路径、换形态、换票据形态全部无用 ⇒ **命中即整批停手冷却，不要「换个端点再试」**。
  ★★ **铸票步失败会污染结论**：惩罚态下导航不产出票 ⇒ 回放全灭，脚本却**照常跑完**并打印出一批看起来像**否定/判死**的结果 ⇒ **每轮先断言「本次导航确实拿到票参数」**，断言失败则整批结果作废，登记为**「未测」而非「已判死」**（本族曾据这种空结果把未测面误登记成已排除）。
- ★★ **口碑是累积的、按出口记账，且升上去会把「已经打通的放行面」一起关掉**：同一出口对同一 host 持续打点后，**原本免挑战的 GET、甚至带有效 Bearer 的请求也会翻成挑战页**（实测某实例：先前 GET 面直通真数据，高频打几轮后**连带票的 GET/POST 全部吃 ≈110KB 挑战体**）⇒ **开工就把出口分成「侦察/扫面（脏）」与「取数/写面（干净）」两条，主面永远用没被打脏的出口**；发现已通的面突然整片挑战，**先换出口复测**（多半是口碑掉了），别当成「目标改了配置」重写整套打法，也别把带票请求的挑战读成「票失效」。
- ★★ **`X-Forwarded-For` 是第二个记账键，绝不能混进页内通道**：页内 `fetch` 一旦带上 XFF（哪怕只为绕登录 IP 白名单 / 解封），WAF 就按新键重新计账 ⇒ **该请求连同整条已打通的页内放行面一起翻成挑战**，且撤掉头**不自动恢复**，须重新导航建会话。⇒ **IP 白名单绕过、出口轮换、换 IP 解封这类动作只在纯 HTTP / 铸票重放通道上做；页内通道永远不发 XFF**（把「绕白名单」和「取数」拆成两条通道，别在一条上同时干两件事）。
- 每次实验记录：状态码 + body 前 200 字 + 长度。

## 8. 批量扫路径：逐路径 doc 导航，别用页内 fetch 扫
**反例（烧过一次）**：导航到 `https://host/` 后再在页内同源 `fetch` 循环扫 27 条路径 ⇒ 一旦某次导航失败/被 WAF 重置（`ERR_CONNECTION_CLOSED`），页面留在**上一个 origin**，此后所有 fetch 全部 `TypeError: Failed to fetch` ⇒ **整批 270 条结果零信息量**。
**正解**：每个 `(host, path)` 一次 `Page.navigate`（doc 导航是放行面，**但不是恒过 —— 见 §11 重试纪律**），读 `document.body.innerText` + `document.title` + 长度。代价 ~6-7s/条（80 条约 10 分钟），换来**每条结果都可信**。判读：`Whitelabel Error Page` = 应用层 404/403；`很抱歉…被阻断` = WAF 规则命中（**只证明有该规则，不证明组件存在**）；`Invalid encrypted request` = 命中信封过滤器；应用 JSON = 真业务响应。
**推论铁律**：`/actuator` 若返回应用自身 404，则 `/actuator/{env,heapdump}` 被 WAF 拦**不能**当作「组件已注册」的证据（WAF 规则列表是通用黑名单）。

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
