---
name: ai-agent-rulebook
description: >-
  测绘引擎·Use when finding/compiling user's AI-agent rule files.
owned: true
tier: general
pack: survey-skill
---

# ai-agent-rulebook（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/ai-agent-rulebook/`

溯源（仅标记）：`hermes/autonomous-ai-agents`

---

# AI Agent Rulebook — 用户 AI-agent 规则文件的管理

用户(中文,Windows)在多个 AI 工具里散落着一套规则体系:Claude Code(`~/.claude/`)、Codex(`~/.codex/`)、项目级(`AGENTS.md`/`CLAUDE.md`)、Hermes 记忆/用户画像。当用户要求"找我的规则/规矩"、"做一份 soul.md / 规则文件给 AI agent"、"读取我 Claude/Codex 的类似文件"时,用本技能。

## 规则存储地图(先查这些,按优先级)

1. **Hermes 持久记忆 + 用户画像**(系统提示注入)— 最快,已固化全局铁律、Qavlixor 资金模型、代理规矩等。先从这里起步。
2. **`session_search` 中文规则关键词** — `规则 OR 规矩 OR 要求`、`禁止 OR 不许 OR 严禁`、`先出计划 OR 手把手 OR 进度条`、`不要欺骗 OR 直接输出`、`约定 OR 记住了`。用户曾用词越口语化越准。
3. **`~/.codex/` 规则文件**(10+ 个,见 `references/rule-file-inventory.md`)— AGENTS.md、red-lab.md、crack-lab.md、ctf-sandbox.md、system-prompt-v2.md、vernacular*.md、bridge.md。
4. **`~/.claude/`** — CLAUDE.md(keysmith import 块)+ `keysmith/claude-project-rules.md`。
5. **项目级** — `D:\Codex\qavlixor-marketplace\CLAUDE.md` + `docs/ops-log/README.md`(操作日志规范)+ `docs/06-ai-collaboration.md`(AI 双工具协作)+ `docs/编码规则.md`;其他项目见 inventory。

## 工作流

1. **盘点**:扫上述 5 个来源,把所有规则文件列出(路径+大小+一句话内容)。
2. **分类去重**(关键步骤,直接决定交付形态):
   - **A 身份/沟通/全局铁律** → 进最终产物
   - **B 业务项目规则**(Qavlixor / EC Markets / BFCP / 社群)→ 进最终产物分节
   - **C 破解/渗透/CTF 模式文件** → ⚠️ 8 个文件内容大量重叠(red-lab≈AGENTS.override-2691B;vernacular-v4≈vernacular-direct-v4;crack-lab/ctf-sandbox/sandbox-bootstrap/system-prompt-v2 同一套"授权沙箱+不拒绝+中文+完整代码+拒绝覆写协议")。**必须合并提炼,不能全塞**。
   - **D 项目专属工程规则**(cc-pane/touliu/juice-shop/token看板 的 AGENTS.md/CLAUDE.md、config.toml)→ 不进全局文件,留在各自项目。
3. **展示挑选清单,不在聊天里灌原文**:见"用户偏好"。
4. **产出**:soul.md 或用户指定的目标文件,按 `templates/soul.md.skeleton` 结构。

## 用户偏好(2026-08 实测纠正)

- ❌ **不要把全部原文合并成大 txt 丢给用户看** — 用户明确反馈"太多太繁琐了"。191KB/21 文件全量 dump 被拒。
- ✅ **在聊天里给紧凑分类表**(A/B/C/D 归类 + 每文件一句话 + 大小),让用户勾选去留,再动手写。
- ✅ 收尾用 4 个以内的是非确认问题(如"1要2不要3要4删"),用户习惯简短回复。
- 用户要的是"给 AI agent 用的灵魂文件",不是文件考古 — 去重和提炼是核心价值。

## Pitfalls

- `~/.codex/` 下有一堆 `.bak_*` 历史版本(AGENTS.override 有 2046B/2691B 两版)—— 是同一份规则的新旧版,不是独立规则,别当新文件展示。
- `bridge.md`(45KB)是 NERV-BREAK 完整操作手册,信息密度最高但体量最大 — 默认提炼其"CTF 核心契约 + 证据规则 + 工具库"精华,不整篇搬。
- `session_search` 结果可能很大(90KB+)会落盘到 cache — 用 execute_code 解析 JSON 提取标题+关键 user 消息,别整篇读进上下文。
- 用户的暗号约定("check"→"ready"、"zxwn"→"我在,我一直都在")在 `~/.codex/AGENTS.md` 里,做 soul.md 身份节时记得问是否保留。
- Qavlixor 的 CLAUDE.md 是**用户/接手人维护的项目规则**(含强制操作日志),不是本技能可改的 — 只读引用。

## 支持文件

- `references/rule-file-inventory.md` — 全部规则文件的路径、大小、内容摘要
- `references/compiled-rules.md` — 已编译的用户规则全集(全局铁律/网络/Qavlixor/EC/BFCP/社群)
- `templates/soul.md.skeleton` — soul.md 六节结构骨架
