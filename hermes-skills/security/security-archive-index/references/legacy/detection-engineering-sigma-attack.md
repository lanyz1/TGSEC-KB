<!-- archived from /root/.hermes/skills/security/detection-engineering-sigma-attack/SKILL.md on 2026-10-21 -->

---
name: detection-engineering-sigma-attack
description: "Use when 写检测规则/狩猎:Sigma、Splunk SPL、ATT&CK映射、紫队。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/detection-engineering-sigma-attack`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/detection-engineering-sigma-attack/…')`，不要相对 `references/legacy/` 解析。

# 检测工程 · Sigma / SIEM 规则 / ATT&CK 紫队

蓝队面：把攻击行为翻译成可上线规则，再用原子化对抗验证覆盖度。反向的「未采集即免检面」见 `references/attack-view-reuse.md`（授权靶场用）。

## 触发场景
- 写 Sigma 规则，或转 Splunk SPL / Lucene / EQL / ES|QL
- 评估检测覆盖度、找缺口、做紫队演练（Atomic Red Team / Caldera）
- IR 后发现「日志里有痕迹但没告警」→ 补规则
- Sysmon 配置、LOLBins 检测点、告警误报调优

## 工作流
1. **先盘数据源**：确认哪些事件源在采集（Sysmon EventID、4688 命令行审计、云审计、EDR 遥测）。未采集=检测不到，这一步决定后续所有结论；把「假设已采」当事实是最常见的翻车点。
2. **Sigma 作为单一事实源**：`sigma check` 验规则正确性 → `sigma convert -t <backend>` 出各 SIEM 原生查询。一套规则多后端，不手写四份。
3. **上线前压误报**：父链/签名/路径白名单 + 阈值；用真实环境 7 天历史回放估告警量再上。
4. **验证**：Atomic Red Team 打原子 → 看是否触发；未触发即记为缺口（记录技术号 + 缺失的数据源）。
5. **覆盖度台账**：ATT&CK Navigator 图层标 0–3 级，缺口按「技术影响面 × 数据源可获得性」排序。
6. **回归**：规则留 id/status（stable/test/experimental），不直接覆盖线上规则。

## 命令速查
```bash
pipx install sigma-cli && sigma plugin install splunk elasticsearch   # 实测 sigma-cli 3.1.0
sigma check rule.yml                 # 必须 0 errors / 0 condition errors / 0 issues
sigma convert -t splunk rule.yml     # -t 还可取 lucene / eql / esql / siem_rule_ndjson
sigma convert -t esql -p ecs_windows --disable-pipeline-check rule.yml  # esql 会被 pipeline-check 拦
sigma list formats ; sigma plugin list
sigma analyze attack {count|max|level} OUTPUT INPUT...   # 子命令签名以此为准
```
```splunk
# 进程链：Office 类拉子进程
index=windows EventCode IN (1,4688)
| eval proc=lower(coalesce(Image,New_Process_Name)), parent=lower(coalesce(ParentImage,Creator_Process_Name))
| where match(parent,"(winword|excel|outlook|powerpnt)\\.exe$") AND match(proc,"(powershell|pwsh|cmd|wscript|cscript|mshta|rundll32|regsvr32|bitsadmin|certutil)\\.exe$")
| stats count values(CommandLine) as cmdline by host,User,parent,proc | sort - count
# 大流量外连：出站远大于入站（外传信号）
index=zeek sourcetype="bro:conn:json"
| stats sum(orig_bytes) as out_b sum(resp_bytes) as in_b dc(dst_port) as port_cnt by src_ip,dst_ip
| where out_b > 104857600 AND in_b < 1048576
| eval ratio=round(out_b/(in_b+1),1) | table src_ip,dst_ip,ratio,port_cnt | sort - out_b
```
```powershell
Install-Module invoke-atomicredteam -Scope CurrentUser
Invoke-AtomicTest T1059.001 -ShowDetailsBrief ; Invoke-AtomicTest T1059.001 -TestNumbers 1 -CheckPrereqs
Invoke-AtomicTest T1059.001 -TestNumbers 1            # 打完回 SIEM 看有没有告警
Invoke-AtomicTest T1059.001 -Cleanup                 # 清理痕迹，便于下一轮
# 原子清单路径参数是 -PathToAtomicsFolder（上游写作 -Path，错）
```
Caldera：仓库已迁至 **apache/caldera**（旧 mitre/caldera 地址过期）：`git clone https://github.com/apache/caldera && pip install -r requirements.txt && python3 server.py --insecure --build`；agent one-liner 以服务器 UI 生成为准（不手抄）。

## Pitfalls
- **ATT&CK 已重编号**：T1562 → **T1685**（含 .001/.002/.003/.005）、T1070.001 → T1685.005，战术 TA0005 更名 Stealth，新增 TA0112 Defense Impairment（v19.2 实测）。不核对就直接整表错位；旧号仅作迁移对照。
- **未采集＝检测不到**：Sysmon 3（网络连接）、22（DNS）官方默认关闭；没开事件源却宣称有覆盖是假结论。写下规则前先回查数据源是否真在收。
- `sigma convert` 不给 `-p` 管线时字段名可能与你的 ECS/字段命名不符；转换后必须在目标 SIEM 里先跑一条 `| fieldsummary` 核字段名。
- **上游伪码不要收录**：上游 SPL 里引用不存在字段、占位式取 IP 的写法不可直接跑；本卡只收可执行语句。
- 规则上线前做历史回放估告警量；无白名单的泛化规则（如所有 `certutil`）在真实环境会被噪声淹没。
- 纯脚本类检测仅靠命令行字符串会被绕（大小写、环境变量拼接、Base64 分段）：关键行为要用父链 + 签名 + 网络三要素关联。

## 参考文件
- `references/detection-engineering.md`：3 条完整 Sigma YAML（LSASS EID10 / 可疑 PowerShell / 卷影副本删除，均 `sigma check` 0 errors 实测）、sigma-cli 与 pysigma 全命令（含 8 种实测否决的错写法）、SPL/KQL/EQL/ES|QL 真查询、Sysmon 15 行 EventID 表、LOLBins 清单与优先级、调优与覆盖度评估。
- `references/attck-purple-hunting.md`：23 行 ATT&CK→数据源映射表、狩猎假设四来源与查询、Atomic Red Team/Caldera 实操、Navigator v4.5 图层 JSON、覆盖度 0–3 级评估与补测优先级。
- `references/attack-view-reuse.md`：反向复用清单（默认未采集=免检面、日志投递断裂点、阈值绕过、探面顺序）——仅限授权靶场验证。
- `references/provenance-and-unverified.md`：来源核对（哪些命令搬自上游 / 哪些是补充 / 未验证清单）。
