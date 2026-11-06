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

