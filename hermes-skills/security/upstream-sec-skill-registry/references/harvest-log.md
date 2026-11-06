# 收割记录（harvest log）

## 2026-09-25 · din4e/Skills4RedTeam（#网络安全）

| 项 | 结果 |
|---|---|
| 克隆 | `D:/skills4redteam/Skills4RedTeam`（127K） |
| 清点 | 全部文件仅 `.gitignore` / `LICENSE` / `README.md`；**SKILL.md = 0** |
| 定性 | **索引型仓库**（不自带任何 skill，只做社区仓库推荐榜） |
| 处置 | 抽取 38 个上游仓库 → `references/registry-38repos.md`；本仓库本体不建卡 |

## 2026-09-25 · manbamax/pentest-pro-skills（13 张 SKILL.md）

融合来源：ymaine / wyang / Prohao42(aimy-skill) / DouglasRao / frendysanusi / Claude-Red。
每张 1.5–3.2KB，属**方法论摘要型**（总控 + 攻击面清单），非深水命令集。

### 逐卡去重结论（数据来自 `scripts/dedupe_gate.py`，原始输出见 `gap-final.txt`）

| 上游卡 | 已覆盖 | 真缺口 | 中文标题 | 自引用 | 署名 | 结论 |
|---|---|---|---|---|---|---|
| `active-directory` | 37 | 0 | 2 | 0 | 2 | 已被本库超越 |
| `auth-api-security` | 31 | 0 | 0 | 0 | 2 | 已被本库超越 |
| `binary-exploitation` | 22 | 0 | 3 | 2 | 0 | 已被本库超越 |
| `cloud-mobile-iot` | 19 | 0 | 0 | 0 | 1 | 已被本库超越 |
| `code-audit` | 17 | 0 | 4 | 3 | 0 | 已被本库超越 |
| `crypto` | 18 | 0 | 3 | 0 | 2 | 已被本库超越 |
| `pentest-process` | 9 | 0 | 4 | 0 | 3 | 已被本库超越 |
| `post-exploitation` | 35 | 0 | 0 | 0 | 1 | 已被本库超越 |
| `privilege-escalation` | 26 | 0 | 0 | 0 | 0 | 已被本库超越 |
| `recon` | 23 | 0 | 5 | 4 | 1 | 已被本库超越 |
| `web-architectural` | 22 | 0 | 2 | 1 | 1 | 已被本库超越 |
| `web-injection` | 36 | 1 | 1 | 0 | 3 | 有真增量，已补 |
| `wireless` | 31 | 0 | 2 | 0 | 1 | 已被本库超越 |

合计：token 命中本库 **326** 次；真缺口 **15** 个（全部为术语/工具别名级，**零域级缺口**）→ 处置后 **1** 个。

### 15 个真缺口的处置

| 缺口 token | 出锅卡 | 处置 | 落在哪张卡 |
|---|---|---|---|
| `rpcclient` | active-directory | 补工具别名 | `ad-windows-router` 工具别名表 |
| `session_matrix` | auth-api-security | 映射到已有能力 | `ad-windows-router` → `object-matrix-authz` |
| `cig` | binary-exploitation | 与 ACG 并入规避表 | `edr-bypass-re` 执行规避三件套 |
| `goop` | code-audit / recon | 补同类工具 | `vcs-repo-exposure` |
| `gmac` | crypto | 补 nonce 重用 | `crypto-toolkit` 弱随机行 |
| `poodle` | crypto | 补 TLS 三漏洞 | `crypto-toolkit` TLS 行 |
| `applocker` | post-exploitation | 补约束绕过 | `edr-bypass-re` 执行规避三件套 |
| `crd` | privilege-escalation | 补 K8s 提权面 | `cloud-k8s` P7 |
| `blueborne / killerbee / otaa / pmf / zcl` | wireless | 补英文术语别名索引 | `wifi-wireless` 分流表 |
| `aimy_oob_domain` | web-injection | **不采纳**：上游作者私有 OOB 域名变量，非技术点 | — |

### 同时修掉的库内问题

- `kubernetes-security` 原为 481B 空壳且 **frontmatter YAML 非法**（description 裸冒号）⇒ 改为重定向卡 + 引号修正，正文并入 `cloud-k8s`。
- `wifi-wireless` / `crypto-toolkit` 等 7 张卡按真实缺口补行（见上表）。

## 范围外发现（未处理，待指示）

`D:/skills4redteam/HiFullHouse-CyberSecurity-Skills`（195 卡 `*.md`，含蓝队/取证/合规/加固/ICS）—— **不在 din4e 索引 38 仓库内**，也不在本次两个仓库范围内。
过闸结果（`--glob '*.md'`）：HOLE 1819，主体是 **MITRE ATT&CK 编号（T1590/T1589…）、工具名（subover/builtwith）、JSON 字段名**，与本库缺口语义不同（本库是攻击向，无 ATT&CK ID 索引层）。是否收割需单独决策。

### 纪律（下次照做）

1. 上游 13 卡与本库 898 卡**域级 100% 重合**，照搬建卡 = 制造 13 张重复卡。

2. 只有 4 类东西值得从这类仓库吸：**术语别名映射**、**工具链名称**（Fernflower/Vineflower、goop）、**新攻击面**（CRD/Operator）、**编排细节**。

3. 结论必须由 `dedupe_gate.py` 的 HOLE 数支撑，不以「看起来像缺口」下判断。

---

## 2026-09-25 · 第二轮：HiFullHouse 196 卡按「渗透角度」整理（用户口径：只整理渗透向）

| 项 | 结果 |
|---|---|
| 源 | `D:/skills4redteam/HiFullHouse-CyberSecurity-Skills`（196 张 `*.md`，逐卡自带 `category`/`tools` frontmatter）|
| 归位 | 渗透向 **122 卡** / 25 类（其余为蓝队·取证·合规·加固·IT 运维，**不并入**）|
| 判定 | 工具名逐 token 过闸：绝大多数已在库（nmap/sqlmap/Burp/Frida/Mimikatz/Prowler/Slither…），真缺仅工具级 |
| 结论 | **域级零缺口**；上游价值 = 具体工具/命令/API 名，不是方法论 |

### 本轮落地（详表见 `references/pentest-skill-map.md`）

| 动作 | 对象 | 说明 |
|---|---|---|
| 新建 | `covering-tracks` | 攻击侧清痕/反取证（本库真缺的攻击面）：Windows/Linux 证据源、清除顺序、清痕动作自身的留痕 |
| 填实 | `malware-analysis` | 判型表（加壳/.NET/Go/PyInstaller/ELF）→ 静态/动态/脱壳/IOC/YARA；工具 PEStudio/INetSim/FakeNet-NG/CAPE/FLOSS |
| 填实 | `lateral-movement` | Windows 远程执行矩阵（SMB/WMI/WinRM/DCOM/RDP/计划任务）+ 凭据复用 + 检测点自检 |
| 填实 | `dotnet-reverse` | dnSpy/de4dot 主线 + 卡密校验定位 + IL patch + 强名处理 |
| 补工具 | 17 张宿主卡 | SAST 族 13 个、硬件/IoT 工具链（ChipWhisperer/Ubertooth/MQTTsa/CANtact…）、BAS（PurpleSharp/Stratus Red Team/CALDERA）、Stowaway、Cloudsplaining/PacBot、Muraena、MEV-Inspect/Teku/Prysm、Foolbox/Counterfit/ART、Chipsec/UEFITool、SIPVicious、k6/ghz、ISF/PLCScan |

### 顺带修掉的库级问题（重要）

- **67 张英文名占位空壳转重定向卡**（`active-directory`/`cloud-aws`/`web-xxe`/`reverse-engineering`/`persistence` …）：正文原本只是 description 复制，触发即空转；现保留触发词并指向真卡。
- **26 张 frontmatter YAML 修复**：`description` 裸冒号导致解析失败（`full-crack`/`crack-keygen`/`client-crack-cheat`/`card-key`/`vip-bypass`/`malware-analysis`/`lateral-movement`/`dotnet-reverse`/`codex-backend-patch` …）；修复后 902 张全部通过 `yaml.safe_load`。
- 保留原样 2 张（`biometric-spoof`/`quantum-crypto`，非渗透向，无真卡可指）。

### 纪律增补

4. 空壳占位卡 → 重定向，不要填第三份同域内容；无真卡可指才填。
5. 改卡后跑 YAML 校验（裸冒号是高频坑）。


## 2026-09-25 · Hi-FullHouse/CyberSecurity-Skills（39 模块 / 195 卡 / MIT）

| 项 | 结果 |
|---|---|
| 克隆 | `D:/skills4redteam/HiFullHouse-CyberSecurity-Skills`（3.9M，`--depth 1`，默认分支 master） |
| 清点 | 195 张 `*/skills/*.md`（扁平镜像 `_mirror_hfh` 用于去重门）；另有 `index.json` / `agent-manifest.json` / `scripts/validate_skills.py` |
| 去重门 | `dedupe_gate.py --src _mirror_hfh --min-hits 2 --json gap-hfh.json` → EXIT=0，输出 `gate-hfh.txt` |
| 定性 | **卡片型仓库**（PTES + OWASP + NIST 800-115 骨架），攻击面 1–13 已被本库超越，**防御/治理面整片空白** |
| 处置 | 新增 9 张家族卡 + 4 处既有卡补丁；上游原文作为 references 落地（不重写、保留出处） |

### 判别依据（两层证据，避免只看 token 级 HOLE 误判）

1) **名称级**：本库 899 张卡逐名核对 → 上游命中的主题词（Sigma/SOAR/SIEM/ZTNA/微隔离/PAM/SBOM/DLP/等保/MISP/STIX/TAXII/Falco/LOLBins/IEC 62443/MDM/Volatility）在本库**几乎零命中**（仅在 72stack-sec 等报告语料里偶然出现）。
2) **内容级**：`coverage_scan.py`（只读，输出 `coverage-report.txt`）比对 989 张本库卡，模块覆盖率 avg **最低带 0.218–0.240** = 22 数据隐私 / 31 SOC / 29 情报 / 39 合规 / 36 零信任 / 24 红蓝 / 37 端点 / 27 OS / 09 报告 / 16 大模型 / 32 IAM；**最高带 0.36–0.41** = 10 移动 / 01 信息搜集 / 03 漏洞利用（本库已远超上游，不建卡）。
3) 卡级最低：PKI/证书与国密 0.161、Word 报告模板 0.158、国产 OS 0.145、Linux 加固 0.139、MDM 0.155、Bug Bounty 计划 0.186、APT 归因 0.187、SOC 分级 0.19、联邦学习 0.19、勒索 0.189。**token 级 HOLE 多为 ATT&CK ID / 工具名 / JSON 字段，不构成域级缺口**——这是本次判别方法的关键更正。

### 落地清单

| 新卡 | 覆盖 |
|---|---|
| `detection-engineering-sigma-attack` | Sigma YAML + sigma-cli 转换 + Splunk SPL/Elastic KQL + Sysmon/LOLBins + ATT&CK 映射与紫队验证 |
| `endpoint-os-hardening-baseline` | CIS/等保扫描、Lynis/oscap/InSpec/Ansible、Windows secedit+auditpol+Defender ASR、Docker/K8s 基线、Sygmon/EDR 遥测 |
| `enterprise-iam-pam-zerotrust` | Vault/CyberArk/Teleport、SAML/OIDC 断言错误配置、MFA 弱面、云 IAM 审计、ZTNA/微隔离审计与绕过面 |
| `data-privacy-compliance-ops` | DLP 三形态、分类分级、TDE/pgcrypto/脱敏/k-匿名/差分隐私、等保2.0 与 ISO27001/CSF/SOC2/GDPR 映射、CVSS+EPSS 优先级 |
| `sbom-supplychain-integrity` | Syft/Trivy/cdxgen、cyclonedx-cli 校验、cosign keyless+attestation、SLSA、in-toto/TUF、Dependency-Track、IaC/SAST/DAST 流水线与 CI 攻击面 |
| `adversarial-ai-model-security` | FGSM/PGD/C&W、投毒与后门、模型窃取/成员推断、HF 供应链审计、Garak/PyRIT、LLM Top10 2025 × ATLAS |
| `threatintel-platform-ops` | MISP/PyMISP、TAXII2/STIX、OpenCTI/TheHive/Cortex、IOC 生命周期、APT 归因与真实数据源 API、狩猎假设+PDCA、SOAR 剧本 |
| `ransomware-defense-ir-recovery` | 家族指纹+YARA/Sigma 检测点、卷影/备份破坏命令、遏制与取证取舍、解密评估、3-2-1-1-0 与不可变备份、恢复演练 |
| `pki-cert-ops-and-gm-crypto` | 证书链审计（s_client/testssl/nmap）、私有 CA 四步链、证书生命周期与吊销、国密 SM2/SM3/SM4 + GMSSL |
| `metasploit-framework-ops` | msfdb/workspace/db_nmap、模块搜索与配置、msfvenom payload 矩阵、handler+resource 自动化、meterpreter 后渗透、route/socks_proxy 代理链、msfrpcd |

| 既有卡补丁 | 内容 |
|---|---|
| `security-report-templates` | 修掉 2 条悬空引用；落地 5 份真模板（Markdown 42K / HTML 60K / Word 48K / 报告编写 / CVSS 评级）+ `report-schema-outline.md`（可脚本消费的字段模型） |
| `secure-code-review` | `references/per-language-audit-cheatsheet.md`（9 语言危险函数+grep 正则+扫描器命令+CWE） |
| `malware-analysis` | `references/reverse-malware-increments.md`（CS beacon 配置提取、FLOSS/capa、CAPE、反调试对照、Volatility 3、YARA 骨架） |
| `cloud-security-audit` | `references/cloud-audit-cn-multicloud.md`（aliyun/tccli/hcloud + ossutil/obsutil + AK/SK 泄露影响面 + IMDS 对照） |
| `crypto-toolkit` | 证书/国密分流行 → `pki-cert-ops-and-gm-crypto` |

### 上游排雷（本次实测/官方核对出的错误，写入各卡 Pitfalls 以防照抄）

- **Defender 参数**：真为 `-LowThreatDefaultAction`、`-AttackSurfaceReductionRules_Ids/_Actions`（带下划线）；上游 `-LowfiThreatLevel`、无下划线写法不存在。
- **ASR GUID 表**：上游三条 GUID 尾部为连号式杜撰（前缀恰等于真实 GUID）——全组丢弃，以 Microsoft Learn 为准。
- **`secedit /export`**：不写 stdout 且导出 UTF-16LE，上游 `secedit ... | Select-String` 恒无效。
- **SLSA**：上游 L4 不存在，现行 SLSA v1.0 只到 Level 3。
- **cosign**：`cosign attach sbom` 已废弃，改 attestation 流程。
- **kube-bench**：`--version` 非法参数；docker-bench-security 在 Docker Desktop 上因 npipe 端点连不上。
- **自编 Python class**：上游大量 `*Engine`/`*Model`/`*Pipeline` 伪代码与假占位值（假 webhook、假 VT 返回）一律丢弃。
- **国产 OS 厂商 CLI**：`kylin-security-*` / `kysec-tools` / `uos-security-center` 名称无法核实 → 改为 `command -v` 探测优先。
- 未验证项一律在各卡 `references/provenance-and-unverified.md` 中列明（含来源年份）。
