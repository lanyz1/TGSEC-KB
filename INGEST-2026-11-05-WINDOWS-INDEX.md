# INGEST 2026-11-05 · lanyz1/TGSEC-Qtzuu 全量回流（Windows / DSH 主机）

> 源：`https://github.com/lanyz1/TGSEC-Qtzuu` · 默认分支 `master` · 仓内 README 标注 **2026-11-05**
> 取法：`codeload.github.com` tar.gz 快照（本机无 git），173,476,830 B → 解包 43,427 文件 / 453.3 MB
> 落地：`C:\Users\Administrator\.dsh\tgsec-kb`（KB 层）+ `C:\Users\Administrator\.dsh\skills`（技能层）
> 本机吸收前状态：`docs/updates` 到 **2026-10-19**，`hermes-skills/` 仅 30 张伞形卡，`arsenal.db` 不存在

## 一、一条命令做了什么

```powershell
# 1) 取快照
Invoke-WebRequest -Uri 'https://codeload.github.com/lanyz1/TGSEC-Qtzuu/tar.gz/refs/heads/master' -OutFile _stage\tgsec.tar.gz -UseBasicParsing
tar.exe -xzf _stage\tgsec.tar.gz -C _stage

# 2) 增量镜像（源 2026-11-05 时间戳 > 本机 10-19/10-20，故 /XO = 仓库新版本胜出；本地独有文件不删）
robocopy _stage\TGSEC-Qtzuu-master C:\Users\Administrator\.dsh\tgsec-kb /E /XO /XJ /R:1 /W:1

# 3) 30 张伞形卡同步进活跃技能层
robocopy ...\hermes-skills\security\<卡名> C:\Users\Administrator\.dsh\skills\<卡名> /E /XO /XJ

# 4) 重建检索索引（捆绑 python 3.12.14 / sqlite 3.53.1，FTS5 可用）
$env:ARSENAL_SKILLS='C:\Users\Administrator\.dsh\tgsec-kb\hermes-skills'
$env:ARSENAL_DB='C:\Users\Administrator\.dsh\tgsec-kb\arsenal\arsenal.db'
python.exe C:\Users\Administrator\.dsh\tgsec-kb\tools\arsenal\arsenal_build.py
```

robocopy 终态：`Dirs 12,890 / Files 43,427`，**Copied 43,399 文件 / 453.34 MB**，`FAILED 0`，`Extras 2,909 文件 / 75.33 MB`（本地独有，未删）。

## 二、吸收前后（磁盘实数）

| 池子 | 吸收前 | 吸收后 | 变化 |
|---|---|---|---|
| `domains/` 域数 | 30 | 30 | 0（同名对齐，无新增域） |
| `domains/` 文件 | 30,975 | **38,657** | **+7,682** |
| `domains/` 体积 | — | 687 MB | — |
| `hermes-skills/` 卡目录 | 30 | **2,352** | +2,322 |
| `hermes-skills/` `SKILL.md` | 30 | **2,380**（唯一 2,348） | +2,350 |
| 卡状态 | — | 启用 **574** / 归档 **1,805**（`.disabled.json`） | — |
| `arsenal.db` | 无 | **354 MB / 2,348 卡**（enabled 574 · disabled 1,774 · legacy 1,856） | 新建 |
| 活跃技能层 `.dsh/skills` | 30 | **31**（30 张更新 + `tgsec-arsenal-router`） | +1 |
| `docs/updates` | 至 2026-10-19 | 至 **2026-11-05**（+10-22 / 10-23 / 11-01 / 11-05） | +4 |

### 按域新增文件

| 域 | 前 | 后 | 新增 |
|---|---|---|---|
| 0day-exploits | 14,591 | 20,446 | +5,855 |
| ctf | 1,743 | 2,806 | +1,063 |
| recon | 1,924 | 2,414 | +490 |
| web-attack | 412 | 492 | +80 |
| gambling-pentest | 32 | 71 | +39 |
| llm-ai-security | 126 | 165 | +39 |
| other | 147 | 173 | +26 |
| cloud-security | 299 | 315 | +16 |
| ai-infra-security | 4,971 | 4,986 | +15 |
| redteam-framework | 544 | 557 | +13 |
| gpu-ai-security | 11 | 18 | +7 |
| api-security | 99 | 105 | +6 |
| web-injection | 1,274 | 1,280 | +6 |
| auth-security | 122 | 126 | +4 |
| business-logic / malware-dfir / reverse-engineering / web-security | — | — | 各 +1 |
| ad-attack / binary-pwn / crypto-attacks / file-vulns / linux-post / mobile-security / post-exp-tools / skill-catalog / social-eng / vuln-intel / windows-post / wireless | — | — | 0 |

> 双向差集都保留：`0day-exploits` 本地原有 14,591 含仓库版没有的富集文件，仓库另带 13,673 —— 合并后 20,446，未做删除。
> 备份：`tgsec-kb\.absorb-backup-20261105\`（10 个根级导航文档原件 + `local-newer-than-repo.txt`，实测 **0 个本地文件比仓库新**）。

## 三、本轮真正的新知识（来自 4 篇 update）

| 批次 | 落点 |
|---|---|
| 2026-11-05 · ExploitGrid 2025–2026 语料（1,510 条 PoC 全文 → 761 CVE → 672 缺口 → 16 新卡 + 4 补强） | `weaver-ecology-dubbo-rce` 泛微 E-cology `dubboApi` 未授权 RCE（在野）· `sharepoint-trust-deser-rce` `/_trust` DEFLATE+BinaryFormatter + 同原语 dump farm keys · `rails-activestorage-vips-rce` 四层解析混淆读文件→`SECRET_KEY_BASE`→RCE · `atlassian-dc-preauth-file-read` 先路由后 `unescapeSlashes()` 的 `..::` 穿越 · `servicenow-preauth-rce` KEV 沙箱逃逸 · `aiowpm-secondorder-sqli-to-rce` · `mariadb-frm-oob-rce` · `gitlab-ci-lint-regex-rce` `{5(?#)7805}` 绕 `REPEAT_MAX` · `openam-jato-deser-rce` · `windows-rdp-xfg-bypass-rce` · `cve-2026-98432-linux-tcp-race-uaf` · `yootheme-pro-image-handler-rce` CVSS 10 在野（IPTC Caption 藏 PHP）· `lmcache-zmq-pickle-rce` · `beyondtrust-rs-pra-rce` KEV · `weblogic-2026-cve-pack` · `unauth-rce-2026-11-pack` |
| 2026-11-01 · 报告包 127 篇 → 29 技术族（17 新卡 + 41 卡补 45 处）+ threatwire 17 条 | `java-tomcat-2026-10-cve-pack` · `node-runtime-2026-10-cve-pack` · `dujiaoka-yipay-notify-weaktype` · `internal-wallet-transfer-unauth` · `kvm-vhost-csum-host-read` · `jdbc-malicious-mysql-file-read` · `cognito-anon-pool-s3-takeover` · `yudao-oauth-token-captcha-bypass` · `fastadmin-filter-op-tenant-bypass` · `login-scene-branch-bypass` · `magic-link-token-reuse` · `eth-rpc-debug-exposure` · `threatwire-cve-briefs-2026-11` |
| 2026-10-23 · 技能库全量入仓 2,206 卡 | `hermes-skills/` 全量可检索（本机这次才真正拿到 2,350 张） |
| 2026-10-22 · 检索三通道 + 8 项门禁 | `arsenal/` 与 `tools/arsenal/`（`arsenal_build.py` / `skill_find.py` / `post_rebuild_gate.py` / `selftest.py` / `eval_core.json`）入仓 → 本机已跑通 |

## 四、蒸馏动作（不只是复制）

1. **新建 `tgsec-arsenal-router`**（唯一的全新活跃技能卡）：把仓库里 `/root/.hermes/arsenal/skill_find.py` 的 Linux 用法改写成本机 Windows 入口，写清 `[E]/[D]` 两种正文路径、`--phase` 全阶段扫法、重建索引命令、6 条实测命中表。
2. **新建 `tgsec-kb\tools\cardfind.cmd`**：一行封装 python 路径 + `ARSENAL_SKILLS` / `ARSENAL_DB` / `ARSENAL_DIR` / `UTF-8`，调用 `skill_find.py`：
   `& "C:\Users\Administrator\.dsh\tgsec-kb\tools\cardfind.cmd" "泛微 dubbo" --top 8`
3. **回写 `tgsec-suite`**：规模数字按磁盘实测改成 `30 域 · 38,657 文件 · 2,380 个 SKILL.md（唯一 2,348）· 启用 574 · 伞形 31`，伞形表加 `tgsec-arsenal-router` 一行。
4. **回写 `security-kb-ingest/references/full.md`**：Archived repos 表加本次回流一行（体量、技能层变化、索引实数）。
5. **30 张伞形卡实质升级**（文件数变化即证据）：`pentest-execution` 28→153 · `web-sec` 1→44 · `security-kb-ingest` 8→19 · `0day-exploit-library` 1→12 · `cdn-origin-tracing` 8→23 · `reverse-skill` 2→8 · `lfi-rfi-exploit` 1→4 · `open-redirect-chain` 1→3。
6. **`DSH-INTEGRATION.md`** 重写为本机实际入口（KB 路径、技能层、检索命令、索引重建）。

## 五、验收（可复跑）

| 项 | 命令 | 实测结果 |
|---|---|---|
| 索引建库 | `arsenal_build.py` | `{"total":2348,"enabled":574,"disabled":1774,"legacy":1856,"bytes":353157120}`，95.1 s |
| 检索 Top1（6 条新卡） | `cardfind.cmd "<关键词>" --top 3` | `weaver-ecology-dubbo-rce` 2728.7 · `sharepoint-trust-deser-rce` 1953.3 · `rails-activestorage-vips-rce` 2487.3 · `gitlab-ci-lint-regex-rce` 2632.6 · `yootheme-pro-image-handler-rce` 2667.5 · `lmcache-zmq-pickle-rce` 3728.3 · `servicenow-preauth-rce` 2270.9（全部 [E]） |
| 归档卡路径可读 | `--top 3` 的 `[D]` 行 → `catalog=...\references\legacy\<卡名>.md` | `druid-console-unauth` 989.5 命中，legacy 文件存在 |
| 技能层对齐 | 目录比 | 31 个技能目录，30 张与 `hermes-skills/security/` 同名同源 |
| 导航文档 | 根级 md | `README.md` 25,783 B / `MASTER.md` 7,826 B / `ROUTING.md` 7,265 B / `START.md` 21,008 B（均为 2026-11-05 版） |

## 六、留给后续的账

- 仓库 `domains/` 与本地 `domains/` 各自有独有文件（仓库少 8,856 个），本机现在是并集；下次要发布时需决定哪些本地富集面推回仓。
- `arsenal.db` 354 MB 属生成物，不入仓；重建命令写在 `tgsec-arsenal-router` 卡与 `tools/arsenal/README.md`。
- `tools/arsenal/post_rebuild_gate.py` 的 8 项门禁按 Linux `/root/.hermes` 路径写死，本机只跑了 `arsenal_build.py` + `selftest.py` 路径下的检索实测；要全门禁需把 `ARSENAL_*` 环境变量补齐后单独跑。
- 本机无 git，后续同步走 tar 快照 + robocopy `/E /XO`（或先装 Git for Windows 改回 `git pull`）。

@TGSEC社区 · @TGSEC-Qtzuu 整理
