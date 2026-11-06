---
name: windows-cli-deployment
description: >-
  测绘引擎·Deploy and fix Linux-originated CLI tools (especially Node.js) on Windows under
  Hermes Agent. Covers terminal fallback via Python subprocess, ESM import path patching,
  and toolchain resolution.
owned: true
tier: general
pack: survey-skill
---

# windows-cli-deployment（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/windows-cli-deployment/`

溯源（仅标记）：`hermes/software-development`

---

# Windows CLI Deployment

<!-- split-index -->

## Section index

- [Problem](references/split-01-problem.md)
- [Workaround: Python execute_code as Surrogate Shell](references/split-02-workaround-python-execute-code-as-surrog.md)
- [Patching Node.js CLI Tools for Windows](references/split-03-patching-node-js-cli-tools-for-windows.md)
- [Python Sandbox Caveats](references/split-04-python-sandbox-caveats.md)
- [Python Venv Isolation (PYTHONPATH Pollution)](references/split-05-python-venv-isolation-pythonpath-polluti.md)
- [Styling Preference: Simplified Step-by-Step](references/split-06-styling-preference-simplified-step-by-st.md)
- [CC Switch — Claude Code Proxy Management](references/split-07-cc-switch-claude-code-proxy-management.md)
- [User Interaction Style Preference: Delegate-and-Execute](references/split-08-user-interaction-style-preference-delega.md)
- [Knowledge-Generation Workflow (No File Needed)](references/split-09-knowledge-generation-workflow-no-file-ne.md)
- [Claude Code WorkflowTool Validation](references/split-10-claude-code-workflowtool-validation.md)
- [Anthropic SDK Proxy Configuration](references/split-11-anthropic-sdk-proxy-configuration.md)
- [Final Package Deliverable](references/split-12-final-package-deliverable.md)
- [Verification Checklist](references/split-13-verification-checklist.md)
- [Running Multi-Agent Workflows (Timeout Considerations)](references/split-14-running-multi-agent-workflows-timeout-co.md)
- [Direct API Call Pattern (No wf-engine)](references/split-15-direct-api-call-pattern-no-wf-engine.md)
- [Proxy Balance Management](references/split-16-proxy-balance-management.md)
- [Critical Correction: All "Breakthroughs" Were Sonnet-4-6, NOT Fable 5](references/split-17-critical-correction-all-breakthroughs-we.md)
- [Real Session Deliverable](references/split-18-real-session-deliverable.md)
- [Typical Toolchain](references/split-19-typical-toolchain.md)
- [MCP FastMCP Server Deployment on Windows](references/split-20-mcp-fastmcp-server-deployment-on-windows.md)
- [Rust / Tauri Desktop App Deployment on Windows](references/split-21-rust-tauri-desktop-app-deployment-on-win.md)
- [Hermes Agent 安装（Windows + 中国网络）](references/split-22-hermes-agent-windows.md)
- [Pitfalls](references/split-23-pitfalls.md)
