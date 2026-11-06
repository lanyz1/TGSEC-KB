---
name: arsenal-router
description: >-
  任何渗透/安全任务开工或换阶段先查全库 2,173 张技能卡、0day/CVE/PoC 漏洞库与 TGSEC 整仓：
  按目标指纹、症状、阶段检索，返回精确的 skill_view / read_file / run 命令。
  触发：军械库、技能检索、漏洞库、CVE、PoC、有没有打法、以前打过、找技能、skill_find、vuln_find、repo_find、换阶段。
tags: [arsenal, router, skills, retrieval, pentest]
---

# Arsenal Router — 全库军械检索

## 为什么要有这张卡

吸收 ≠ 能用。技能库里 **2,173 张卡**，其中 **1,799 张已归档禁用**；它们不在常驻索引里，但全文、脚本、字典、模板只有真正导入的才在——**启用面 114/123（缺 9 个，含 `se_inject`），归档面仍有 106 个 `tools/ops` 名无文件**。
**不要凭记忆重写打法，也不要因为常驻索引里没有就认为没卡。** 先检索，再加载，再执行。

## 一条命令

```bash
python3 /root/.hermes/arsenal/skill_find.py "<目标栈/产品/症状>" --top 8
```

开局不知道先打哪面时，一次拉全阶段候选（每阶段 Top 3）：

```bash
for p in recon auth injection file ad cloud mobile cms api gambling ai reverse cve tools report; do
  echo "===== $p ====="
  python3 /root/.hermes/arsenal/skill_find.py "<目标栈/产品/症状>" --phase "$p" --top 3
done
```

可选：

```bash
--phase recon|auth|injection|file|ad|cloud|mobile|cms|java|php|api|gambling|ai|reverse|cve|tools|report
--deep        # 默认已开：扫候选卡全文
--fast        # 只查名称/描述/标题/摘要，最快
--enabled-only
--json
```

输出每张卡都带 **状态 + 分数 + 命中字段 + 加载命令**：

- `[E]` 启用卡：`skill_view(name='<卡名>')`
- `[D]` 归档卡：`skill_view(name='<目录卡>', file_path='references/legacy/<卡名>.md')`

**直接照 `load:` 行执行**，不要自己拼路径。归档卡读完若需要脚本/字典，按卡内 `原目录` 或 `Formerly` 回原路径取。  
若 `skill_view` 返回 `[SKILL_PRUNED]` 或被压缩，用 `--json` 输出里的 `body_path` 直接 `read_file`。

## 漏洞库 / PoC 另查（CVE、产品版本）

技能卡告诉你“怎么打”，漏洞库告诉你“哪个 PoC 在哪、脚本叫什么”。**CVE/产品/版本命中时，skill_find 和 vuln_find 都要跑。**

```bash
vuln_find "CVE-2026-87902"
vuln_find "WordPress 87902"
vuln_find "nginx ignition" --top 8
vuln_find "1Panel 未授权"
```

输出带：

- `[POC]` 真实的 `CVE-*/exploit/*.py` 目录 + `run:` 命令 + `read:` README/analysis；
- `[CARD]` 技能库里的 CVE 卡（含归档 legacy）；
- `[IDX]` 1day/0day 索引里命中但未落 PoC 的条目。

覆盖：`/root/TGSEC-Qtzuu/domains/0day-exploits`（135MB / 13,686 文件 / 960 个产品-CVE 目录 / 1,189 个 py / 814 张 by-cve 卡）、`1day-nuclei-kit` 的 CVE 索引、本机 `p2s`/`php2shell`/`cve-2026-87902-poc` 等 PoC 仓。  
**先读 README/analysis 的前置条件再执行，PoC 不是通用 RCE。**

整仓知识（不止 0day）走 TGSEC 自带路由：`/root/TGSEC-Qtzuu/AGENTS.md` → `ROUTING.md` → `MASTER.md` → `domains/<面>/`；`arsenal-router` 只负责把技能卡和漏洞库拉出来，不替代 TGSEC 的 24 域导航。

```bash
repo_find "支付 回调"          # 整仓 6,265 条：ROUTING 信号 + 25 域 README + case/playbook 文档
repo_find "API 越权 BOLA"
repo_find "ADCS ESC1"
```

`[ROUTE]` 是 ROUTING.md 的关键词行，直接给你 2–6 个 `read_file` 路径；`[DOMAIN]` 是域 README；`[DOC]` 是具体案例/playbook。

## 工具缺口：现场装，不写死

渗透中缺什么装什么，不要把“没装”当结论：

```bash
tool_get --check          # 看缺什么
tool_get nuclei           # 装/验证单个（apt / gem / GitHub release）
tool_get --all            # 补核心六件套：nmap sqlmap ffuf whatweb wpscan nuclei
```

装完必须 `command -v` / `--version` 验证，并记 `/root/.hermes/arsenal/tool_install.log`。当前核心六件套全在线；nuclei **v3.11.1 + 13,619 模板**。  
nuclei 离线/本地靶场默认会等 interactsh 和更新检查，先加 `-ni -duc`；需要 OOB 再去掉 `-ni`。

## 闭环边界（别把检索当作战）

- **检索层**：2,173 卡 + 8,055 漏洞/PoC 入口 + 6,265 整仓文档，已闭环。
- **工具层**：`tool_get` 现场补，已闭环。
- **执行层**：完整 231 个历史 `tools/ops` 已补 **125 个真实 ops 名**（`kit_run` + 路由/探针 + 高频补链 + 兼容入口 + 28 个直达 symlink）+ 29 个标准库脚本 + 已装二进制。全库引用覆盖率 **1,264/1,539 = 82.1%**；**启用卡 114/123 名、227/241 引用 = 94.2%**，9 个缺失。
- **当前门禁**：`python3 tools/ops/coverage_gate.py --active --strict` → **exit 1**（9 个启用面缺口）；`--strict` 全库也 exit 1，因为 106 个 disabled/legacy 名字未补。
- **案卷/报告**：`case_ledger.py` + `case_report.py` + `evidence_gate.py` + `object_matrix.py` + `scope_lint.py`，本地 E2E 已跑通（gate PASS + REPORT.md）。
- **未闭环**：**106 个归档面专用 ops + 9 个启用面缺口** 没有逐一对齐；`--kit web/recon` 只覆盖最小 Web 面，不代表全打法自动化。`coverage_gate.py --strict`（全库）仍会指出这些；`--active --strict` 是当前启用面的闸门。

所以：**最小 Web/侦察闭环已跑通，完整作战编排仍不是全闭环**；执行前先 `ls` 确认脚本存在，再按能力用现有替代。

## 强制检查点

每个新目标、每次换面，先跑一次；至少这 6 个时刻不能跳：

1. **目标指纹出来**：技术栈/产品/端口/云/移动端 → `--phase recon`
2. **撞到登录/鉴权/验证码**：`--phase auth`
3. **发现参数/输入点/文件面**：`--phase injection` 或 `--phase file`
4. **进域/进云/进容器**：`--phase ad` / `--phase cloud`
5. **拿到后台/shell/数据库**：查 `mobile`、`cms`、`api`、`report` 里的接管与取证卡
6. **写报告/定级前**：`--phase report`，查复现与证据闸门

## 阶段 → 查询示例

| 阶段 | 查询 |
|---|---|
| 侦察 | `skill_find.py "cloudflare 源站" --phase recon` |
| 认证 | `skill_find.py "若依 druid 未授权" --phase auth` |
| 注入 | `skill_find.py "mssql xp_cmdshell" --phase injection` |
| 文件 | `skill_find.py "thinkphp 上传 包含" --phase file` |
| AD | `skill_find.py "ADCS ESC1 证书" --phase ad` |
| 云 | `skill_find.py "s3 bucket 未授权" --phase cloud` |
| 移动 | `skill_find.py "apk 逆向 后端" --phase mobile` |
| CMS | `skill_find.py "wordpress batch sqli" --phase cms` |
| API | `skill_find.py "fastapi openapi 未授权" --phase api` |
| 博彩 | `skill_find.py "白标 博彩 后台" --phase gambling` |
| AI | `skill_find.py "llm prompt injection" --phase ai` |
| 逆向 | `skill_find.py "wasm 签名" --phase reverse` |
| CVE | `skill_find.py "gitlab 漏洞" --phase cve` |
| 工具 | `skill_find.py "jenkins 未授权" --phase tools` |

## 命中之后

1. 先读卡里的 **决策规则/前置条件**，确认目标真的满足；不满足就换卡，不要硬套。
2. 卡里给的脚本/字典/模板，优先用原路径；归档卡的 `原目录` 在 legacy 文件头部。
3. 一张卡不够就再查同阶段 Top 3，不要只加载第一张。
4. 打完一轮，把 **用了哪些卡、哪些卡没用上、缺什么打法** 记进案卷；缺的再补卡，不重复造轮子。

## 维护

技能库新增/合并后重建索引：

```bash
python3 /root/.hermes/arsenal/arsenal_build.py
python3 /root/.hermes/arsenal/selftest.py   # 30 条实战问句路由回归
python3 /root/.hermes/arsenal/vuln_build.py # 0day/PoC/CVE 仓重建
python3 /root/.hermes/arsenal/repo_build.py # TGSEC 整仓文档路由重建
```

数据库：`arsenal.db`（技能卡）+ `vuln.db`（漏洞库/PoC）+ `repo.db`（TGSEC 整仓文档）。  
检索器：`skill_find.py`（技能）+ `vuln_find.py`（CVE/PoC）+ `repo_find.py`（整仓文档）。

**判断标准只有一个：实战中能不能被查到、被加载、被执行。** 常驻索引大小不是目标。
