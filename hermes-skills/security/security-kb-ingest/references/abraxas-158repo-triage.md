# abraxas 158 仓 triage（2026-10-12，五源批次 · ✅ 已收口）

> **状态**：已全量执行 —— 145 包入库 + AnyDesk AnyPwn + 工具/方法论提炼；**署名/来源全批清理归零**。账本 `domains/0day-exploits/INGEST-20261012-INDEX.md` · 更新 `docs/updates/UPDATE-2026-10-12.md`。本文件保留作对账底稿（注意：实际导入 phpMyAdmin×10、CakePHP×9，以此处列表为准的个别计数以账本为准）。

来源: https://github.com/abraxas （abraxaslabs.tech · @abraxas_null）
格式: 每仓 = 1 漏洞完整包 — README（CWE/CVSS 向量/commit pin/受影响版本/How-I-found/Wrong turns）+ lab/ 一键复现 + PoC .py + header.png。绝大多数 "no CVE yet"（作者自报）。抓法: raw.githubusercontent 免配额 + `users/abraxas/repos?per_page=100&sort=updated&page=1..2`（共 158 条）。
本地库: /root/TGSEC-Qtzuu/domains/0day-exploits/ 。对账方法与坑见 SKILL.md「HIT check / 对账 pitfalls」。

## SKIP — 已覆盖（对账确认）
- CVE-2026-5430 WSO2 → `jwt/CVE-2026-5430`
- CVE-2026-19089 WooCommerce Tych / CVE-2026-61628 nginx-ignition → 已收
- CVE-2026-75650 Magento（lab 全套 Dockerfile/exploit.py 在 `magento/`）/ CVE-2026-87902 WP Core → 已收
- CVE-2026-12793 JetFormBuilder → 仅 sploitus-index 弱命中，复核后定夺

## 差量补充 — 产品目录在但包不对（复核去重后补）
- proftpd: 本地只收 CVE-2026-24061；1.3.9d 新 3 包（site-copy / sftp-copy-file / rewrite-utf8trans BSS）
- gitea: 本地只收 act-runner-container-options；9 仓去重（user-keys-idor / stargazers-hidden / restore-file-open / public-only-pat-org / hostmatcher-0000-ssrf / git-redir-ssrf / follow-existence / artifact-v4-readall）
- gitlab: 3 仓复核（webhook-0net-ssrf / gitea-import-ssrf / gitaly-fetch）
- nextcloud: 4 仓复核（webhook-tokenneeded / calendar-sharee-publish / ldap-put-isadmin / federated-ocm-token）
- n8n: 2 仓复核（function-vm2 / databricks-path-join）

## 真缺口 — 产品线全新（~120 包）
大组:
- SQLite 3.53.4 ×14（rsync-ssh RCE / CLI go+、recover 命令注入 / rtree UAF / FTS3 UAF / FTS5 ×2 / session heap OOB / WAL 页泄漏…）
- phpMyAdmin 5.2.3 ×11（ImportLdi+auth-plugin+designer/central SQLi / 2FA 清除 / WebAuthn 跳过 / CSRF / isSuperUser / setup-validate 残留 / VQB XSS）
- CakePHP 5.4.2 ×7 + CVE-2026-79752/77635（unserialize / CRLF×2 / SQLi / trustedProxies / cookie 后缀）
- MySQL 26.7.0 ×6（JDV DEFINER SQLi / SET ROLE 残留 / mysqldump×2 / install-component）
- VFS for Git ab95cf51 ×6（4 LPE + quote-breakout RCE + mount dehydrate）
- CVE 类 26+（sudo 96512 LPE / Tomcat 86350 HTTP/2 走私 / Strapi 22599 / OpenProject 52782 / UAA 59358 / chamilo 45140 / Tickera 82226 / stellarwp 78159 / grav 75827 / Grafana-MCP 15583 / GravityForms 87796 / Elementor 62062 / CryptoPayment 81648 / BrokenLink 18937 / WP-PrivEsc 81294 / FrontendAdmin 75816 / DynamiApps 19952 / SMS-OTP 11387 / inspireui 13447 / WPFunnels 84753 / joomlaeventmanager 77991 / gist 105221 / Loom 103956 / Linux-BPF 38502）
小组:
- Moodle 5.2.3 ×4 | Drupal 11.4.8 ×4 | Joomla 6.1.3 ×4 | Forgejo 16.0.5 ×4
- Element ×3 | LiteBox ×3 | Signal-Server | Grafana 13.2.3 ×2 | Prometheus ×2 | OpenLiteSpeed ×2 | Lago ×2 | Hyperswitch ×2 | CPython ×2 | lighttpd | Kafka-Connect | Bitwarden | Vaultwarden | Uptime-Kuma | MsQuic | SONiC

## 工具/研究类
- P1: veneficus + veneficus-implant-public（kill-chain 植入物，Rust 伪代码）· ShieldCrash（Win Defender 0day）· Chrome-App-Bound-Encryption-Decryption · Fortigate-SSL-VPN-Exploit-Kit（79 clients × 53 SKU）· CVE-2025-38502-LPE
- 参考: Atlas（C# Titanis 网络执行）· GregsBestFriend（进程注入）· GateX（Nuitka/XOR/Argon2id 逆向样本）· mintranet（内容待看）
- SKIP: lpe-toolkit（本地已有 `domains/linux-post/lpe-toolkit`）· exploitarium（机制重叠）· team-teso（空）· llm-jailbreaks · LEAKSFORUMS · opencrabs/pentagi/mithril

## 同批其他四源
- **AnyDesk AnyPwn**（threatwire 文章 + v12-security/pocs）: Linux AnyDesk 8.0.2 pre-auth heap overflow → root RCE，打 7070 免批准连接。本地 `v12-security-pocs/collection/` 已有（pintheft/postgresql/firefox/thorchain/mariadb/terramaster/fragnesia/dirtydecrypt/qemu）——**anydesk = 差量**，补 anypwn.py + README。
- **MalikHettige**: JWT/ + authentication/ = PortSwigger 教科书 → SKIP（jwt-bypass-pentest 已覆盖）。`idor_matrix.py`（多身份对象矩阵，${ENV} 引用不打印密钥）→ P2 工具；`vdp_finder.py`（VDP 新项目监控，arkadiyt 数据集）→ P2。
- **spectre (qingnian112233)**: 不整仓收。设计点参考: `verify_chain.py`（时间盲注对照组+抖动扣除+置信度 0-100 打分）/ `pentest-orchestrator`（确定性 DAG wave + resolved 台账）/ `atk_meta`（经验蒸馏）——对照 evidence-gate / hypothesis-ledger / ops-review。

## 决策表（✅ 已全部执行）
- P0: abraxas ~120 漏洞包 → 0day-exploits 对应产品目录；AnyDesk AnyPwn → v12-security-pocs
- P1: veneficus / ShieldCrash / Chrome ABE / Fortigate kit / 38502
- P2: idor_matrix / vdp_finder / spectre 设计点
- SKIP: PortSwigger 脚本 / lpe-toolkit / exploitarium / team-teso
