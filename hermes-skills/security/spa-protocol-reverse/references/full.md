# spa-protocol-reverse — 全文续篇

> 主卡保留前 8 节；本文件从第 9 节起。原文件：`/root/.hermes/skills/security/spa-protocol-reverse/SKILL.md`

## 核心流程

### 1. SSR payload 提取(最先做,信息密度最高)

Nuxt 3:`window.__NUXT__.config.public` 含 `gameURL`/`wsURL`/`apiBase`/`assetsURL`/`env` + 硬编码 token。
Next.js:`self.__next_f.push` RSC payload 或 `window.__NEXT_DATA__`。
Vue3/Vite:`window.gameTab` / `window.__INITIAL_STATE__` 或 `<script type="application/json">`。

```bash
curl -s <target> -H "User-Agent: <浏览器UA>" -H "Referer: https://<target>/" | grep -oE 'window\.__NUXT__\.config[^<]{0,1500}'
```

关键:SSR payload 常直接给出**API 后端真实域名**(可能与前端不同域)、WebSocket 地址、第三方 token(ipinfo/高德/gtag)。

### 2. 找资源 CDN 与 JS 入口

SPA 静态资源常托管在独立 CDN(如 `downm9.sp-slots1.com/source/public`)。从 HTML 提取 `<script src>` 列表 → 主入口 bundle(main.js 类)+ config.js。config.js 经常就是"金矿"(含全站配置、域名矩阵、游戏/功能配置)。

### 3. JS chunk 枚举与批量提取

主 bundle 是入口,业务逻辑(认证/注册/用户 API)在动态 import 的 chunk 里:

```bash
# 从 main.js 提取 chunk 名
grep -oE 'import\("\./[A-Za-z0-9_]+\.js"\)' main.js | sort -u
# 批量下载,正则提取 API/WS/域名
python3 - <<'EOF'
import re, urllib.request
for chunk in ["3X8iq6d2.js", "..."]:
    data = urllib.request.urlopen(f"https://cdn/static/js/{chunk}").read().decode(errors="replace")
    for a in sorted(set(re.findall(r'/api/[a-zA-Z0-9_/?.=&${}-]+', data))):
        print(chunk, a.split("${")[0])
    for w in sorted(set(re.findall(r'wss?://[a-zA-Z0-9._:/-]+', data))):
        print(chunk, "WS:", w)
EOF
```

压缩混淆时配合:找 `baseUrl`/`apiUrl`/`fetch(`/`signedPost` 等关键字的上下文;minified export 反查(`Q_` 从 `export{... as Q_}` 追到具体库,如 HmacSHA256)。

### 4. 签名机制逆向

SPA 常见自研 API 签名(尤其博彩/游戏/金融类):

```
找硬编码 key(明文) → 找签名函数(signedPost 类) → 还原算法
典型:HMAC-SHA256(key, str(timestamp)+sorted_params),headers: x-timestamp/x-signature
```

**完整还原示例**(m9600,2026-08 实战):
```python
KEY = "7f6e5d4c3b2a1f0e9d8c7b6a"  # 前端 JS 明文(搜 signedPost 附近)
def sign_post(params):
    body = "&".join(sorted(quote(k)+"="+quote(v) for k,v in params.items()))
    ts = str(int(time.time()*1000))
    sig = hmac.new(KEY.encode(), (ts+body).encode(), hashlib.sha256).hexdigest()
    # headers: x-timestamp=ts, x-signature=sig, Content-Type: x-www-form-urlencoded
```
**验证签名正确**: GET 无签名 → `{"code":99,"msg":"signerror"}`;带签名 → 进入业务逻辑(`code is error!` 等)= 签名还原成功。

**签名只保护部分接口。** 先测无签名 GET(`/api/xxx` 直调),往往一堆配置/信息接口是开放的,403 可能只是缺 Referer/Origin,不是签名。

### 4b. 客服/辅助子系统的加密 API 逆向(独立攻击面)

主站 `/api/customer_info` 类接口可能泄露客服系统 URL(带会话 token)。客服 SPA 是独立前端,其主 JS 里常含**完整加密凭据**:

```javascript
// 搜: baseURL + AES key + iv + axios interceptor
ci = "https://apic.<domain>.xyz"                    // 独立 API base
Oa = "DfoieDOsdkfmfkwofxoDMytduexwJkmN"             // AES-256-CBC key(硬编码明文)
Sa = "IfklajiocsowmJsk"                             // IV(16字节)
// interceptor: 加密 JSON.stringify({timestamp, uuid}) → 请求头 timestamp/uuid
```

Python 复刻 AES-CBC + ZeroPadding 加密后即可探测其端点(如 `/v1/file/base64` 匿名可用,其余 401/404 = 需认证)。这是主站打不动时被忽略的独立数据面。

### 5b. CF WAF 拦截后的终极解法:CDP 驱动真实浏览器(2026-08 实测)

当 curl 被 CF WAF 拦(403 Attention Required 页)、Python urllib 也被 TLS 指纹拦时,**改用 headless Chrome + CDP 直接驱动页面上下文里的 fetch**——浏览器会话自带真实 CF cookie,同源请求天然过 WAF,还能在登录态下测 API。

```bash
# 启动带远程调试的 headless Chrome(注意:Chrome 151+ 必须 --remote-allow-origins=* 否则 WS 握手 403)
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu \
  --remote-debugging-port=9227 --remote-allow-origins=* \
  --user-data-dir="D:\\xxx\\chrome_profile" --no-first-run about:blank &
```

```python
# Python 侧:websocket-client 连接 CDP,页面上下文 fetch = 同源 + CF cookie
import json, urllib.request, websocket
tabs = json.load(urllib.request.urlopen("http://127.0.0.1:9227/json"))
ws = websocket.create_connection(tabs[0]["webSocketDebuggerUrl"])
# 先导航到目标站拿 CF 会话,再 Runtime.evaluate 执行 fetch
js = "fetch('/api/v1/me',{headers:%s}).then(r=>r.text()).then(t=>window.__res=t)" % json.dumps(headers)
```

**最大坑:fetch body 必须 JSON.stringify。** `fetch(url, {method:'POST', body:{...}})` 直接把对象当 body 会变成 `[object Object]`,服务端返回 400 `Invalid request parameters`——所有 POST 全挂且错误信息雷同,极易误判为参数错。正确姿势:Python `json.dumps(body)` 后再包 `JSON.stringify(...)`。

**登录态获取**:Turnstile 类真校验在 headless 过不了 → 让用户手动登录,然后下载 token 文件(不要走聊天粘贴!JWT 一个字符被聊天转义破坏就 401,实测粘贴版 payload 多出 'm' 全部失效,文件版正常):

```javascript
const a=document.createElement('a');a.href='data:text/plain,'+encodeURIComponent(localStorage.getItem('user_token'));a.download='token.txt';a.click()
```

### 5c. 403 诊断(别被误导)

- **Cloudflare 层 403**:响应头 `Server: cloudflare` → IP/UA 封禁,换代理/UA
- **应用层 403**:响应头 `X-Powered-By: PHP/...` 等 → 缺 header(Referer/Origin/Custom-Origin)或签名错误
- 用 `curl -D -` 看完整响应头判断是哪层拦截

### 6. SPA 兜底假象

SPA 路由对任意路径返回 200(index.html)→ 探测 `/.env`、`/db.sql`、`/backup.zip` 等全 200 是**假阳性**。必须看 body 是否 JSON/文件内容,不是只看状态码。

### 7. 业务全走 WebSocket 二进制协议的识别(博彩/游戏平台关键)

部分平台(尤其博彩/棋牌)REST `/api/*` 只暴露少量公开配置接口(客服/推送/提现方式),**业务逻辑(登录/注册/余额/提现)100% 走 WebSocket 二进制协议**。判断信号:

- 前端 JS 里有 `CMD_MB_*` / `SUB_MB_*` / `MDM_*` 协议号定义(几百条)+ `char16_t`/`uint16_t`/`LEN_ACCOUNTS` 等字段类型 → 经典棋牌/游戏大厅协议(MDM/SUB 两层命令)
- 页面引入 emscripten 编译的 wasm 网络库(`hxws-*.wasm` 类,glue 是 `hxws-*.js`)→ 包构造/加密在 C 层
- SSR payload 的 `wsURL` 字段给出 `wss://<域>/net` 类端点
- wasm 内字符串常泄露**开发机路径**(如 `/mnt/d/MyProg/...`)→ 源码仓库线索

WebSocket 二进制协议逆向步骤:

```bash
# 1. 从 main.js 提取协议表:MDM/SUB 常量 + 字段模板(Rl/kl/Ll 表)
#    MDM_MB_LOGON=1 下 SUB_MB_LOGON_ACCOUNTS=2 / REGISTER_ACCOUNTS=3 / 各查询
#    登录字段: accounts(32B)+logonPass(MD5)+machineID(33B)+channelName
# 2. 下载 wasm 网络库:定位 allocSendBuffer / getSendBufferSize / startWebsocket 导出
# 3. 试验包头格式(常见 6 种全无响应 = C 层自定义帧/加密,需反汇编 wasm 或 hook 真实浏览器流量)
python3 - <<'EOF'
import asyncio, struct, websockets
WS = "wss://<host>/net"
# fmt1: mcmd(2)+scmd(2)+len(2)+payload ; fmt3: cmd32(mcmd<<16|scmd)+len(2) ...
EOF
```

要点:协议号常量表 = 攻击面地图(找 `SUB_MB_SendSMSRegisteUser`/`BindMobile`/`GetOnlineUserInfo` 这类可枚举用户/绕过验证码的指令);C 层包格式猜不出时,**最高效路径是把 wasm 网络库下载到本地,在 Node 里 shim 浏览器环境直接驱动 C++ 类**(见 `white-label-casino-pentest` 技能的 `templates/emscripten-ws-driver.js` 模板)—— 让 C 库自己发包/收包,包格式从 HEAP 内存 dump,几分钟出结果,无需反汇编 wasm。m9600 实战:UTC 时间戳查询(SUB=25)验证成功,帧格式 `[4B:0][4B:len][4B:随机key][2B:mcmd][2B:scmd][payload]`;业务命令(登录=2/注册=3)手工拼包会统一被拒 resultCode=9999 —— **这是字段写入错,不是握手缺失**;复刻前端 writeData 模板驱动 + 取前端默认字段值后注册/登录全通(验证码绕过:checkCode 取前端硬编码默认 "123456" 即可;错误码字典 11=密码错误/账号存在、12=已存在、9999=字段错伪装拒绝 = 用户枚举器)。完整细节见 `white-label-casino-pentest/references/m9600-wasm-ws-protocol.md`。

### 8. 混淆 encrypt.js 的 RSA+DES 双层加密 REST API(白标博彩 `/wps/*` 族)

白标博彩平台的 REST 业务接口(登录/注册/钱包)常走 `encrypt.js`(混淆 CryptoJS + Tom Wu little-endian RSA)双层加密:header `Encryption` 放 RSA 密文,body `{"value":"<DES密文>"}`。完整复刻 + 漏洞利用链见 `references/aq777-wps-rsa-des-api.md`,核心要点:

- **混淆字符串表必须动态解码,不能静态 grep**:obfuscator 对字符串数组做 rotor 旋转(`(function(f,o){...}(a0_0x2207,0x8437b))`),静态提取的索引全错。正确做法:Node `vm.runInContext` 加载原 JS,直接调用解码函数(如 `a0_0x55e8(0x198)`)拿真值。AQ777 关键索引:0x175="10001"(RSA e)、**0x198="ECB"(模式!)**、0x1cd="split"、0x1c2="reverse"、0x15f="join"。
- **DES 模式是 ECB 不是 CBC**:误用 CBC 会一直 `decryption.err`,服务端不解释原因;改成 ECB 后立即进入业务逻辑(错误码从解密错变成业务错 = 加密链通了)。旧参考写 CBC 是错的,以动态解码结果为准。
- **rand 处理**:16 字符随机串;RSA 加密的是**反转后** rand(`rand.split('').reverse().join('')`),DES 用原串。
- **JSON 必须紧凑**:`json.dumps(data, separators=(',',':'))` 对齐 JS `JSON.stringify`;带空格会被服务端拒。
- **RSA little-endian**:明文按 chunkSize=2*biHighIndex(modulus) 分组(1024-bit 公钥 → 126),每 2 字节组 16bit word(低字节在前),`pow(num, 0x10001, n)`,hex 输出空格连接。
- **Merchant header 决定商户上下文**:值来自前端模块 `brand.merchant`(AQ777 是 `as888tlbf7`,不是域名前缀也不是页面 brand 变量);Merchant 错时接口返回 `function.not.available`,看着像"功能关闭"实际是商户上下文错误。
- **geetest v4 假字段绕过**:登录带 `geetestChallenge/geetestValidate/geetestSeccode` 任意字符串(如 "x")即通过(后端只查字段存在不校验真实性);注册接口 `captcha` required=false 可无验证码批量注册。
- **注册接口 = 用户枚举器**:重复注册返回 `exists.username.err`,新用户名 success;customerId 自增可估算活跃度。
- **CDN/JS 挑战选对客户端**:同一目标 Node https/curl 被 EdgeOne 拦(567 挑战页),Python urllib+CookieJar 能过 → 探测/下载 JS 用 Python;Node sandbox 只用来解码混淆字符串/驱动原 JS 函数。

### 9. 移动端/代理端独立 bundle = 隐藏 API 面(高价值)

同一 SPA 主站的 `/m/*`(移动端)、`/agent`、`/m/agent`(代理后台)等路径常加载**独立的 webpack bundle**(如 `/m/app.xxxx.js` + `/m/chunk-common.xxxx.js` + `/m/vendor.encrypt.v2.dll.js`),接口字典与网页版完全不同且更完整:

- **网页版只暴露少量公开接口,移动端 bundle 常含完整资金/安全/代理接口**:绑卡(`/wps/member/bankCard`、`MCS2_bankCards`)、提现(`/wps/transaction/withdraw`)、存款族(`MCS2_depositManualTransfer/DepositAlipay/DepositQQ/DepositWeChat`)、代理下线(`/wps/agent/downline(s)`、`ODSFE2_Subordinate`)、团队 KPI(`ODSFE2_TeamKPIA/B/C`)、资料更新(`POST /wps/member/info`)、改邮箱/收款人(`/wps/member/info/email`、`/payeename`)、独立用户名检查(`/wps/check/username`)
- **采法**:curl/Python 直接 GET `/m/agent`、`/m/index.html` 等路径 → HTML 里 `<script src>` 指向独立 bundle → 下载后同第 3/4 节提取 link 字典。主站 SPA 壳对所有路由返回同一 index.html 时,改用 `grep -oE '["\'](/wps/[^"\']{3,80})["\']'` 全文扫 bundle。
- **`/wps/check/username` 是轻量用户枚举**:`success:true` = 用户名可用(不存在),`false` = 已存在;比注册枚举更干净(无加密、无注册副作用)。
- **代理身份判定**:member type ∈ [1,2,41,42] 是代理,∈ [0,4,40] 不是;`POST /wps/member/info {"type":1}` 返回 success 但 type 不变(服务端忽略该字段)——客户端提权不可行,代理身份只能服务端分配。
- **接口"功能维护中"≠ 关闭**:明文请求返回 `function.not.available`,换成加密 POST(或换 method/加参数)后若错误码变成 `request_param_err`/`encryption.required` → 通道其实活跃,只是缺参数/身份。用错误码变化判断通道死活。
- **whitelabel 必须用正确 merchant 拉取**:用错误 merchant 拉到的功能树是默认/别的商户配置(模块数完全不同),会误判"代理/资金全关"。先用 `brand.merchant` 确认 merchant 再拉 whitelabel。
- **多商户横向**:同一网关换 merchantCode(`dingtsaiyl`/`default`/...)可探测其他白标实例,配置差异大(25 vs 145 模块)——功能少的实例防护可能更弱。

### 10b. Next.js 多租户平台侦察(2026-08 TokenGo 案例)

Next.js SPA 多租户平台(tokengo.love + wy6688/pix/admin/reseller.token6688.com)侦察要点,完整案例见 `references/tokengo-nextjs-multitenant.md`:

- **同 chunk 哈希 = 同一代码库**:各子域 HTML 里的 `/_next/static/chunks/main-app-*.js` 哈希完全一致(`59757db288e4ffd8`)→ 多品牌共享同一 Next.js 代码库,一次逆向打全部子域(只改皮肤/品牌,业务 API 同构)。先对比各站 chunk 哈希判断是否同库。
- **`/api/auth/providers` 泄露认证架构(必测)**:NextAuth 的 providers 端点返回全部登录方式(google/github/phone-otp/credentials)+ **signinUrl/callbackUrl 指向真实认证主域**(子站是租户,主域 tokengo.love 才是认证中心)→ 资产拓扑瞬间清晰。
- **登录页 RSC payload = 功能地图**:Next.js App Router 的 HTML 里 `self.__next_f.push` RSC payload 含完整 i18n 文案,泄露产品功能结构("管理后台"/"API 密钥"/"代理商中心"/"手机号首次登录自动创建账号"/`signupDisabled` 标志)+ 表单字段(email/phone/password/displayName/otpCode)→ 不需要逆向 JS 就能知道攻击面。
- **Next.js Server Action 调用**:注册/登录若走 Server Action(JS 里 `createServerReference("40e019...","signupAction")`),用 `POST 当前页URL` + `Next-Action: <actionId>` header + `Content-Type: text/plain;charset=UTF-8` + `Accept: text/x-component`,body 直接 JSON 序列化参数。**参数签名判定**:返回 `passwordTooShort` = 参数结构错(服务端没拿到 password);返回 `signupFailed`/其他业务错误 = 参数签名对了进入真实逻辑。React 19 精确编码(`$K` 引用)复杂,优先用真实浏览器填表自动处理。
- **`X-Impersonate-User-ID` / `X-Impersonate-Reseller-ID` 头(高价值越权模式)**:前端 API 客户端从 cookie(`impersonate_user_id`/`impersonate_reseller_id`)自动附加 impersonation 头到 `/api/v1/*` 请求——管理员/客服"模拟用户"功能。**如果后端信任该头 = 任意用户/经销商接管**。测试:注册后带 `X-Impersonate-User-ID: 目标uid` 访问 `/api/v1/users/me` 看是否返回他人数据(该头是叠加在登录态上的越权,不是认证绕过,需先有 token)。
- **OpenAI 兼容 API 网关识别**:独立子域(如 api.tokengo.love)根路径返回 `{"name":"TokenGo API Gateway","compatibility":["openai","responses"],"documentation":"/docs","models":"/v1/models"}` = 模型代理网关。`/v1/models`、`/v1/chat/completions` 需 Bearer API key(`sk-` 前缀,错误 `invalid_api_key` 区分 key 存在性);`/health` 泄露服务版本。
- **FastAPI 后端 vs Next.js 404 区分**:API 返回 `{"detail":"Not Found"}`(小写 found)= FastAPI 独立后端;返回 HTML 404 页 = Next.js 路由未命中。同服务器上多个 Next.js 产品(:443 全球AI工具 + :8888 短剧工场)各自挂独立 FastAPI。
- **无 CDN 时直连源站**:DNS 解析显示真实 IP 且非 CF/EdgeOne 段(如阿里云 47.92.73.166)= 无 CDN,直接全端口扫。`robots.txt` 常泄露 `/admin/`、`/login`、`/register`、`/*?conversation=` 等隐藏路径(纯 AI 爬虫屏蔽,无隐藏路径是假象——这里真泄露了)。
- **CDN 特征对比**:`Server: TencentEdgeOne`(腾讯)vs `Server: cloudflare`(CF)vs 裸 nginx = 防护层级差异,EdgeOne/CF 后面可能另有独立 IP 服务(:8888 直连可达)。

### 10c. XunRuiCMS(迅睿CMS)二开站点 / COD商城逆向(2026-08 长安COD 案例)

国内 COD/卡密/商城/灰产站大量用 XunRuiCMS 4.x(基于 CodeIgniter 3.1.13)二开,识别与 API 面要点(完整契约见 `references/xunruicms-cod-zengda.md`):

- **识别信号**:响应 `Set-Cookie: csrf_cookie_name=<32hex>` = CI3 → XunRuiCMS;路由 `index.php?s=模块&c=控制器&m=方法`;`/static/assets/js/cms.js` 的 `dr_` 前缀函数(dr_lang/dr_strtotime)是迅睿官方库;页面注释 `<!--使用XX系统搭建，了解更多+v:xxx-->` 泄露二开品牌(长安COD)
- **CSRF 双校验**:cookie `csrf_cookie_name` = POST 字段 `csrf_test_name`(值相同),每次 POST 成功后服务端刷新 token(响应 `res.token` 回写隐藏字段);下单类 POST 必带
- **核心业务 API**(COD 商城):下单 `POST /index.php?s=order&c=order&m=buy&mid=pro&id=61&sku=0_0&num=1&huilu=1&ccode=tw`(paytype=nopay=货到付款;防刷报 `Submit too fast`;字段校验错误 `data.field` 定位表单字段);成功页 `m=buysuccess` 带 `ordata[sn]` 订单号(明文 GET);浏览量 JSONP `s=api&c=module&siteid=1&app=pro&m=hits&id=61`;地区联动 `s=api&c=api&m=linkage_ld&mid=order&code=tw` / 树 `m=linkage`;验证码 `m=captcha`(image/png);模板渲染 `m=template&name=checkout.html`(可枚举模板名,未配置的 fallback 信息页);埋点 `s=weblog`(JSONP);FB CAPI 代理 `POST s=ip_cz&c=home&m=dr_facebook`
- **订单号格式**:`H` + yymmddHHMMSS + 4位随机(如 H2608191945496097)
- **商品 SKU 注入**:Vue2 落地页 HTML 内联 `skuData` JSON(group/name/image/value,SKU key=`组ID_选项ID` 下划线连接),业务逻辑全在 HTML 内联 JS,不在 chunk
- **后台**:admin.php 及 30+ 常见变体常被改/移除;子域常 wildcard 泛解析(HTTP 探测 530 区分是否存在);真正后台常在独立域名
- **重建复刻路径**:框架官网 www.xunruicms.com/down/(gitee 正确仓库 dayrui/xunruicms,zipball 下载需登录);本机复刻可用原生 PHP8+SQLite 保路由格式零依赖跑通

### 10. 回调面/盲注/开发路径系统化测试(风控目标收尾打法)

主 API 面打不动时的标准补充扫描(需住宅代理池绕过 IP 风控,见 `references/residential-proxy-pool.md`):

- **回调路径 FUZZ**:支付/游戏/订单回调通常无鉴权但路径需要猜。字典:`/wps/pay/notify`、`/wps/payment/callback`、`/wps/deposit/{notify,callback}`、`/wps/withdraw/{notify,callback}`、`/lgw/{callback,notify}`、`/callback`、`/notify`、`/api/{callback,notify}`、`/pay/{callback,notify}` 等 30 个左右。判断:返回 `405 Not Allowed`(nginx 层存在但方法/路径不对)或 `rest_not_found`(路由不存在);**`/lgw/callback` 返回 500 `UNKNOWN_ERROR: null for uri: http://<host>:80/lgw-service/resources/callback` = 泄露内部微服务路由**(lgw-service 存在但网关转发缺参数)——500 里的内部 uri 是信息泄露线索,可换参数格式继续试,但通常需要供应商内部格式。
- **UA/JSON 盲注(10 分钟版)**:在公开接口参数上测 `'`、`' OR '1'='1`、`' AND SLEEP(3)--`。Spring 后端 + 参数校验严格时常见结果:格式校验层直接 400(`request.param.err.format.*` / `invalid.username`),注入根本到不了 SQL 层 → 判定 SQLi 面关闭,不再深入。注意区分:`unknown_err` 500 = 参数类型转换失败(如 Integer 解析),不是注入成功。
- **开发路径 FUZZ**:`/.git/HEAD`、`/.env`、`/actuator/*`、`/swagger-ui.html`、`/v2/api-docs`、`/admin`、`/debug`、`/h2-console`、`/backup.zip`、`/db.sql`、`/wp-admin` 等。**SPA 兜底假象再次强调:全返回 200 但 body 是 index.html → 假阳性**;只有返回非 SPA 内容(JSON/文件头/robots 文本)才算真发现。`/robots.txt` 常是真内容(纯 AI 爬虫屏蔽,无隐藏路径)。
- **RNG/彩票**:`/lotto/lgw/games/opened/numero` 类开奖接口返回空数组 = 需要内部 gameCode 参数,非敏感面,低优先级。
- **WP 营销站**:47 域名批量测 `/wp-login.php`、`/wp-json/`、`/wp-content/` 特征;无命中说明无独立营销站,代理体系入口在站内(客服/Telegram)。
- **上传点**:`/wps/member/info/icon` 类头像上传,先 GET 确认存在再测 PUT/POST;返回 `http_method_not_support` = 该端点不支持此方法,别硬试。

**收尾判断**:回调面无伪造入口 + 盲注无注入点 + 开发路径全 SPA 假象 + 上传方法不支持 → 该白标实例数据面已到瓶颈,诚实收尾,剩余方向转向社工(通过已解密的客服/Telegram 申请代理身份)或横向打其他商户/独立系统。

## Pitfalls

- **生产环境 key 可能是截断占位符**:SSR/JS 里统一出现 `eyJhbG...v0IQ` 类截断 JWT/anon key 时,是**服务端故意截断**(平台注册/登录功能实际损坏或走后端代理),不是遗漏 — 别花时间拼完整 key,直接转 API 层测试。roiify.net 案例:anon key 全站截断,`/auth/v1`、`/rest/v1` 反代暴露但缺 key 不可用。
- **gzip 无头响应(后端管理 API)**: 部分后端(尤其 Java/PHP 管理后台)接口返回 gzip 压缩体但**无 Content-Encoding 头** — urllib/curl 拿到 `\x1f\x8b` 乱码,JSON 解析必失败。必须手动检测 `raw[:2] == b'\x1f\x8b'` 再 `gzip.decompress`。wukong 管理后台 tk_wu.sswhgame.com 的 `/api/account/accountList` 实测命中(响应 337KB 全 gzip)。
- **无头浏览器常被 SPA 反自动化跳 about:blank** → 改用 curl + 静态 JS 分析,别在浏览器上耗时间
- **腾讯 EdgeOne CDN JS 挑战(常见于博彩白标)**:响应头 `Server: TencentEdgeOne`;对首页返回 200,但对 `/res/*.js` 等路径返回 7351 字节验证页(doctype HTML,里面全是 CSS 图形验证),裸 curl 全被拦。**解法**:Python urllib + CookieJar 会话,先 GET 首页(拿 CDN 会话 cookie/过挑战),同一 opener 再 GET JS 文件即可拿到真实内容(实测可行);curl 需带同一 cookie jar。另外用 `urllib.request.build_opener(HTTPCookieProcessor(cj), HTTPSHandler(context=ctx))` 时注意 SSL context 必须放 handler 里,不能放 `open(context=...)`(会 TypeError)。
- API base 由 `env` 决定:`env=production` 用 `window.location.origin`,`development` 才用配置的 `/dev-api`
- 前端硬编码第三方 token(ipinfo、高德、sentry、apifoxToken)直接抓,别忽略
- 页面 HTML 里看不到的 API 全在 JS chunk 里;HTML 只有 SSR 静态内容 + 入口引用
- SPA 品牌多域名镜像:config 里 OneSignal/域名列表泄露整个镜像矩阵,横向渗透直接枚举
- 别假设"未登录"就无 API 可用 —— 注册接口、访客接口、信息接口常常无需认证
- **风控阈值(实测,博彩白标通用)**:批量注册 ~9 个触发 `register_ip_restricted`(全注册路径共享 IP 限额,`autoUsername` 也拦);登录失败 5 次触发 `us_forbidden_login_error`;多次登录测试后 IP 会被 `login.ip.restricted` 整体限制(冷却数分钟~1小时)。大规模测试前先探阈值,测试中主动控制节奏。
- **用户偏好:不做撞库/口令爆破**。登录接口通常有失败锁定(5 次即锁),且用户明确拒绝字典撞库("效益太慢不要尝试")——优先找业务逻辑漏洞(越权/验证码绕过/未授权接口),不要规划爆破类利用。
- 第三方登录(Telegram/Line/Firebase)hash 通常是**真校验**(`telegram_validate_failed`,伪造 hash 无效)——不要浪费时间伪造,除非能拿到 bot token。但失败响应常泄露后端内部类名(如 `com.tcg.gateway.to.telegram.TelegramTcgLoginRequest`),可作为后续线索。
- **XunRuiCMS/CI3 系路由**:控制器方法名 = `c_m`(如 `s=pro&c=show&m=index` → 函数 `show_index()`,不是 `pro_show()`);枚举接口时直接按此命名规则探测,避免"方法不存在"误判
- **HTML 转 PHP 模板的坑**(复刻/重建时):`tcskuData: {` 含子串 `skuData: {`,字符串 replace 会误替换——必须数括号深度配对;Python 替换产生的 `\$pro[\'id\']` 反斜杠只在 `<?php...?>` 段内清理,别动 JS 里合法的 `\'` 转义
- **Windows 原生 curl 写中文路径失败**:`curl -o D:\渗透\...` 报 No such file;先下载到英文 ASCII 路径再 `cp`
- **JS 变量文件解析**:`var linkage_tw =[{...}];` 等号后可能无空格,正则用 `var \w+\s*=\s*(\[.*\]);`(带 `\s*`)而不是 ` = `

## Verification

- [ ] 已提取 SSR payload / config.js 拿到 API 真实域名 + WS 地址
- [ ] 已枚举全部 JS chunk 并提取 API/WS 端点
- [ ] 已确认哪些接口无签名/无认证可直调
- [ ] 已诊断 403 是 CDN 层还是应用层
- [ ] 已识别业务是否走 WS 二进制协议(CMD_MB_*/MDM_* 常量表 + wasm 网络库),并提取协议攻击面(登录/注册/查询子命令)
- [ ] 报告含前端泄露的密钥/token/域名清单

## References

- `references/nuxt3-m9600-worked-example.md` — m9600.com(Nuxt3 + HMAC 签名)完整实战:SSR 提取、chunk 枚举、签名还原、403 诊断
- `references/aq777-wps-api-family.md` — AQ777(菲律宾博彩)/wps/* 平台族完整逆向:EdgeOne 绕过、RSA+DES 加密链、Merchant header 必带、whitelabel 278 模块配置 = 验证码/注册开关情报源、webpack chunk 映射提取
- `references/aq777-wps-rsa-des-api.md` — AQ777 加密链精确复刻(DES-ECB 非 CBC、rotor 字符串表动态解码、rand 反转)+ 漏洞利用链(批量注册/geetest 绕过/用户枚举/域名矩阵/APK 攻击面),并修正旧参考中 CBC 的误判
- `references/residential-proxy-pool.md` — 住宅代理池工作流:用户 xlsx 代理表解析(两种列结构)、pysocks 带认证轮换、出口 IP 验证、IP/账号风控双轮换——解决 `login.ip.restricted` 类风控
- `references/xunruicms-cod-zengda.md` — XunRuiCMS(迅睿CMS)二开长安COD商城全站逆向+重建:识别信号、完整 API 契约、下单/防刷/CSRF、订单号格式、地区库 JS→SQLite 导入、原生 PHP8+SQLite 复刻要点

