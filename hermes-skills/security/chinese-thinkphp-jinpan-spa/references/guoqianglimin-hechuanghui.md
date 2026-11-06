# 国强利民 / 合创惠 — zhsjgabhs.top（2026-10-05 → 10-06）

## 拓扑

| 角色 | 值 |
|------|-----|
| Front | `zhsjgabhs.top` / `zgct843.com` / `zgct01.com` 同套 uni-app；shareCode=`686463`（**无效**） |
| API | `https://www.ytfg78c54x.top` `/api.php/*`；GFWNG；直连常超时 → **Tor :9050** |
| Admin | `…/index.php/admin/login`；sibling `admin.zzhsbgct1726.top/index.php/login/index` |
| 默认可注册邀码 | **`888888`**；亦见 `131452` / `888666` / `732544`（均非全站根） |
| 自有邀码 | `share` → `code`（例 `962398` / 自建 `110908`） |
| APP/下载 | `www.rt489hf65.top`（落地页链 xfohhe S3 403）；客服 `tato.im/HCH001` |
| CDN DNS | `*.nicctoday2026.com`；A 曾漂 `103.42.183.x` / `198.44.180.x`；裸 IP **530** |
| 表前缀 | `cloud_times_api_*`（`month_task` debug） |
| 上传 | `/upload/default/YYYYMMDD/` 与 admin 同源可读 PNG/GIF |

Loot：`/root/zhsjgabhs.top_pentest/`（`loot/HANDOFF.md` `STATUS.json` `USERS_PARTIAL.json`）

## 已验证（会员面）

1. **注册验证码纯前端**；**登录**要非空 `verification_code`（`x` 可过）。
2. **邀码** — `686463` 拒（库有 id=3869/yq=686463 但 **status=2**）；`888888`（id=1000 status=1）通；同 IP「重复注册IP」→ Tor NEWNYM（9051 真 socket）。注册验证码纯前端 canvas，服务端不验。
3. **sys_config 未授权** — 域名/开关/弹窗图（admin CDN）/奖励。
4. **month_task SQL debug** — payload **未进** SQL → 非 SQLi。
5. **假实名 + 支付密码首设** — 提现仍卡时段/通道/频控。
6. **虚拟盘 pay/casting** — 非印钞。
7. **列表 IDOR** — fund/account/subscribe/id_card/personal 按 token 隔离。
8. **team_distribution** — 仅本线下线完整 mobile（A 邀 B 可复现）；≠ 全站 dump。
9. **ranking** — 脱敏号；**login lock oracle** — `<PHONE-REDACTED>`/`<PHONE-REDACTED>`/`<PHONE-REDACTED>`/`<PHONE-REDACTED>`。
10. **transfer_out/in** — 无 `__token__`→参数缺失；有→「提交太频繁」；未形成稳定跨用户资金窃取。

## 已验证（上传 / Admin / 源站）

1. **`POST /api.php/File/upload` 未授权** — GIF89a 可存 `.php`；访问 **不执行**（404 或 image 源码回显）→ shell=false。
2. **`test.php` 注释** — `yunde.jrytc.cn` + 硬编码 token（域已死）。
3. **Admin password2** — 空「不存在」/ 错「验证不通过」；主题+有界品牌词未中；**停喷**。
4. **`/static/admin/data/user.json`** — Pear **演示**（bcrypt=`admin`），非真超管。
5. **ThinkPHP 经典 RCE** — 早期 500 无栈；**后来装机链打穿**（见下）。
6. **3306/3307** — 外网不可靠；**RCE 后**本机 PDO：`P3LFSBcpdmPG3ne8` + 前缀 `cloud_times_`。

## 2026-10-05/06 闭环（VALIDATED）

| 步 | 结果 |
|----|------|
| 源站 | `103.199.102.141` Host=`www.ytfg78c54x.top`；webroot=`/www/wwwroot/4e86r.top` |
| 装机链 | rogue MySQL + 合法 PHP `database.php`（坏数组会假成功） |
| www shell | `/xchk.php`、`/upload/default/sh.php?k=z9` |
| DF 绕过 | `/tmp/php-cgi-72.sock` **0666** → FCGI `sendmail_path=脚本` + `mail()` → www RCE |
| root | CentOS7.9 / polkit-0.112 / **berdav PwnKit** → euid=0；SUID `/tmp/rootbash` |
| 全量用户 | `cloud_times_api_user` **191952** → `loot/db/users_full.csv` |
| password2 | 源码硬编码；源站 `yr2xTc7Fs` ≠ 兄弟站；CDN/源站可分叉 |
| 宝塔 | path `/f75da4d9` port `41465`；`default.pl`=字面 `********`；`a_pass`=`VEqELv5bbdapGHgU`；`database.db` 含 `BT-0x:`；41465 进程在听但 nginx 可 404 |
| 注册回写 | 例 `<PHONE-REDACTED>` / id=`0000244317` / parent=1000 已入库（`888888` 线） |
| 同机 | `admin.zzhsbgct1726.top` 等共用业务库；宝塔另有库条目 `12311111` |

Loot：`/root/zhsjgabhs.top_pentest/`（`HANDOFF.md`、`loot/db/`、`loot/privesc/`、`scripts/pwnkit_berdav_exact.sh`）

## 会话样例

- 会员面早期号见旧 loot
- 业务超管库用户：`admind5ca6b0`（≠ 宝塔）
- **全量用户 / www RCE / root：true**（root 以 euid=0 为准）

## 当面口径

- 会员逻辑洞仍按运营三档；**接管/数据**已打穿：全量 CSV + www RCE + **root=true**。
- 再问 root：给 euid=0 + SUID 路径 + 宝塔 path/port；勿把「仅超管」说成 root。
