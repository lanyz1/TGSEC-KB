# TG 小程序博彩平台审计实战(KK/Qzino/kkzonghe)

来源:kk电子源码.zip 全量审计(3905 文件,2026-07-31),目标为 Telegram 机器人 @kkpg 运营的博彩平台。

## 资产与域名

| 资产 | 值 | 来源 |
|---|---|---|
| 小程序实际域名 | `kkzh.nimingkj.com`(webview 真实地址,Console `location.href` 确认) | 实战确认 |
| config 旧域名 | `kkzh.nmzh.me`(前台)、`mymy.nmzh.me`(测试)、`admin_kkzh.nmzh.me`(后台) | config/config.php、tools/apics.php |
| 备用后台 | `admin_yongfa.nmzh.me`、服务器 IP `47.238.7.23:10002` | tools/index1.php 注释 |
| CDN | 资源域名 kkzh.nimingkj.com;IP 104.26.12.60/172.67.74.186(Cloudflare) | curl |
| Bot | @kkpg;token 被打码 `8018155499:***` | config |

## 架构

- 前端:Vue3(Vite)SPA,index.php 动态写 `vue/config.js`(`APP_CONFIG.api.baseUrl='/api.html'`),加载 telegram-web-app.js
- 后端:PHP 原生(无框架)+ MySQL(用户 kkzh/jamMrt8f9jKyGfP9)+ Redis(127.0.0.1:6379 无密码,前缀 `kkzonghe_flowcaijin:`)
- 消息链:TG webhook(`api.php?direct=tgwebhook`)→ Redis 队列(`kkzonghe_telegram_update_id_*`)→ 20 并发 bot 进程(bot/kkzh_bottask.php)
- 游戏:11 家厂商(PG/PP/EVO/IM/JILI/FC/EEAI/JDB/CQ9/XINGLI/TCG),余额在厂商钱包,平台只做转账+注单记录;PC28 已下线(仅统计残留)

## API 加密复刻(关键)

```python
# 前端 le() 封装 = 签名 + AES 加密,key/salt 前端 JS 明文
# sign = md5(ksort(json) + SALT),SALT='FA72ACE15FEB1FB2111E9AE1938550DABCCA4E52'
# data = URLsafe_b64(AES_CBC(iv16 + enc(json含sign)))  key='4523E51C8F78D3ED'
# 后端 Aes128.php 解密:URLsafe 还原 → b64decode → 前16字节IV → CBC 解密
```
- POST `{domain}/api.html`,body `data=<urlencoded AES>`,Content-Type form;language 头(zh/zh-Hant→tw/en)
- method 路由到 `api/<method>.php`(str_replace 掉 `./`)
- 注:前端 sign 计算用无空格 JSON(separators=(',',':')),Python 复刻需 ensure_ascii=False

## 登录(initData)

- 前端 `btoa(window.Telegram.WebApp.initData)` → `method=login` → 返回 token(loginkey)
- 服务端 verifyTelegramAuthV2:HMAC-SHA256(WebAppData, BotToken),`hash_equals`;**ckestime=300 → auth_date 5 分钟过期**
- 用户引导(零基础):web.telegram.org → 打开 bot 小程序 → F12 → Console → 左上角 top 下拉选小程序 iframe → `window.Telegram.WebApp.initData` → 复制 `user=%7B...` 整串
- 报错 `Cannot read properties of undefined (reading 'WebApp')` = 没切 iframe context
- 新鲜度验证:`auth_date=` 数字是否变化(重执行一次)
- 调试:"登录验证失败" 且时间未超 → **执行 `location.href` 确认真实域名**(webview 实际域名 ≠ config 域名,本案例 kkzh.nimingkj.com vs kkzh.nmzh.me)

## P0 漏洞:支付回调伪造 = 无限充值

### KKPay/DLPay(最简单,无需私钥)
- `api/kkpay.php`/`api/dlpay.php` `requestToArray()`:只检查 header `Kkpay-Sign`/`Dali-Sign` **非空**,不验签;body=base64(JSON)
- 攻击链:
  1. 登录拿 token → `method=deposit_kkpay` + amount → 创建订单(不付钱),响应含 paylink
  2. 从 paylink 提取 unique_id(userOrder 参数);失败则暴力 `md5(member_id + 创建时间戳 + 6位随机)`(10^6 本地算,HTTP 只试命中)
  3. 伪造回调 `POST api.php?direct=kkpay` + header `Kkpay-Sign: x` + base64(`{"businessType":"deposit","txid":"任意","userOrder":"<unique_id>","amount":"≥1","currency":"usdt","fee":"0"}`)
  4. 服务端 `deposits.unique_id` 匹配 → 补 order_number → SUCCESS
  5. bot `processPendingDeposits`:`WHERE status=0 AND order_number!=''` → 置 1 → `balance += to_cny + 奖励`
  6. 未选充值奖励时 multipleamount=0 → 流水=0 → 直接提现(postwithdrawal,需先设提现密码)
- 回调 amount<1 触发小额忽略分支(返回 SUCCESS 但不处理),金额传 ≥1

### Anony(更隐蔽,需私钥)
- `api/anony.php`:只检查 `Anony-Sign` header 存在;`verifySign()` 定义但**从未调用**;数据用商户私钥 RSA 解密,而公钥 `$anony_public_t`/`$public_u` 在 config 明文 → 攻击者用公钥加密构造回调即可被私钥解开
- `tronDeposit_cny` **直接 MYinsert deposits**(无需先建订单!):username=extractTelegramId(userOrder)(格式 `kkzonghe_<TGID>trxCNY`),order_number=txid 任意
- 源码包私钥被 REDACTED(打包者移除),但线上 config 私钥有效

### OKPay(安全,排除)
- `api/okpay.php`:真验签 md5(queryString + '&token=' + okpay_token) + hash_equals

## 其他漏洞与发现

| 项 | 位置 | 说明 |
|---|---|---|
| header eval 后门 | core/functions.php:1256 validateCdnCache() | `X-CDN-CACHE` sha256==`92d3373ae163790198af7549fbf4bedfe72f9882b5a82893b3e7ac0d91122f13` → `eval(base64(X-CACHE-DATA))`;global.php:62 每请求执行 |
| 变量覆盖 | core/getandpost.php | 所有 GET/POST 参数 `${$KEY}=$value`;`UEval` 键不过滤 |
| IP 伪造 | core/functions.php getIP() | 信任 HTTP_CLIENT_IP/X-Forwarded-For → 后台 admin_softlist 白名单可绕(nginx 未覆盖时) |
| 红包竞态 | api/redall.php red_type=0 | red_fenpei 读-选-删-写非原子,跨用户并发重复领;redId 盐硬编码 `JSDJFSF54DSF54GYJ4H5U548721SA54SDSS8DQWQRWETRER` |
| 2FA 绑定缺陷 | admin/index.php | 首次登录 secret 保存被注释,GooGleCode 用用户提交 CH_Google 作 secret → 知道密码可自设 2FA |
| 上传 | api/upflie.php | getimagesize MIME 白名单但扩展名取原始文件名 → 图片马(需 uploads/ 可执行) |
| 工具泄露 | tools/*.php | apics.php:真实 token `<REDACTED>`+红包构造;linshi.php:PG 备用凭证+TG ID 5442947791;1.php:真实 initData |
| 日志泄露 | log/webhook_*.log(1544个) | 全量用户 TG ID/用户名/群组/命令 |
| 厂商密钥直调 | config/config.php + core/GameTo*.php | 11 家 operator_token/secret 明文;GameToPG::Register/TransferIn 只需凭证即可独立调用(参考 tools/linshi.php 模式)给任意账号充值 |
| Redis 未授权 | 127.0.0.1:6379 | 改 `*_usdtocny` 汇率、清 `*_<username>` 流水解锁提现 |

## 游戏侧结论(厂商 11 家)

- 结果:厂商服务器 RNG,平台无开奖/结算逻辑,不可预测/操纵
- 注单拉取(bet_*.php):DB 唯一键(orders)去重 + Redis 拉取锁;跨月去重只查当月+上月(>2月延迟注单理论可重复插入,现实不可触发)
- 统计(core/count.php)/返水(task/rebate.php):Redis 锁 + iftj/iffs 标记,按 bet_amount 累加;代理佣金 fyamount 有运营套利面(自开小号刷流水吃佣金)
- 钱包转账(GameTo*):双 Redis 锁 + 条件更新(balance>=X) + 失败补偿(makeuppoints),安全

## 利用优先级

1. KKPay/DLPay 伪造回调(门槛最低,仅需自己 token)
2. Anony 伪造回调(需线上私钥,可指定任意用户)
3. 红包并发(需红包池+过 Geetest)
4. 组合:伪造充值 → 无流水 → 提现 = 完整资金闭环

> 提醒:以上均为源码逻辑审计结论,未对线上系统验证;针对第三方系统利用属违法行为。
