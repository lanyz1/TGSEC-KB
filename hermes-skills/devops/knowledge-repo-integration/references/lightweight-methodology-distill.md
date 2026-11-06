# 轻量方法论提炼（非整仓 vendor）— 2026-09-20 实录

用户选档：「轻量提炼：只融缺口…不新建独立技能」vs「中量 router」vs「先别动」vs「整仓 vendor」。

上游样例：`cloudflare/security-audit-skill`（MIT，~672K，白盒多智能体 6 阶段）。

## 何时用轻量档

- 来料是 **编排/审计 skill**（SKILL + companion 攻击类 + schema/validators），不是 PoC 合集也不是产品本体
- 本库 **已有同主题名字引用或活靶闸门**，但缺机器契约 / 缺面 companion
- 用户明确不要新建 Hermes 伞形、不要整仓堆叠

## 先评估：名字引用 ≠ 已吸收

```bash
rg -n '<repo-name>|security-audit-skill' /root/TGSEC-Qtzuu -g '*.md' | head
# 只有「开源参考」一行 = 未吸收
# 有独立目录 + schema/validators + README 路径 = 已吸收
```

与活靶技能划界：

| 问题域 | 本库已有 | 别混写 |
|--------|----------|--------|
| CDN/源站/Turnstile | `cdn-origin-tracing` / `cloudflare-turnstile-bypass` / `cf-hidden-*` | 活靶外网 |
| 源码白盒多智能体审计 | （提炼前几乎只有点名） | 源码优先 + 沙箱本地 |

## 缺口探测（CF 案）

真缺口（优先吸）：

- `coverage-ledger.json` 概念 + `validate-coverage-ledger.cjs`
- `findings.json` 三态 schema + `validate-findings.cjs`
- companion：`DATA-ISOLATION-AND-LIFECYCLE` / `DESKTOP-MOBILE-AND-LOCAL-IPC` / `PROTOCOLS-RPC-AND-MESSAGING` / `RESOURCE-EXHAUSTION-AND-AVAILABILITY` / `SUPPLY-CHAIN-AND-RELEASE`

可保留卡形但已有部分重叠：WEB-PROTOCOL-AND-AUTH / CLIENT-SIDE / CLOUD / AI-AND-LLM / MEMORY-SAFETY

**不吸**：上游全文 `SKILL.md`/`HUNTING.md`/`RECONNAISSANCE.md`/`VALIDATION-AND-REPORTING.md` dump；不新建 `skill_view(security-audit)`。

## 落点模板

```text
domains/<面>/<topic>-distill/   # 例 file-vulns/code-audit/cloudflare-security-audit/
  README.md + FUSION.md
  methodology/          # 纪律卡：pipeline / ledger / verdicts / anti-patterns
  attack-classes/       # 缺面优先 + 必要保留
  schema/               # report-schema.json + validate-*.cjs(+tests)
```

提炼纪律卡，不要原文堆叠。产物契约写清：Guidance vs Full audit；三态 `confirmed|needs_validation|rejected`。

## 接线（否则 AI 仍调不到）

1. `domains/<面>/README.md` 加一行路径说明「轻量提炼 / 非整仓」
2. 原 methodology README（中英）加增量节
3. 把「开源参考：xxx」改成 **可点路径**（`secure-code-review` 名挂 → 真入口）
4. `MASTER.md` / `ROUTING.md` 关键词一行
5. `domains/FUSION-YYYYMMDD-<name>.md` 账本
6. **不要**为轻量档新建 Hermes 伞形技能

## 校验再提交

```bash
cd .../schema && node --test validate-findings.test.cjs
node --test validate-coverage-ledger.test.cjs   # 全绿再 commit
# push 前 unset Tor 代理；战役明文 loot 不进仓
```

CF 实落：`domains/file-vulns/code-audit/cloudflare-security-audit/`；commit `ea2a2649`。
