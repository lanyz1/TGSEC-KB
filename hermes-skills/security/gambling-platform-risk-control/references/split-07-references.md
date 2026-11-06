## References

- `references/gambling-rtp-knowledge.md` — 会话沉淀:API 传参动态 RTP + 配置界面解读
- `references/ph-gambling-frontend-recon.md` — 菲律宾博彩站(m9600/MM99)前端 recon:厂商 type ID 映射、镜像域名矩阵、HMAC 签名逆向、Nuxt 配置提取
- `references/m9600-leaderboard-and-rest-signature.md` — m9600 实战配方:排行榜接口批量泄露完整账号+投注额(2500条/1454手机号)、REST HMAC 签名复刻(signedPost+密钥提取+signerror验证)、白标管理端侦察结论(SPA fallback 识别/服务商侧不暴露)
- `references/m9600-userdata-credential-stuffing.md` — m9600 撞库+身份提取实战配方:排行榜账号撞库(命中率0.55%)、GetWithdrawHistoryAccount(1224)拿真实姓名+GCash钱包号、GetMobiles(1278)支付手机号、归属校验规律表、断点续跑+Python包装器工程要点
- `references/m9600-customer-service-api.md` — 客服系统独立 API 攻破配方:customer_info 泄露客服链接(hash token)、apic 服务器 + merchant-id/cid 鉴权、/customer-service/v1/customer/{history,config,m,send2} 客户 API、/service 401 客服工作台、cid 不可枚举、CF bot 检测用页面内 fetch 绕过
- `references/m9600-money-fund-interfaces.md` — 资金接口测试配方(⚠️ 重要修正:资金接口通过 CF 全超时但**直连源站后可用**,提现三层校验 1904金额/127余额/2001限速、抽奖每日限次1500、CMD_MB_PlaceOrder price(int64) 可控、批量扫描工程坑(LOGON_EXIT 登出/完整 LOGON 解码模板/响应 scmd=请求+1/超时兜底/断连重连/限流冷却)、"无高价值漏洞"诚实结论)
- `references/m9600-getmobiles-global-lib.md` — GetMobiles(1278) 全局手机号库批量提取配方:任意账号拉45随机巴西号、批量注册(checkCode=123456)+6并发=9248手机号、数据层级澄清(注册256万≠绑定手机1.2万≠排行榜1454)、客户分层交付(高净值标注投注额)
- `references/rtg-lobbycore-pentest.md` — RTG(LobbyCore)白标赌场渗透:CDK.logIn 绕过 ProduceSessionID、登录后数据接口清单、注册 BFF 字段枚举、优惠券代码枚举链、收银台 Router.ashx
- `references/cloudflare-origin-discovery.md` — CF 源站发现 13 项技术矩阵(批量解析/子域爆破/证书/历史DNS/AXFR/SPF/whois/Wayback/FOFA/nginx指纹/多DNS源/第三方资产)与 m9600 全失败结果、CF 段速查表、证书签发方陷阱、"无 shell 结论逻辑"
- `references/gambit-mgs-pentest.md` — Gambit(Microgaming/gameassists)平台完整渗透:deviceinfo JSON、appSettings 泄露、BFF Gateway 无鉴权(checkUserExists 枚举/mfa IDOR)、UCP 客户端库逆向链、login/real + demo login 突破、429 按账号绕过、JWT 泄露、VeyronProxy、swift embedded 路径绕过 CF + valueactive 后端 + money-in 支付方式、充提方式情报调查(FAQ/thirdPartyBanking 判断)
- `references/maktub-engine-and-webhook-pentest.md` — Maktub B2B 游戏提供商渗透(crypto-games.io 实战):自研引擎 REST+WS 协议(游戏启动 slug 格式/下注 schema 校验链/ws/ticket 30秒/实时 crash 消息)、webhook 签名机制(HMAC t.v1 + legacy x-webhook-secret 明文 fallback + payload actions win 贷记)、管理后台(admin.maktub.bet 葡语 + admin:admin 密码对但 TOTP 挡 / backoffice email 字段差异 / CVE-2025-29927 已失效)、docs.maktub.bet 文档 + npm SDK 源码泄露面
- `references/maktub-crypto-games-pentest.md` — crypto-games.io 完整渗透面(与 maktub-engine-and-webhook-pentest.md 重叠,本文件侧重:架构拓扑/子域地图/api.crypto-games.io 注册登录/用户 API 族/**密码重置链(用户枚举+注册密码失效+verificationCode 接管)**/工具技巧(CF 内容保护绕过/console 正则问题/Zod schema 泄露/Spring 路由枚举)
- `scripts/usdt_payment_scan.py` — 批量扫描赌场站点 USDT/加密支付支持(主页+JS+支付路径并行,关键词字典 + 上下文二次验证 + 支付 logo 图片最强证据)

