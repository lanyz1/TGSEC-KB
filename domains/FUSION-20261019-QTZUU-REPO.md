# FUSION-20261019 · GitHub 仓 `lanyz1/TGSEC-Qtzuu` 全量回归融合

> 源：https://github.com/lanyz1/TGSEC-Qtzuu （`master`，pushed 2026-10-19T14:22:09Z）
> 目标：本机知识库 `C:\Users\Administrator\.dsh\tgsec-kb`
> 方式：**逐文件 sha256 双向对账 → 仓侧独有全量并入 / 双侧差异按"谁新谁全"择优 / 本地独有零删除**
> 结论：**仓库 → 本地库 单向满覆盖（除 7 个 LFS 对象）**；本地库仍为严格超集。

---

## 一、对账基线

| 项 | 仓 | 本地库（融合前） |
|---|---|---|
| 文件数（含隐藏，排除 `.git`） | 29,904 | 29,349 |
| `SKILL.md` | 1,110 | 1,140 |
| 体积 | 348.0 MB | 524.1 MB |
| 域（`domains/*`） | 30 | 30 |

对账结果（CRLF 归一后）：

| 分类 | 数量 | 处置 |
|---|---|---|
| 完全一致 | 27,684 | 不动 |
| **仓侧独有** | **2,189** | **全量复制入库** |
| 双侧差异 | 24 | 取仓侧 17 / 跳 LFS 7 |
| 本地独有 | 1,641 | **零删除**（超集保活） |

---

## 二、仓侧独有 2,190 件落点

| 域 | 件数 | 内容 |
|---|---|---|
| `domains/0day-exploits` | 1,112 | **pfSense CE 2.9.0-DEV ×640** · Spark 4.2.0 ×104 · **OpenMeetings 9.1 ×103**（8 条独立漏洞线：backup-config-path / calendar-save-idor / chat-user-idor / kms-unauth / nettest-ping-dos / remember-me-password / soap-otp-skip / soap-user-rights，每条带 `lab/` Dockerfile + `poc.py`）· **OPNsense 26.7.6 ×88** · **pfSense-API ×82** · vsftpd 3.0.5 ×27 · wordpress ×20 · nextjs ×14（CVE-2025-55182 React2Shell 扫描器 + 可跑靶场）· atlassian ×13（CVE-2026-21589 预认证任意文件读 9.3，4 份独立 PoC：AtlasSniper / marcus-program / tc4dy / watchTowr）· telegram-desktop ×10 · tomcat ×10 · `INGEST-20261017-INDEX.md` |
| `domains/recon` | 781 | **Web-Fuzzing-Box 词表族**（500+ 文件：省级手机号段 / 上传扩展名 fuzz / SQLi payload / XSS / 穿越 / JWT secrets / XML bomb / 路径字典）· ClatScope · HUNT · keyhunter · CloudRip · XNLDorker · JS-Analyser · recox · bypass-403 · ffufai · CerberusX |
| `domains/web-attack` | 203 | **xss-labs 20 关**（每关 `app.py` + `templates/` + `solution/README.md`）· `xss-pdf-credential-harvesting`（PDF 内嵌 XSS 钓鱼，含 `gen_pdf.py` + PoC PDF） |
| `domains/malware-dfir` | 20 | `sinian-anti-forensics` 分册（part-01..20） |
| `domains/windows-post` | 18 | `offensive-windows-boundaries` / `offensive-windows-mitigations` 分册（day-1..7 + appendix） |
| `domains/post-exp-tools` | 16 | `sinian-data-exfiltration` 分册（part-01..16） |
| `domains/binary-pwn` | 7 | `offensive-crash-analysis` 分册（part-01..07） |
| `domains/other` | 9 | `sinian-sinian-omnipotent` 分册（part-01..09）+ `scripts/sinian_pipeline.py`（18.6 KB 管线脚本） |
| 其余 9 域 + 根 | 41 | `docs/updates/UPDATE-2026-10-17.md` · `UPDATE-2026-10-19.md` · `docs/SKILL-AUDIT-20261017.md` · `domains/INGEST-20261017-PACK.md` · `INGEST-20261019-PACK.md` · api-security / gambling-pentest / business-logic / crypto-attacks / gpu-ai-security / redteam-framework / reverse-engineering / web-security 增量 |

---

## 三、双侧差异 24 件的裁决

### 取仓侧（17 件）

| 文件 | 仓 / 本地（字节） | 裁决理由 |
|---|---|---|
| `README.md` | 18,642 / 46,783 | 仓侧是**重构后的精简版**（§〇 只留最近一轮，历史迁 `docs/updates/`）。旧长文全量存档为 `docs/updates/README-PRE-FUSION-20261019.md` |
| `START.md` | 18,065 / 16,645 | 仓侧多 2026-10-17 abraxas 批 |
| `MASTER.md` | 7,975 / 7,350 | 同上；本轮旗标同步 |
| `domains/CASE-INDEX.md` | 29,113 / 24,191 | 仓侧课 **139** vs 本地 113，且多 `lynxcode-heapdump-whitelist-takeover` / `dalikefu-backup-2fa-skip` / `sonata-code-array-totp-secret` / `zgycpd-lockout-oracle-budget` / `botion-point-captcha-mask` / `we7-cashier-fee-tamper` / `olympus-tm99s-filament-rce-ddl` / `r64-grey-card-ledger-desens` / `ttzslots-gameinternal-rtp-control` / `v66-seo-poison-front-token` 等行 |
| `domains/0day-exploits/README.md` | 2,655 / 1,946 | 仓侧含 2026-10-17 增量批账目 |
| `domains/recon/README.md` | 2,735 / 2,084 | 仓侧含 Web-Fuzzing-Box / 工具族索引 |
| `domains/web-attack/README.md` | 2,424 / 2,054 | 仓侧含 xss-labs 靶场索引 |
| `domains/api-security/case-lessons/711tock-tg-cloud.md` | 2,549 / 1,596 | 仓侧多「2026-10-17 复读增量」段（WASM oracle 直调 `window.goEncrypt/goDecrypt` · `/clienter/pageList` 明文口令面 · 18,343→18,229 数据面 · CF 1010 限流指纹 · 跨租户 IDOR 负结果） |
| `domains/gambling-pentest/case-lessons/nbgame-agent-console-takeover.md` | 2,909 / 1,990 | 仓侧多一节 |
| `scripts/check-large-files.sh` | 2,719 / 2,460 | 仓侧多 LFS / 大文件守卫分支 |
| 7 × 分册化 `SKILL.md` | 见下 | 索引化，正文拆 `references/`，字节校验无丢失 |

### 分册化内容零丢失校验

| Skill | 旧单体 SKILL.md | 新 SKILL.md + references/ | 差值 | 判定 |
|---|---|---|---|---|
| `binary-pwn/offensive-crash-analysis` | 421,719 | 423,839 | +2,120 | OK（分册头） |
| `malware-dfir/sinian-anti-forensics` | 378,125 | 379,752 | +1,627 | OK |
| `other/sinian-sinian-omnipotent` | 746,909 | 770,190 | +23,281 | OK（+`scripts/sinian_pipeline.py` 18,608 + 分册头） |
| `post-exp-tools/sinian-data-exfiltration` | 214,651 | 216,248 | +1,597 | OK |
| `web-attack/offensive-basic-exploitation` | 365,095 | 366,499 | +1,404 | OK |
| `windows-post/offensive-windows-boundaries` | 582,677 | 584,249 | +1,572 | OK |
| `windows-post/offensive-windows-mitigations` | 545,045 | 546,482 | +1,437 | OK |

### 跳 LFS（7 件）

`domains/0day-exploits/ios-vphone/vphone-aio/vphone-cli.tar.zst.part_{aa,ab,ac,ad,ae,af,ag}`
上游 LFS 对象 **404**（`3c96624…` Object does not exist on the server），7×2 GB = 14 GB VM 镜像。本地保留原占位指针，不覆盖。取法：`git lfs pull` 需上游先补齐，或直取 vphone 官方发布件。

---

## 四、本地独有 1,641 件（零删除，全部保活）

| 类型 | 件数（抽样 400 计） | 说明 |
|---|---|---|
| `.pdf` | 217 | `poc-catalog/vuln-wiki` 报告全文（`.gitignore` 排除） |
| `.png` / `.gif` / `.webp` / `.jpg` | 140 | 漏洞复现截图 / PoC 图 |
| `.dll` / `.pdb` | 29 | `generic/CVE-2026-50522/ysoserial` 完整反序列化链依赖 |
| `.zip` / `.mp4` / `.jsonl` | 12 | openclaw dist 5.x 包 · CCTV mp4 · `pocs-summary.jsonl` |
| `.md` | 1 | `ABSORB-DSH-20261017.md` |

额外本地独有：`hermes-skills/`（256 文件，伞形路由源）· `DSH-INTEGRATION.md` · `docs/updates/` 中早于仓的 note · 本轮新增存档 `README-PRE-FUSION-20261019.md`。

---

## 五、融合后规模（实计）

| 指标 | 值 |
|---|---|
| 文件总数 | **31,546** |
| `SKILL.md` | **1,140**（仓侧 0 新增 SKILL.md，纯增量文件 + 分册） |
| 域 | **30** |
| `0day-exploits` 产品目录 | **309** |
| `case-lessons` 实战课 | **139** |
| `0day-exploits` 文件数 | 14,590 |
| `recon` 文件数 | 1,924 |

---

## 六、回滚

覆盖前的 17 个原文件在 `C:\Users\Administrator\Desktop\1\_absorb\backup-kb-20261019\`（保持相对路径）。
仓侧独有文件为纯新增，回滚只需删同路径。旧 README 全文另存 `docs/updates/README-PRE-FUSION-20261019.md`。

---

## 七、遗留 / 下一步

- `ios-vphone` 7 个 LFS 分片仍缺实体（上游 404）；需要实体时从 vphone 官方 release 取。
- 仓侧 `pfSense` 家族（640 + 82）与本地既有 `pfsense-xss-to-rce` 技能卡是「PoC 仓」↔「技能卡」两层，**未合并**，两级都在。
- 仓侧 `.claude/skills`（240 文件）与本地 `hermes-skills/`（256 文件）为两套并行伞形入口，**按工具各自保留**。

---

@TGSEC社区 · @TGSEC-Qtzuu 整理
