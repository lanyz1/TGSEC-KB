# 抽取报告：data-privacy-compliance-ops

任务：从上游技能库 `D:/skills4redteam/HiFullHouse-CyberSecurity-Skills` 抽取「数据安全与隐私 + 合规框架 + 等保2.0 + 漏洞优先级」的真实可用内容，产出参考文件 + SKILL.md 草案。

## 0. 产出

| 文件 | 行数 | 定位 |
|:--|:--|:--|
| `references/data-security-dlp.md` | 199（限 ≤200） | 分类分级、DLP 三形态、DLP 绕过检测点、库加密、脱敏、k-匿名/差分隐私、备份加密 |
| `references/compliance-frameworks-cn.md` | 142（限 ≤200） | 等保2.0 流程与清单、跨框架映射表、渗透发现映射、GDPR/个保法流程、CVSS+EPSS+SLA |
| `DRAFT-SKILL.md` | 正文 88 行（限 ≤130），frontmatter 仅 name/description | 草案 |
| `REPORT.md` | 本文件 | 抽取记录 |

## 1. 读取的上游文件

| 上游文件 | 体量 | 读法 |
|:--|:--|:--|
| `22-数据安全与隐私-DataSecurityPrivacy/skills/DLP数据防泄漏策略-DataLossPrevention.md` | 6,673 字符 | 整读 |
| `22-…/skills/数据分类与分级保护-DataClassificationGrading.md` | 5,345 | 整读 |
| `22-…/skills/数据库安全与加密-DatabaseSecurityEncryption.md` | 8,470 | 整读 |
| `22-…/skills/数据脱敏与匿名化-DataMaskingAnonymization.md` | 7,448 | 整读 |
| `22-…/skills/GDPR-个保法合规评估-PrivacyCompliance.md` | 9,213 | 整读 |
| `22-…/skills/隐私影响评估-PIA-PrivacyImpactAssessment.md` | 8,790 | 整读 |
| `22-…/README.md` | — | 目录清单核对 |
| `39-安全治理合规-GovernanceCompliance/skills/安全框架与合规审计-SecurityFrameworkComplianceAudit.md` | 17,591 | 整读（框架对比+合规审计流程的主要来源） |
| `39-…/skills/风险管理与安全度量-RiskManagementSecurityMetrics.md` | — | 定向检索（EPSS/CVSS/SLA/风险矩阵 7 处） |
| `14-安全审计-SecurityAudit/skills/等级保护合规审计-ClassifiedProtectionAudit.md` | 2,826 | 整读 |
| `14-…/skills/配置安全审计-ConfigSecurityAudit.md` | 4,676 | 整读（现场命令来源） |
| `14-…/skills/网络安全合规评估-NetworkComplianceAssessment.md` | 2,416（前 80 行） | 部分读 |
| `26-漏洞管理-VulnerabilityManagement/skills/漏洞优先级与风险评估-VulnerabilityPrioritization.md` | 17,818 | 整读 + `EPSS\|CVSS\|SLA\|SSVC` 检索 40 处 |
| `09-报告撰写-Reporting/skills/安全报告模板-Markdown.md` | — | 检索 58 处 + 第 100–170 行（合规映射段落写法） |
| `16-大模型安全-LLMSecurity/skills/LLM数据泄露与隐私保护-DataLeakagePrivacy.md` | — | 仅检索 199 处，未整读（判断为不相关，见 §2 丢弃项） |

**与任务清单的差异**：任务里写的 `14-安全审计/skills/安全框架与合规审计*.md` **在该目录不存在**。已 `ls` 核对该目录实际只有 7 个文件（AI Agent 安全审计、安全架构审计、等级保护合规审计、配置安全审计、容器安全审计、网络安全合规评估、云安全审计）；`安全框架与合规审计-SecurityFrameworkComplianceAudit.md` 实际位于 `39-安全治理合规-GovernanceCompliance/skills/`，已整读。14 目录下其余文件与四主题重合度低，未读。

## 2. 逐条吸收 / 丢弃

### 2.1 直接吸收（内容真实、可用，原样或压缩后进参考文件）

| 上游内容 | 去向 |
|:--|:--|
| DLP 三形态架构（网络/终端/存储）+ 检测点清单 | dlp §2 |
| Zeek 敏感数据发现脚本（`event http_header` / `uri` / `to_lower` / 正则） | dlp §2（修正为可跑形式） |
| base64 正则 + 熵值检测思路 | dlp §2 |
| tshark DNS 检测 | dlp §2（`dns.txt_len` 标【未验证】） |
| ndpiReader 明文协议发现 | dlp §2（保留但标【未验证】，非主推） |
| 分类分级落地步骤（清单 → 标签 → 权限 → 审计） | dlp §1（改写为可勾选检查表） |
| SQL Server TDE 全套命令 + `sys.dm_database_encryption_keys` | dlp §3 |
| pgcrypto 对称/非对称加解密函数 | dlp §3（密钥生成部分更正，见 2.2） |
| 静态脱敏 SQL（`UPDATE … CONCAT`） | dlp §4 + 补三条陷阱 |
| SQL Server DDM（`ADD MASKED WITH (FUNCTION=…)`、`GRANT UNMASK`） | dlp §4 |
| PostgreSQL Anonymizer（`SECURITY LABEL FOR anon`、`anon.init()`） | dlp §4（语法更正，见 2.2） |
| Oracle `DBMS_REDACT` | dlp §4 |
| k-匿名泛化实现 + 差分隐私 Laplace 机制 + 基本/高级组合定理公式 | dlp §5（公式与上游一致，表述重写） |
| 备份加密（`gpg -e -r`、`openssl enc`） | dlp §6 |
| 等保 2.0 十个分类（技术 5 + 管理 5）与控制项 | compliance §1 |
| 等保测评流程（定级备案→现场测评→整改→复测） | compliance §1 |
| 配置安全审计命令（login.defs / shadow / ss / auditpol / mysql.user / SHOW ssl / lynis / oscap） | compliance §1 |
| 框架对比（ISO 27001 / NIST CSF / SOC 2 / PCI DSS） | compliance §2（升级为映射表） |
| 漏洞优先级：CVSS v3.1 公式、EPSS 分级区间、`priority = cvss/10×(1+epss)×(1+asset)`、业务风险 0–100 公式、SLA 表、KPI | compliance §5 |
| 报告中的"合规映射"写法（发现→控制项→建议） | DRAFT-SKILL 工作流第 6 步 |

### 2.2 更正后吸收（上游写法错误或不存在，已改为真实可用形式）

| 上游写法 | 问题 | 处理 |
|:--|:--|:--|
| `aws macie2 create-classification-job --s3-job-definition bucketDefinitions=[{bucketId=my-data-bucket}]` | `bucketId` 不是该接口字段，且嵌套结构不能用这种简写 | 改为官方 JSON：`'{"bucketDefinitions":[{"accountId":"…","buckets":["my-bucket"]}]}'`；补注 Macie 只覆盖 S3、压缩/加密文件检出受限 |
| `SELECT gen_keypair('RSA', 2048);` | pgcrypto **没有**此函数 | 改为用 `gpg` 生成密钥对 + `pgp_pub_encrypt(…, dearmor(pg_read_binary_file('/keys/pub.asc')::text))` / `pgp_pub_decrypt(…, …, 'passphrase')` |
| `CREATE EXTENSION pg_ddm; CREATE MASKING POLICY … FOR COLUMN` | 无此扩展/语法 | 动态脱敏改为真实 PostgreSQL Anonymizer：`CREATE EXTENSION anon CASCADE` + `SECURITY LABEL FOR anon ON COLUMN … IS 'MASKED WITH FUNCTION anon.partial(phone,2,$$******$$,2)'` + `anon.k_anonymity()` |
| `SELECT anon.anonymize('users') TO '/tmp/…'` | 语法不存在 | 改为 `anon.anonymize_table('public.users')` / `anon.anonymize_database()` |
| `anon.partial(anon.random_phone(),3,******,3)` | padding 参数未加引号，非法 SQL | 改为 `$$******$$` 定界 |
| Purview DLP 配置写成 PowerShell 哈希表（`$dlpPolicy = @{…}`） | 不是可执行配置 | 改为真实 cmdlet：`New-DlpCompliancePolicy -Name … -ExchangeLocation/SharePointLocation/OneDriveLocation`、`New-DlpComplianceRule … -ContentContainsSensitiveInformation -BlockAccess`；SIT 名称要求现场用 `Get-DlpSensitiveInformationType` 核对 |
| `az purview classification-rule create …` | 疑无此命令（`az purview` 目前主要是账号管理） | 标【未验证】，不作为交付命令 |
| Symantec `dlpcmd policy -list` | 参数未证实 | 标【未验证】 |
| `Set-AIPFileLabel` | AIP 客户端模块逐步退役，现行以 Purview 统一标签为主 | 保留但标【需核对】 |
| 分类分级自造 4 级（公开/内部/秘密/机密） | 与国标不一致 | 改用 GB/T 43697-2024：核心/重要/一般数据 + 一般数据 4 级框架 + 附录 H 最低级别（敏感个人信息≥4 级、一般个人信息≥2 级等） |
| `openssl enc -aes-256-cbc -salt -pass pass:密码` | 口令进 `ps`/history | 改为 `-pbkdf2 -iter 200000 -pass file:/etc/backup.key` |
| "ARX-style k-匿名实现" | Python 演示并非 ARX | 改称算法演示，并补 `anon.k_anonymity()`、DP 应使用成熟的 DP 库 |
| 终端 DLP 用 `Register-WmiEvent` 监控 USB | 事件注册会阻塞管道、依赖 PS5.1 | 保留但标注限制，补真实可验证路径：`auditpol /set /subcategory:"Removable Storage"` + 安全事件 6416 / 打印事件 307 |
| MySQL TDE / keyring 描述 | 版本与版本能力差异大 | 只保留要点并标【未验证】，补 MariaDB `file_key_management` 表级加密路径 |

### 2.3 丢弃（含理由）

| 上游内容 | 丢弃理由 |
|:--|:--|
| `pip install security-audit-tool` / `security-audit --level 3` | 疑不存在（未验证），写进报告会成硬伤 |
| ClamAV `clamscan --gen-json` 作为 DLP 手段 | 属病毒扫描，与数据泄漏检测不是一回事；留着会误导 |
| StegExpose.jar 作为主要检测工具 | 项目老旧、依赖 Java 与样本集；改为把"隐写载体外传"作为 DLP 绕过检测点，用 `steghide` 做验证 |
| `39-…/安全策略体系与安全意识-SecurityPolicyAwareness.md` 方向的内容 | 纯治理/培训，与"不做企业治理叙事"的定位冲突 |
| `16-大模型安全-LLMSecurity/skills/LLM数据泄露与隐私保护-DataLeakagePrivacy.md` | 属 LLM 安全另一条线（提示注入/训练数据/模型反演），与本次四主题不重合，避免摊薄 |
| 通用合规流程空话（"建立数据安全治理体系""加强员工意识"等） | 无操作性，交付价值为零 |
| 上游对 GDPL/个保法的概述性描述 | 已有更权威的官方法条文本可核对，只保留可核对的条款号与流程骨架 |

## 3. 非上游补充（本次新增，均已核对来源）

- **法规/标准核对**（用官方或权威公开文本核对，非记忆）：GB/T 43697-2024《数据安全技术 数据分类分级规则》（2024-03-15 发布 / 2024-10-01 实施，三级 + 附录 H/I 分级参考）；《数据安全法》第二十一条（分类分级与重要数据目录）；《网络安全法》2025 年修订（2026-01-01 施行，日志留存六个月现为第二十三条第（三）项，修订前为第二十一条）；《网络数据安全管理条例》第二十九条（重要数据定义）；《个人信息保护法》第六、十三、十四、十五、十六、十七、十九、二十八、二十九、三十、三十一、三十六、三十八、三十九、五十二至五十九条（第 55 条 5 种 PIA 情形、第 56 条报告至少保存三年、第 57 条泄露通知内容均已逐字核对）；PCI DSS v4.0 8.3.6（口令≥12 位，系统不支持时≥8 位）。
- **框架条款**：ISO/IEC 27001:2022 Annex A 具体控制项编号（A.5.15/5.16/5.17/5.19–5.22/5.24–5.28/5.33/5.34、A.6.3、A.8.2/8.5/8.8/8.9/8.10/8.11/8.13/8.15/8.16/8.24/8.28/8.32）；NIST CSF 2.0 六大功能与类别（GV/ID/PR/DE/RS/RC，PR.DS-01/02 等）；SOC 2 TSC（CC1–CC9 + A1/C1/PI1/P1–P8）；PCI DSS 4.0 要求族（3/4/6/7/8/10/11/12）——均标注"需核对现行版本"。
- **命令与工具**：`cvss` PyPI 库（CVSS3/CVSS4 真实调用）；EPSS 官方 API（`api.first.org`，含批量与 `percentile` 字段）；`trufflehog filesystem`、`gitleaks detect --no-git`、`detect-secrets`、`rg -a -u --hidden`（存储面数据发现）；`SSLKEYLOGFILE` + `tshark -o tls.keylog_file`（TLS 后可见性）；`7z a -p… -mhe=on`、`steghide embed`、`curl --doh-url`（DLP 绕过验证）；`auditpol` Removable Storage、Windows 安全事件 6416 / PrintService 307；Macie 官方 JSON 语法、GCP DLP `locations/global` 路径。
- **风险提示**：PostgreSQL Anonymizer 3.1.0 之前 `anon.k_anonymity()` 存在注入类问题（CVE-2026-9617），升级或弃用该函数——"脱敏工具本身也是攻击面"的实例，作为 Pitfall 写入。

## 4. 限制与后续

- 除标注【未验证】者外，参考文件中的命令取自上游原文或官方文档，**未在本机逐条执行**；交付给客户前应在靶场/测试环境跑一遍。
- 等保控制点编号形如 `8.x.y.z` 未逐条对照标准原文，参考文件统一要求写控制项**名称**而非编号；正式报告引用编号前须核对 GB/T 22239-2019 现行版本。
- 个保法/网络安全法/条例的条文号以官方公开文本为准，本次已核对到条级；**修订与配套规定可能变化**，交付前复核。
- 未完成项：上游 14 目录其余 6 个审计卡、22 目录 README 全量内容未整读（与四主题重合度低）；如需扩展"云审计/容器审计"方向可另起一卡，避免本卡膨胀。
