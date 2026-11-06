# PHP 博彩/会员系统源码审计方法论（拿到整套源码包后）

场景：拿到完整 PHP 源码包（zip/压缩包，常见于 Telegram 群/频道打包分享、服务器打包流出，常附"后门自行排查"说明）。这类源码通常无框架、配置明文、可能存在打包者植入的后门。按以下顺序静态审计。

## 一、后门猎杀（最高优先级）

1. **全局加载点的 header-eval 后门**：找所有入口都会 require 的 `global.php` / `init.php`，逐个函数看有没有 `@eval(base64_decode($_SERVER["HTTP_XXX"]))`。特征：一个请求头做 hash 校验（如 `hash("sha256",$_SERVER["HTTP_X_CDN_CACHE"])=="固定值"`），另一个头带 base64 代码。校验头原值可用字典/短串暴力尝试（先常见值，再 1-4 位字符集爆破）。
2. **混淆函数先验调用点**：`_kv_dec` 类（`chr(ord($s[$i])-1)` + base64）不一定是后门——公告标题/轮播图内容可能用它做"防直接读"编码。先 grep 调用点确认用途再定性，避免误报。
3. **配置表的异常行**：`admin_setting` 类表里 setname/setval 出现随机字符串（非业务 key），可能是植入标记或后门配置。
4. **危险函数全库扫描**：`eval( assert( base64_decode(超长串) shell_exec system( passthru( proc_open create_function` 先粗扫，`curl_exec` 正常业务不要误报。

## 二、高危模式速查表

| 模式 | 代码特征 | 危害与利用 |
|---|---|---|
| register_globals 模拟 | `foreach($_GET as $K=>$v){$$K=$v;}`（常带一个豁免参数名） | 覆盖 `$DB`/`$AdminMember`/`$BotToken` 等全局变量 → 越权/逻辑绕过 |
| IP 白名单绕过 | getIP() 优先读 `HTTP_CLIENT_IP`/`HTTP_X_FORWARDED_FOR` | `X-Forwarded-For: <白名单IP>` 绕过后台 IP 白名单（nginx 未覆盖时） |
| 2FA 绑定缺陷 | 首次登录生成 secret 但 `MYupdate` 被注释；数据库 Google 字段为空时用用户提交值做验证 | 知道密码即可自设 2FA secret 完成登录 |
| 上传扩展名伪造 | getimagesize 校验 MIME 白名单，但扩展名取原始文件名 `pathinfo($name)` | 合法图片头 + PHP 尾 + `.php` 名 → 图片马（需 uploads/ 可执行） |
| webhook/请求日志泄露 | `log/webhook_*.log` 存原始 TG update JSON | 用户 TG ID、用户名、群组、bot 命令枚举 → 代理链挖掘 |
| 拼接 SQL | 封装层参数化（PDO prepare+字段白名单）但 `querys($SQL)` 直接执行 | 逐个验证调用点；多数拼 DB 值/intval/floatval 时安全 |

## 三、后台防御链常见组合（绕过顺序）

Host 域名校验 → IP 白名单表 → cookie loginkey → Google 2FA。
先试 `X-Forwarded-For`，再试全局变量覆盖，再试 2FA 绑定缺陷，最后考虑 header-eval 后门。

## 四、附加价值点

- 源码里全明文的支付密钥、游戏厂商 API 凭证（PG/PP/JILI/JDB/CQ9 等）可外溢利用——厂商侧余额/接口即是攻击面
- TG Bot token + webhook secret（`md5(BotToken+SecretTokens)`）可接管机器人
- 数据库密码明文 + SQL 结构文件 → 可部署本地副本实测漏洞（不碰线上）
- 日志文件（webhook_*.log 等）里的真实运营数据是用户/代理链枚举金矿

## 五、实战案例

KK 综合平台（kkzonghe，Telegram 博彩聚合平台）完整审计见 `references/kk-telegram-gambling-source-audit.md`：
- 全局 RCE 后门 `validateCdnCache()`（X-CDN-CACHE SHA256 校验 + X-CACHE-DATA base64 eval）
- 全量明文凭证（DB/支付/11 家游戏厂商/API AES key/签名盐）
- 60+ 表结构、攻击路径顺序
