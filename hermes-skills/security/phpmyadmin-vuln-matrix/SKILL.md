---
name: phpmyadmin-vuln-matrix
description: "Use when 打 phpMyAdmin：10 条 SQLi/XSS/鉴权/2FA 面，含 pmadb 中心表注入与 designer JSON 注入。"
---

# phpMyAdmin 漏洞矩阵（10 条，abraxas 2026-10 批次）

## 一句话
`github.com/abraxas` 在 phpMyAdmin 上一次性产出 10 个独立漏洞，每条都有 PoC + README（Class / Reach / 受影响精确版本 / 源码行号）。本卡把它们压成一张矩阵，命中的直接去抓 README 取触发条件。

## 清单
| 仓 | 级别 | 可达 | 类型 | 要点 |
|---|---|---|---|---|
| `phpmyadmin-auth-plugin-unquoted` | High | Remote | SQLi | auth plugin identifier unquoted |
| `phpmyadmin-config-set-2fa` | High | Remote | 2FA | config/set clears two-factor |
| `phpmyadmin-csrf-sql` | High | Remote | CSRF | token strip on /sql |
| `phpmyadmin-designer-json-sqli` | High | Remote | SQLi | Designer JSON unsanitized identifiers |
| `phpmyadmin-importldi` | High | Remote | SQLi | ImportLdi TERMINATED BY leftover |
| `phpmyadmin-issuperuser` | High | Remote | leftover | isSuperUser check skipped |
| `phpmyadmin-pmadb-central-sqli` | High | Remote | SQLi | central columns pmadb query leftover |
| `phpmyadmin-setup-validate` | High | Remote | leftover | setup/validate still reachable |
| `phpmyadmin-vqb-xss` | High | Remote | XSS | Designer Visual Query Builder |
| `phpmyadmin-webauthn` | High | Remote | 2FA skip | WebAuthn ceremony can be skipped |

## 逐条要点（Class/Reach 原文摘录）
### `phpmyadmin-auth-plugin-unquoted`
  - **Class:** SQLi
  - **Reach:** Remote
  - **phpMyAdmin** `5.2.3` (`RELEASE_5_2_3` / `962857e`) - phpMyAdmin
  - **A signed-in phpMyAdmin user injects SQL into their own `ALTER USER` through the change-password form. Extra SQL in the plugin field is SQL, not a plugin name.**
### `phpmyadmin-config-set-2fa`
  - **Class:** Privilege leftover / missing step-up
  - **Reach:** Remote
  - **phpMyAdmin** `5.2.3` (`RELEASE_5_2_3` / `962857e`) - phpMyAdmin
  - **A logged-in session, or XSS/CSRF that can POST the page token, can send `key=2fa` and `value=null`. The next password login has no TOTP, WebAuthn, or Simple prompt. Durable strip, not a one-request 
### `phpmyadmin-csrf-sql`
  - **Class:** CSRF
  - **Reach:** Remote
  - **phpMyAdmin** 5.2.3 (tag `RELEASE_5_2_3`, commit `962857e`). `Common.php` builds the PSR-7 request from globals before `checkTokenRequestParam`. On mismatch, `Sanitize::removeRequestVars` clears `$_P
### `phpmyadmin-designer-json-sqli`
  - **Class:** SQLi
  - **Reach:** Remote
  - **phpMyAdmin** 5.2.3 (tag `RELEASE_5_2_3`, commit `962857e`). Designer AJAX `save_setting_value` `json_encode`s the settings blob and concatenates it into a single-quoted UPDATE/INSERT on the control-
### `phpmyadmin-importldi`
  - **Class:** SQLi
  - **Reach:** Remote
  - **phpMyAdmin** `5.2.3` (`RELEASE_5_2_3` / `962857e`) - phpMyAdmin
  - **A signed-in user POSTs `format=ldi` with a quote in `ldi_terminated`. The issued `LOAD DATA` contains the raw POST inside `TERMINATED BY`. SQL injection into the user connection, not the control use
### `phpmyadmin-issuperuser`
  - **Class:** Privilege leftover
  - **Reach:** Remote
  - **phpMyAdmin** `5.2.3` (`RELEASE_5_2_3` / `962857e`) - phpMyAdmin
  - **A phpMyAdmin policy bypass, not a new MySQL privilege. SELECT on mysql.user plus DROP, and no SUPER, is enough to Drop through PMA.**
### `phpmyadmin-pmadb-central-sqli`
  - **Class:** SQLi
  - **Reach:** Remote
  - **phpMyAdmin** 5.2.3 (tag `RELEASE_5_2_3`, commit `962857e`). Central columns writes `col_extra` by concatenating POST `extra` and `attribute` into a single-quoted SQL literal on the control-user link
### `phpmyadmin-setup-validate`
  - **Class:** SSRF
  - **Reach:** Remote
  - **phpMyAdmin** 5.2.3 (tag `RELEASE_5_2_3`, commit `962857e`). `setup/index.php` dies when `config.inc.php` is present. `setup/validate.php` does not. It still loads under `$isMinimumCommon`, takes a C
### `phpmyadmin-vqb-xss`
  - **Class:** Stored XSS
  - **Reach:** Remote
  - **phpMyAdmin** `5.2.3` (`RELEASE_5_2_3` / `962857e`) - phpMyAdmin
  - **A stored XSS in the phpMyAdmin origin. Same class as PMASA-2025-1, different feature. Check-tables headings were escaped. This path was not.**
### `phpmyadmin-webauthn`
  - **Class:** 2FA bypass
  - **Reach:** Remote
  - **phpMyAdmin** 5.2.3 (tag `RELEASE_5_2_3`). Default tarball. `web-auth/webauthn-lib` is suggest / require-dev. `composer install --no-dev` does not install it. `createServer` therefore uses `CustomSer

## 怎么用
1. **先定版本**：这批洞全部绑定精确小版本（如 `4.2.0` / `3.53.4` / `7.2.20`），版本不对别浪费时间。
2. **取原文**：`curl -sL https://raw.githubusercontent.com/abraxas/<仓名>/main/README.md` —— README 里 `Class` / `Reach` / 受影响版本 / 源码定位四段就够判断能不能打。
3. **按可达性分流**：`Remote` 的先打；`Local`/`Authenticated` 的留到已有 shell 或低权账号之后。
4. **一条一条验**：这批是同产品的平行洞，别把一个的结论套到另一个上（同产品不同入口的前置条件常常不一样）。
