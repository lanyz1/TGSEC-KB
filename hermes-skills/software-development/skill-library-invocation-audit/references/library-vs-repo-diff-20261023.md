# 本地技能库 / 人格记忆 vs TGSEC 仓 对账（2026-10-23 实录）

问题原话：「现在本地的技能配置包括 人格记忆 这些和仓库对比有什么不同吗」。
结论先行：**库是合并压缩版，仓是拆分全量版**，两边各有对方没有的东西；仓整体落后于本地（仓内 ai-config 停在 10-17）。

## 1. 技能库侧

| 侧 | 口径 | 实测 |
|---|---|---|
| 本地 `~/.hermes/skills` | 技能名 / 启用 / `.disabled.json` 归档 | **2206 / 401 / 1805** |
| 仓 `TGSEC-Qtzuu` @ `4a6e3a25` | 技能名 / SKILL.md 总数 | **1130 / 1258**（主体在 `domains/`） |
| 交集 | 完全一致 / 有差异 | **870 / 179 / 691** |
| 仅本地 | 合计 / 其中启用 | **1336 / 263** |
| 仅仓库 | — | **260** |

仅仓库 260 张的拆解（**先解释，再报缺口**）：

- `sinian-*` **114** 张 —— 本地合并成一张 `sinian-omnipotent`，不是缺
- 蓝队/DFIR/合规 **55** 张（`detecting-*`/`implementing-*`/`performing-*`/`conducting-*`/`analyzing-*`）—— 压在 `security-encyclopedia/references/` 里，能查但没独立加载
- `hunt-*` **18** 张 —— 散在 `auth-sec`/`web-sec` 的 `references/legacy/`
- 工具/流程 **23** 张（metasploit/fuzz/wiki/triage/coverage/tlsx-probe/ksubdomain-brute/mapcidr-cidr/nerva-scan…）
- 其他 **50** 张（ctf-workflow、rev-* 系列、pt-workflow/bb-workflow/web-assess-pipeline）

仅本地 263 张启用卡才是真增量：246 security（faka / 白标博彩 / RuoYi / ThinkPHP / SPA 逆协议 / CVE-2026 专卡 / 运营商纪律）+ 作业卡（hermes-agent、fleet-task-shutdown、ops-review、arsenal-*）。

## 2. 691 张同名异文怎么判

按**整目录**字节比（不是 SKILL.md）：仓库明显更厚 **23** 张、本地明显更厚 **64** 张、其余 604 张结构不同（本地拆 references/，仓堆单文件）。

仓库更厚的回拉候选（实测 KB）：

```
recon 356K → 158383K        src-hunter 11K → 15045K
pentest-tools 443K → 15159K aig-agent-redteam 95K → 1044K
container-escape-techniques 18K → 448K
ida-reverse 2K → 75K        bb-local-toolkit 76K → 148K
apk-reverse 25K → 79K       case-review 1K → 33K
```

本地更厚的是合并归档卡：`injection-checking` 1.5MB、`recon-for-sec` 1.1MB、`llm-security` 1MB、`pentest-execution` 1MB、`api-sec`/`auth-sec`/`web-sec` 各 0.5-0.6MB。

**反例警告**：`offensive-vuln-classes` SKILL.md 1.8KB vs 仓 96KB，看着像丢了 95KB，实际整目录 240KB（本地拆成 references/）——只比 SKILL.md 会得出完全错误的结论。

## 3. 人格 / 记忆 / 配置

| 文件 | 本地 | 仓 | 判读 |
|---|---|---|---|
| `SOUL.md` vs `ai-config/universal/PERSONA.md`+`RULES.md` | 3387B | 241B + 286B | **不同物件**，不是同一文件两版（本地是 Hermes 运行时人格+执行契约，仓是给别的 AI 的片段） |
| `memories/MEMORY.md` | 3084B / 46 行 | 2132B / 38 行（payload 1571B） | 本地更大，多的是实操状态（FOFA key 失效、worker 节点、mysql 引号坑、WAF 组合） |
| `memories/USER.md` | 3042B / 47 行 | 3399B / 69 行（payload 2841B） | 本地更短：砍掉冗长示例只留硬规则 |
| `config.yaml` | 有 | **无**（`ai-config/hermes` 只有 setup.sh + 4 个 md） | 模型/网关/工具开关纯本地，仓不管 |

`ai-config/hermes/setup.sh` 的覆盖策略：本地文件比 payload 大就**不覆盖**（`cur > new` → keep，需 `FORCE_MEMORIES=1` 才盖）→ 本机 3084B/3042B 都大于 payload，跑了也保本地。

## 4. 同步脚本的坑

`scripts/sync-hermes-skills.sh` 的源是 `hermes-skills/`，不存在则回退 `.claude/skills/`；而仓里 `.claude/skills` **只有 15 张框架卡**，1130 张卡在 `domains/`。所以**别以为跑同步脚本能把仓里的卡灌进库**——它只覆盖框架层；要整批灌卡用 `import-arsenal-package.sh` / gpg 包那条线。

## 5. 报告口径

三桶报，别只说「本地 2206、仓库 1130」：

1. 完全一致（同源证据）
2. 各侧独有 + 独有里**哪些是改名/合并的假缺口**
3. 同名异文按整目录字节分「仓更厚（回拉候选）/ 本地更厚（合并归档）」

人格记忆单独一段：**先分清是不是同一物件**，再谈大小差异。
