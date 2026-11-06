# 用客户端自带的加密对象当 oracle（加密 SPA / TMA / 混合 App）

适用：请求体是 `data=<hex/base64>`、`crypt=V6`、`sign=` 一类加密信封，bundle 混淆/密钥难静态提取，但**目标自己的客户端在真实浏览器/WebView 里跑得好好的**。

核心判断：**页面已经加载了完整加密实现时，不要重造密钥；直接调它的函数。** oracle 产出的 body、签名、时间戳格式与服务端天然一致，省掉整轮派生/模式试错。

---

## 1. 先找客户端自带的 crypto 对象

```javascript
// 页面加载后枚举全局
Object.keys(window).filter(k => /crypt|enc|dec|sign|sdk/i.test(k))
// 常见：CryptoData / CryptoJS / __crypt / LandingSDK / 业务 SDK
```

```javascript
// 试加密一个已知对象，看返回的是「完整 body」还是只有 data
typeof CryptoData === 'object' && CryptoData.Encrypt
CryptoData.Encrypt({mod:'user', code:'index'})
// 实测可能直接返回：client=pwa&timestamp=...&data=...&sign=...
```

- 返回完整 form body 的最省事：直接 `fetch(API,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body})`。
- 只返回 `data` 的，再按客户端拦截器的字段顺序拼 `{timestamp,data,sign,crypt}`。
- 响应解密同理：`CryptoData.Decrypt(j.data)`；**请求与响应可能用两把不同的 key**，别假设同一把。

自检：先调一个已知 control 方法（如 `user/index`），确认 200 + `status:1`，再打未知方法。

---

## 2. 抓真实请求体（不破坏页面）

优先级：**CDP Network 监听 > 页面内 hook**。

页面内 hook 只在需要拿「加密前明文」时用，并且要在 anti-bot/captcha 初始化**之后**注入；过早在 `window.fetch`/`XMLHttpRequest` 上装 wrapper 会把挑战 widget 弄坏。

```javascript
window.__reqs=[];
const of=window.fetch;
window.fetch=async function(...a){let r=await of.apply(this,a);try{window.__reqs.push({t:'fetch',url:String(a[0]),body:(a[1]&&a[1].body)||null});}catch(e){}return r;};
const oo=XMLHttpRequest.prototype.open, os=XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open=function(m,u){this.__m=m;this.__u=u;return oo.apply(this,arguments)};
XMLHttpRequest.prototype.send=function(b){try{window.__reqs.push({t:'xhr',m:this.__m,u:this.__u,body:b?String(b):null});}catch(e){}return os.apply(this,arguments)};
```

拿到真实 `body` 后，用客户端自己的 `Decrypt` 解 `data`，即可读出服务端实际认的 `mod/code/oauth_id/token/version` 和字段名——比读混淆 bundle 快得多。

---

## 3. 浏览器内批量调用的硬限制

`browser_exec` 的 `js()` 底层是 CDP `Runtime.evaluate(awaitPromise:true)`，**单次 IPC 约 5s**。

- 一批最多 **5 个**请求；需要几十个模块枚举时拆成多次 tool call。
- 批间加 100–200ms 限速；一次 40 个请求的循环必被 `Runtime.evaluate timed out` 截断。
- 每批前先自检：

```javascript
location.href          // 可能是 about:blank，tab 被重置
typeof CryptoData      // undefined 就 new_tab 重开并等 5–6s
```

- 不要在单次 eval 里 `await` 几十个网络请求再把结果拼成一个大对象；超时后一个结果都拿不到。

---

## 4. 认证绑定：oauth_id 可能才是会话键

实测一类 PWA 的 `user/index` **不带 token 也能返回 isLogin:true**，认证绑的是 `oauth_id`；换一个 oauth 即使 token 正确也回游客。

规则：
- **oauth_id 与 token 成对保存**，不要只记 token。
- token 过期很快；需要继续打时，在**同一次 eval** 里先 `regOrLogin(type:'login')` 拿新 token，立刻用它发后续请求。
- 新旧 oauth/token 组合要矩阵试一遍（`oauth_old+token_old`、`oauth_new+token_new` 等），以 `user/index.isLogin` 为准，不要只看登录接口的 `msg`。
- 登录返回 `msg:"更换成功"` 不等于会话已激活；必须回读 `isLogin:true` 才算数。

---

## 5. 错误语义分层，别把「不存在」写成「没权限」

同一 API 可能同时出现：

| 响应 | 含义 |
|---|---|
| HTTP 503 / 空体 | 网关/上游异常，或未知方法被框架直接打死 |
| HTTP 200 + `status:0` + `msg:"系统错误"` | **未知 mod/code**（路由没匹配） |
| HTTP 200 + `status:0` + `msg:"参数不全"` | 方法存在，缺必填字段 |
| HTTP 200 + `status:1` | 方法存在且成功 |
| HTTP 200 + `status:0` + `msg:"无权限"` | 真权限门 |

- 先用已知 control（`user/index`）证明会话/路由正常，再判断未知方法。
- 503 或「系统错误」**不是**权限结论；不要写进报告说「该接口无权限」。

---

## 6. 加密挑战网关：没有前端就及时停手

症状：任意路径（`/admin`、`/manage`、`/login`、`/static/...`）都返回同一结构：

```json
{"errcode":0,"timestamp":1792717016,"data":"<hex>","sign":"<32hex>"}
```

- 每次 `data/sign` 都变 ⇒ 每请求挑战，不是静态错误。
- 做**有界**尝试即可：AES-CBC/CFB/CTR/GCM × 已知 key/派生、MD5/SHA/HMAC sign 公式；跑完一轮就停。
- 没有前端 JS 时，继续爆破命中率接近零；转去拿客户端 bundle / 静态资源 / 等后台恢复。
- **vhost 的 `/` 502 不代表静态资源可绕过**：同一 server block 可能把所有路径都 proxy 到死上游，静态 JS 也回 502；`/admin` 503 + `/` 200 空也要当「后台应用停机」处理。
- 403 全路径通常是 IP allowlist，不是目录索引问题；换 XFF/直连源站通常无效。

---

## 7. 提权/业务门的两条验证纪律

### mass assignment
- **单字段测试**：先只加 `role_id:1`，不要同时塞 `is_admin/isVip/coins`。
- 未知字段可能让服务端直接 503；混发会把「role_id 被忽略」误判成「role_id 被拒绝」。
- 注册成功 ≠ 字段生效；必须 `user/index` 回读 `role_id`，变了才算提权。

### paywall
- detail 端点返回数据 ≠ 能看完整片。
- 对比**付费 id** 与**免费 id**：付费 `is_canwatch:false` 且 `playUrl` 无 `encrypt_url`/`verify_token` = 服务端真门控，`detail` 只给了预览。
- 只有付费 id 也返回完整播放地址/凭证，才算绕过。

---

## 8. 客户端产物情报（拿不到 oracle 时）

按顺序找：
1. **公开逆向仓库**：GitHub 搜 App 包名/命名空间/品牌 + `apk` / `逆向` / `crypto` / `api.php`。常带 APK、jadx 产物、抓包日志、协议说明。
2. **抓包日志**：`URL=http://...||<response>` 这类行直接给明文响应和 `mod/code`；比逆 bundle 快。
3. **动态 API 配置**：APK 里 grep `raw.githubusercontent.com` / `dsp.txt` / `config`；运营方常把当前 API base 放在公开 GitHub raw，直接 fetch 最新域名。
4. **版本对齐**：公开仓库的 APK 与线上版本不一致时 key/接口可能不同；以能跑通的那版为准，并用 control 方法验证。

---

## 9. 作业纪律

- 单点 502/挑战解不开时，按「客户端产物 → 公开仓库/动态配置 → 同族活端点 → 监控恢复」继续换面。
- 不要连续发「还是 502」的总结，也不要在没有新证据时反复要方向；用户要的是新结果。
- 监控脚本用**状态码+长度指纹**判断正常/异常，不要用子串匹配（`*" 502"*` 会漏掉开头的 `502`）；`pgrep -af script` 会匹配到当前 shell 自身，用 `pgrep -f 'bash /path/script.sh'`。
