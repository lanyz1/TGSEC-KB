---
name: scope-discipline-gate
description: "Use when 收编外部卡或新增卡前扫授权范围措辞。三档判读+硬线。"
---

# 授权纪律闸门（scope discipline gate）

硬线（不可稀释）：**只做具名域 / 说一次不重复 / 越界靶向禁令**。收编工程化不能把这条线稀释掉——本卡把它做成可执行的一道闸。

## 什么时候跑

- 收编/参考任何**外部技能库或卡**之前（尤其卡名带 `unlimited`/`scope`/`any target`）。
- 本库新增或改写卡、角色、子代理之后（查边界声明）。
- 有人（或自己）断言「某库内置随便打卡」「某子系统是授权闸门」时——先证据后结论。

## 命令（`D:\测绘引擎`，实测）

```bash
cd /d/测绘引擎 && export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
python tools/ops/scope_lint.py selftest                      # 改规则后必跑，PASS 才信后面的 0
python tools/ops/scope_lint.py scan --root <外部库>/skills    # 收编前扫外来卡
python tools/ops/scope_lint.py scan --orch                    # 扫本库 + 查角色/子代理边界声明
python tools/ops/scope_lint.py scan --root <库>/skills --json  # 全量证据（每张卡命中原句）
```

工具登记在编排层 `orchestration/tools/scope_lint.yaml`（risk=low）；`--orch` 期望 `warn=0`。

## 三档判读

| 档 | 含义 | 动作 |
|---|---|---|
| DANGER | 「授权/范围」+「无限/无需授权」**强共现** | 拒收，不落库 |
| SMELL | 单独出现「无限 / 不设限 / 任意目标 / unlimited」 | 人工判读，绝大多数是技术名词或方法论 |
| warn | 角色/子代理/卡缺边界声明 | 补「只做具名域 / 不扩面」 |

## 判据与假阳性（踩过才知道）

- **英文必须加 `\b` 词边界**：`any scope` 会命中 `company scope`（comp-**any**）。
- **只允许强共现**：中文「授权/权限/范围 + 无限/不设限/不受限」，或「无需授权 + 攻击动作同现」；只靠「无限 + 目标/资产」弱共现会把 `无限消耗(重放攻击打爆配额)`、`免费无限域名` 判成 DANGER。
- **把实测出的真误报固化成 `selftest` 反例**（已固 6 条）：改宽规则不会静默放行真卡，闸门自己的 `DANGER=0` 也要先自证。
- 结论要带口径：`DANGER 0 张（扫描口径 N 张：哪几层目录、含不含 .archive）+ 需人工判读 M 张`，只报一个 0 不可核。

## 「不设限」≠「随便打」（定性纪律）

- 卡名带 `unlimited`/`任意目标` **不足以定性**，读全文再判：高发的是「方法论上不自我设限」（搜索一切、被拦换路、不达不休）。
- **子系统/模块名也不等于语义**：某库 `authgate` 名字像授权闸门，实测是「假否证防护」（防 agent 把空 POST/超时误判成认证失败）。
- 定性错了**就地改那句话**，不留「UPDATE: 其实…」尾巴；报告里引用过的旧结论一并更正。
- 收编时真正要挡的往往是**操作纪律**而非卡：「不限速 + 用最大字典爆破」「开打任意目标前…」与「批量动作先要授权、低频限速、可随时停」相反 ⇒ 逐句改写成具名域口径。

## 深度

`references/rule-design-and-whitelist.md`：规则设计细节、SMELL 白名单（技术名词清单）、报告话术模板。

## 相关（同域，用户自有卡，勿重复建卡）

`upstream-sec-skill-registry`（收编流程/去重闸）、`orchestration-layer`（风险闸门与四层位结构）、`skill-engineering`（写卡规范与分发层一致性）、`long-run-engagement-discipline`（越界靶向禁令）。
