---
name: chinese-thinkphp-jinpan-spa
description: "Use for 合创惠/国强利民 ThinkPHP api.php 金盘 SPA."
version: 1.0.0
tags: [thinkphp, jinpan, uni-app, pear-admin, gfwng, hechuanghui, invite-code, captcha]
---

# 中国 ThinkPHP `/api.php` 金盘 / 产业投资 SPA

uni-app H5 + ThinkPHP `api.php` + Pear Admin 后台。品牌词常见：**合创惠、国强利民、头雁、铸造黄金、风投线**。CDN/DNS 常挂 `*.nicctoday2026.com`，Server 头 **GFWNG**。

**不是** 菲菲计划室（→ `chinese-lottery-ops-spa`），不是博彩代理 BFLA（→ `gambling-platform-pentest`），不是 FastAdmin 记账（→ `fastadmin-platform-pentest`）。

触发：`/api.php/login/user_register`、`parent_code`/`shareCode`、`verification_code` 纯前端、`token` 请求头、`index.php/admin/login` + **二级密码 password2**、`sys_config`、`gm_price`/`xm_price`、`casting`/`pay`。

案例：`zhsjgabhs.top` → `www.ytfg78c54x.top`（2026-10-05）详谱 `references/guoqianglimin-hechuanghui.md`。

## 开局顺序

1. 拉 SPA `index.html` → `static/js/index.*.js` + lazy chunks；抽 `baseURL` / `ajax("/api.php/...")` 全表。
2. `dig` 前端/API/admin/APP 域；记 GFWNG / nicctoday CNAME；裸 IP 常 **530 Domain Unconfigured**——业务流量仍打域名。
3. 先打 **未授权** `sys_config` / 新闻 / 协议，再注册。
4. 后台入口只做指纹 + ≤4 主题词；**禁止长喷**（见下）。

## 会话与注册

| 件 | 说明 |
|----|------|
| Auth | Header `token: <opaque>`（非 JWT） |
| 注册验证码 | **纯前端 canvas**（`Captcha.validate` 本地比对）；无服务端图码接口时 `verification_code` 任意非空/`abcd` 即可；`__token__` 可空串 |
| 登录验证码 | 可能要求**非空**（空/缺省→「验证码不能为空」）；任意非空（`x`/`1234`）常仍过，**不等于**真校验 |
| 邀请码 | 用户 `shareCode` 常无效；试 **`888888`**（及 `131452`/`888666`/`732544` 等同模板码）。**库有 yq_code ≠ 可注册**：`status≠1`（如 `2`）仍回「请输入正确的邀请码」——先 `select id,yq_code,status from … where yq_code=?` 再换根代理码。错码文案 vs 成功注册要分清 |
| 限额 | 同 IP「重复注册IP，联系客服」→ Tor NEWNYM/换出口；**控制口用真 socket**，勿经 SOCKS 连 9051 |
| 登录 oracle | 「账号或密码错误」vs「错误次数太多已被锁定」= 弱存在性；锁定号弱密仍锁，**别当可登** |
| 出口 | 直连 API 常超时/墙；**Tor SOCKS5 `127.0.0.1:9050`** 再打业务面 |

注册体典型：

```http
POST /api.php/login/user_register
mobile=&password=&confirm_password=&parent_code=888888&verification_code=x
→ code=200 + data.token
```

登录：`user_login` 带 `verification_code=x`（非空即可时）。

## 高价值面（按优先级）

### A. 未授权配置 / 调试残留
- `POST /api.php/login/sys_config` → 全量运营配置（域名、奖励、提现文案、弹窗图、APP、客服链）。**常无鉴权**。
- `month_task` 等接口 `data.debug` 回显完整 SQL + 表前缀（如 `cloud_times_api_*`）。**输入未进 SQL = 不是 SQLi**，只报信息泄露。
- `parent_code` 单引号 → ThinkPHP 500「系统发生错误」；生产关 `app_debug` 时无栈/路径，**不要当 RCE**。

### B. 业务逻辑（会员弹药，≠ 接管）
- 注册送虚拟盘：`gm_price` / `xm_price` / `gy_price`——**平台币，非法币/链上**。
- `id_card_save` 常接受任意姓名+身份证 → `status=1`；`edit_pay_password` 可无旧密首设（字段名试 `confirm_password`/`pay_password_confirm`）。
- `POST /api.php/index/pay` `{product_id,amount,__token__}` 可「投入成功」扣 gm；`casting` `{type:1}` 铸造。
- 提现：`withdrawal` 要实名 + `wallet`/`type` + 时段开关；「银行卡提现已关闭」「不在可提现时段」「提交太频繁」。
- **`transfer_out`/`transfer_in` 字段 oracle（重要）**：
  - 缺 **`__token__`**（从 `product_detail`/`account_get` 等取）→ 稳定「参数缺失」
  - 带 `__token__` + 常见收款字段 → 常变「**您的提交太频繁**」（说明已过参数门，进频控）
  - `transfer` 路径本身可能 404；只打 `_out/_in`
  - 前端入口常下线；冷却/换号后再探，**禁止狂喷**；频控≠已转账成功
- 改价 `amount=0/负/小数` → 参数错误；超额 →「今日已参与」— **不要报印钞**。

### C. 未授权上传（常见，≠ shell）
- `POST /api.php/File/upload`（及 `/api.php/file/upload`）常 **无 token 也可**。
- 字段名 `file`/`image`/`img`/`upload`/`files` 多可；**GIF89a 头**可过内容检查并保留 `.php` 后缀。
- 回包 `data.file_path` 如 `/upload/default/YYYYMMDD/<md5>.php`。
- **判定执行**：同 host 与 sibling admin/CDN 拉该 path。典型结果：
  - `.php` → nginx **404**（禁执行/不映射）
  - 含 PHP 的 `.gif`/`.png` → `image/*` **源码回显**，不执行
- 落盘可报「任意文件上传/存储型」；**未看到 `SHELL_OK`/phpinfo/uname 执行输出前，shell/rec=false**。
- `test.php` 等残留可能泄露兄弟域硬编码 token——域名常已死，先探活再跟。

### D. Pear Admin（超管门）
- 入口：`/index.php/admin/login` 或 sibling `/index.php/login/index`（同套后端时 sys_config 同源）。
- 字段：`username` + `password` + **`password2`（二级密码）**；页面里 captcha 常是死代码（`#codeimg` 可能不存在），AJAX **无 url**（POST 当前路径）。
- **password2 文案差分**（结构探测，不是长喷许可证）：
  - 空/缺省 →「二级密码**不存在**」
  - 非空错误 →「二级密码**验证不通过**」
  - 一阶错密 + 空 password2 也可能「不存在」→ **不要**把「不存在」当成 admin/admin 已通的强预言机
- 主题弱口令 ≤4 次；有界品牌词表可短试一轮后**停**。验证码预言机 ≠ 开喷许可证。
- `/static/admin/data/user.json|menu.json|table.json` = **Pear 演示静态数据**（bcrypt 常解成 `admin`）→ **不是**真后台账号/菜单；勿据此报超管已破。
- 成功跳转 `/admin` 或 `/index.php`；会员 token **不能**当后台会话。

### E. ThinkPHP RCE / 装机链 / www→root（2026-10-05 国强利民闭环）
- 经典 `invokefunction` / phpunit / 模板写马：`api.php?s=...` 常 500 无栈、301 登录、或 nginx 404。版本未确认前不要把 500 当 RCE。
- **Pear-Admin-Think / 可重装面**：`app/install` + `database.tpl` 写 `config/database.php`。
  - **username 注入必须语法合法**（坏数组 → `@file_put_contents` 失败仍可能「安装成功」）。
  - 成功文案 **≠** 执行：die 金丝雀 / OOB / 标记文件 + **纯 HTTP** 复验。
  - 源站：`https://ORIGIN_IP/` + `Host: www.…`；CDN 与源站代码可分叉（password2/路由不同）。
- **www 已写马但 disable_functions 全禁**：查 `/tmp/php-cgi-*.sock`。宝塔常见 **0666** → FastCGI 设 `PHP_ADMIN_VALUE=sendmail_path=/path/cmd.sh`（**必须是脚本文件**，禁止 `bash -c '…'`）再 `mail()` → www RCE。详见 `references/php-fpm-fcgi-sendmail-rce.md`。
- **CentOS7 + polkit-0.112**：有 gcc 后严格 **berdav CVE-2021-4034**（`pwnkit.so:.` + `cp true GCONV_PATH=./pwnkit.so:.`）。自创 gconv/`SHELL=/bin/bash` 常失败。见 `references/pwnkit-berdav-centos7.md`。
- **root 判定**：`euid=0` + 读 `/etc/shadow` 或 `/www/server/panel/default.pl`。仅业务超管/读库 **≠** root（`rec/root` 口径）。
- **宝塔 loot（root 后）**：`default.pl`、`admin_path.pl`、`port.pl`、`a_pass.pl`、`data/db/database.db`（`BT-0x:` + `PluginLoader.db_decrypt`）。port 在听但 curl 404 ≠ 无面板。
- **`default.pl` 字面星号**：内容可以是 8 个字符 `********`（真口令），**不是**摘要打码；用户问「密码是什么」就原样给，勿当成 redaction。`users` 表 md5(admin) 可能过期，**以 default.pl 为准**。

### F. 跨用户 / 「所有用户数据」
- 双号对照：`fund_detail_list` / `account_list` / `subscribe_list` / `id_card_get` / `personal_center` 按 token 过滤 → **不报 IDOR**。
- `team_distribution`：仅**本线下线**完整 mobile（自建树可验证）；**不是**全站用户表。
- ranking 脱敏手机；本号 subscribe 含自己 id_card ≠ 他人 PII。
- 用户要「所有用户数据」时的稳路径只认：**(1) admin 会话导出 (2) 真 RCE/读库 (3) 可达 DB 会话**。会员面抠列表/邀码树/锁定 oracle **不等于**全量 dump——当面直说 **false**。

## 报告口径（CRITICAL）

当面「能不能搞 / 有漏洞吗」只认：
1. **他人用户数据**（跨用户真吐）
2. **接管**（admin 会话 / RCE / rec shell）
3. **资金**（真金回调伪造、跨用户转账、可提现印钞）

可报运营级但非接管：无限开会员（验证码+默认邀码）、sys_config、SQL debug 回显、假实名。

**不要**把虚拟盘买入/签到/铸造写成「资金打穿」；**不要**把二级密码挡写成「还能再喷」；admin/shell/root/rec 未拿就直说 **false**。

## 坑

- SPA fallback：任意 path 200 HTML ≠ 真路由；看 `Content-Type` + 体积。
- `transfer` 404、`transfer_out` 缺 `__token__`→「参数缺失」、带 token→「太频繁」→ 冷却/换号挖字段，**不要**改喷后台。
- 上传 `.php` 成功 ≠ shell；必须拉 path 看是否执行。
- Pear `static/admin/data/*.json` 演示数据 ≠ 真 admin。
- 源站 3306/3389 nmap open + greeting/会话超时 = 暴露面，**不长喷 MySQL**。
- IP 注册限额后换码仍「重复注册IP」→ 换出口（Tor NEWNYM 用真 socket 打 9051）。
- 用户邀码无效时先试 `888888` 等同模板码；若库里该 yq_code 存在但 `status≠1`，换有效代理码，**不要**死磕 URL 上的 shareCode。
- 「要所有用户数据」：会员面 IDOR/team/ranking 走完仍 false 时，停循环同法变体，汇报缺口 + admin/RCE/DB 路径。
- 装机「成功」但无 shell：查 `database.php` 语法/写路径；CDN vs 源站分叉时只信源站直连复验。
- password2 常硬编码在 `app/common/service/AdminAdmin.php`（源站与兄弟字符串可不同）。
- `rec/root`：必须 euid=0 证据；www RCE+读库仍 **root=false** 直到提权闭环。

## 相关

- 案例：`references/guoqianglimin-hechuanghui.md`（含 2026-10-05 root 闭环）
- FCGI/PwnKit：`references/php-fpm-fcgi-sendmail-rce.md` · `references/pwnkit-berdav-centos7.md`
- 执行纪律：`pentest-execution`（user-owned，需 `hermes curator adopt` 才能由 curator 改）
- 计划室 PHP SPA：`chinese-lottery-ops-spa`
- CDN/源站：`cdn-origin-tracing`
