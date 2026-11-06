## 接手第一件事
1. 读 `D:\跨境商城\qavlixor-marketplace\docs\ops-log\HANDOFF-交接文档.md` — 项目权威现状:红线/架构坑/当前阶段/待办。每次交接更新它,它是跨会话唯一事实来源(私有 memory 不算数)。
2. 读 `D:\跨境商城\qavlixor-marketplace\docs\项目规则与逻辑.md` — 全项目入口级总览(架构/资金模型/钱包三态/保证金/订单机/入驻/消息/编码规则/规则体系/进度/史山记录),2026-08-04 新建。
3. 确认 dev 活着:`netstat -ano | grep -E ":3000.*LISTEN"`。
4. `git log --oneline -5` + `git status --short` 看工作树。
5. 会话产物(量测报告/设计基线/临时脚本)存 `D:\跨境商城\会话产物\`(规则见 `会话产物\存放规则.md`)。

