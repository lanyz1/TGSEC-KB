## 压缩风暴作业纪律（长会话实测）

- 超长 execute_code 脚本有被截断风险 → 拆 <1KB，或改 patch 工具逐文件小刀。
- 关键结果落盘（/tmp/xxx.txt）后 `read_file` 读回核验；git 状态可 `read_file` `.git/COMMIT_EDITMSG`。
- 修复脚本幂等（先查再改 + 计数断言），看不到上次输出也能安全重跑。
- 单行小输出比大输出存活率高；提交核验 `rev-parse --short HEAD`+`status --short` 两行钉死。
- 输出被压缩吞掉时，`skill_view` 存根仍保留字符数（`name=X (N chars)`）：错误像 **Ambiguous ≈455 chars** vs 内容 KB 级——**字符数即状态回执**，正文被吞也能判生死。

详见 `references/skill-library-invocation-audit.md`（完整流程 + 2026-10-12 实例档案）。

同域相邻伞形（用户自有，curator 无权改）：`skill-engineering`（写法/交货）、`engine-distill`（张数盘点）——本卡专注“可调用性”证据链；日后若 adopt 可合并。
