---
title: "1day与Nuclei作业手册.md"
generated: 2026-10-21
kind: consolidated-playbook
note: 由现役技能卡自动汇总；保留原卡语义，未改写攻防步骤
---

# 1day与Nuclei作业手册.md

> 本页由引用该路径的现役技能卡汇总生成。原始内容与完整步骤见下方来源卡；不要把它当成独立的新打法。

## 来源卡

- `/root/.hermes/skills/security/1day-nuclei-kit/SKILL.md`

## 汇总内容

### 1day-nuclei-kit

来源：`/root/.hermes/skills/security/1day-nuclei-kit/SKILL.md`

# 1day / Nuclei 作业（Cursor Skill）

<!-- MERGED-INDEX:START -->
## 归档子卡（已合并 23 张）

- 索引：`references/index.md`
- 加载：`skill_view(name='1day-nuclei-kit', file_path='references/legacy/<name>.md')`
- 子卡脚本/字典仍在原目录（索引里给了绝对路径），可直接 `read_file` / `terminal`。
- **先按本卡判据决策**；本卡不够时才展开对应子卡，不要一次全读。
<!-- MERGED-INDEX:END -->

> **本机核验（2026-10-21）**：旧文里的 `tools/1day-kit/od_kit.py`、`docs/playbooks/*` 在当前仓**不存在**，别按空路径跑。  
> `vuln_find "CVE/产品"` 先定位真实 PoC；nuclei 已装 **v3.11.1 + 13,619 模板**（在 `/usr/local/bin/nuclei`），缺别的工具用 `tool_get <name>` 现场补。


## 何时用

- 指纹明确、要快速过已知 CVE/misconfig
- 需要查本地 `exploitarium` 研究型 PoC 是否相关
- 跟 [cvebase.io](https://cvebase.io/) 近期 KEV / 在野洞补手法
- Tsecbench / 靶场「漏洞利用」类题的默认入口之一

## 真源（按序）

1. `tools/1day-kit/od_kit.py`（`learn` / `explain` / `nuclei`）
2. **`docs/playbooks/Nuclei引擎学习手册.md`**（官方 v3 YAML + 本库三层；先学这个）
3. `docs/playbooks/1day与Nuclei作业手册.md`（短作业清单）
4. `docs/playbooks/1day在野洞情报手法.md` · **`CVE情报日报手法.md`** · 当日 `CVE日报-YYYY-MM-DD.md` · `docs/intel/cve-daily/*.json`
5. `docs/playbooks/打网站手法.md` · 同目录各栈手法卡（Metabase/UpSnap/MRBS/Grafana/Jenkins/XXL-JOB 等）
6. `poc-db/exploitarium/`（研究 PoC，非自动扫）
7. 广谱发现可并行 `pentest-swarm`；出洞后交专用 Skill
8. `references/77169-intel-2026q3.md`（**77169/华盟 2026Q3 新CVE弹药清单**：A级未认证RCE/SQLi、B级LPE、C级边界、D级移动端、E级手法、F级工具；抽查8个CVE已NVD核验）
9. `references/77169-intel-2026q3-full.md`（**151条全量高价值索引**：110个CVE、代码块/PoC/GitHub计数 + 摘要 + 原文链接；已剔新闻与汽车安全系列）
10. `references/77169-full-site-cve-index.md`（**全站500个CVE总索引**：2016-2026全部技术类文章去重，含标题/原文链接/文章数；429个为新增未吸收编号）
11. `references/2026-10-cve-poc-repos.md`（**2026-10-16~19 PoC 仓库核验**：4条真新增 + 4条旧洞纠错 + 公开索引源；NVD/GitHub created_at 双核验，只链接不贴步骤）
12. `references/abraxas-0day-index-2026-10.md`（**abraxas 0day 工厂索引**：2026-10-11~18 共 152 个仓库/26 产品族，pfSense 53、OpenMeetings 12、Spark 9、OPNsense 7、Jellyfin 4；**未分配 CVE 的自研 0day，版本为作者测试版本**，只记攻击面原语）

## 强制步骤

1. 目标在 scope（情报查询可无目标；扫站必须有）。
2. `python3 tools/1day-kit/od_kit.py doctor`（缺二进制：`bash scripts/install-arsenal-macos.sh`）
3. 要学引擎/YAML：`od_kit.py learn` · `explain --id <模板>` · 手册 `Nuclei引擎学习手册.md`
4. 模板空：`od_kit.py update-templates`（写入 `tools/1day-kit/nuclei-templates/`）
5. 情报（可选）：`od_kit.py cvebase trending` / `lookup --cve CVE-… --docs`
6. 扫：先 `nday_route.py`，再  
 `od_kit.py nuclei --url <URL> --case <案卷> --custom-only`  
 或 `-t tools/1day-kit/custom-templates/<id>.yaml`（与手法卡同一写法）。  
 然后才 `--tags cve,rce`。hits 里的专卡优先于广谱 nuclei。
7. 本地 PoC：`od_kit.py search --q <组件>` → `show --id <目录名>`
8. 证据：`exports/bot-recovery/<案卷>/测绘/1day/`

## cvebase 快捷

```bash
export CVEBASE_API_KEY="cvb_..." # 可选；否则匿名约 10/日
python3 tools/1day-kit/od_kit.py cvebase trending
python3 tools/1day-kit/od_kit.py cvebase lookup --cve CVE-2026-72898 --docs
```

业务站栈（Metabase/UpSnap/MRBS/Grafana/Jenkins/XXL-JOB/Jeecg/Shiro/Druid/ThinkPHP/宝塔PMA/用友致远/WP/Laravel…）：见 `打网站手法.md` + 对应手法卡 + `custom-templates/` 
「今天新 CVE」完整落盘：切 Skill **`cve-daily-intel`**（JSON+日报+P0 专卡+Skill），禁止只口头汇总。 
UpSnap → `upsnap-unauth-rce`；MRBS → `mrbs-ssrf`；GeoServer → `geoserver-jsonarraycontains-sqli`；FreePBX → `freepbx-unauth-rce`；WP 插件 8/15 窗 ATO/假付 → `wordpress-plugin-unauth-takeover`；Ray Dashboard → `ray-dashboard-unauth`；GitLab GraphQL → `gitlab-graphql-unauth`；**Gitea / diffpatch / CVE-2026-60004** → `gitea-diffpatch-rce`；MLflow webhook → `mlflow-ssrf-webhook`；Zimbra SNMP → `zimbra-snmp-rce`；ICEcoder → `icecoder-unauth-rce`；JetEngine → `jetengine-unauth-rce`；Ollama → `ollama-unauth`；Langflow → `langflow-unauth-rce`；Flowise → `flowise-internal-header-rce`；CVE-2024-4577 → `php-cgi-cve-2024-4577`；xmlrpc.php → `wordpress-xmlrpc-surface`；信任头 → `trusted-ip-header`；开放重定向 → `open-redirect-chain`；**Oracle WebLogic Proxy / CVE-2026-21962** → 指纹模板 `weblogic-proxy-cve-2026-21962.yaml`。HITCON 学洞 → `hitcon-zeroday-intel`。 
Java 面一条分流：`python3 tools/ops/java_web_surface_probe.py -u <授权站> --case <案卷>` 
设备/边缘（LoadMaster/Tomcat集群/VeloCloud/PAN…）：情报可留，网站案默认降权

## 不要做

- 未授权扫网段 / 未授权 dump
- 把完整 nuclei-templates 硬 clone 进 `tools/vendor`
- 命中业务指纹后仍只跑 nuclei 结案（Actuator/支付等要切专用链）
- 把 cvebase 匿名配额浪费在无目的广搜上

---

<!-- 补充视角: vuln-scanner (兄弟技能库 2026-09-12) -->


# Vulnerability Scanner Workflow

Auto-chain without confirmation:

Phase 1 — Enumerate:
  `skills/network-pentest/scripts/port_scanner.py` → all open ports
  `skills/network-pentest/scripts/service_enum.py` → service versions

Phase 2 — CVE Match:
  Cross-reference service versions against known CVEs.
  Prioritize: RCE > privilege escalation > information disclosure.

Phase 3 — Exploit match:
  `skills/exploit-dev/scripts/shellcode_gen.py` → for

…（截断，全文见来源卡）
