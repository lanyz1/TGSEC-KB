## 十二、与 cyberstrike-eino-demo 的联动（Eino 技能系统）

### 12.1 Eino 技能系统概述
本工作区采用 Eino（Agent Skills 兼容）技能包规范：**`SKILL.md` 为清单+主说明**，同目录可挂 `scripts/`、`references/`、`assets/` 子目录；由 Eino 的 `ListPackageFiles` / `resource_path` 与多代理内 ADK **`skill`** 工具按包加载，`FilesystemSkillsRetriever` 支持包摘要与 `##` 分块检索。参考 `cyberstrike-eino-demo` 包的 HTTP `GET /api/skills/...`、`section=`、`resource_path=` 机制。

### 12.2 将本技能封装/调用为 Eino skill
- 本文件即 `security-automation` 技能包主文档：多代理会话内用 **`skill`** 工具加载本包，即可获得 CI/CD 管道、扫描编排、SOAR、Agentic 自动化的可执行命令与模板
- 建议配套（可复用 demo 包结构）：
  - `scripts/`：管道扫描脚本（如 5.3 归一化脚本）、门禁检查脚本
  - `references/`：SBOM/CIS/合规证据收集清单、剧本模板
  - `assets/`：报告模板、规则示例
- 按需加载 `section=扫描工具链` 等分块，节省 token；需要脚本原文用 `resource_path=scripts/xxx.py`

### 12.3 多代理协作场景（Eino + 本技能）
```
协调代理(任务拆解/上下文传递)
 ├─ 扫描代理     → 加载 security-automation: nuclei/SAST/SCA 命令
 ├─ 利用代理     → 加载 fastjson-exploitation / log4shell 等利用技能（授权内）
 ├─ 响应代理     → 加载 incident-response: 处置动作/证据留痕
 └─ 报告代理     → 加载本技能第十一章: 证据收集/报告生成
```
技能间的上下文衔接：扫描代理输出（资产/漏洞清单 JSON）作为下游代理的输入，统一 schema 便于多代理传递。

### 12.4 与 AI 安全自动化结合
- Eino 技能包可作为 Agentic 安全自动化的**工具库**：LLM Agent 通过 `skill` 工具加载本技能后，即可调用其中被封装的扫描/门禁/报告命令，实现"Agent 用技能干活"
- 技能包版本化（frontmatter `version`）支持 Agent 选择稳定版本，避免行为漂移

