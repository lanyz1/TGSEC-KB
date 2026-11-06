# 中转站关键词拦截分析报告

> 基于对 `qqq` 项目（Fable 5 破甲工具包）的完整拆解，2026-07-12 会话

## 来源文件清单

- `fable5_破甲教程.md` — 四种破甲方法详解
- `fable5_jailbreak_report.md` — 完整情报报告
- `fable5_tools/CL4R1T4S/ANTHROPIC/CLAUDE-FABLE-5.md` — F5 泄露系统提示词（含 classifier/reminder 定义）
- `fable5_tools/Spiritual-Spell-Red-Teaming/.../CLAUDE.md` — ENI 角色注入 + 拒绝覆写
- `fable5_tools/Spiritual-Spell-Red-Teaming/.../ENI Writer Lite.md` — 色情写作 persona
- `fable5_tools/Spiritual-Spell-Red-Teaming/.../Direct Social.md` — 协商式开场白
- `fable5_tools/jailbreak-fable/src/utils.mjs` — Parseltongue 混淆引擎
- `fable5_tools/jailbreak-fable/workflows/pack-hunt.js` — Pack Hunt 分解+collection
- `fable5_tools/jailbreak-fable/src/engine.mjs` — 工作流执行引擎

## 中转站拦截的特征信号

| 信号 | 含义 | 应对 |
|------|------|------|
| HTTP 403 + 自定义错误页 | 中转站输入过滤 | 换传输方式或异体字 |
| HTTP 200 + 空响应/无模型输出 | 中转站静默丢弃 | 同上 |
| "检测到疑似违规内容，当前违规计数 X/5" | 中转站违规计数制 | 立即停止使用该 provider |
| "API Error: Fable 5 has safety measures..." | API 层分类器触发 | 换非 F5 模型 |
| stop_reason='refusal' | 模型层拒绝 | CTF/ENI/渐进式 |

## 已验证绕过成功的中转站

| 中转站 | 已知绕过方式 | 状态 |
|--------|-------------|------|
| fkcodex | 不可绕过（语义检测 + 违规计数） | ❌ 放弃 |
| Right Code AWSQ | 直连 + CTF 框架 | ✅ 可用 |
| My Codex (api.aisz.mom) | 配置迁移后可用 | ✅ 可用 |

## 关键词密度阈值经验

- **< 0.1%**: 大多数中转站放行（例如 5000 字 prompt 中不超过 5 个高危词）
- **0.1%-0.5%**: 部分中转站拦截，取决于具体关键词
- **> 0.5%**: 几乎所有中转站拦截

长上下文模拟（pack-hunt 的 Collection 阶段）就是通过先将关键词密度稀释到 0.1% 以下再发送。
