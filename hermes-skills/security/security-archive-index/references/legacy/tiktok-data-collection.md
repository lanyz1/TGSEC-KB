<!-- archived from /root/.hermes/skills/security/tiktok-data-collection/SKILL.md on 2026-10-21 -->

---
name: tiktok-data-collection
description: >-
  测绘引擎·采集 TikTok 账号数据(粉丝/作品)。SSR解析用户信息+CDP抓Cookie+页面fetch绕过签名。
owned: true
tier: ops
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/tiktok-data-collection`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/tiktok-data-collection/…')`，不要相对 `references/legacy/` 解析。

# tiktok-data-collection（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/tiktok-data-collection/`

溯源（仅标记）：`hermes/software-development`

---

# TikTok 账号数据采集

## 触发
- 需要绑定 TikTok 账号、采集粉丝/作品/播放/点赞/评论/收藏数据(投流平台、选品、账号监控)
- 用户要"抓 TikTok Cookie / CK"或提交 Cookie 采集数据
- 参考 wukong 类 TikTok 私信/采集工具的技术路线

## 数据采集三通道(全部实测验证,2026-08)

### 通道1: 用户信息 = 页面 SSR 解析(零依赖,优先)
- 访问 `https://www.tiktok.com/@handle` → 解析 `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">` 内 JSON
- 路径:`__DEFAULT_SCOPE__.webapp.user-detail.userInfo.{user,stats}`
- 可得: uniqueId/nickname/signature/secUid/avatarLarger/verified + followerCount/videoCount/heartCount/followingCount
- **无需 Cookie、无需签名、零成本**。@tiktok 实测:粉丝 95.3M/作品 1491/获赞 4.6 亿
- 附赠:同 JSON 里 `webapp.app-context` 有 csrfToken/webid/odinId 可作 API 参数

### 通道2: 抓登录 Cookie = CDP(唯一能读 HttpOnly 的路径)
- **`sessionid`/`odin_tt`/`ttwid` 全部 HttpOnly**——`document.cookie`/console 一律拿不到(实测 Set-Cookie 头确认),别教用户 console 方案
- 正确做法: Chrome `--remote-debugging-port=9222 --remote-allow-origins=*` 启动(用户默认 profile,保留登录态)→ CDP `Network.getAllCookies` 读全部 cookie(含 HttpOnly)
- **Chrome 111+ 必须 `--remote-allow-origins=*`**,否则 WebSocket 握手 403("Rejected an incoming WebSocket connection")
- 关键 cookie: `sessionid`(登录态) + `odin_tt` + `ttwid` + `msToken`(其实在 API 参数里,不在 cookie)
- 用户侧工具(智能版v3,2026-08 用户"不太智能"+"内置代理"反馈后重写): `scripts/抓tk_ck.py` + bat(GBK+CRLF)——**双击 → 读/输入代理(选填,存 proxy.txt)→ 有代理起本地 SOCKS5 认证桥 → 脚本自己启动 Chrome**(独立 user-data-dir profile,**不碰用户正用浏览器,勿再要求关 Chrome**;9222 已被占则复用) → 打开 tiktok.com → 用户登录 → **自动检测 sessionid(2 秒轮询+连续 2 次一致+len≥25 真实性校验)零按键抓取** → 剪贴板+ck.txt → **MessageBoxW 弹窗**(成功/超时/失败,成功时提示"绑定平台时把同一代理也填上"——抓取IP=登录IP=采集IP三合一风控最小);profile 保留登录态,**第二次双击即抓**(体验关键卖点)
- **客户交付打包(2026-08 三阶段演进,以最终 GUI 版为准)**:① v3 命令行版(bat+exe) → ② **GUI 整合版 `tk_ck_gui.py`**(用户拍板"完整 exe:IP 列表+添加IP+右键『登录TK并抓取CK』+CK 列点击复制"):tkinter Treeview 三列(代理IP/状态/Cookie)+右键菜单,每 IP 独立 Chrome 实例/独立端口/独立桥(多 IP 并行),queue 消息泵更新 UI,data.json 持久化 → ③ **内置 Chrome for Testing 便携版**(chrome/ 目录,客户连 Chrome 都不用装)。PyInstaller `--onefile --windowed`。**工程坑:onefile 的 `__file__` 指向临时解压目录→用 `sys.executable if getattr(sys,'frozen',False) else __file__` 定位 exe 目录;exe 在 GBK 控制台 print emoji 会 UnicodeEncodeError 崩溃→交付脚本全纯文字;--windowed 崩了无任何输出→先打 console 版诊断;simpledialog.askstring 传 width 会静默 TypeError(点击无反应);tk.Frame 构造不支持元组 pady**。完整实现+坑见 `references/socks5-auth-bridge.md` 第六~八节
- **★客户端云端更新下发(2026-08-16 用户"我想要下发云端更新"后落地)**:exe 内置 `APP_VERSION` 常量 + 启动时 GET `https://tiktide.com/tool/version.json`(Caddy 静态服务 `/tool/*`,root=/srv/tikflow/public,file_server;Next 生产不实时服务 public 新增文件必须走 Caddy handle)→ 版本不同弹窗"发现新版本"→ 下载新 exe 到同目录 `抓CK工具_new.exe` → 生成 **update.bat(GBK 编码,含中文路径)**:`timeout 2 → taskkill /f /im 抓CK工具.exe → copy /y new exe → del new → start exe → 自删` → 重启自动完成。**更新只传 exe(12MB)不传 chrome/(200MB)**。v1.1.4 起**每 60 秒轮询** version.json(发版后分钟内同步);可选模式提示后 **5 分钟冷却**再提示(不是本会话不再弹);v1.1.5 起支持 **`force:true` 强制更新**(无"稍后",点关闭=退出程序,更新失败也退出);下载带 sha256 校验。完整机制/发版流程见 skill `tiktok-ck-tool-dist`。**老客户无更新机制的历史版本不会自动更新**——发手动更新包(新exe+更新.bat+说明,解压到工具文件夹双击 bat)升一次后全自动。发版 3 步:改 APP_VERSION → pyinstaller 打包 → 上传 exe + 改 version.json(无需重启,验证 curl 两个 URL)
- 抓取工具工程坑(2026-08 实测):
  - **★bat 编码陷阱**:GBK 编码的 bat **绝不能写 `chcp 65001`**——cmd 按当前代码页解析 bat 字节,chcp 65001 后 GBK 中文(含 `python "%~dp0抓tk_ck.py"` 的文件名参数)全变乱码 → "can't open file"。保持 bat 纯 GBK、默认代码页解析,中文参数即正确(python argv 走宽字符,cmd 解析对就行)。同理别用 `cmd //c` 从 git-bash 调中文 bat(用 `MSYS_NO_PATHCONV=1 cmd /c "cd /d 路径 && xxx.bat"`)
  - **★ctypes 剪贴板 64 位指针截断**:`GlobalAlloc/GlobalLock/SetClipboardData` 不设 `restype=c_void_p`(+argtypes)时,句柄被截断成 32 位 → **静默失败**(OpenClipboard 单测返回 1 但完整写入流程 False,超隐蔽)。必须声明 restype;再加"重试 5 次 + PowerShell `Set-Clipboard` 兜底"
  - 弹窗:`ctypes.windll.user32.MessageBoxW(0, text, title, 0x40|0x1000)`(信息图标+置顶),零依赖
  - **测试自动检测逻辑**:无需真账号——CDP `Network.setCookie` 向 .tiktok.com 注入假 `sessionid=test123`,脚本应在 2 秒内自动抓取并写 ck.txt;测完清理进程(按命令行匹配杀)+删 ck.txt
- 已有资产: 用户本机 `D:\渗透\wukong\cdp_get_all_cookies.py` 是同一思路(9225 端口版)
- **★sessionid 真实性校验(2026-08 实测)**:真实 TikTok sessionid 是 40+ 位随机串;工具若把任意短值(如测试注入的 `test-session-123`)当"已登录"会抓出假数据交差。`get_sessionid()` 必须 `len(value) >= 25` 才视为有效登录,过短的忽略继续轮询。同理清理环境时**删掉整个独立 profile 目录**避免假 cookie 残留(用户曾把测试残留当真实 CK 提交过)
- **★不频繁登录防封号 = 产品卖点**:用户明确担心"频繁登录会封号"。两种模式都保证登录一次长期有效:① 独立 profile(抓tk登录ck.bat):登录态存 `ttck\profile`,第二次双击直接已登录秒抓;② **日常浏览器模式(日常Chrome.bat)**:用**用户默认 profile** + `--remote-debugging-port=9222` 启动日常 Chrome(登录态/书签全保留,一次性退出普通 Chrome 即可),之后随时双击抓取工具读当前登录账号——适合主号、已有登录的窗口。别让用户反复登录

### 通道3: 作品列表 = CDP 注入 Cookie + 页面内 fetch(绕过签名,核心突破)
- **TikTok 2026 已全面升级 X-Gnarly/X-Dynosaur 动态签名**——Python requests 直连 `/api/post/item_list/` 即使带完整参数+msToken 也全被拒:
  - `HTTP 400 statusCode 10201 "missing required fields..."`(伪装的签名拦截)
  - `HTTP 200 但空 body`(user/detail 匿名/半套参数时)
- **不要逆向签名、不要自建签名服务器(wukong 模式)**——页面里 webmssdk.js 会**自动给同源请求签名**,驱动浏览器即可:
  1. CDP 把用户 Cookie 注入(`Network.setCookies`, domain=.tiktok.com, httpOnly:true)
  2. 浏览器打开目标主页(拿 secUid)
  3. `Runtime.evaluate` 页面内 `fetch('/api/post/item_list/?uniqueId=xx&secUid=xx&count=20&cursor=0&aid=1988', {credentials:'include'})`
  4. 返回 200 + itemList(播放/赞/评/藏全有,实测 20 条/527KB)
- **post/item_list 必填 `secUid`**(从 SSR 拿);`recommend/item_list` 简单参数页面 fetch 也能 200
- `window.byted_acrawler.frontierSign(url)` 只生成短 X-Bogus(16 字符),**不够**——必须走页面 fetch 让 webmssdk 自动签名

## ★纯 HTTP 采集通道（2026-08-17 实测，推荐方向——绕开浏览器反爬）

- **为什么**：TikTok JS 反爬只作用于浏览器环境（自动化检测 → 跳首页/SSR 空）；**纯 HTTP 请求（无 JS 执行）拿完整 SSR**——实测通过用户代理 curl @tiktok → **368KB 页面 + `"videoCount":1491` + itemList + desc 全在**，无需浏览器、无需 X-Gnarly 签名、无 JS 反爬对抗
- **curl 式请求要点**：走代理（`--socks5-hostname user:pass@host:port`）；带 Chrome UA + `sec-ch-ua`/`sec-fetch-*` 完整头（不带也行，实测带 UA 即可拿数据）；可选带 `cookie` 头（登录账号自己的数据）；`-o` 存文件后 grep `"videoCount"` / `"itemList"` 验证
- **服务器落地方向**：`fetchProfileByCookie`/`fetchVideosByCookie` 的 CDP 实现可用 **HTTP GET @handle 页面 → 解析 SSR HTML** 替代（**资料+stats 全拿**：nickname/avatar/secUid/followerCount/videoCount/heartCount——秒级、稳、零签名）。**★2026-08-19 复核修正：SSR 的 `userInfo.itemList` 永远是空数组**——HTML 里的 `"videoCount":1491` 是 stats 统计不是作品列表，**作品列表不在 SSR 里**（需懒加载 API，带签名）。HTTP 通道只能做资料/统计，作品列表仍需签名接口或 CDP 监听原生请求（见下节"游客模式"）
- **服务器出口必须走用户代理**：香港机房 IP 真被降级（12KB+captcha），**服务器直连无代理采集必失败**——所有采集请求带 account.proxy（代理必填已实施 ✅）
- 实测记录/证据链详见 `references/ip-reputation-and-http-collection-2026-08.md`

## ★游客模式 vs 登录态模式（2026-08-19 实测，作品列表触发条件）

- **游客（不注入 cookie）CDP 打开 @handle 账号页 → 滚动 → 页面 JS 自动请求 `/api/post/item_list/?...&secUid=...`（带 secUid 的账号作品接口），HTTP 200 + JSON（hasMore:true + itemList 完整作品）**——页面自己请求，拦截器自动加 X-Gnarly，无需构造参数/签名
- **注入 cookie（登录态）后反而 0 请求**——登录态账号页不触发懒加载作品请求（防爬策略差异），且手动 fetch（简单参数）返回 200 空 body
- **完整参数集坑**：手动 fetch 用简参（uniqueId/secUid/count/cursor/aid）→ 200 空 body；页面原生 URL 带几十个参数（WebIdLastTime/app_language/browser_*/device_id/odinId/msToken/...）→ 成功。**要复刻原生请求必须抄完整 URL 模板**（用 `Network.requestWillBeSent` 捕获原生 URL 作模板）
- **★CDP 取响应体坑（2026-08-19 已闭环）**：`Network.getResponseBody` 对 item_list 返回空 body（即使 `responseReceived` 时立即获取 + `maxTotalBufferSize` 100MB，`encodedDataLength` 显示 1147 字节但 body 空）——**正解 = puppeteer 层 `page.on('response')` + `resp.buffer()`**（内部处理 gzip/br 解压，实测拿到 425-466KB 完整 JSON）。坑位记录：encodedDataLength>0 但 getResponseBody 空 ≠ 响应空，别在这条路上死磕
- **★完整采集方案（2026-08-19 已验证成功，fetchVideosByCookie 生产实现）**：CDP 游客打开 @handle（**不注入 cookie**）+ stealth（webdriver→undefined + chrome.runtime 清除 + 时区伪装 America/Los_Angeles）→ `waitForSigner`（webmssdk 就绪）→ 等 3s → **滚动 8 次（900-1200ms 随机间隔）触发懒加载，最多 2 轮**（首轮空则再来一轮防波动）→ `page.on('response')` 监听 `/api/post/item_list/`（排除 prefetch）→ `resp.buffer()` 解析 itemList。**实测 @tiktok 79 条完整作品（id/desc/plays/likes/comments/cover）17.8s**。空结果判定：SSR `videoCount===0` → 账号无作品正常返回空；`videoCount>0` 但 items 空 → 抛"作品列表加载失败（IP/浏览器环境被风控）"
- **★作品对象字段（2026-08-19 实测）**：顶层键 `id/desc/stats/author/video/contents/...`（**无 share_url 无顶层 cover**）；`video.cover` 和 `video.originCover` 是**字符串 URL**（不是对象！）；封面取 `video.cover`（字符串）→ `video.originCover` → `video.playAddr.url_list[0]`；videoUrl 无 share_url 时构造 `https://www.tiktok.com/@handle/video/<id>`；stats 字段 `playCount/diggCount/commentCount/collectCount`
- **★同 IP 高频访问触发账号页临时降级（2026-08-19 实测）**：同一代理 IP 短时间连续采集 10+ 次账号页 → 账号页作品懒加载被临时停（**原成功脚本也变 0 条，所有账号都失败**），15min+ 恢复。**测试时控制频率（间隔≥2min），生产 30min 刷新 + 每账号独立 IP 不受影响**
- **★全链路实测闭环（2026-08-19 用户真实数据验证通过）**：真实新抓 CK + 真实 SK5 代理 → ① tokenBeat ok:true → ② `multi_sids=(\d+)` 提 uid → ③ im/user/profile 拿 handle（**绑定可免填 handle，产品增强点**）→ ④ fetchProfileByCookie 资料全拿（nickname/followers/secUid/videoCount）→ ⑤ fetchVideosByCookie 作品全拿（小账号 3 条全采到，含封面/plays）。**全链路无人工干预**
- **★新代理首次连接慢坑（2026-08-19 实测）**：新代理首次跑 CDP 可能页面导航超时（45s Navigation timeout）→ **直接重试一次即成功**（首次连接握手慢/波动），别立刻判代理坏；curl 先验证 IP 本身正常（完整页 367KB+videoCount 在）再重试浏览器

## ★App 协议（api16 tiktokv.com + X-Gorgon）移植结论（2026-08-19 实测）

- **wukong 的 `algorithm/xGorgon8404.ts`（312 行纯 TS + crypto，零依赖）签名算法可整体移植**：`XGorgon8404.stringToMD5(params)` + `XGorgon84MD5(paramMd5, '', cookieMd5, null)` → `X-Gorgon` + `X-Khronos` 头
- **签名+设备参数验证通过**（用 wukong 样例设备参数 device_id/iid/openudid/cdid/idfv）——App tokenBeat 返回**业务错误 `401 session_expired`** 而非签名错误 = 签名算法正确、设备参数被接受
- **★致命限制：App 协议需要 App 会话**——web cookie（sessionid）在 App 域（api16）不通用，tokenBeat 返回 session_expired；aweme/v1/aweme/post 直接 200 空 body。**别移植 App 协议拿 web 登录账号数据（除非用户能提供 App 会话）**——wukong 的 App 协议只适合它自己 App 登录的账号体系
- 域名：api16-normal-c-useast2a.tiktokv.com（443 HTTPS）；wukong 设备参数样例见 `asar_extracted/electron/api/authAPI.ts:244` 注释（完整 URL 含 iid/did/openudid/cdid）


## ★Linux 服务器环境指纹硬伤（2026-08-19 实测，\"用户网页空白\"的服务器侧真相）

- **现象**：本机（Windows 完整 Chrome 152 + 用户代理）采集 79 条成功；同代码同代理在服务器（Linux headless）上**命中 2 次 item_list 但响应全空**——页面正常（标题不跳转）、签名器就绪、请求发了，TikTok 服务器就是不给数据
- **根因**：Linux 服务器浏览器环境有三处**浏览器级只读硬伤**，TikTok 综合判定为自动化：
  1. **`navigator.platform` = "Linux x86_64" 无法覆盖**（Chrome 只读属性，`Object.defineProperty` 静默失败；连 puppeteer-extra-plugin-stealth 也改不了）——与伪装的 Windows UA 自相矛盾
  2. **WebGL = "none"**（headless 无 GPU；`--use-angle=swiftshader-webgl --enable-unsafe-swiftshader` 在 snap 版无效；真人浏览器必有 WebGL）
  3. **时区伪装失败**：`Intl.DateTimeFormat.prototype.resolvedOptions` 覆盖在 Linux Chromium 上不生效（tz 仍 UTC）
- **已验证全失败**：headless shell（UA 带 HeadlessChrome → 页面直接跳首页）、完整 chromium-browser（snap）、xvfb 有头模式、puppeteer-extra-plugin-stealth（plugins/langs 覆盖生效但 platform/webgl/tz 依旧）——**结论：Linux 服务器上把 Chromium 伪装成 Windows 真浏览器不可行，别在这条路上继续投入**
- **★evaluateOnNewDocument 注入中断陷阱（顺带发现）**：注入脚本里 `Object.defineProperty(navigator, "platform", ...)` 在 Linux 上**抛 TypeError → 整个注入脚本中断**，后续 webdriver/时区/chrome.runtime 覆盖全部失效（表现为 webdriver 还是 true、标题跳转）。**每个覆盖必须独立 try-catch**，platform 失败不影响其他
- **★TS 语法不能写进 .mjs（2026-08-19 实测）**：给 server.mjs 打补丁时写了 `function (this: any)` → `SyntaxError: Unexpected token 'this'`（node --check 可先验语法）——纯 JS 文件里 `this: any`/`{...r}` 展开都要换成无类型标注 + `Object.assign({}, r, ...)`
- **★Safari UA + Chromium 内核矛盾反而被降级**：tiktok-signature 默认 Safari macOS UA（MacIntel platform）在 Linux Chromium 上冒充 Safari → UA/内核矛盾 → **账号页降级**（首页不降级，SDK 初始化正常）；改成 Chrome Win UA + Win32 platform 后依旧 SSR null（Linux 深指纹仍是主因）——**curl 无 JS 任意 UA 都正常（367KB），浏览器任何 UA 组合都救不了账号页**
- **★ttwid/msToken 解析坑**：ttwid cookie 值是 URL 编码（`1%7C<dev>%7C<ts>%7C<sig>`）——**必须先 `urllib.parse.unquote` 再按 `|` split**（直接 split 越界）；签名响应 `device-id` 字段可能为 None（不是每次都返回），别依赖它
- **★/collect 模式（可复用实现）**：给签名服务加的"页面原生请求监听"端点模式——`page.on('response')` 匹配 `/api/post/item_list/`（排除 prefetch）→ `resp.buffer()` → JSON.parse → 存 `itemListCache`；`/collect {handle}` → goto @handle → 等 5s → 滚动 8×900ms → 返回缓存。本机已验证原生监听有效；服务器端因环境指纹导航账号页 SSR null 而空。**这是"让页面自己请求、我们只监听"的通用实现模板**，客户端采集可复用
- **SSH exec_command 传 JSON body 的坑**：paramiko `exec_command` 内联带引号/& 的 JSON 会挂——**base64 编码后 `echo b64 | base64 -d > f.json && curl -d @f.json`**；python `open()` 写文件写在**本地**（Windows），传服务器必须 sftp.put（MSYS /tmp 路径 ≠ 服务器 /tmp）
- **出路**：签名服务（下节）绕开浏览器访问 TikTok 页面，或客户端采集（Windows 环境指纹真实，本机已验证）

## ★tiktok-signature 签名服务探索（2026-08-19，部分可行，未最终闭环）

- **资源**：npm `tiktok-signature`（v4.3.6）——webmssdk 完整 SDK（`javascript/webmssdk_5.1.3.js` 等 3 个版本）+ **`xgnarly.mjs`（220 行纯 node X-Gnarly 算法，零浏览器依赖，ChaCha20 + 自定义 base64）** + 签名服务（server.mjs，puppeteer-extra stealth + Safari macOS UA + MacIntel platform + 1920x1080 viewport）
- **xgnarly.mjs 用法**：`encode(queryString, body, userAgent)` → X-Gnarly 头值；`fields` 含 `md5(queryString)/md5(body)/md5(UA)/ts/sdkVersion`（sdkVersion 默认 "1.0.0.368"，字段9 固定 "5.1.3-ZTCA"）——**可纯 node 生成 X-Gnarly（不访问 TikTok、无指纹检测）**，已拷入项目 `src/lib/tiktok/xgnarly.mjs`
- **部署实测**：服务器 `/srv/tsig`（server.mjs + xgnarly.mjs + javascript/webmssdk_*.js + puppeteer-extra）→ `node server.mjs` → `/health` OK（initMethod: local-sdk, hasAcrawler:true, 捕获 6 cookies）——**webmssdk 本地注入成功，浏览器无需访问 TikTok 页面也能生成签名**
- **★外部重放无效（实测确认）**：`POST /signature` 返回签名 URL（1153 字符，含 X-Gnarly/msToken）→ curl 外部重放（同 IP）→ **HTTP 400 statusCode 10201**——签名绑定浏览器会话上下文，外部重放被 TikTok 拒绝（与 memory 既有结论一致）
- **★IP 一致性原则**：香港服务器 IP 会话下 `/fetch` 也 10201（IP 层被风控）；签名服务加 `PROXY_ENABLED=true PROXY_HOST=127.0.0.1:8888`（本地桥 → 用户代理）后 `/fetch` 返回 `httpStatus:200`（过了风控）但 `data:null`（浏览器内 fetch 响应仍空）——**最后一步未闭环**（浏览器会话签名 fetch 的响应仍空，可能参数/会话上下文问题）
- **经验教训**：① secUid 从 SSR 实时解析拿**完整值**（测试截断版导致 10201 误判）；② 服务器起 socks5 认证桥用 python 脚本（`scripts/proxy_bridge_srv.py`，socks5 握手 + 双向 pipe）；③ 签名服务的浏览器会话 IP 必须 = 外部请求 IP

## ★服务器采集终极结论（2026-08-19 全路线穷尽，别再投入服务器浏览器方案）

- **Linux 服务器上任何浏览器方案都拿不到账号页作品数据**——穷尽验证：headless shell（UA HeadlessChrome 跳转）/ 完整 chromium（platform 硬伤）/ xvfb 有头 / puppeteer-extra-stealth / X-Gnarly 纯算法外部重放 / tiktok-signature 签名服务 / 带会话 cookie 外部请求 / /collect 页面监听——**全部失败**
- **签名服务也救不了（最终闭环，推翻上节"部分可行"）**：签名服务浏览器换 Chrome Win UA + platform Win32 + 时区伪装 + 走用户代理桥后：`/collect` 导航账号页 **SSR 仍 null**（200 无数据）；`/fetch` 页面内 fetch **200 data:null**；`/signature` 外部重放（同 IP + 会话 cookie + 完整头）**200 空 body**——TikTok 2026 只认"浏览器上下文内 + 真实环境指纹（Linux 无法伪造）"的请求，**签名生成 ≠ 请求放行**
- **curl 是唯一稳定通道（资料级）**：无 JS = 无指纹检测，**任意 UA（Linux/Windows）**走用户代理都能拿 367KB 完整 SSR（secUid/videoCount/followers/私密标记）——但 **SSR 不含作品列表**（`userInfo.itemList` 永远空数组，videoCount 只是统计）
- **★结论架构（2026-08-19 用户拍板「按客户端开发」，已实施 v1.3.2）**：**资料 = 服务器 curl SSR（零浏览器，已验证 367KB）**；**作品 = 客户端（Windows 真实 Chrome）采集上传**——Linux 服务器任何浏览器方案都拿不到作品，客户端是唯一能拿到作品的路径。**服务器浏览器采集是时间黑洞，别再投入**

## ★客户端作品同步通道（2026-08-19 已上线 v1.3.2，作品采集最终方案）

- **架构**：服务器只管 tokenBeat 验证 + curl SSR 资料；作品由客户端工具（Windows 真实 Chrome 环境，本机已验证 95 条）采集后上传
- **同步码（syncToken）机制**：绑定成功 → `TikTokAccount.syncToken`（randomBytes(6).hex，12 字符）→ 绑定 API 返回 → 前端弹窗显示「同步码」+ 复制按钮 → 客户端输入同步码认领账号 → `POST /api/tiktok/videos/sync {syncToken, videos[]}`（zod 校验，≤200 条，按 tiktokVideoId upsert 去重）→ 服务器 `syncVideosFromClient` 落库 + 更新 lastSyncAt
- **客户端采集实现（tk_ck_gui.py，Python 纯 CDP 无 puppeteer）**：
  1. `SyncTask`：起 Chrome（**游客 profile** `guest_{hash(host+port)}` + 代理桥）→ `collect_videos_cdp` → `upload_videos_sync` → 关闭 Chrome
  2. **★CDPClient 必须单 recv 循环**：websocket 非线程安全，双线程同时 recv 消息乱/丢 → `CDPClient` 类（一个 `_loop` 线程 + `_pending` 回调 dict + `events` 队列，主线程 `call()` 等待响应）
  3. **★Network.getResponseBody 在有头完整 Chrome 上直接可用（95 条实测）**——与 headless 下"空 body"（Node puppeteer 实测）形成对照；客户端工具用有头 Chrome 所以**原生 CDP 即可，无需 puppeteer 层 resp.buffer()**。body 可能 base64Encoded（需 base64 解码）
  4. 采集流程同游客模式：注入 webdriver 覆盖 → Network.enable(maxTotalBufferSize 100MB) → Page.navigate @handle → 等 8s → 滚动 8×1.2s → 遍历 responseReceived 事件（匹配 `/api/post/item_list/` 排除 prefetch）→ getResponseBody → 解析 itemList → 按 id 去重
  5. 作品字段映射：`video.cover` 字符串 URL（或 originCover/playAddr.url_list[0]）；videoUrl 构造 `https://www.tiktok.com/@handle/video/<id>`；stats 取 playCount/diggCount/commentCount/collectCount
  6. GUI：「同步作品」按钮（Toplevel 弹窗：同步码 + handle + 提示用选中行代理）→ `_start_sync` 起线程 → 事件 `sync_status/sync_done/sync_error` 走 msg_q（复用 _drain 泵，新事件类型必须与解包格式一致）
- **产品流程**：绑定成功弹同步码 → 工具填同步码+handle → 采集上传 → 平台作品网格有真实数据。**私密账号采不到**（游客模式只能看公开页）——与服务器端一致，非 bug
- **坑**：同步码输入校验 ≥6 字符；handle 去 `@`；代理用列表选中行（避免重复输入）；上传用 tiktide.com 正式证书直连（国内可达）


```
用户浏览器(CDP工具) → Cookie → 网站提交
        ↓
服务器 headless Chromium + CDP: 注入Cookie → 打开主页 → SSR解析用户信息 + fetch作品列表
        ↓
落库 → 定时刷新(30min+,风控保守) → Cookie失效标记(检测sessionid无效)
```
- 用户信息通道无需 Cookie → 绑定账号可只填 handle(零门槛),Cookie 作选填增强
- 服务端 headless Chrome: Playwright/Puppeteer-core 均可,复用单浏览器实例按账号切 Cookie

## Next.js 14 集成 CDP（工程坑,2026-08 实测）
- **webpack 不认 `node:` 前缀**:`node:child_process` / `node:crypto` → `UnhandledSchemeError`。修复见 `references/nextjs-14-browser-automation.md`
- **instrumentation.ts 会同时编译 edge 版本**:register() 里 import node:child_process → `edge-instrumentation.js` SyntaxError → **全站页面 500**(登录 API 200 但页面全挂,症状隐蔽)。修复:浏览器启动移到独立脚本 `scripts/start-cdp-browser.ts`(pm2/tsx 托管),instrumentation 只消费 CDP 端口(`if (NEXT_RUNTIME !== "nodejs") return` 只防运行不防编译)
- **puppeteer-core v24 类型需 ES2015+ target**:单文件 lint 报 node_modules 类型错是假警报(不读 tsconfig skipLibCheck),以项目级 `npx tsc --noEmit` 为准
- **作品列表代码化后 `json_200_` 空 body（已定位，2026-08 最终结论）**:手工 CDP 成功但 puppeteer 代码化后 fetch 空——试过 `networkidle2`、goto→reload、`waitForFunction('window.byted_acrawler.frontierSign')`+600ms、额外 4s 延时,**全部无效**。最终 CDP 诊断(主 tab 复测同样空)确认根因是**异地 IP 风控**(见 Pitfalls),不是时序。判别法:**先主 tab 手工复测**——空=风控(别改代码),有数据=才查时序/参数

## Pitfalls
- **教小白用户拿 Cookie**:F12/Application 面板对多数人太复杂 → 直接给 CDP 工具(bat 双击),别教 console(拿不到 HttpOnly)
- **★异地 IP 风控（实测，会话级，与数据中心 IP 降级不同）**:用户浏览器登录的 Cookie 从**异地 IP**(代理/服务器)使用时,TikTok 会**静默风控**——同一浏览器+同一 Cookie 几小时前成功(20条/527KB),之后变 `HTTP 200 空 body`,无任何错误提示。判别法:**同浏览器手工 CDP 复测**——也空 = Cookie 被风控(非代码问题),成功 = 才是代码/时序问题。这是行业现实(wukong 养 169 个号+固定 IP 的原因),不是可修复的 bug
- **★数据中心 IP 全局限级（2026-08-17 实测，第四类空数据原因，与 Orca 接口拦截并列）**：**出口 IP 是数据中心 IP（DC 代理 199.239.16.12 / 香港机房 118.107.3.134）时，TikTok 对内容接口全局限级**——SSR `postData` 完全为空（连 @tiktok 官方账号、verified 账号也一样）、页面 DOM 滚动加载不出作品（DOMvids:0）、服务器直连抓包仅 12KB 骨架页 + captcha。**tokenBeat 护照接口不受影响（所以验证通过但采集为空——用户"应用了 wukong 协议还是采不到作品"的真相）**。判别三连：① tokenBeat ok:true（登录态好）；② 页面正常渲染（标题/用户信息有）；③ **SSR `ud.postData.itemList` 空 + DOM 滚动 0 作品 + 直连 curl 页面 <15KB 含 captcha** = IP 信誉降级。**与 Orca 拦截的区分**：Orca 是 recommend 正常而 post/item_list 空（接口级）；IP 降级是**所有内容数据全空**（SSR 就空）。**无解（协议无关）**——必须换住宅 IP 代理（residential），数据中心 IP 换什么协议都拿不到内容。已上线：`fetchVideosByCookie` 遇 SSR 空 → `no_items_ip_blocked` → 可读错误"出口 IP 被 TikTok 降级（数据中心 IP 常见），请更换住宅 IP 代理"
- **★IP 信誉判定法 + 2026-08-17 深夜复核（推翻上条对 199.239.16.12 的"降级"结论——IP 是干净的，真凶是 Chrome JS 反爬）**：
  - **判定法（铁律：先用 curl 对照，别直接怪 IP）**：`curl --socks5-hostname 'user:pass@host:port' -H 'UA: Chrome Windows' 'https://www.tiktok.com/@handle' -o page.html`（服务器上跑，走同一代理）→ 页面 **≥200KB 且有 `"videoCount":N` / `"itemList"`** = **IP 干净**，问题在浏览器侧；页面 **<15KB 含 captcha/verify** = IP 真被降级（如香港机房 118.107.3.134 实测 12KB+captcha）。
  - **权威 IP 类型检测**：`curl --socks5-hostname ... 'http://ip-api.com/json/?fields=query,isp,org,as,proxy,hosting,country,city'` → `hosting:false, proxy:false` = 非机房非代理标记。用户 SK5（199.239.16.12，NTT America/Centennial CO）实测 **hosting:false proxy:false**，curl 通过它拿 368KB 完整 SSR（@tiktok videoCount:1491）→ **代理 IP 从未被降级**。ipinfo.io 免费版 `type` 字段常缺，用 ip-api 更全。
  - **★Chrome 自动化被 JS 反爬降级（同 IP 同 URL：curl 有数据 / Chrome SSR 空 的决定性差异）**：TikTok 客户端 JS 检测自动化环境（不止 navigator.webdriver——CDP 痕迹/环境指纹），命中后**跳转首页**（`document.title` 变 "TikTok - Make Your Day"、`location.href` 变根路径、postData 空、DOM 滚动 0 作品）。**判别：页面 evaluate 时看 title/href 是否被跳首页**。**★2026-08-19 实测补丁组合：`--disable-blink-features=AutomationControlled` + `navigator.webdriver→undefined` + 时区伪装（`Intl.DateTimeFormat.prototype.resolvedOptions` 覆写 timeZone=America/Los_Angeles）后页面不再跳转**（标题保持 @tiktok | TikTok）——单 webdriver 覆盖确实不够，**时区伪装是关键补强**。**别在浏览器反爬对抗上死磕——绕开浏览器走纯 HTTP（下节）**
  - 结论修正：**"数据中心 IP 换什么协议都拿不到内容" 仅适用于真被降级的 IP（香港机房类）**；用户代理类 IP 先按判定法验证再下结论
- **★wukong im/user/profile 免签名账号资料接口（2026-08-17 实测）**：`GET https://www.tiktok.com/tiktok/v1/im/user/profile/?aid=1988&user_ids=%5B<uid>%5D`（**user_ids 是 URL 编码 JSON 数组** `%5Buid%5D`，裸 uid 返回 Invalid parameters）带 Cookie + UA + sec-ch-ua + Origin/Referer → status_code 0 + `users[0].im_user_profile`（nick_name/unique_id/avatars/signature/user_id_str）——**免签名、数据中心 IP 也能用**，可作为账号资料兜底（私密/风控账号时至少能拿 handle/昵称/头像）。uid 从 cookie 取：`multi_sids=(\d+)`（**uid_tt 可能被脱敏截断成短值，别用它**）
- **★新 Cookie 生命周期预期(产品设计必知)**:新抓的 Cookie 首次从服务器 IP 使用可能短暂可用(首次陌生 IP 放行),随后被标记风控(几小时~一天内)→ **用户需定期换新 CK**,这是 CK 主通道模式的固有运维节奏,前端 UNAUTHORIZED 提醒+一键更新就是为此设计的。别承诺"绑定一次永久可用"
- **★绑定"一直绑定中"修复(2026-08-16 实测)**:根因=绑定流程**串行跑两次浏览器采集**(fetchProfileByCookie + fetchVideosByCookie,各自 goto 40s+reload 45s+waitFor 20s → 最坏 3.5 分钟)+ 前端 loading 无超时 → 用户看到无限"绑定中"。三层修复:① 后端 `Promise.all([profile, videos])` **并行采集**(独立实例同时跑,耗时减半);② 总超时 `Promise.race([Promise.all([...]), new Promise(reject => setTimeout(90s))])` → 超时抛 CookieAuthError("绑定采集超时...")→ 400;③ 前端 fetch `AbortController` + 90s `setTimeout(abort)` → `AbortError` 显示 bindTimeout 文案("绑定超时(90秒),请检查 Cookie 和代理后重试")。改后最坏 90 秒必出结果(成功或明确错误),不再无限转圈。验证生产代码生效:`grep '绑定采集超时' .next/server/chunks/*.js`
- **★新抓 CK 报"已失效"的四因排查(2026-08-16 用户实测)**:用户新抓的 CK 绑定报 cookie_invalid,按此序排查:
  1. **误抓旧登录态(最隐蔽,已修)**:工具用独立 profile 保留登录态——**代理不通/TikTok 页面没加载出来时 cookies 仍在**,轮询照样能抓到 sessionid → 显示"抓取成功"但实际是过期旧 CK。用户看到 Chrome 窗口"未连接到服务器"但工具报成功 = 铁证。工具修复(v1.1.1+):轮询时检查页面 URL(`chrome-error://`/`ERR_`/`无法访问`/`unreachable` → 明确报"代理连接失败,请检查代理是否过期/可用"并停止,不抓旧 CK);抓到后二次校验页面非错误页
  2. **抓取 IP ≠ 绑定代理 IP**:用旧工具或抓取时没填代理 → Cookie 绑定本地网络 IP;绑定填了美国代理 → 服务器从美国 IP 访问 → TikTok 判异地 → 失效。铁律:抓取时浏览器必须走代理
  3. **动态轮换代理**:每次连接出口 IP 不同 → 抓取时 IP₁/采集时 IP₂ → 触发风控。要求客户用**固定 IP(sticky)模式**
  4. **★Orca 风控吞 item_list(2026-08-16 定位,最隐蔽,详见下条)**:`post/item_list` 返回 **HTTP 200 空包**(json_200_)即使 profile SSR 完全正常。判别特征:响应头带 **`tt_orcas_res: 1`**;同页面 `recommend/item_list` 正常。最易触发组合:**新注册小号(0粉0作品) + 数据中心代理 IP(ddcn=DC) + headless 指纹**。**修复已上线**:作品列表失败不再致命(见下条"对绑定的影响"),前端错误码细分不再误导"Cookie 无效"
- **★作品列表 json_200_ 空包的第三类原因:Orca 接口级拦截(2026-08-16 实测,区别于全局 IP 风控)**:post/item_list 返回 HTTP 200 空 body,但**同页面同 Cookie 同 IP 下 recommend/item_list 正常返回(实测 661KB)** → 签名器就绪、IP 未被全局限,是 TikTok Orca 风控引擎对**登录敏感接口**的针对性拦截。判别三连(实测有效):
  1. profile SSR 解析出登录用户 → **Cookie 完全有效**,别信前端"Cookie 无效或已失效"文案(那是 videos 失败映射的误导)
  2. recommend/item_list 有数据 → 签名器/IP 正常
  3. post/item_list 空包(200, content-length 0, content-type application/json)→ Orca 拦截;铁证=响应头 **`tt_orcas_res: 1`**(正常响应带 `bd-tt-error-code: 0` 且无 orcas 头)
  触发场景实测:新注册小号(0粉0作品)+ 数据中心代理(用户名含 ddcn,出口 199.239.16.12)+ headless 指纹,三者叠加信誉极低;连 @tiktok(1491作品)同条件也空包,证明是**会话级接口拦截**而非账号无作品。缓解:住宅(residential)代理 + 养号(工具浏览器真实浏览几分钟再抓 CK)。
  **对绑定的影响**:bindAccount/updateAccountCookie 里 profile+videos 并行,videos 空包 → CookieAuthError → route 只回 `{error:"cookie_invalid"}`(message 被丢弃)→ 前端"Cookie无效或已失效"。**CK 没坏,是作品列表被拦**。**修复已上线(2026-08-16 拍板+E2E验证)**:① `fetchVideosByCookie` 作品列表类错误(no_ssr/no_user/json_200_ 等)一律 `console.warn`+`return []`(仅网络/代理层错误仍抛),绑定/刷新成败由 profile 决定;② `CookieAuthError` 加 code(proxy_error/page_unreachable/page_blocked/bind_timeout),bind route 返回 `{error:e.code}`,前端 bind-dialog 按 code 映射 i18n(bindProxyError/bindPageBlocked/bindPageUnreachable/bindTimeout/cookieInvalid);③ E2E 实测:真实 CK+代理绑 fan87921 → HTTP 200/38s/BOUND(作品0),坏代理 → 400 page_unreachable,裸 host:port → 400 invalid_input。复现探针:`scripts/repro-bind-flow.js`
- **服务器容量参考(2026-08-16 实测 12核/8GB)**:无代理账号共用 9223 常驻实例,每 page ~50-100MB;有代理账号每次刷新动态独立实例 ~250-300MB/个,同时并发 15-20 个;刷新**串行**(for 循环),30 分钟窗口约刷 60-100 个账号。**风控是真正上限**:无代理全部共用服务器 1 个 IP → ≤3-5 个(互相关联风险);有代理独立 IP → 50-100 个。闲置账号(无 ACTIVE 投放)完全不刷,挂多少都不占资源
- **作品列表 `json_200_` 空 body 的三类原因**:① webmssdk 签名器未就绪(新开 tab 立即 fetch,`waitForFunction('window.byted_acrawler.frontierSign')` + 延时可缓解)② Cookie 被全局风控(见上,延时无效)③ **Orca 接口级拦截(2026-08-16 实测,见上一条:recommend 正常而 post 空包 + 响应头 tt_orcas_res:1)**。判别法:同页面复测 recommend——recommend 有数据而 post 空 = 第③类(Orca 接口拦截,别改代码);recommend 也空 = ①/② 再细分
- **页面 fetch 报 SyntaxError**:CDP 拼 JS 表达式时不要用 Python f-string 内插长值(secUid 等),改成 JS 内 `document.getElementById(...)` 自取或 `JSON.stringify` 转义
- **Cookie 敏感**:测试完提醒用户在 TikTok 设置"退出所有设备"作废;库中存储应加密;API 返回必须剥离 cookie 字段(stripCookie)
- **风控**:采集频率保守,优先只采绑定账号本人;高频/多账号会被风控
- 别名: CK = Cookie;wukong 的签名服务器(getWssWebHeader)是旧方案,用 CDP 浏览器自动签名替代

## 产品闭环（CK 主通道,2026-08 用户拍板）
- **CK 是主通道**:用户提交 Cookie → 采集账号+作品数据;Cookie 掉了(刷新失败/采集失败) → 账号标 `UNAUTHORIZED`
- 前端:卡片状态徽章(已绑定/异常/Cookie失效)+ 失效横幅提示"Cookie 已失效,请更新" + 「更新 Cookie」入口(弹窗只填新 Cookie,handle 只读)
- 后端:`POST /api/tiktok/bind` body 带 `accountId + cookie` → 更新模式:新 Cookie 采集验证 → 更新凭据+status=BOUND+重同步(updateAccountCookie)
- 不做自动降级(EnsembleData 可作兜底但用户明确 CK 主通道);SSR 用户信息零依赖仍是最稳的兜底展示

## ★每账号独立代理 IP(用户明确要求,2026-08 补)
- **为什么必需**:异地 IP 风控的根源 = 服务器单一出口 IP 与用户登录 IP 不一致 + 多账号同 IP 互相关联。用户拍板:**用户自己提供代理,IP 与自己登录 TikTok 的网络一致** → 登录 IP = 采集 IP → 风控大幅降低(wukong 养号做法)
- 实现:账号绑定时填代理地址(选填),采集时**动态启动带 `--proxy-server` 的独立浏览器实例**(puppeteer.launch + executablePath=TIKTOK_CDP_BIN),用完 close;无代理账号走常驻实例(connect)
- schema:`TikTokAccount.proxy String?`(敏感,与 cookie 一样**仅存库不返前端**,stripSensitive 一并剥离)
- 采集函数签名:`fetchProfileByCookie(cookie, handle, proxy?)` / `fetchVideosByCookie(cookie, handle, proxy?)`;刷新时读 `account.proxy` 传入;更新模式 `updateAccountCookie(userId, accountId, cookie, proxy?)` 也接受 proxy(bind route body 带 accountId 时一并透传)
- **代理不可达必须转可读错误**:puppeteer goto/reload 抛 `net::ERR_PROXY_CONNECTION_FAILED` → 不转换会 500。用 `CookieAuthError`(匹配 /ERR_PROXY|ERR_CONNECTION|ETIMEDOUT|ECONNREFUSED/)→ 上层 400 cookie_invalid,前端提示检查代理
- launch 参数:`--no-sandbox --disable-gpu --no-first-run --disable-dev-shm-usage --remote-allow-origins=* --proxy-server=... about:blank`
- 代理格式:`http://user:pass@host:port` 或 `socks5://host:port`(SK5),`#美国` 等备注标签自动剥离(parseProxy 里 `replace(/#.*$/,'')`)
- **★代理认证处理(2026-08 两阶段演进,以最终方案为准)**:① **socks5 带账号密码 Chrome `--proxy-server` 不支持**——但不要抛错拒绝(用户实际代理全是带认证 SK5!):**起本地认证桥**(纯标准库 HTTP CONNECT 桥 → SOCKS5 带认证上游),Chrome 连 `http://127.0.0.1:随机端口`,认证信息不进 Chrome 参数。完整实现+验证见 `references/socks5-auth-bridge.md`(含 CONNECT 响应残留字节坑:不读完 ATYP 后地址部分会污染 TLS → ERR_SSL_PROTOCOL_ERROR);② **HTTP 认证绝不能塞进 `--proxy-server`**(Chrome 会弹认证框/失败)——`parseProxy()` 正则 `^(https?|socks5|socks5h):\/\/(?:([^:@/]+):([^@/]*)@)?([^/\s]+)$` 拆出 user/pass,`--proxy-server` 只放净化后的 `scheme://host`,认证用 `page.authenticate({username,password})`,且 **`browser.on('targetcreated')` 监听给后续新开的页面自动 authenticate**(launch 时只覆盖初始页);桥的生命周期绑定 `browser.on('disconnected')` 自动 close
- **★客户端 GUI 工具同款修正（v1.3.1，实测）**：`--proxy-server=http://user:pass@host:port` 被 Chrome **完全静默忽略并回退直连**（不是弹框/报错，是无痕失效——代理收不到任何请求）→ **抓取 IP ≠ 代理 IP = 绑定失效隐患**。修复：客户端 HTTP 带认证同样走本地桥（`_connect_upstream` 加 http/https 分支：CONNECT 隧道 + `Proxy-Authorization: Basic`；`run()` 里 `proxy.get("user")` 也进桥）；HTTP 无认证直塞 `--proxy-server=http://host:port` 合法。**验证法：本地起 Basic 认证 HTTP 代理 → 工具桥 → 访问 example.com 应 200 + 认证头送达；旧实现 Chrome 直连成功但代理 0 请求**。另 v1.3.1 `parse_proxy` 支持 IPv6（`[::1]:1080` 含认证）
- 桥依赖:`npm i socks`(纯 JS);**必须加进 next.config externals**(它 require('net'/'stream') 不带 node: 前缀,webpack 服务端构建报 `Module not found: Can't resolve 'net'`);引入新 node 生态依赖后**务必本地 `npm run build` 验证再部署**(typecheck 过≠webpack 打包过)
- UI:绑定/更新弹窗 Cookie 输入框下方加"代理地址"Input,placeholder 提示"建议与你登录 TikTok 的网络 IP 一致"(zh/en 已含 socks5 格式说明)
- **★代理必填(2026-08-16 用户拍板:"没有提交独立的ip的直接不能在官网绑定")**:
  - 后端 `bindSchema.proxy` 从 `z.string().max(200).optional()` 改**必填 + 格式校验**:`.min(7,'proxy_required').max(200).regex(/^(https?|socks5h?):\/\/[^\s]+$|^[^\s:@/]+:[^\s@/]+@[^\s/]+:\d+$/,'proxy_format')`(支持 `#美国` 备注;裸 `host:port` 无 scheme 会被拒——要求显式 http/socks5 前缀)
  - 前端:新绑定提交前校验 `!isUpdate && !proxy.trim() → setError(proxyRequired)`;**isUpdate(刷新已有账号)可不填→沿用 account.proxy**(后端 `proxy?.trim() || account.proxy` 兜底)
  - i18n:`proxyOptional` 键删除,新增 `proxyRequired`("必填 · 每账号独立 IP");placeholder 注明"需与登录 TikTok 的网络 IP 一致"
  - zod 校验断言验证法:本地 `node -e` 直接 require zod 建同构 schema 跑用例矩阵(空→too_small / SK5带认证+备注→pass / http带认证→pass / 裸host:port→reject),比打 API 快

## 服务端部署(headless 采集浏览器)
- **★snap 版 chromium 有 AppArmor 限制**:`--remote-debugging-port` 不监听(进程在、端口不通,curl 空)——服务器上勿用 snap chromium 做 CDP
- 正确:Chrome-for-Testing **headless shell** 独立二进制(`chrome-headless-shell-linux64.zip`,storage.googleapis.com,~100MB),解压到 /opt/chromium
- headless shell 运行依赖(Ubuntu 24.04):`libnspr4 libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2t64 libpango-1.0-0 libcairo2 libx11-6 libxcb1 libxext6 fonts-liberation`——**`libasound2` 在 24.04 改名 `libasound2t64`**(旧名无安装候选,apt 直接失败);缺库症状:binary 报 `error while loading shared libraries: libnspr4.so`(只列第一个缺的,实际可能缺一串)
- 服务器可能无 `unzip` → 用 `python3 -c "import zipfile; zipfile.ZipFile('x.zip').extractall('/opt/chromium')"`;CfT zip 解压后**二进制丢执行权限** → `chmod +x .../chrome-headless-shell`
- pm2 托管路径坑:`pm2 start node -- scripts/start-cdp-browser.cjs` 相对路径按 pm2 cwd(/root)解析 → **必须绝对路径** `pm2 start node -- /srv/tikflow/scripts/start-cdp-browser.cjs`
- 部署脚本陷阱:tar 包上传后**记得 `tar xzf` 解压**再 build(update.sh 模板易漏此步,漏了就是旧代码上线)
- 生产 .env:`TIKTOK_CDP_BIN=/opt/chromium/chrome-headless-shell-linux64/chrome-headless-shell` + `TIKTOK_CDP_PORT=9223`
- 浏览器守护:pm2 托管纯 JS 脚本 `scripts/start-cdp-browser.cjs`(node 直接跑,勿依赖 tsx):`TIKTOK_CDP_BIN=... TIKTOK_CDP_PORT=9223 pm2 start node --name tikflow-cdp -- scripts/start-cdp-browser.cjs`
- 应用侧只消费端口(`cdpConfigured()` 读 env),instrumentation 只注册刷新定时器(见 Next.js 工程坑)
- **live 测试隔离**:需真实 Cookie 的测试命名 `*.live.test.ts`(默认不被 vitest 收集),`TT_CK=... npx vitest run tests/.../xxx.live.test.ts` 手动跑,`describe.skipIf(!TT_CK)` 保护

## ★生产 .env 变更不生效 = pm2 环境快照坑(2026-08 实测,通用)
- **症状**:改 .env 加新变量(如 `USDT_TRC20_ADDRESS=...`)→ `pm2 restart tikflow` 后功能仍不生效(充值仍 503 payment_not_configured)
- **根因**:pm2 进程 env 快照里**已有同名键但值为空**(早前 .env 空值占位时 `pm2 start` 带入快照)→ Next 的 dotenv **不覆盖已有 env 变量** → .env 新值被忽略
- **判别**:`pm2 env <id> | grep 变量名` 看进程快照——值空 = 中招
- **修复**:`export VAR=真实值 && pm2 restart tikflow --update-env`(把 shell 值注入进程 env 覆盖空值),再验证 `pm2 env 0 | grep VAR`
- **规律**:.env 首次出现的键没问题;**从空值/占位改成真实值**的键必踩此坑;payments 类(USDT/PAYPAL/STRIPE)尤其常见(初始全是空占位)
- 顺带:PAY_METHOD 枚举是大写 `"USDT"`(z.enum),测试传 `usdt` 小写会 invalid_input 400——先过 schema 再打 API,别被误导成配置问题

## 支付启用链路(USDT TRC20 主通道,2026-08 验证)
- .env 配 `USDT_TRC20_ADDRESS=<T开头34位地址>` + 可选 `TRON_API_KEY`(不配走公共节点) → 充值订单 HTTP 200
- 返回 `mode:"onchain"` + `expectedAmount` 含**校验尾数**(如 100.9272)→ 精确金额自动匹配到账(60 秒轮询 `USDT_SCAN_SECONDS`),用户无需提交凭证
- 未配任何网关时充值 503 `payment_not_configured`(前端显示禁用态)——这是防白嫖设计,不是 bug
- **未开通通道的前端提示(2026-08)**:`GET /api/wallet/methods` 返回 `{methods:{PAYPAL:false,USDT:true,VISA:false}}`(gateway.paymentMethodsStatus,凭证配齐自动变 true 无需改代码)→ 前端点击不可用通道按钮时提示而非等充值才报错;**用户文案偏好:简短中性,不要推销/引导式**——"该通道正在开通中,请先使用 USDT 充值"被否,最终定稿 **"该通道暂无可支付方式"**(en: "No payment method available for this channel yet")。提示用页面内联错误条,不置灰不加角标(用户明确不要)
  - **★点击必须保留视觉反馈**:不可用通道被点后**蓝框/选中态必须跟随过去**(用户\"蓝色的框不跟随,一直定死\"反馈)——选中 + 同时弹提示,而不是拦截选中只弹提示。充值按钮再拦一道(selected 不可用通道点\"立即充值\"同样提示,不发请求)
  - **★错误提示要渲染在所有 step**:错误提示条若只写在 step=pay 视图,form 页点击会\"没反应\"(状态设置了但无渲染位置)。任何表单页的点击反馈错误必须在该视图内联渲染(按钮下方)
- **★支付信息结构化卡片(2026-08 用户\"优化一下样式\")**:USDT 链上转账的 payInfo 一长串文字(地址+金额+说明混排)用户难看清——后端 `ChargeResult` 加 `payDetail?: {address, amount, currency, network}`(usdtGateway 返回;recharge route 透传 `payDetail ?? null`),前端 mode==='onchain' && payDetail 时渲染两卡片:① 地址卡(label+等宽 font-mono 地址+**复制按钮**,复制后变\"已复制\"2s,navigator.clipboard);② 金额卡(text-2xl 大字+右角\"金额含校验尾数/自动匹配到账\"小字);非 onchain/无 payDetail 走原 payInfo 纯文本兜底

## 提现链路（USDT 收款地址,2026-08 完善）
- 流程：用户填金额 + **USDT TRC20 收款地址** → 冻结余额(REVIEWING) → 管理员在 `admin/withdrawals` 看到地址**人工打款** → approve(置 COMPLETED)/reject(退回余额+理由,note 存理由)
- **★最低提现 100 USDT(2026-08 用户要求)双层校验**:后端 `requestWithdraw` 内 `amount < 100 → WalletError("min_amount")`(service 层铁律)+ route schema `z.number().min(100).max(1_000_000)`(入参层);前端弹窗 `min={100}` + submit 校验 `amount < 100 → setError(withdrawMinError)`(本地即时提示,不发请求);错误映射 route 里 `min_amount → 400 min_amount`;文案键 `withdrawMinError`(\"最低提现 100 USDT\")+ label 显示 `最低 100 · ≤ 可用`
- schema：`WalletTransaction.payToAddress String?`(WITHDRAW 类型必填；admin.ts listPendingWithdraws 返回 address 字段)
- **TRC20 地址格式校验**：`/^T[1-9A-HJ-NP-Za-km-z]{25,42}$/`（base58 字符集，**不含 0/O/I/l**）；宽松校验防误填，前端同正则
- ★测试/夹具地址必须用合法 base58 字符：如 `TAbcdefghijkmnopqrstuvwxyz23456789`——`TTest1234567890...` 含 `0` 会 invalid_address 拒掉（正则校验对测试数据同样生效，别用随手编的串）
- 前端提现弹窗：金额 + 地址输入(必填,font-mono) + 时效说明"审核通过后 1-3 个工作日打款"；成功视图显示进度提示
- 管理端列表加"收款地址"列（`font-mono break-all` + title 完整值），管理员照地址打款——地址是人工打款流程的必要信息
- API：`POST /api/wallet/withdraw {amount, address}`；错误映射 invalid_address / insufficient_balance(400)
- `requestWithdraw(userId, amount, payToAddress)` 改为 3 参数——**改签名必须同步改测试**（tests/admin/admin.test.ts、tests/wallet/ledger.test.ts 里所有调用点，否则 typecheck 红）
- **人工加余额(客服/运营操作,2026-08 实测)**:生产 `cd /srv/tikflow && node -e "..."` 用 PrismaClient 直接 `user.update({where:{email}, data:{balance:{increment:N}}})`(balance 在 User 表,无独立 Wallet 表);先 `findUnique` 确认用户存在并打印 before→after;临时脚本用完删除;注意生产 node 读 .env 用 prisma 直连(不走 Next)

## 上线前文案清理(用户偏好:正式感)
- 落地页/钱包页开发痕迹文案(沙箱/全模拟/演示/占位)**必须全清**:如"全模拟沙箱"→"全自动到账"、"PayPal/USDT/Visa 沙箱秒到账"→"USDT/PayPal/Visa 充值秒到账"、"我已完成支付(沙箱)"→"我已完成支付"、footer"全模拟管理式"→正式定位
- 代码注释/内部逻辑(沙箱结算分支、法务核订注释)保留无妨(不渲染);生产环境沙箱结算分支已禁用
- 改完 `grep -rn "沙箱|全模拟|演示|模拟数据" messages/` 确认零残留再部署

## 域名 + HTTPS 上线(Caddy,2026-08 实测)
- **分工**:用户去注册商加 DNS(我不能碰注册商),我配服务器 Caddy。用户只做一步:A 记录 `@` → `118.107.3.134`(www 可选),各注册商位置:阿里云/腾讯云/Namecheap Advanced DNS/Cloudflare
- **Caddyfile 双块结构**(IP 回退 + 域名 HTTPS 块共存):
  ```
  http://118.107.3.134 { encode gzip; reverse_proxy 127.0.0.1:3000 }
  tiktide.com, www.tiktide.com { encode gzip; reverse_proxy 127.0.0.1:3000 }
  ```
  → `caddy validate --config /etc/caddy/Caddyfile` → `systemctl reload caddy` → **443 自动开始监听**(证书由 Caddy 自动向 Let's Encrypt 申请,无需手动配置)
- 证书签发依赖 DNS 生效;域名块配好后 443 监听即就绪,等 DNS 解析过去即可访问 https://域名
- HTTPS 就绪后:**删除 .env 的 `COOKIE_SECURE="false"`** → `pm2 restart tikflow --update-env`(登录 Cookie 全面启用 Secure 属性)
- **域名挑选**:Tik 生态词(tikflow/tikpulse/tiksurge...)基本全被注册,连 .io/.ai/.net 都难;可行方向=换序(flowtik)、造词(tiklly/tikyflow)、小众后缀(.tech/.xyz/.cc/.me)、语义组合(boosttik/tiktide)
- **域名可用性探测**:`nslookup domain | grep Address` 会误判(**解析服务器地址也匹配 Address**,所有域名都显示"已注册")——用 Python `socket.gethostbyname(d)`,`socket.gaierror` = 无 A 记录 = 可注册候选;⚠️无 A 记录≠一定可注册(注册未解析的很多),最终以注册商搜索结果为准,看好立刻注册

## ★前端弹窗 fixed 定位被 backdrop-filter 劫持(2026-08 实测,通用 React/Next 坑)
- **症状**:弹窗(overlay + fixed inset-0)打开后\"卡在页面内容流里\"——不浮层、不居中、遮罩只盖一小块、关不掉的样子(用户原话\"提现框卡进去了\")。实测 overlay rect = 父卡片尺寸(如 943×198)而非视口(1249×1277)
- **根因**:CSS 规范——**祖先元素有 `backdrop-filter`(或 filter/transform/perspective/contain)时,该祖先成为后代 fixed/absolute 元素的 containing block**。本项目 `.tf-glass` 类自带 `backdrop-filter: blur(8px)`,弹窗恰好在 tf-glass 卡片(钱包页 header)内部渲染 → fixed 以卡片为基准
- **判别**(CDP):`[...document.querySelectorAll('*')].filter(e => getComputedStyle(e).position==='fixed')` 逐个看 `getBoundingClientRect()`——rect ≠ 视口尺寸 = containing block 被劫持;再沿 parentElement 链找 `getComputedStyle(ancestor).backdropFilter !== 'none'`
- **修复**:React **`createPortal(<弹窗/>, document.body)`** 渲染到 body 下,彻底脱离卡片链。改完验证:overlay rect 恢复全屏 + `document.querySelector('.tf-glass.max-w-md').getBoundingClientRect()` 居中(centeredX/centeredY 偏差 <5px)
- **检查清单**:页面内所有条件渲染弹窗(bind-dialog / withdraw-dialog / 任何 modal)若有 fixed overlay 且可能挂在带 backdrop-filter 的卡片下,**一律 Portal**——同类隐患一次修完,别等用户挨个报
- 部署时注意:该修复改的是 .tsx 渲染结构,typecheck + 本地 CDP 验证后走常规部署即可

## ★Cookie 有效性验证 = 官方 tokenBeatWeb 协议(2026-08-16 实测,wukong 参考,最终方案)
- **为什么**:CDP 浏览器采集验证(打开页面查 SSR 数据)受 **headless 指纹**影响——TikTok 风控不给自动化浏览器登录态数据 → 页面无数据 → **有效 Cookie 被误判"已失效"**(用户"新抓的 CK 绑定报无效"的另一重要根因,与 Orca 拦截并列)。官方鉴权接口不受渲染影响
- **协议**(wukong `asar_extracted/electron/api/tiktokAPI.ts` tokenBeatWeb 方法,反编译参考):
  ```
  GET https://www.tiktok.com/passport/token/beat/web/?device_platform=web&aid=1459&scene=boot
  头: cookie=<完整cookie> + UA(Chrome Windows) + sec-ch-ua/sec-ch-ua-mobile/sec-ch-ua-platform
      + Origin: same-site + Sec-Fetch-Mode: cors + Sec-Fetch-Site: same-site + Pragma: no-cache
  响应 error_code===0(顶层或 data.error_code,注意个别是字符串 "0")= 登录态有效
  ```
- **无需浏览器渲染、无需签名算法(X-Gnarly)**——纯 HTTP,秒级、精准。本地实测:wukong 真实登录 Cookie + SK5 代理 → ok:true;香港服务器直连接口 200
- 服务器实现:`src/lib/tiktok/token-beat.ts`(手动 CONNECT 隧道 + socks5 走桥 + http 代理带 Proxy-Authorization,node 标准库零依赖)
- **绑定流程改造(bindAccount)**:① 先 tokenBeat 快验证 → 失败 400 明确报错(proxy 失败→"代理连接失败";否则"登录态已失效");② 通过 → CDP 采集 profile+videos **尽力而为**(catch 回退空数据,60s 兜底),**采集失败不再误判 Cookie 无效** → 绑定必成(tokenBeat 是唯一裁决)
- **工具端同步验证(v1.1.6+)**:抓取成功 → 本地 tokenBeat 验证(urllib 走桥,15s 超时)→ False 立即提示"登录态验证未通过,请确认已登录后重试"(不复制);True → "登录态有效,可绑定平台";None(网络失败)→ 复制但提示无法验证
- **★webpack 坑**:token-beat.ts 用 `node:net/tls/https` → next.config externals **必须加 `{ "node:tls": "commonjs node:tls" }`**(net/https 已有),否则生产 build 报 `Build failed because of webpack errors` + `Import trace: node:tls`。引入新 node 内置模块后先本地 `npm run build` 再部署
- **参考 wukong 更多协议**:`D:\渗透\wukong\asar_extracted\electron\api\tiktokAPI.ts`(2976 行)含 iOS tokenBeat(X-Gorgon 签名)、私信/IM protobuf、账号管理全协议——同类需求直接挖这个文件,比逆向 web 端快

## 参考
- `references/tiktok-signature-service-2026-08.md` — **签名服务探索（tiktok-signature + xgnarly.mjs 纯 node X-Gnarly + 外部重放 10201 结论 + IP 一致性原则）**，服务器采集的备选路线记录
- `scripts/proxy_bridge_srv.py` — **服务器端 socks5 认证 → 本地 HTTP CONNECT 代理桥（python 标准库）**，给签名服务/Chrome 用的无认证本地代理
- `references/collection-deep-dive-2026-08.md` — 深度诊断记录：游客/登录态触发差异、CDP getResponseBody 空体坑、App 协议(X-Gorgon)移植验证+App会话限制、tsx interop 坑、手动 CONNECT 隧道
- `references/tiktok-api-probe-2026-08.md` — 实测记录(SSR结构/接口参数/签名验证过程/400与空body的判别)
- `references/nextjs-14-browser-automation.md` — Next.js 14 集成 CDP/puppeteer-core 工程坑(node: 模块对象形式外部化/instrumentation edge 编译/tsx 调试/socks 包 external)
- `references/socks5-auth-bridge.md` — **带认证 SK5 的本地 HTTP CONNECT 桥完整实现(纯标准库)+ 验证方法 + PyInstaller 打包 Windows 交付工具的坑(onefile __file__/GBK emoji)**
- `scripts/抓tk_ck.py` — 用户侧 CDP 抓 Cookie 工具(智能版v3:内置代理+认证桥+自动启动Chrome+MessageBox弹窗);配套 bat 要点见 通道2
- `scripts/start-cdp-browser.cjs` — 服务端 headless 采集浏览器守护(纯 JS,pm2 托管,读 TIKTOK_CDP_BIN/PORT)
- `scripts/repro-bind-flow.js` — **绑定链路复现探针**(服务器上跑:桥+headless+注入CK,判别 profile/recommend/post 三接口;Orca 拦截排查用,2026-08-16 验证)

## 给用户看 dev 预览的技巧
- 用户"搞个dev我看看"时:dev server 起来后,用 `open_preview` 在预览面板打开页面让用户直接看,比截图更直观
- 登录态页面(账号管理页等)预览面板没有登录 cookie → 用 **CDP 注入会话**:`curl` 登录拿 set-cookie → 连 9222 调试 Chrome `Network.setCookie`(domain=localhost) → `Page.navigate` → `Page.captureScreenshot` 存 png → **MEDIA:路径直接发图**(用户能内联看图)
- 当前模型(deepseek)无原生 vision 且辅助视觉模型不支持 image_url → `vision_analyze` 会 400 失败,**不要依赖它验证截图,直接发图让用户看**,再让用户描述问题
