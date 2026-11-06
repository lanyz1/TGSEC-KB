---
name: acw-js-challenge-waf-bypass
description: Use when 打阿里云 ACW 挑战式 WAF. 放行面判定+假 oracle 陷阱.
---

# 阿里云 ACW（JS 人机校验型 WAF）作战卡

## 触发指纹
- 响应 body 含 `<textarea id="renderData">{"_waf_bd8ce2ce37":"…"}</textarea>`
- `Server: Tengine`；**HTTP 200**（挑战页是 200，不是 403！）
- 挑战脚本外链形如 `/<path>/<path>/<path>`（如 `/u21pn7x6/r8lw5pzu/psk8uqfi`），约 174KB 混淆 JS
- 页面被重定向到 `/?<word>__<4位数字>=<混淆串>`；**参数名前缀每 host 不同**（同批实测：`refer__1720` / `type__1719` / `type__1718` / `timestamp__1717`）⇒ 抓令牌的正则必须写成 `([a-zA-Z]+__\d{4})=`，写死名字必失败
- 请求被降级时出现 `?alichlgref=<原URL>`
- cookie：`aliyungf_tc` / `acw_tc` / `ssxmod_itna` / `ssxmod_itna2`

## 0. 铁律（先读，省几小时）
1. **挑战页是 HTTP 200** ⇒ 「200 = 成功」是错的。判成功必须看 body：含 `renderData`/`_waf_` 或长度 ≈110310 即为挑战。
2. **恒定响应不能当 oracle**。任何通道先跑「不带特殊头/缺头」的**对照**；若对照与实验返回**同一字响应**，该通道零信息量，立即换通道。
3. **换出口 IP / 跳板机对 ACW 无效**（连 `GET /` 都挑战）。别浪费跳板。
4. **ACW 只放行「顶层导航」与「后缀白名单路径」**；一切 XHR/fetch 一律挑战 —— 与 Origin、cookie、指纹头、TLS/JA3 伪装**都无关**。

## 1. 放行面判定矩阵（实测）
| 请求形态 | 结果 |
|---|---|
| 顶层导航（`Sec-Fetch-Mode: navigate`，GET） | ✅ 放行（需先解挑战） |
| 任意 XHR / fetch（含页内同源、带全部 cookie） | ❌ 200 + 挑战页 |
| 路径后缀 `.js .css .png .jpg .jpeg .gif .svg .ico` | ✅ **放行（连 POST 也放行）** |
| `;x=.js` 矩阵参数（`;` 后跟白名单后缀） | ✅ 放行（WAF 看**原始 URI 后缀**） |
| `.html .do .jsp`、`?a=.js`（查询串）、尾斜杠、`..;/`、`//`、`/./` | ❌ 挑战 |

⇒ **能过 WAF 且到达应用的只有两类：`;x=.js` 矩阵形态，和字面 `.js` 形态。**

★ **三态判层法（比看状态码可靠）**：① `110310B` + `renderData`/`aliyun_waf_aa` = 未过 WAF；② 骨架自家 404（如 `235B` `Powered by JFinal`）= **已到应用**；③ 容器英文 404（`786~801B` 含 `requested resource [...]`）= 到 Tomcat 但 URL 失配。**同名后缀在不同站结论可相反，只认字节数+文案。**
★ **完整放行面（实测）**：GET+导航令牌 ✅；**HEAD ✅（200|0）**；**OPTIONS ✅（200|2 = `{}`）**；**任意方法 + `.jsp` 后缀 ✅（POST 也过）**。被拦：无后缀的 POST/PUT/PATCH/DELETE、带 query 的 curl。
★ **坑：`.js`/`.css`/`.json`/`.xml` 后缀在 nginx `location /` 会 prepend 前缀（如 `/walletsysintf`）⇒ 双层路径 ⇒ 永远 404**（Tomcat 的 `requested resource` 句会显示双层）。故资源后缀白名单 ≠ 可用通道。
★ **`;x=.jsp` 矩阵参数**: Tomcat 不剥 ⇒ 污染 actionKey ⇒ 自家框架恒 404。

★ **`;x=.js` 不是通用放行**（多 host 实测反例）：在 Tomcat + Servlet context 站上，`;x=.js` 会让 **context 匹配失败**，返回**第三种响应格式**（英文 `HTTP Status 404 – Not Found`，约 789B）——既不是挑战页(110310B)也不是框架 404(235B)。⇒ 判「是否到应用」**只能靠响应字节数/格式**，不能靠后缀规则；同一后缀在不同 host 上结论可相反。
★ **`.jsp` 后缀（无 query）**：某些站到应用但框架不认（JFinal 对 `.jsp` 回自身 235B 404）。

## 2. 应用侧闸门（与 WAF 解耦后才能看）
WAF 与框架对路径的视图不一致，是可利用缝隙也是陷阱：
- WAF 看**原始 URI 后缀** → `;x=.js` 放行。
- Spring `UrlPathHelper` **剥离 `;` 矩阵参数** → 路由可能命中真端点；但**应用自己的加密/权限过滤器按剥离后路径判定**。
- ⇒ 结果：`;x=.js` 能到应用，但过滤器判「真路径」⇒ **无加密头 → 恒定 400**；带加密头 → **同为恒定 400**（连「不带加密头」也是同字）⇒ **零判定力**。

## 3. 假 oracle 陷阱（最贵的坑）
常见误判：`POST /<real>;x=.js` 明文 → 400 `Invalid encrypted request`；`POST /<real>.js` 明文 → 401/404（过闸门）
⇒ 于是误以为「400=信封错、401=过闸门」。**错**：
- 该 400 对「无加密头 / 缺 key / 各种 padding / 各种明文外壳」**全部同字** ⇒ 无法反映信封正确性。
- 字面 `.js` 路径可能被闸门当静态资源而**永不解密**，见加密头即拒 ⇒ 仍无判定力。

**正确做法**：先把「过 WAF 的形态」与「应用判定」解耦，**只在能同时满足（真路径 + 任意方法/头/body）的通道上**才谈 oracle。

## 4. 绕不过去的三条（实测反证，别再试）
| 尝试 | 结果 |
|---|---|
| Python 复用挑战后 cookie + 伪造 `Sec-Fetch-Mode: navigate` 全套导航头 | 仍挑战（ACW 认 TLS/JS 执行证明） |
| 把 `refer__1720` 令牌挂到真路径（查询串/头/cookie） | 仍挑战（令牌只对导航有效） |
| CDP `Fetch.continueRequest` 把**导航改写成 POST + 自定义头 + body** | ACW 把它**降级为 `GET …?alichlgref=<原URL>`**，body/头全丢 ⇒ 应用只见无加密 GET |
| 表单式 / 导航式 POST | ACW 降级为 `GET …?alichlgref=`，body 丢弃 |
| `X-Http-Method-Override` / `?_method=` | 404（WAF 只看 URL 形状） |

## 5. 三条出路（按性价比排序）
1. **只打「能过 WAF 的面」**：`.js/.css/.png` 后缀路径 + 顶层导航。
   - 导航探测法：`Page.navigate` 到真路径，读渲染出的 JSON ⇒ 能拿到应用真实响应。
   - `.js` 后缀探测法：把真实 URL 加 `.js` 发 POST/GET ⇒ 常能拿到框架层响应（401 认证 / 404 路由），探测端点是否存在、鉴权层次。
2. **逆向挑战脚本**（唯一能解锁真路径的路）：抓 `/…/…/…` 那个 174KB 混淆 JS，还原 `renderData` → 令牌 的算法，离线生成 `refer__1720` / 挑战 cookie，让普通 HTTP 客户端过 WAF。工作量按天计。
3. **换面**：若业务另有前端域/姊妹域/移动端/开放平台，从那些不经 ACW 的入口打。

## 5.5 ★★铸签重放：把普通 HTTP 客户端变成全速 GET 通道（最实用的一招）
**令牌是「(host, 路径)」粒度的查询参数，且在同路径内可重复使用** ⇒ 铸一次，用 requests 全速打该路径。

```python
def mint(path, wait=25):           # 导航 → ACW 解挑战 → 从 location.href 抓令牌
    t.call("Page.navigate", url=HOST + path)
    t0 = time.time(); found = {}
    while time.time() - t0 < wait:
        t.pump(2)
        href = str(t.ev("location.href"))
        for m in re.finditer(r"([A-Za-z_]+__\d+)=([^&#]+)", href):   # ★名字勿写死
            found[m.group(1)] = urllib.parse.unquote(m.group(2))
        body = str(t.ev("(document.body?document.body.innerText:'')"))
        if found and body and "renderData" not in body: return found
        time.sleep(0.4)
    return found

sig = mint("/mer/list")                     # {"refer__1720": "2790552d-..."}
r = requests.get(HOST+"/mer/list?"+urlencode({**sig,"pageNum":1}), verify=False)  # ✅ 无 cookie 也过闸
```

实测（同批）：int3 `encode__1715` 铸签后 `/captchaImage` `/getInfo` `/getRouters` ✅；int7 `refer__1720` 铸签后 `/mer/list` `/mer/info` `/mer/user/list` `/app/list` ✅。
- **签名按 (host, path) 绑定**：换路径 ⇒ 必挑战；换 host ⇒ 必挑战。一次导航换一条路径的通道。
- **GET 面完全打开**（无需 cookie；`Server: Tengine` 收到 `?<name>__<NNNN>=<token>` 即放行）。
- **POST 不受益**：用**路径正确**的签名 POST（`/captchaImage?encode__1715=<v>`）**仍挑战** ⇒ 证明是**按方法硬闸**，与签名无关。POST 只能走白名单后缀（`.js/.css/.ico/.png/.woff/.svg`）或静态精确路径（`/favicon.ico`）。

## 5.6 三层闸模型（2026 实测，同族多 host 共性）
拿不到数据时按层归因，别混为一谈：
1. **L1 阿里云 ACW（边缘）** — body 含 `renderData`/`aliyun_waf_aa`，HTTP **200**，约 110310B。GET+铸签可过；POST 恒挑战。
2. **L2 应用路径白名单** — 过 L1 后仍返 `{"timestamp":…,"status":403,"error":"Forbidden","path":"/login"}`（Spring 默认错误 JSON）⇒ 该 host 把路径**精确白名单化**，XFF/X-Real-IP 注入全无效（**别误判成 IP 判**）。
3. **L3 自研加密过滤层** — 过 L1+L2 后返 `{"code":400,"msg":"Invalid encrypted request"}` ⇒ 需家族加密信封（RSA 封随机 AES 密钥 → `encrypt-key` 头 + AES-ECB 体，GET 用 `encryptParams`、POST 用 body）。**公钥按域族不同（801 / 802 不通用），拿错公钥 = 该 400 恒同字**。
★ **L3 可能事后开启**：同一 host 的同一明文本子串接口，早批可读全量、回溯复测已变 `Invalid encrypted request` ⇒ **拿到数据先落盘快照**，别假设接口会一直开着。

## 5.7 假泄露陷阱（差点写成战果）
- `POST /system/user/list.js` → **200 且空 body** ⇒ 看着像「过闸鉴权的未授权接口」。实为 **Tengine 静态层对 `/system/**` 的 200 空响应**；同 host 的 `/getInfo.js`（无静态目录）返 **404** 才是 Spring 在答。判据 = **换一条同前缀但无静态目录的路径对照**。
- `POST <任意路径>.js` 若返 `{"msg":"请求访问：<path>，认证失败","code":401}` = **过了 ACW 但止于鉴权入口**（认证失败 ≠ 未授权可读）。
- 静态后缀会**改写路径**，Spring 6 已移除后缀模式匹配 ⇒ `.js` 形态**到不了** `@RequestMapping("/login")`。分号形态（`/login;x=.js`）能过闸但被 Spring `StrictHttpFirewall` 拒（500）。

## 6. 侦察纪律
- 每条通道先跑**对照**（缺头/无头/明文），再下结论。
- 每次实验记录：状态码 + body 前 200 字 + 长度。**长度 110310 = 挑战**。
- 低频：ACW 见过 `Punish-Loc: keepper` 处罚标记。

## 7. 工具片段
```python
# 挑战判定
is_challenge = ("renderData" in txt or "_waf_" in txt or len(txt) == 110310)

# CDP 导航探测（能过 WAF，读到应用响应）
t.fire("Page.navigate", url=BASE + path)
t.pump(10)   # 事件循环；结束后读 Network.getResponseBody(networkId)
```
