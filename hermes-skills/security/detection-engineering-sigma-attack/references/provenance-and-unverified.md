# REPORT — detection-engineering-sigma-attack

产物：`references/detection-engineering.md`（227 行，中文）｜本文件（REPORT.md）。未生成 SKILL.md（按要求）。

## 栏 A：读了哪些文件（上游）

| # | 文件 | 读法 |
|:--:|:---|:---|
| 1 | `31-SOC运营-SOCOperations/skills/SIEM告警规则与关联分析-SIEMAlertCorrelation.md` | 全文（13,271 chars）+ 分片重读（offset 23 limit 120）+ headings/fences/关键词 grep |
| 2 | `37-端点安全-EndpointSecurity/skills/文件less恶意软件与LOLBins检测-FilelessMalwareLOLBinsDetection.md` | 全文（14,746 chars） |
| 3 | `37-端点安全-EndpointSecurity/skills/EDR部署与检测规则-EDRDeploymentDetectionRules.md` | 全文（12,074 chars） |
| 4 | `28-威胁狩猎-ThreatHunting/skills/Sigma规则检测工程-SigmaRuleEngineering.md` | 全文（8,255 chars） |
| 5 | `28-威胁狩猎-ThreatHunting/skills/ATT&CK威胁狩猎-MITREAttackHunting.md` | 全文（9,686 chars） |
| 6 | `28-威胁狩猎-ThreatHunting/skills/网络流量与日志异常检测-TrafficLogAnomalyDetection.md` | 全文（11,546 chars） |
| 7 | `28-威胁狩猎-ThreatHunting/skills/威胁狩猎方法论-ThreatHuntingMethodology.md` | 全文（7,801 chars） |
| 8 | `38-勒索软件防御-RansomwareDefense/skills/勒索软件攻击链分析与检测-RansomwareAttackChainAnalysisDetection.md` | 局部（offset 280 limit 65 = 2,175 chars；另 grep `shadow/vssadmin/7045`） |
| 9 | `37-端点安全-EndpointSecurity/skills/端点加固与合规基线-EndpointHardeningComplianceBaseline.md` | 仅 grep（`sigma/sysmon/eventid/7045/4104/4688`） |
| 10 | `31-SOC运营-SOCOperations/skills/安全自动化与编排-SOAR-SecurityAutomationOrchestration.md` | 仅 grep（fences + `shuffle/n8n/thehive/cortex/misp/curl/python/api`） |

说明：会话中途发生上下文压缩，上述全文读取的**原文内容已不在上下文内**，本 REPORT 只记录来源、篇幅与用途，不复述原文；本产物中所有引文均以压缩前的读取结论为准，凡不能确证的一律进栏 D。

## 栏 B：原样搬自上游（来源 → 落到产物哪里）

1. 「SIEM 告警规则与关联分析」的**分段/阶段式关联思路**与 Splunk 查询骨架 → 产物 ③ 的趋势类查询（重写为可跑形态）。
2. 同文件的 **KQL 块混写问题**（`process where ...` 是 EQL、`| stats ... | where ...` 是 SPL/ES|QL，注释用 `#`）→ 产物 ③ 末尾的「KQL ≠ EQL ≠ ES|QL」提示（**问题原样引用**，未抄其代码）。
3. 同文件的两处**不可运行片段**：`| eval risk_score=(phase_recon*0.2)+...`（引用不存在字段）、`| search src_ip IN (从阶段2获取的IP列表)`（占位伪码）→ 产物 ③ 3.1 标题行内引用并注明「未收录」。
4. 「文件less 恶意软件与 LOLBins」的 **LOLBins 名单与父进程异常优先**思路 → 产物 ⑤ 表格与优先级结论。
5. 「Sigma 规则检测工程」的 **Sigma 规则字段清单与转换命令骨架** → 产物 ① 必备字段行、② 命令区（命令均经本机 `sigma --help` 复核后写入）。
6. 「ATT&CK 威胁狩猎」的**覆盖度分级口径**（≥70 高 / 30–69 部分 / <30 无）与 `Invoke-AtomicTest <Txxxx> -CheckPrereqs/-Cleanup/-ShowDetails` 参数写法 → 产物 ⑥第 4 条与第 3 条（参数经复核属 AtomicRedTeam PowerShell 模块的正规参数）。
7. 「网络流量与日志异常检测」的**大流量单向外连**思路 → 产物 ③ 3.1 第 4 条（Zeek conn.log，阈值 100MB/1MB）。
8. 「勒索软件攻击链分析与检测」的**卷影副本删除规则**→ 产物 ① 1.3（上游版本含 `status: production`、顺序 UUID 等缺陷，缺陷点原样指出后重写）。
9. 「EDR 部署与检测规则」的**遥测字段/分层**概念 → 产物 ④ 第 6 条与 ⑥ 的数据源优先原则。

## 栏 C：本次补充（全部标【补】）

【补】1. **3 条完整 Sigma 规则**（LSASS EID10 / 可疑 PowerShell / 卷影副本删除）：含 `title/id/status/description/author/date/tags/logsource/detection/falsepositives/level`，经 `sigma check` 实测 **0 errors, 0 condition errors, 0 issues**，并经真实转换产出 Splunk SPL、Lucene、EQL NDJSON。
【补】2. **ATT&CK v19 标签改名实测结论**：`attack.defense-evasion` 与 `attack.defense_evasion` 均报 `InvalidATTACKTagIssue`；TA0005 现名 stealth；`T1562` → `T1685 Disable or Modify Tools`；`T1070.001` → `T1685.005`（用 pySigma 内置 ATT&CK 数据实测，非引用）。
【补】3. **logsource 组合陷阱**：`product + service:sysmon + category` 三者同写触发 `SpecificInsteadOfGenericLogsourceIssue`(HIGH)，正确写法只留 `category + product`。
【补】4. **sigma-cli 实测全量命令与取值**：`-t` 全取值（lucene/eql/esql/elastalert/splunk/splunk_spl2）、`list formats` 取值、`-o/-od/-ot/-P/-s/-e/-j/--disable-pipeline-check` 语义、7 个子命令清单。
【补】5. **`sigma analyze` 真实签名**：`analyze attack {count|max|level} OUTPUT INPUT...`、`analyze logsource OUTPUT INPUT...`、`analyze fields -t <target> INPUT...`；实测 attack 图层 JSON 为 attack 19.2 / navigator 4.8.1 / domain enterprise-attack。
【补】6. **管道能力边界实测**：`-t esql -p ecs_windows` 触发 pipeline-check 拦截（ecs_windows 未注册给 esql），须 `--disable-pipeline-check`；`-p splunk_cim -f data_model` 对 process_creation 产出 `tstats ... from datamodel=Endpoint.Processes`，对 process_access 报 `Rule type not yet supported by the Splunk data model CIM pipeline!`。
【补】7. **实测否决的 8 种错误写法**（`sigma list-backends`、`list formats -t`、`convert -d`、缺管道、`load_directory()`、`SplunkSavedSearchBackend`、`sigma create` 等）。
【补】8. **Sysmon EventID 表**（1/3/6-7/8/10/11/12-14/15/17-18/19-21/22/23/25 + 26）与 4 条配置要点（ProcessAccess 必开、CallTrace 优于 GrantedAccess、ArchiveDirectory/HashAlgorithms、转发丢事件排查）。
【补】9. **LOLBins 检测点表**（12 行）+ 父链检测模板 + 检测点优先级六条（父进程 > 二进制名等）。
【补】10. **误报调优六法与上线硬指标**、**覆盖度三件套判定与分母口径**、AtomicRedTeam 反向验证用法及其仓库拆分说明。
【补】11. **SPL 4 条 / KQL 4 条 / EQL 2 条 / ES|QL 实跑样例**（进程链、编码 PowerShell、服务创建、大流量外连；SPL 含 `coalesce` 双源字段兼容）。

## 栏 D：未验证（共 10 项，不改写在产物中当作已验证）

1. 所有 Splunk SPL / Elastic KQL / EQL 查询**未经真实 Splunk / Elastic 索引执行**（无联通的 SIEM 环境）；字段名依 CIM/ECS 常见映射与 sigma 转换产出推定，上线前必须 `| fieldsummary` 核对。
2. Sysmon 配置元素名（`ProcessAccess`、`ArchiveDirectory`、`HashAlgorithms`、`CheckRevocation`、`DnsLookup`）为配置 XML 既有元素名，未在真实 sysmon 配置上跑 `sysmon64.exe -c --` 逐项核对。
3. ES|QL 样例取自 `sigma convert` 实跑产出，但**未在真实 Kibana 中执行**。
4. `sigma convert -t elastalert` 与 `-t splunk_spl2` 未实跑转换。
5. 上游 AtomicRedTeam 的 `pip install -r requirements.txt`（仓库已拆为 `atomic-red-team` + `invoke-atomicredteam`）未验证、未执行。
6. `Invoke-AtomicTest -Tactics TA0002` 整战术批量执行未实测（且需明确授权）。
7. 上线硬指标阈值（30 天命中 >0 且 <20/天、抽样精确率 <30% 不上线）为经验值，未在任何客户环境标定。
8. LOLBins 表中具体参数形态（如 `/a {REGSVR <路径>}`、`/INJECTRUNNING`、`esentutl /y /vss`）为通用攻防知识，未逐条在目标环境复现。
9. `SigmaCollection` 方法清单来自 `dir()` 自省，未逐个调用验证；`SplunkBackend(processing_pipeline=...)` 仅按签名书写，未在本会话运行。
10. Sysmon 与 SIEM 收量的 >5% 差异阈值为经验判断，未实测。
