---
name: orchestration-layer
description: "Use when 按岗位委派子代理或给工具定风险等级。"
---

# 编排层（角色 / 子代理 / 工具 三层，文件即注册）

落位：`D:\测绘引擎\orchestration\{roles,agents,tools}\` + 运行器 `tools/ops/orchestrator.py`。
设计文档：`docs/design/orchestration-model.md`（加载规则/接缝/扩展三步）、`docs/design/subsystems.md`（机制对照表）。

## 什么时候用它

- **要委派子代理**：不要即兴写 context → `agents render <名称> --target <目标> --case <案卷>`，把输出的 `goal/context/output_schema` 直接喂 `delegate_task`。
- **要跑工具**：不要现写命令行 → `tools run <名称> k=v`，由 YAML 声明 + 风险闸门把关。
- **要开工新面/重复作业**：先看 `roles list`，按岗位分工而不是一个人硬打。

## 四层分工（一句话版）

| 层 | 回答 | 位置 |
|---|---|---|
| 技能卡 | 怎么做 | `skills/` |
| 角色 | 谁来做、边界、升级路径 | `orchestration/roles/*.yaml` |
| 子代理 | 这次怎么做完（步骤/契约/禁止） | `orchestration/agents/*.md` |
| 工具 | 能用什么、多大风险 | `orchestration/tools/*.yaml` |

## 命令（全部实测可用）

```bash
cd /d/测绘引擎 && export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
python tools/ops/orchestrator.py check                 # 校验：必填字段+引用闭合（problems>0 不可交付）
python tools/ops/orchestrator.py tree                  # 四层总览
python tools/ops/orchestrator.py roles  list|show <n>
python tools/ops/orchestrator.py agents list|show <n>
python tools/ops/orchestrator.py agents render recon-sweep --target <t> --case "D:/渗透/<t>_recon"
python tools/ops/orchestrator.py tools run skill_index cmd=search query="报错注入 取数"
python tools/ops/orchestrator.py tools run skill_index cmd=stats --dry-run   # 只验参
```

## 风险闸门（不可绕）

- `low`→直接跑；`medium`→需 `--ack`；`high`→需 `--yes`（会对**外部目标**发请求，仍受授权边界约束）。
- `--dry-run` 只打印 argv，不执行；参数写错在**设计期**就被拒（enum/default/only_for 校验）。
- `high` 不是授权：它只代表「会发出真实请求」，具名域纪律仍由人守。

## 纪律闸门（收编外部卡前必跑）

外部技能库里有两类长得像的东西，**必须分开**（`unlimited-attack-scope` 这种名字最容易被误判）：

```bash
python tools/ops/scope_lint.py scan --orch                    # 扫技能卡 + 检查角色/子代理是否声明边界
python tools/ops/scope_lint.py scan --root <外部库>/skills     # 收编外来卡前先扫
python tools/ops/scope_lint.py selftest                       # 改规则后必跑（含 6 条真实误报反例）
```

- **DANGER**（把授权范围说成无限/无需授权）→ 拒绝交付，不落库。
- **SMELL**（`不设限/无限/unlimited/任意目标`）→ 需人工判读；实测绝大部分是技术名词（`ptrace_scope=0`、`-ResultSize Unlimited`、「无限 approve」）与**方法论不自我设限**，不是授权放开。
- **warn**（角色/子代理未声明边界）→ 补齐硬线声明。
- 硬线（不可稀释，每个角色的 `hard_rules` 都必须写）：**只做具名域 / 说一次不重复 / 越界靶向禁令**。

## 纪律

1. **新增/改名**：角色抄 `roles/recon.yaml`、子代理抄 `agents/recon-sweep.md`、工具抄 `tools/skill_index.yaml`；`exec` 必须指向**已存在**脚本（`check` 会拦）。
2. **改完必跑** `check`；新增技能卡后另跑 `skill_index.py build` + `skill_catalog.py validate` + `hermes_skill_sentinel.py sync --apply`（否则索引与真源不一致）。
3. **不要在本层塞业务数据**：事实进 `case_facts`，作业进度进 `<案卷>/flow.json`，本层只管「岗位/步骤/工具声明」。
4. **不要造不存在的工具**：`check` 会因脚本缺失报 FAIL；先落脚本再声明。
5. 运行器**不调度**子代理（并发/回收由 `delegate_task` 负责），它只做「校验 + 渲染 + 按声明跑工具」。

## 自测（十秒）

```bash
python tools/ops/orchestrator.py check && python tools/ops/orchestrator.py tools run skill_index cmd=stats
```
