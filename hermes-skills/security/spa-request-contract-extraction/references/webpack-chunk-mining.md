# Webpack/Angular SPA 全量 chunk 契约挖掘

用于：黑盒探测拿不到请求契约(同错误码闸门)时，从已上线 bundle 取出**真实调用点**。

## 1. 抓入口与资产清单

```python
html = get("/h5")                       # SPA 入口
assets = re.findall(r'(?:src|href)="([^"]+\.(?:js|json))(?:\?[^"]*)?"', html)
# 典型: main.<hash>.js(业务主包) + polyfills.<hash>.js + runtime.<hash>.js
```

主包即 `main`，但它**只含服务定义与端点常量，不含字段名**。

## 2. 从 runtime 拿 chunk id→hash 映射

`__webpack_require__.u` 压缩后常成单行拼接模板，**直接正则 u 的函数体基本 0 命中**。改为正则**映射表本身**：

```python
maps = list(dict(re.findall(r'(\d{1,4})\s*:\s*"([0-9a-f]{8,24})"', runtime_js)).items())
# 一次可拿到上百个 id→hash（实测 170 个）
```

## 3. 批量抓全量 chunk

URL 模板 = `<publicPath>/<id>.<hash>.js`（`publicPath` 见 runtime 里 `__webpack_require__.p`；取不到就试入口同级目录）。

```python
# 同一 HTTPS 连接 keep-alive 顺序抓；失败则重连重试一次；每个 cap 700KB 足够
for cid, hsh in maps:
    st, body = req("/h5/%s.%s.js" % (cid, hsh))
    if st == 200 and len(body) > 500:
        save("h5chunks/%s.js" % cid, body); store[cid] = body
save("h5all.js", "\n".join(store.values()))          # 落盘后再 grep
```

实测：170 个映射抓到 168 个、总量约 6 MB，一轮完成。**先落盘再 grep**，不要在内存里循环只打印命中行。

## 4. 找"调用点"（关键步）

方法定义与 API 常量表都**没有字段名**：

```js
// 零字段信息 —— 只说明 body 是 n
getAuthState = function (n, t) { return this.http.post(C.getAuthStateUrl, { paramsToken: n, channel: t }) }
login        = function (n)    { return this.http.post(C.loginUrl,  n) }
```

字段名只在组件构造实参处。grep 调用点（超长单行用 `-o` 带上下文，别用行模式）：

```bash
rg -o '.{0,300}\.login\(.{0,500}'            h5all.js
rg -o '.{0,300}verfitySmsCode\(.{0,500}'     h5all.js
rg -o '.{0,300}UnionLogin\(.{0,500}'         h5all.js
```

判读模板 → 抄下来的对象字面量就是 body：

```js
// submit()
this.api.login({ phone: A.phone, code: A.smsCaptcha, nonce: this.smsCaptchaNonce, channel: this.channel })
//   成功回包: { uid }        ⇒ 4 字段四件套, 验证码键名 = code
this.api.verfitySmsCode({ userId: this.userId, smsCode: this.smsCaptcha.value, phone: this.bindCardForm.value.phone })
this.api.sendSmsCaptcha({ phone: n, captcha: i })     // ⇒ 回 { nonce }
this.api.UnionLogin(this.clientId, this.phone, this.channel)   // clientId/phone/channel 取自 URL queryParams
```

要点：
- `form.get("x")` / `loginForm.value` 里的字符串是**控件名**，经映射后才是字段名 —— 所以要抄映射后的键，不要照抄控件名。
- 同一业务流的不同端点字段名**不统一**（`code` vs `smsCode` vs `captcha`），必须逐个端点各抄一次。

## 5. 分层验证（零副作用）

1. 按抄到的完整字段集发一发，看是否越过参数闸门。
2. 逐字段置空 / 置假值，观察错误码是否**跨阶段跳变**。
3. 伴随字段（`nonce`/`channel`/`type`/`timestamp`）两发定位：`""`/`null` 一发 + `"0"*32`/`"1"` 一发。

| 观察 | 判读 |
|---|---|
| 所有形状同一错误码 | 前置参数闸门未过 ⇒ 回第 4 步读调用点 |
| 缺字段 → `参数错误`；给假值 → `认证失败` | 契约已通，进入凭证校验阶段 |
| 回显入参的 `<实体><id>不存在` | 免鉴权存在性 oracle（枚举面，可入报告） |
| `<实体>null不存在` | 必填字段没解出来，**不是**业务拦截 |
| 500 Internal Server Error + 不同 code | 参数已过、后端抛异常 ⇒ 继续补上下文字段 |

## 6. 请求体是密文时

前端加密模块常形如：

```js
var o = {
  key: location.href.indexOf("https://<host>") > -1 ? "<hexA>" : "<hexB>",   // 按域名切换的硬编码密钥
  decrypt: ..., encrypt: ...                                                  // AES-128-ECB / Pkcs7 / iv=""
}
```

- 出现 `decrypt(n.<field>)` ⇒ **服务端下发的该字段是这枚密钥的密文**（抓包即可本地解，高价值）。
- 本地复现（与 CryptoJS `toString()` 的 base64 一致，含默认 PKCS7）：

```bash
printf '%s' '<PHONE-REDACTED>' | openssl enc -aes-128-ecb -K <hexA> -nosalt -base64
```

- 密文只在**字段名正确**时才被读取 ⇒ 加密不是"参数错误"的原因，别把两件事混在一起排查。

## 7. 边界

短信/验证码登录的 `nonce` 由发码接口签发，而**发码接口会真实触达用户手机**。不调用、不爆破真实验证码；只做空值/假值/不存在 id 的零副作用探测，把"缺服务端签发 nonce"作为卡点如实上报，并先去换宿主/环境复用同一契约（测试环境校验往往更松）。

## 8. Vue-CLI / rollup 构建：API 模块 id → 导入者 → 调用点实参

App 主包（`app.<hash>.js`）常**只有 API 定义、零调用点**（调用点在 lazy 路由 chunk）：

```js
"73b7": function (A, C, g) { "use strict"; g.r(C);
  g.d(C, "a", (function () { return B })),   // a = /safe/infos
  g.d(C, "k", (function () { return I })),   // k = /safe/setmail
  ... }
function B(A) { return Object(E["a"])({ url: "/safe/infos", method: "get", params: A }) }
```

**① 反查模块 id —— 回溯窗口要小：**

```python
s = open("app.<hash>.js", encoding="utf-8", errors="ignore").read()
i = s.find("/safe/infos")
m = list(re.finditer(r'"([0-9a-f]{3,6})":function\(A,C,g\)\{', s[max(0, i-1200):i]))
mid = m[-1].group(1)          # ✅ 73b7（紧邻的那个才是承载模块）
```

窗口开大（如 12 KB）会先吃到**资源映射表**里的 4-hex 值（实测拿到 `76c1` = 一个 SVG 资产 id）
⇒ 拿假 id 去 grep 导入者**全 0 命中**，白一轮。

**② 读导出别名表**：模块头之后的 `g.d(C,"x",(()=>FN))` 列表 = `别名 → 端点` 一次定死整族
（实测：`a`=infos `k`=setmail `d`=editmail `h`=sendmail `g`=sendTgecode `i`=setdrawpwd `b`=editdrawpwd `e`=getNewDrawpwd）。

**③ 找导入者 —— 用赋值形态，不要用模块内部形参名：**

```python
re.finditer(r'([A-Za-z_$]\w*)\s*=\s*[A-Za-z_$]\w*\(\s*"73b7"\s*\)', chunk_text)
# 模块内部的 require 形参名（如 g）在导入者里不存在 ⇒ g("73b7") 恒 0 命中
```

**④ 读调用点实参 —— 正则要容忍 `(0,c["k"])(...)`：**

```python
re.finditer(re.escape(var) + r'\["([a-z])"\]\)?\s*\(', t)
# c["k"])( {loginpwd:this.loginpwd,email:this.email,ecode:this.ecode,tgecode:this.tgecode} )
```

漏掉 `]` 与 `(` 之间那个 `)` ⇒ **全 0 命中**（Vue-CLI 产物普遍是 `(0,c["k"])(…)` 形态）。

**⑤ 判读**：一次拿到整族真契约，例如
`setmail={loginpwd,email,ecode,tgecode}`、`getNewDrawpwd={email,ecode,drawpwd}`、
`editmail={oldemail,oldecode,newemail,newecode}`。
★ 「忘记密码」族端点常见形态是 **邮箱码 + 新密码，不需要旧密码**
（`getNewDrawpwd={email,ecode,drawpwd}` / `getNewLoginpwd={email,ecode,loginpwd}`）⇒
拿到契约就等于拿到「重置并直设新密码」的写入面，比继续爆破旧口令省一个量级。

## 9. 静态分片不在 API host：用入口 HTML 字节数认亲

lazy chunk 在 API / 后台域名上 404（且回一个小体积 WAF 页，如 1059B）时，别逐个域猜：

```bash
for h in a.online b.online int.x.com; do
  curl -s -m 12 -o /dev/null -w "$h %{http_code} %{size_download}\n" "https://$h/"
done
```

与本机已存入口 HTML **字节数一致**的那个域就是站点 host（实测 API 域 404、站点域回 2235B = 本地同一份）
⇒ 在该域按 runtime 映射表批量抓 `static/js/<name>.<hash>.js`，实测 76/76 全中。

## 10. 参数穷举的最快通道：同 path 页内 fetch（带票）

导航一次预热（~20s）后，页内 `fetch` **在原 `location` 基础上追加参数**
（`fetch(location.pathname + location.search + "&<名>=<值>", {credentials:'include'})`）
回**真业务 JSON**，约 1s/发 ⇒ 一次导航换几十次参数枚举，远快于每发一次导航。

★ **自建 URL（不带票）必被 WAF 挑战**：`fetch('/safe/setmail?suid=…')` 这种从零拼的地址即使同域也回挑战体
⇒ 一律沿用 `location` 的 query（WAF 票 = `(host,path)` 粒度、query 自由）。
★ 因此**每个新 path 仍需一次导航铸票**；同 path 内才享受 1s/发。
★ 页内 fetch **不要附加 `X-Forwarded-For` 等自造头** —— 会毁掉该通道的口碑/指纹（见 WAF 通道技能）。
