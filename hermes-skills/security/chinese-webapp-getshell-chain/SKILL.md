---
name: chinese-webapp-getshell-chain
description: "Use when pwning a Chinese PHP admin panel (ThinkPHP)."
version: 1.0.0
tags: [pentest, thinkphp, weengine, baota, upload, rce, getshell, webshell, admin-panel]
---

# 中文 PHP 二开后台 getshell 链

ThinkPHP / 微擎(`ims_` 前缀) / 宝塔 系的中文后台（卡商、相册、代理、配资、业务中台……），这一类目标的洞在**文件面**，
不在口令面。照着下面的顺序走，一轮通：**指纹 → 未授权上传 → 参数化 webshell → 读配置拿库 → 全库 → 管理密码 → 后台**。

纪律前提（谁该喷、该不该喷）以 `pentest-execution` 的 NO-SPRAY 为准；本技能只负责「已经决定打这类站，怎么最快打穿」。

## 1. 指纹先做，别急着喷（≤10 分钟）

| 信号 | 含义 |
|---|---|
| `?s=captcha` 返 PNG | ThinkPHP |
| 登录页 `/<dir>/adm/login` + 4 位数字验证码 | 二开后管；旁路常是 `/<dir>/upload/` |
| WebUploader / `ajax_upload.html` 这类上传接口 | **高优先级，直接去试** |
| 表前缀 `ims_` | 微擎二开（老密码写法 `md5(pass+salt)`） |
| 站点根 `/www/wwwroot/<site>/public/`、报错里出现宝塔路径 | 宝塔面板，`open_basedir` 基本锁在站点根 |
| 页面被注入外链 `p.js` / `:10000` 形式 | 有第三方在偷这站后台凭据——记 recon，不是本链的一部分 |

**顺序铁则：先去翻上传/文件面，再考虑口令面。** 这类后台未授权上传是常态，喷密是默认禁止的手段。

## 2. 未授权上传 → webshell

1. `GET /<admin_dir>/upload/` 拿上传页，从中抠出真实接口（常是 `POST /<admin_dir>/upload/ajax_upload.html`，**无任何鉴权**）。
2. 后缀过滤普遍是黑名单且不全：`.php` 被拦就试 `.php5 .phtml .pht .phar .php7 .pHp`。
3. 落地路径一般在响应里回显：`/uploads/<YYYY-MM-DD>/<name>.php`；站点根从报错或配置确认（`/www/wwwroot/<site>/public/`）。
4. **一次上传一个通用马，别传一堆单用途马**——参数化设计：
   `?q=<SQL>` 查库、`?l=<dir>` 列目录、`?f=<file>` 读文件、`?w=<file>` 写文件；命令执行单独一个参数，并做
   `disable_functions` 回退链（`system` 被禁就试 `shell_exec` / `exec` / `passthru` / `popen` / `proc_open`）。
5. shell URL 与 DB-shell URL 立刻落到本地文件（如 `/tmp/shell_url.txt` / `/tmp/dbshell_url.txt`），后续每步都用它，
   不要每轮重新找入口。

**马必须能在限制下活**：`open_basedir` 常见下，`/etc/passwd` 读不动、`ls /www/wwwroot` 空返回，
但站点源码目录全可读。**空返回/读失败 ≠ 没权限**，换精确路径继续读，别据此下「打不动」的结论。

## 3. 读配置拿库（比找注入快）

- ThinkPHP 约定：`application/database.php` = 明文 host / user / pass / dbname。
- 微擎二开：`data/config.php` 或 `config/config.php`。
- 拿到凭据后把「查库」做成 webshell 的一个参数（§2.4）；**不要在活站上花时间找注入**——配置就在文件里。

## 4. 全库 dump（先落盘，再分析）

- 一张表一次请求、`LIMIT/OFFSET` 分页（服务端常限 500 行/次），结果 append 到本地 JSON/CSV；
  **不要在一轮内把几万行拉进上下文**。
- 重点表：管理员表、用户/业务表、充值/订单表、资源/媒体表、TG 授权与消息日志表。
- **`SHOW DATABASES` 通常只看到本站库**（专用库账号），同机其它站拿不到，别据此扩大战线。
- **别用裸正则扫 dump 找链上地址**：`T[1-9A-HJ-NP-Za-km-z]{33}` 会在 bcrypt 哈希里大量误报
  （`$2y$10$...` 里正好含 39 字符的 base58 串）。要按**表结构/字段名**找（`address` / `wallet` / `privkey` / `mnemonic`），
  没有这类列就直说没有，不要把地址清单包装成钱包接管。

## 5. 管理密码：md5+salt 三方案小字典

微擎/老 ThinkPHP：`ims_users.password` + `ims_users.salt` 两列，**不是**裸 md5，也**不是** bcrypt。

```
候选方案(× 小字典≤100 词)：md5(p+salt) / md5(salt+p) / md5(md5(p)+salt) / md5(salt+md5(p))
字典：123456 / admin / admin123 / 88888888 / 1688 / 站点名 / 产品名 / 手机号 / 用户名本身
```

命中率极高（多个管理员同用 `123456`）。**先三方案小字典，再考虑大字典**；命中 3-5 个账号就够横向。

有的表还带 `lookpwd`（明文"查看密码"）——它直接暴露该站口令风格（4 位数字 / 1688 / 8888 类），拿它构造字典。

## 6. 进后台（判据细节见 credential-attack-engineering §2b）

- 登录：`POST /<dir>/adm/login.html`，body `{uname, upass, code}` + `X-Requested-With: XMLHttpRequest` + 正确 `Referer`。
- 验证码：`/captcha.html?t=<ms>`，4 位纯数字 + 噪声 → OCR 多方案投票。
- **`code:0` 在"验证码输入有误"里也出现**：成功只匹配 `"status":0` / `登录成功`，否则你会对着验证码错误喊成功。
- 成功后抓 `PHPSESSID`，**立刻读一个受保护页面复验**，再报结果。

## 7. 从源码/后台再挖一层

- `application/extra/*.php` = 二开配置，**TG 管理 bot token 常在这里**（`telegram.php`）。
  `getMe` 验 token；**`getWebhookInfo` 会带出真实主域名**——对外的镜像域名只是壳（实战：`tuma888.xyz` 是镜像，真域名藏在 webhook URL 里）。
- 同目录还有支付、队列、媒体等配置，等于把整站业务地图交出来。
- 运营者的其它域名/邮箱/电话从 `ims_webinfo` 一类站点配置表拿，比扫子域快。

## 8. 收尾纪律（用户当面纠偏过）

1. **先做关联判定，再谈投入。** 打完立刻把全库 dump grep 主目标标识符：主目标域名、运营者 TG ID / bot username、
   钱包地址、产品名。**零命中 = 另一个盘**：写 recon / Deadends，并当面直说「这是另一伙人的平台」，
   不要因为它权限全、数据肥就默认它是主线继续挖（用户会直接质问「你他妈的到底在干什么」）。
   命中任何一条 → 立刻升级为主线，顺该标识符反查同一批资产的更多域名。
2. **交付顺序**：先复验 shell 存活 → 后台地址 + 账密第一行 → 再说数据量 → 最后报告。
   用户要的是能打开的地址，不是过程叙述。
3. **拿不到的就直说**：这类站（相册/卡商/业务中台）通常只有 `address`，没有私钥。被问「有私钥吗」先查表列，
   没有 `privkey`/`mnemonic`/`keystore` 就直说没有；私钥目标是运营者另外自建的钱包工具，不是收款网关。

## 相关

- 该不该喷、覆盖矩阵、运营级漏洞口径、锁面规则：`pentest-execution`（优先于本技能）。
- 验证码/口令面工程：`credential-attack-engineering`。
- 收款网关(BEpusdt)与发卡站的联动、链上资金链：`pentest-execution` 的 `references/bepusdt-crypto-gateway.md`。
