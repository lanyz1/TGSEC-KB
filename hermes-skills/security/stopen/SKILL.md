---
name: stopen
description: "Use for automated OODA-loop pentest agent."
version: 1.0.0
---

# Stopen (local) — /root/Stopen

Automated Penetration Testing Agent (swfk2154/Stopen). OODA loop + Blackboard architecture, FastAPI + Web UI.

## Content

| Area | Path | Description |
|---|---|---|
| **Core App** | `stopen/` | FastAPI backend, frontend, models, routes, services |
| **Skills** (8) | `stopen/skills/` | recon, vuln_discovery, exploitation, post_exploit, ctf_web, ctf_crypto, ctf_reverse, report |
| **Tool Services** | `stopen/services/tools/` | crypto_tools, js_discovery, mcp_bridge, scanners, space_search, web_tools, yaml_loader |
| **Routes** | `stopen/routes/` | agent, c2, chat, config, mcp_config, roles, tasks, tools, vulnerabilities, webshell, yaml_tools |
| **C2** | `c2d/` | C2 daemon |
| **Install** | `install.py` | One-click install (pip + storage init) |
| **Frontend** | `stopen/frontend/` | Web UI (dist + src) |

## Architecture

OODA loop (Observe-Orient-Decide-Act) + Blackboard-driven multi-tool integration.

## Usage

```
cd /root/Stopen
python install.py
python run.py
```

## Notes

- FastAPI + Web UI for interactive pentesting
- Blackboard architecture for shared knowledge state
- 8 pentest skills covering full chain
- MCP bridge integration
- C2 daemon for command/control


---

## 外部库增量（2026-10-11 分享包）

## OODA 决策格式补充（源自 Zen-Ai-Pentest，可与 Stopen 互补）

每步循环输出严格 JSON，带自愈字段（比纯 Blackboard 更强的恢复能力）：

```json
{
  "thought": "上次工具输出的总结 + 异常关联",
  "self_correction": "工具失败(NOT_FOUND/TIMEOUT)后的替代方案",
  "plan": "下一步（Recon→Vuln Research→Exploitation）",
  "tool": "工具名", "params": {},
  "priority": "HIGH/MEDIUM/LOW",
  "expected_state": "ANALYZING",   // 成功后预期状态
  "fallback_state": "RECOVERY"     // 失败后回退状态
}
```

状态机：`PLANNING → EXECUTING → ANALYZING(成功) / RECOVERY(失败) → PLANNING`。

四条关键原则（每条都值得写进 agent prompt）：
1. **Soft-404 检测**：目录爆破不信 HTTP 200，比较 `Content-Length`——10 个路径同大小 = soft-404，忽略。状态码与文件大小必须交叉验证（Never trust, always verify）。
2. **Fail fast, recover smart**：工具失败(NOT_FOUND/TIMEOUT)立即换替代工具（masscan 代替 nmap、subfinder 代替 amass），不卡死在单点。
3. **State is sacred**：agent 永远知道自己在哪个状态，每个决策都带 expected_state + fallback_state。
4. **低垂果实优先**：发现 `/api/`、`/login` 端点立刻优先上 sqlmap；端口关闭就不在该端口浪费爆破时间。

## PoC 验证沙箱（工程化漏洞验证，源自 Zen-Ai-Pentest）

漏洞命中后要「验证可利用性」而不是只报告。三件套流程：
1. **payload 生成**：按漏洞类型（SQLi error/union/time/boolean、命令注入、路径穿越、XXE、SSRF）生成定制 payload。
2. **沙箱执行**：Docker 容器隔离 + 资源限制 + 网络隔离（禁私网出站）+ 只读文件系统 + tmpfs 输出 + 自动清理。风险分级 0-3（passive→aggressive，≥3 需 --force）。
3. **成功验证**：SQLi 看版本提取/表枚举、RCE 看命令回显、认证绕过看 session 令牌、外泄看敏感数据模式。

Guardrails 必带：私网 IP 阻断(RFC1918)、内部域名阻断(localhost/.internal/.local/.corp)、危险命令 sanitize(rm -rf /、mkfs、dd if=/dev/zero、fork bomb)、超时/内存/CPU 上限、SMB 端口(135/139/445)默认封。

## 参考

- Zen-Ai-Pentest: https://github.com/SHAdd0WTAka/Zen-Ai-Pentest （97 skills + 72 tools + 多 agent，payload 库为基础款，web-sec 技能库已覆盖更深）

## 工具 fallback 矩阵 + 错误分类自愈（源自 Zen-Ai-Pentest recovery_engine）

自主渗透 agent 的工具挂了怎么自愈，按错误类型分类处理：

**工具 fallback 矩阵**（A 工具挂/没装 → B 工具）：
```
gobuster→dirb    nmap→masscan    masscan→naabu    ffuf→gobuster
sqlmap→(python sqlmap API)    amass→subfinder    subfinder→assetfinder
nikto→nuclei    burpsuite→zap
```

**错误分类 → 应对**（按 stderr 关键词路由）：
- `command not found` / `not found` → 切 fallback 工具
- `timeout` / `timed out` → 重试 + `--delay` 或切代理
- `permission denied` → 提权（sudo / 检查 capabilities）
- `connection refused` / `reset` → 走 proxychains / VPN
- 其它未知错误 → 把 error+correction+failure_count 回传 LLM 重新规划（replan）

**放弃阈值**：同一工具 `failure_count >= 3` 即放弃，不再重试。

## 11 个专业化 agent 划分（多 agent 渗透编排模板）

Zen-Ai-Pentest 的 coordinator 把渗透拆成 11 个 agent，每个绑定专属工具集，可直接照抄：

| Agent | Persona | 工具集 |
|---|---|---|
| reconnaissance | OSINT/子域/端口 | subfinder, amass, nmap, masscan, whatweb, wafw00f, dig, dnsx, httpx |
| exploitation | 漏洞利用+沙箱 | metasploit, searchsploit, nuclei, sqlmap, hydra |
| analysis | 误报检测+评分 | nmap_parser, vuln_analyze, **cvss_calc, epss_lookup** |
| reporting | 报告 | generate_pdf/html/docx, executive_summary |
| red_team | 红队全流程 | c2_framework, pivot, lateral_move, persistence, exfil |
| social_eng | 钓鱼/社工 | gophish, social_osint, phish_template, tracking |
| network | 网络基础设施 | nmap, masscan, smb_map, snmp_walk, traceroute |
| cloud | 云安全 | aws_scout, azure_enum, gcp_enum, cloudsploit, pacu |
| ics | 工控 SCADA | modbus_scan, s7_enum, dnp3_scan, bacnet_scan |
| mobile | 移动端 | mobsf, apktool, jadx, objection, frida |
| crypto | 加密分析 | ssl_scan, tls_analyze, cert_check, cipher_test |

**要点**：
- 评分用 **EPSS**（Exploit Prediction Scoring System）而非纯 CVSS——EPSS 反映"实际被利用概率"，比 CVSS 更能指导修复优先级。
- 状态机：`IDLE → PLANNING → EXECUTING → OBSERVING → REFLECTING → COMPLETED`，多 agent 之间用 `previous_results` 传上下文。
- PTES 六阶段：Pre-Engagement → Recon → Scanning → Exploitation → Post-Exploitation → Reporting，12 工具分类。
