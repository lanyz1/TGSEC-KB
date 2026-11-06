---
name: infra-daemon-vuln-matrix
description: "Use when 打 FTP/GitLab/Prometheus/Grafana/n8n/OpenLiteSpeed/Tomcat/Kafka/PG 等基础服务：40 条 SSRF、未授权、ACL 绕过、写文件。"
---

# 基础设施守护进程 漏洞矩阵（39 条，abraxas 2026-10 批次）

## 一句话
同一批来源（`github.com/abraxas`，2026-10-23 后推送）里的 39 个独立漏洞，按产品聚成一张矩阵。每条都有 PoC + README（Class / Reach / 精确版本 / 源码定位）。

## 清单
| 仓 | 级别 | 可达 | 类型 | 要点 |
|---|---|---|---|---|
| `Pwnbox` | - | - | - | Privacy focused NixOS pentesting environment with a customizable desktop and security tools. |
| `bitwarden-cipher-create-acl` | High | IDOR | plant decryptable vault items into collections the caller cannot write |  |
| `element-fragment-guest` | High | Remote | Session | fragment guest creds wipe a real session before whoami |
| `element-ics-javascript` | High | Remote | XSS | Univention ICS navigation.json link becomes a javascript: menu href |
| `element-vector-drive-letter` | High | Local | File | vector: protocol reads Windows files outside the asar jail |
| `gitlab-gitaly-fetch-ssrf` | - | - | - | GitLab - High - Gitaly fetch omits resolved_address |
| `gitlab-gitea-import-ssrf` | High | Gitea HTTPS import SSRF | UrlBlocker pin drop |  |
| `gitlab-webhook-0net-ssrf` | - | - | - | GitLab - High - webhook 0.0.0.0/8 SSRF |
| `grafana-gitsync-dns-rebind` | High | Remote | SSRF | Git Sync URLValidator is admission-only DNS |
| `grafana-signup-invite-join` | High | Remote | Invite join | SignUpStep2 joins pending org invites without the code |
| `hashcat` | - | - | - | World's fastest and most advanced password recovery utility |
| `hyperswitch-payout-confirm-secret` | Hyperswitch | High 7.5 | Unauthenticated POST /payouts/{payout_id}/confirm | Unauthorized payout amount raise |
| `hyperswitch-unsigned-webhook` | Hyperswitch | High 7.5 | Unauthenticated POST /webhooks/{merchant_id}/worldpayxml | Payment bypass (unsigned connector webhook) |
| `kafka-connect-filestream-win` | High | Windows FileStream classpath leftover | unauth file read/write |  |
| `lago-invite-ato` | Lago | Critical 9.6 | Authenticated POST /graphql | Cross-organization account takeover |
| `lago-stripe-invoice-idor` | Lago v1.53.0 | Stripe one-time webhook Invoice.find_by unscoped | Cross-org payment bypass |  |
| `lighttpd-win32-dotdot-space` | High | Remote | Path | native Win32 GET /..%20/ reads outside document-root |
| `n8n-databricks-path-join` | n8n | High 8.6 | Unauthenticated POST /webhook/dbx-space | Credential leak on Databricks tenant |
| `n8n-function-vm2` | n8n | High 8.8 | Authenticated POST /rest/workflows | Host RCE (Hidden Function vm2) |
| `openlitespeed-dup-cookie-litespeed-role` | High | Remote | Privilege leftover | HTTP/1 duplicate Cookie skips litespeed_role 403; lsphp still gets HTTP_COOKIE |
| `openlitespeed-h3-mtls-verifycontext` | High | Remote | mTLS skip | HTTP/3 skips Host-vs-SNI bind |
| `php-oom-longjmp` | Critical | Remote | OOM longjmp | CVE-2026-109618 PHP2Shell. Unauth chunked multipart hits memory_limit before app code on Apache mod_php. Lab v |
| `php-stale-global-uaf` | Critical | Remote | UAF | CVE-2026-109619 PHP2Shell. Same-worker fatal backtrace then INI diagnostic on Apache mod_php. Lab vs 8.5.12. A |
| `postgres-basebackup-symlink` | High | Remote | File write | pg_basebackup follows absolute tar symlink leftover of CVE-2026-6475 |
| `proftpd-rewrite-utf8trans` | High | Remote | Crash | RewriteMap int:utf8trans BSS overflow |
| `proftpd-sftp-copy-file-write` | High | Remote | Privilege leftover / File write | SFTP copy-file skips dest WRITE |
| `proftpd-site-copy-dest-follow` | High | Remote | Privilege leftover / File write | SITE COPY dest follows symlink |
| `prometheus-bearer-redirect` | High | Remote | Credential leak | remote_write google_iam/azuread forwards Bearer on cross-host 3xx |
| `prometheus-unix-socket-dial` | High | Remote | SSRF | http_sd __unix_socket__ unsanitized Dial leftover of UDS scrape |
| `signal-server-dropwizard-admin` | High | Remote | Privilege leftover | unauth Dropwizard admin :8081 |
| `sonic-gnmi-noauth` | SONiC gNMI f13a08e | empty UserAuth fail-open | unauthenticated gNMI Set / gNOI write |  |
| `tomcat-rewrite-ns-loop` | High | Remote | DoS | RewriteValve [NS] worker pin |
| `uptime-kuma-setup-toctou` | Uptime Kuma | High 7.4 | Unauthenticated SOCKET.IO setup | Account takeover (hidden second admin, then disableAuth) |
| `vaultwarden-ip-header-spoof` | - | - | - | Vaultwarden 1.37.3 default X-Real-IP trusted-local bypasses login rate limits on Docker NAT |
| `veneficus` | - | - | - | Super elite end-to-end implant 0day. Full kill-chain. Exploit, escalate, pivot, poison, persistence. |
| `veneficus-implant-public` | - | - | - | Spicy malware 0day. Full kill-chain malware: exploit, pivot, c2, persistence. Rust converted to pseudo-code -  |
| `vsftpd-cmds-denied-alias` | High | Remote | Privilege leftover | cmds_denied misses RFC aliases (XRMD) |
| `vsftpd-deny-file-brace-child` | High | Remote | Privilege leftover | brace deny_file misses .private/secret |
| `vsftpd-ssl-data-any-ticket` | High | Remote | Privilege leftover | FTPS data accepts any resumed ticket |

## 逐条要点（原文摘录）
### `element-fragment-guest`
  - **Class:** Session destruction
  - **Reach:** Remote
### `element-ics-javascript`
  - **Class:** XSS
  - **Reach:** Remote
### `element-vector-drive-letter`
  - **Class:** File read
  - **Reach:** Local
### `grafana-gitsync-dns-rebind`
  - **Class:** SSRF
  - **Reach:** Remote
### `grafana-signup-invite-join`
  - **Class:** Privilege leftover
  - **Reach:** Remote
### `kafka-connect-filestream-win`
  - **Class:** File write / unauth file read-write (Windows CLASSPATH leftover)
  - **Reach:** Remote
### `lighttpd-win32-dotdot-space`
  - **Class:** File read
  - **Reach:** Remote
### `openlitespeed-dup-cookie-litespeed-role`
  - **Class:** Privilege leftover
  - **Reach:** Remote
### `openlitespeed-h3-mtls-verifycontext`
  - **Class:** Privilege leftover
  - **Reach:** Remote
### `php-oom-longjmp`
  - **Class:** OOM longjmp / request-startup abort
  - **Reach:** Remote
### `php-stale-global-uaf`
  - **Class:** UAF / Crash
  - **Reach:** Remote
### `postgres-basebackup-symlink`
  - **Class:** File write
  - **Reach:** Remote
### `proftpd-rewrite-utf8trans`
  - **Class:** Crash
  - **Reach:** Remote
### `proftpd-sftp-copy-file-write`
  - **Class:** Privilege leftover / File write
  - **Reach:** Remote
### `proftpd-site-copy-dest-follow`
  - **Class:** Privilege leftover / File write
  - **Reach:** Remote
### `prometheus-bearer-redirect`
  - **Class:** Credential leak
  - **Reach:** Remote
### `prometheus-unix-socket-dial`
  - **Class:** SSRF
  - **Reach:** Remote
### `signal-server-dropwizard-admin`
  - **Class:** Privilege leftover
  - **Reach:** Remote
### `tomcat-rewrite-ns-loop`
  - **Class:** DoS
  - **Reach:** Remote
### `vsftpd-cmds-denied-alias`
  - **Class:** Privilege leftover
  - **Reach:** Remote
### `vsftpd-deny-file-brace-child`
  - **Class:** Privilege leftover
  - **Reach:** Remote
### `vsftpd-ssl-data-any-ticket`
  - **Class:** Privilege leftover
  - **Reach:** Remote

## 怎么用
1. 先确认组件与版本（这批洞多数绑定精确小版本）。
2. 取原文：`curl -sL https://raw.githubusercontent.com/abraxas/<仓名>/main/README.md`。
3. `Remote` 先打，`Local`/`Authenticated` 留到有 shell 或低权账号之后。
4. 与既有专门卡（`gitlab-*`、`prometheus`/`monitoring-plane-unauth-recon`、`grafana`、`ftp` 相关）重叠时以专门卡流程为主，本卡补 2026-10 新洞。
