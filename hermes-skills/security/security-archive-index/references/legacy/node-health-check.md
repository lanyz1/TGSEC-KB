<!-- archived from /root/.hermes/skills/security/node-health-check/SKILL.md on 2026-10-21 -->

---
name: node-health-check
description: Use when 主人下发「全局自检/自检」或开工前核验装备——跑分层节点健康自检与就地修复。
---

> 归档卡：原目录 `/root/.hermes/skills/security/node-health-check`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/node-health-check/…')`，不要相对 `references/legacy/` 解析。

# node-health-check — 节点健康自检与装备核验

触发：「全局自检 / 自检 / health check」；战役开工前的装备盘点；节点行为异常（收发停摆/任务卡死）后的排查。
交付物 = TLDR + 分层健康判定 + 就地修复项 + 遗留观察项。

## 硬规则（always-on）

- **禁止凭 MEMORY / 档案 / 历史战报断言健康**——每一层的结论必须来自本轮实测输出；「声明在位 ≠ 在位」。
- 装备在位判定 = `command -v` + 至少一次实测；代理类必须 live probe 出口 IP（`rotate_proxy.sh curl -s https://api.ipify.org`）。
- 以脚本形式部署的工具（asset_search.sh/.py 类）不算 MISSING，报实体路径。
- doctor 的 ⚠ 与可选 API key 缺失 = 观察项，不判故障；只把关键服务 failed 升级为故障。
- 就地修复：可当场修的小病直接修（可逆优先），修完**复验原故障面**（修什么验什么）再进报告；不可修的列观察项 + 附修复命令（如 `hermes doctor --fix`），不静默吞掉。
- 自检命令被 skill-enforcer 拦截 → 按拦截消息点名 `skill_view` 装载对应域技能，然后**原样重试同一条命令**——禁改措辞、换工具绕过。
- 多段自检命令中含括号/元字符的段头 echo 必须引号包裹，否则整条 compound 命令中途语法中止。
- .env 核验只看 key 名（`grep -oE '^[A-Z_]+='`），不输出值。

## 分层顺序（廉价 → 昂贵）

1. **系统层**：date/uptime/df/free + `systemctl --failed` + `pgrep -af hermes`（进程存活与启动时长）
2. **Hermes 内核**：`hermes doctor`（看 tail）→ logs（gateway.log 收发对 / errors.log 尾部）→ state.db integrity + sessions 数 → plugins → cron jobs.json + ticker 心跳 → 会话/记忆文件
3. **模型链路**：config.yaml model 段 + .env key 名 + errors.log 认证错误定位
4. **装备链**：逐件 `command -v` 盘点 + 代理出口 live probe
5. **就地修复与复验** → 6. 分层报告

完整命令清单与逐层判据 → `references/health-check-runbook.md`。

## 判定口径（易误判点）

- **认证类错误（401 INVALID_API_KEY）**：集中在单会话时间窗且之后零复发 = 上游中转瞬时抖动（重试自愈），非配置病；分散持续出现 = 凭据/配置问题，升级。
- **网关崩溃史**：`gateway-exit-diag.log` 里 exit 75 循环后最后一次 `gateway.start` 延续至今 = 已自愈——既往事实照报，不算当前故障。
- **网关健康判据**：进程在 + gateway.log 近期收/发日志对（inbound → response ready → Sending）+ cron ticker 心跳新鲜，三者齐备才算健康。
- **技能重名冲突**（skill_view 报 ambiguous）：比对两份 SKILL.md——保留有版本 frontmatter + references/templates 结构的正式版；旧快照 `mv` 到 `~/.hermes/backup/<name>-stale-<date>/`（可逆不删），重新 `skill_view` 确认解析干净。

## 报告格式

TLDR-first 分层，每层一句判定：① 系统层 → ② Hermes 内核 → ③ 模型链路 → ④ 装备 → ⑤ 当场修复（修了什么/复验结果）→ ⑥ 遗留观察项（不动的原因 + 修复命令）。结尾给一个可执行的下一步问句。

## 关联
- 行为侧复盘（自己做错了什么）→ `pentest-campaign-ops` §4；开工装备分配 → 同 §1.1
- 后台任务退出码裁定 → `background-job-operations`
