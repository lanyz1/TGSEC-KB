# 活靶战役 → AI 学习报告吸收（四步法，2026-09-22）

适用：用户说「Ai渗透积累学习」「吸收提炼这些」「丢给AI学习报告」——对**本机正在打/刚打完的战役**做知识沉淀，不是外仓 zip 报告包（那走 `field-report-ingest.md`）。

## 用户四步（硬性顺序）

### 1. 通读 → 拆骨架

读透 `cases/<战役>/notes/REPORT.md` + `state.md` + 近期 VALIDATED 笔记，理清：

```text
目标簇 → 攻击面清单 → 攻击链 → 结果（VALIDATED vs 未破）
```

标记关键节点：入口 / 转折 / 打穿。**诚实口径**：VALIDATED 与未破分列，禁止把侧信道/假阳写成打穿。

### 2. 提炼四层知识

| 层 | 写什么 | 落哪 |
|----|--------|------|
| **可复用技能** | 手法、payload、绕过、可靠原语 | 优先**补强已有** references / case-lesson；新 Hermes SKILL 仅当 class 缺口且用户允许 curator adopt |
| **踩坑** | 死路、假阳、浪费时间弯路 | Playbook「已知坑位」+ case-lesson 坑表 |
| **组合链** | 多洞串法、前置条件、顺序 | `playbook-6000/<slug>-chain.md` + 总册增量 |
| **指纹→打法** | 看到什么指纹走什么路 | case-lesson 映射表；分流规则 / AGENTS 仅用户点名时改 |

### 3. 落盘

```text
domains/<面>/case-lessons/<slug>.md          # 脱敏课（无真 Token/邀请码/账密）
domains/<面>/playbook-6000/<slug>-chain.md   # 组合链短卡
docs/playbooks/近期成功接管手法总册.md       # 增量一行/一节
domains/CASE-INDEX.md                        # 登记 slug + 课数+1
战役 REPORT.md 末尾「AI吸收落盘」指针
```

- 署名：`@TGSEC社区 · @TGSEC-Qtzuu 整理`
- **security/* Hermes 技能拒自主写入**（需 `hermes curator adopt`）。可写：suite 课/playbook、以及 curator 管的 `devops/knowledge-repo-integration`、旧卡 **references** 补丁（若该 skill 可写）。
- 本轮可写路径示范：补 `ruoyi-pentest-playbook` / `fastapi-tg-platform-attack-chain` / `chinese-lottery-station-xxpay` 的 references；**不要**新建窄会话级 SKILL 名。

### 4. 回查

- 新手法 vs 已有技能库：needle 扫 `download/resource`、`onDemandFetch`、指纹串等——已覆盖则只加指针，不重复堆叠。
- 问：以前打过的同指纹站能不能用新手法再打？答案写进「指纹→打法」与总册优先级。

## 与 field-report-ingest 的边界

| | 活靶 AI 学习（本文） | 报告包 ingest |
|---|---|---|
| 输入 | 本机 `cases/` + 会话 VALIDATED | zip/pdf 外送报告 |
| 全文 | 已在 cases；一般**不再**复制 case-reports | 双落点 reports+lessons |
| 重点 | 四层 + 旧卡补强 + 总册 | 去重 + 散域 + DIGEST |

## 坑（本轮实录）

- 压缩边界后 skill 变 `[SKILL_PRUNED]` → 落盘前 `skill_view` 重载；security 卡仍可能只读。
- 「Nothing to save」不适用于用户明确要吸收的回合——至少要有 case-lesson 或 references 补丁。
- 窄会话名（`uu-r657-xss`）禁止当技能名；slug 用 class 级 `uu-im-8089-multiface`。
- 712 明文 loot / 邀请码 / cookie **不进仓**；课里写形态与路径模式。

## 完成判据

- [ ] case-lesson 存在且脱敏
- [ ] CASE-INDEX 有 slug
- [ ] 至少一处旧 references 或总册被补强
- [ ] 战役 REPORT 有吸收指针
- [ ] 回查做过（命中表或「无重叠」一句）
