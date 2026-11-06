# spa-frontend-recon 全文 第 2/2 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

## Pitfalls

- **生产环境 key 可能是截断占位符**:SSR/JS 里统一出现 `eyJhbG...v0IQ` 类截断 JWT/anon key 时,是**服务端故意截断**(平台注册/登录功能实际损坏或走后端代理),不是遗漏 — 别花时间拼完整 key,直接转 API 层测试。roiify.net 案例:anon key 全站截断,`/auth/v1`、`/rest/v1` 反代暴露但缺 key 不可用。
- **gzip 无头响应(后端管理 API)**: 部分后端(尤其 Java/PHP 管理后台)接口返回 gzip 压缩体但**无 Content-Encoding 头** — urllib/curl 拿到 `\x1f\x8b` 乱码,JSON 解析必失败。必须手动检测 `raw[:2] == b'\x1f\x8b'` 再 `gzip.decompress`。wukong 管理后台 tk_wu.sswhgame.com 的 `/api/account/accountList` 实测命中(响应 337KB 全 gzip)。
- **无头浏览器常被 SPA 反自动化跳 about:blank** → 改用 curl + 静态 JS 分析,别在浏览器上耗时间
- **前端 bundle 里搜不到 WAF/令牌/挑战字样,不能推出「WAF 按 IP 信誉/地域放行」**:挑战处理脚本是 WAF **运行时注入**的,
  静态源码天然没有它 ⇒ 这条线索零判定力。别据此设计换出口实验(实测 DC 节点 + 真 ISP 住宅出口全被挑战,白烧两轮)。
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

