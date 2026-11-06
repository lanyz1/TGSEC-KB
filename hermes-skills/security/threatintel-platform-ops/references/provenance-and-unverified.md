# REPORT：threatintel-platform-ops 抽取报告

上游根：`D:/skills4redteam/HiFullHouse-CyberSecurity-Skills/`。产出目录：`D:/skills4redteam/out/threatintel-platform-ops/`。
本卡定位：**只写本库没有的三块**——① 情报平台工程（MISP/OpenCTI/TheHive/TAXII/STIX/IOC 生命周期）② 情报驱动狩猎的数据模型与搜索 ③ IR/SOC 响应平台化（分级/SOAR/复盘/证据链）。磁盘内存取证方法论不重复，改为交叉引用 `digital-forensics`、`traffic-analysis-pcap`、`host-ir-check`、`incident-response`。

## 一、读了哪些文件

| 文件 | 角色 |
|:---|:---|
| `29-威胁情报/skills/MISP部署与威胁情报共享-MISPDeploymentIntelSharing.md` | 主源：MISP 部署、共享、API |
| `29-威胁情报/skills/威胁情报馈入与TAXII-STIX管理-ThreatIntelFeedsTAXIISTIX.md` | 主源：TAXII/STIX 馈入、IOC 管理 |
| `29-威胁情报/skills/APT组织分析与归因-APTGroupAnalysisAttribution.md` | 主源：归因三层证据模型 |
| `29-威胁情报/skills/威胁情报驱动安全运营-ThreatIntelDrivenSOC.md` | 主源：情报驱动 SOC 流程与指标 |
| `28-威胁狩猎/skills/威胁狩猎方法论-ThreatHuntingMethodology.md`(28-001) | 主源：假设四来源、PDCA、SPL/Elastic 查询、HMM、KPI |
| `28-威胁狩猎/skills/网络流量与日志异常检测-TrafficLogAnomalyDetection.md`(28-004) | 主源：DNS 隧道熵检测、Beaconing CV、Suricata/Zeek/tcpdump |
| `31-SOC运营/skills/SOC事件分级与响应流程-SOCTriageResponse.md`(31-002) | 主源：L1–L4 分级、三级流程、Playbook、复盘 |
| `31-SOC运营/skills/安全自动化与编排-SOAR-SecurityAutomationOrchestration.md`(31-003) | 主源：SOAR 工作流与集成、KPI |
| `15-应急响应/skills/事件复盘与报告-LessonsLearnedReporting.md`(15-004) | 主源：复盘报告骨架、5-Why、度量指标 |
| `15-应急响应/skills/事件分类与优先级评估-IncidentTriage.md`、`事件遏制与清除`、`日志收集与分析`、`云环境应急响应`、`AI安全应急响应`、`网络流量分析`（清单已列，按其主题取用/丢弃） | 次级 |
| `30-数字取证/skills/磁盘镜像与证据获取-DiskImagingEvidenceAcquisition.md`(30-001，只读证据链/哈希/时间线片段) | 只取 CoC 与哈希校验片段 |
| `30-数字取证/skills/` 其余 4 个（Linux/Windows 取证、内存 Volatility、浏览器邮件取证） | **只检索未细读**：属本库已有卡覆盖范围，明确不重复 |

## 二、逐条：吸收 / 丢弃

### 吸收（进 references/threatintel-platform.md）

| 条目 | 理由 |
|:---|:---|
| MISP Docker 部署流程与 `.env` 关键项、`<EMAIL-REDACTED>/admin` 初值、MISP-Guard 防误共享 | 上游有，且与官方仓库 README 实测一致；平台工程必需 |
| MISP 共享/分发概念（sharing group、TLP） | 情报生命周期"分发"环节的落地条件 |
| PyMISP 用法（建 event/属性、freetext 抽 IOC、feed 管理、tag/object） | 上游思路 + **本卡按 2.5.34.4 实测签名改写**，修正了错误的构造方式 |
| TAXII/STIX 馈入概念与流程 | 上游给流程，命令按 taxii2-client 实测重写 |
| APT 归因三层证据（技术/运营/战略）+ 输出物清单 | 上游最有价值的方法部分，保留 |
| 情报质量指标（IOC 时效、命中率、误报率、alert→block 时长） | 上游 KPI 名保留，补充了覆盖率/富化率/退役卫生 |
| IOC 生命周期六阶段框架 | 上游框架保留，落地命令与去重规则由本卡补 |

### 吸收（进 references/ir-hunting-platform.md）

| 条目 | 理由 |
|:---|:---|
| 假设四来源 + 假设文档字段 + PDCA 四阶段 | 28-001 核心方法论，直接可用 |
| Splunk SPL 两条（异常 RDP、同源多账号）、Elastic `_search` DSL | 保留原查询并标注字段映射风险 |
| HMM 0–4、狩猎 KPI、狩猎报告表结构 | 度量与交付物，可直接落表 |
| DNS 隧道熵检测算法与阈值表 | 算法保留；阈值标注为经验值；修正了 pandas 读 TSV 与列名错误 |
| Beaconing CV 法（`CV<0.5/<0.3`，样本≥5） | 保留算法，补假阳性来源与分组键要求 |
| Zeek/tcpdump/RITA 命令 | 保留并修正（zeek 脚本名、awk 取列错误），补 RITA 实测 CLI |
| SOC L1–L4 分级表与响应时限、评分启发式、三级流程、Playbook 分阶段动作 | 31-002 主体，平台化必需 |
| SOAR 六步剧本、集成清单、运营 KPI | 31-003 骨架保留，stub 全部替换为真实端点 |
| 复盘七节骨架、时间线表、5-Why、改进措施 DDL、度量指标、复盘议程、三层问题清单 | 15-004 主体，流程化交付物 |
| 证据保管链字段、`sha256sum -c`、`dcfldd hashlog`、`ewfinfo`、写保护确认 | 30-001 只取证据链/哈希片段，取证方法论不搬 |

### 丢弃（附理由）

| 丢弃项 | 理由 |
|:---|:---|
| 上游各类模拟类（`APTProfile`、`AttributionAnalysis`、`ROARWorkflow`、`SOARIntegration` 的注释桩、`IncidentHandler/IncidentSeverity/IncidentReporter` 全套 Python 类） | 是教学脚手架，非可运行交付；逻辑已提炼成表与流程，代码删掉 |
| 31-003 中假 Slack webhook、假 VT 返回值（`12/72`）、`("admin","password")` 基础认证 | 编造/占位值，违反"禁编造"铁律 |
| 28-004 的 `BaselineAnomalyDetector` 基线类 | 又是一层教学封装，z-score>3 的判据已在正文一句话说明 |
| 30-001 的 dd/FTK/guymager 全量镜像操作、文件系统分析（mmls/fls/icat/istat）、镜像格式转换细节 | 属取证方法论，本库 `digital-forensics` 已覆盖 |
| 30-002/003/004/005（Windows/Linux/内存/浏览器邮件取证） | 同上，本库已有独立卡 |
| 15-005 遏制与清除、15-006 云应急、15-007 AI 应急的通用流程 | 与本卡平台化主题重叠度低，且流程层本库 `incident-response` 已覆盖 |
| MalwareBazaar"匿名可用"、PassiveTotal API、`docker run thehiveproject/thehive:latest` | 已失效/改名，**实测证伪**后改为失效提示 |
| Slack/邮件通知等无关集成、Confluence/Miro/Lucidchart 工具表 | 与平台工程无关 |

## 三、哪些来自上游、哪些是补充

- **来自上游**：MISP 部署与共享、TAXII/STIX 流程、归因方法与指标名、假设四来源与 PDCA、SPL/Elastic 查询、熵与 CV 检测算法、Zeek/Suricata 规则、SOC 分级与三级流程、SOAR 剧本骨架与 KPI、复盘骨架/5-Why/DDL/度量、CoC 字段与哈希命令。
- **本卡补充**（文中已逐处标【补充】）：MISP/MalwareBazaar/OTX/AbuseIPDB 源状态与鉴权变化、IOC 归一化与去重实现、退役 TTL 与"退役不删=永久误报"、VT v3 端点与 `x-apikey`、OpenCTI XTM One 变化、TheHive 5 实测 API 路径与平台化落点、RITA CLI、Elastic 找"等间隔"的聚合写法、自动化响应五条纪律（可逆/幂等/限速熔断/审计/演练）、时间线工程五条、Mermaid 时间线、取证交叉引用。

## 四、核验状态（区分 实测 / 上游 / 未验证）

**实测（本机跑通或核对到真实返回/源码）**

- `pymisp 2.5.34.4`、`stix2 3.0.2`、`taxii2-client 2.3.0`、`thehive4py 2.1.0` 安装成功；PyMISP/MISPEvent/MISPAttribute/MISPObject 行为实跑（含 `MISPAttribute(type=...)` 抛 TypeError 的反例）。
- MITRE ATT&CK TAXII 2.1：discovery 200（`api_roots=/api/v21`）、collections 200（3 个，含真实 collection id）、`Server→api_roots[0].collections→get_objects(limit=50)` 返回 `{'more':True,'objects':[...]}`，抽样 50 条类型分布 campaign 35/course-of-action 14/x-mitre-collection 1。
- thehive4py 2.1.0 源码中 104 条 `/api/v1/...` 路径（含 case/observable/task/timeline/alert→case/query）。
- 情报源状态码：feodo txt 200、ThreatFox export 200、URLhaus csv_recent 200（含真实字段）、ipsum 200、OpenPhish 302、OTX 403、AbuseIPDB 401、MalwareBazaar 假 Auth-Key→403 `unknown_auth_key`、VT 无 key→401 `X-Apikey header is missing`（`files/ip_addresses/domains/comments` 均为 401，错误路径 404）。
- 仓库与文件：`MISP/misp-docker`(master, 394★) 的 `template.env`/`docker-compose.yml` 存在；`OpenCTI-Platform/docker` 的 `.env.sample`/`docker-compose.yml` 存在；`Shuffle/Shuffle` 的 `docker-compose.yml` + `.github/install-guide.md` 存在（`docker compose up -d`、UI :3001/:3443、REST :5001、`ghcr.io/shuffle/*`）；`MISP/misp-docker` main 分支 404（默认分支非 main）；`TheHive-Project/TheHive` 已 archived。
- `rita import --database=... --logs=...`、`rita view --stdout ...`（README）。

**上游（未复测）**：MISP 登录初值与 Guard 配置文本、SPL/Elastic 查询、熵/CV 阈值、SOC 分级时限与评分权重、SOAR KPI 手工基线、复盘度量"行业基准"列、CoC 字段。

**未验证（已显式标注）**：MISP REST `Authorization` 头在真实服务器上的行为；TheHive/Cortex/MISP 三方联动端到端；Elastic `_search` 字段映射与 EQL 语法差异；Suricata `dns.resp_len` 与替代写法；`zeek-dga` 插件；Elastic beaconing 聚合写法；PassiveTotal→MDTI 的现行 API；Malpedia API 细节；Anomali Limo/OpenCTI TAXII 端点可达性。

## 五、交付物与边界检查

| 文件 | 行数 | 约束 |
|:---|:---|:---|
| `references/threatintel-platform.md` | 205 | ≤220 ✓ |
| `references/ir-hunting-platform.md` | 178 | ≤180 ✓ |
| `DRAFT-SKILL.md` | 86 行（正文 63 行非空） | ≤120 ✓；frontmatter 仅 name/description ✓；description 首 57 字符含触发（"威胁情报平台工程/情报驱动狩猎时用:MISP、OpenCTI、TheHive、TAXII/STIX 采集、IOC"）✓ |
| `REPORT.md` | 本文件 | — |

**未做**：未修改上游仓库任何文件；未创建 Hermes 技能（仅交付草案，落库由父任务决定）；未使用任何真实凭据（所有 key 均为占位符）。

**已知缺口**：TheHive/Cortex 的真实联调、Cortex analyzer 的 API 细节、OpenCTI connector 的具体配置项未实测，标注在文中；上游 31-003 的 Splunk 搜索 API 用法（`/services/search/jobs` + 基础认证）未复测，按上游保留。
