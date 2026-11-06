---
name: finding-traffic-evidence-chain
description: "当要把漏洞发现与真实流量、命令输出绑成防篡改证据链、写报告要卡证据版本、事后要复盘或导出原始报文时加载本卡。覆盖发现入库的单事务落库、快照 SHA-256 内容寻址与 blob 落盘隔离、baseline/proof/verification/supporting 四种用途与全量排序校验、evidence_version 乐观锁与 report_evidence_version 门禁（旧写落 -1）、/api/exploration/findings/{id}/traffic 整组接口与 400/403/404/409/422 边界、24 小时宽限回收与归档重装。触发词：证据链、流量绑定、快照、证据版本、报告版本、导出报文、复盘取证。"
sources: art-content, operator_experience
---

# 发现 × 流量：证据链

## 定位

把一句漏洞结论变成「可哈希复算、跨进程并发安全、随报告版本封存」的证据链：命令输出与真实报文同时在场，原始流量被删、被清理之后，证据仍能读出原字节。

## 三段式主线

### 1 发现入库

`report_finding` 落库，返回第一行 `finding recorded: <探索节点 ID>`，随后 JSON 给独立漏洞记录 `finding_id`、探索节点 `finding_node_id` 与绑定摘要。整段落在一个 `WithEvidenceTx` 事务里：先 `LockTaskEvidenceTx` 锁任务行（读 `tasks.deleted_at` 与 `task_archives.state`，已删或已排队 → `ErrTaskArchiveState`），再逐条读原流量、写 blob、算快照 ID，最后写探索节点、意图关系、漏洞、快照、绑定四组记录，提交后才通知规划者。

无包路径同样成立：`traffic_refs` 为空时 prepared 是空切片，漏洞与报告照写，命令输出仍进 `findings.evidence`。TCP 类非 HTTP 漏洞、未采集、找不到确切记录，都走这条路径，不新增必填字段。

### 2 证据绑定

入口有三：随上报的 `traffic_refs`、`add_hint` / `add_task_hint` 单条或批量 `hints[]` 里带的 `traffic_refs`（Planner 代报时用 `evidence_hint_id` 指向本任务提示，不引用继承提示）、漏绑后的 `bind_finding_traffic(finding_id, traffic_refs)` 或 `POST` 补绑。绑之前先用 `traffic_search` / `traffic_get` 核对真实记录：域名与时间只做候选筛选，不推定任务归属，不按浏览记录猜。

重复追加同一条快照是幂等的：`INSERT ... ON CONFLICT(finding_id,snapshot_id) DO NOTHING`，绑定数不变、原有 `note` 不被覆盖、`evidence_version` 不涨（生命周期测试断言二次绑定后 `Version` 仍为 1 且 `note` 还是 `proof`）。

### 3 报告按版本写

两套 ID 分开记：`get_finding_traffic` 用独立漏洞记录 ID，`update_finding_report` 继续用探索节点 ID。写报告的顺序固定为：`get_finding_traffic(finding_id)` 读 `version` → 生成正文 → `update_finding_report(finding_id, report, evidence_version=读到的 version)`。读取与写入之间证据变动，旧版本写入被拒，重读重写，不拿同一份正文重试。

未传版本的旧调用，`report_evidence_version` 落 0（当 `evidence_version` 也是 0）或 -1，等于自报「没有对着当前证据写过」，渲染层据此标陈旧。

## 快照模型

表 `traffic_evidence_snapshots`，字段：`id`、`source_traffic_id`（原流量 ID）、`captured_at`、`url`、`method`、`status`、`content_type`、`req_head`、`resp_head`、`req_hash`、`resp_hash`、`req_len`、`resp_len`、`created_at`、`unreferenced_at`。

- 原流量 ID、采集时间、URL、方法、状态、头部、正文长度、SHA-256 八项全落行内字段，blob 落盘路径由 `req_hash` / `resp_hash` 推出：`blobs/<hash 前两位>/<hash>.bin`。元数据行本身就是报文的指纹。
- `id` 由 `TrafficSnapshotID` 算：快照 `Normalize()`（UTF-8 清洗）后清空 `id` 与 `created_at`，JSON 序列化再 SHA-256。内容相同即同一条快照，多个漏洞共享；入库 `ON CONFLICT(id) DO NOTHING`。改过 URL 的快照 id 复算不上，归档安装直接报「证据快照元数据哈希不匹配」。
- 正文落盘 `<data>/evidence/blobs/<hash 前两位>/<hash>.bin`，与可清理的 `data/traffic` 目录独立；写入先落 `<data>/evidence/.staging`，`Sync` 文件与目录后 `rename`。哈希校验（`verifyFile` 复算 SHA-256 与长度）在读取、导出、下载、归档安装四处都跑，长度或哈希不符即「证据正文校验失败」。
- 采集侧 `ReadEvidence` 持写锁读 `exchanges` 与 `exchange_bodies`，正文溢出走 blob，旧目录记录读 `request.http` / `response.http` 并切头，读完释放锁；读期间删原流量伤不到已复制内容。
- 列表接口清空 `req_head` / `resp_head`（`trafficSummary`），详情才给头与 8192 字节预览；正文含 NUL 或非 UTF-8 时回「[二进制正文，N 字节；请下载查看]」，原字节只经 `download=1` 出。
- 快照没有内容更新接口，唯一写入路径是采集时的落盘。

## 绑定模型

表 `finding_traffic_bindings`，字段：`finding_id`、`snapshot_id`、`role`、`note`、`position`，唯一键 `(finding_id,snapshot_id)`。

- `role` 四值：`baseline`（正常对照）、`proof`（漏洞证明）、`verification`（补充验证）、`supporting`（辅助证据，默认）。空值落 `supporting`，其余报「无效的流量用途」。用途取值对齐「上游参考实现」的漏洞上报工具指引，只取可选绑定约定，不加必填校验。
- `NormalizeTrafficRefs` 逐条 trim `traffic_id`，空值报错；同一批内重复 `traffic_id` 只留第一条，数组顺序即初始证据顺序。
- `position` 新绑定取 `MAX(position)+1`。排序走 `PUT /order`，必须传全量 `binding_ids`：长度不等于当前绑定数 → `ErrEvidenceConflict`；任一 id 不在当前集合 → 同样冲突。
- `version` 是乐观锁：新增生效、改 `role` / `note`、删除、重排都让 `evidence_version + 1`；无变化的追加不涨。`PATCH` / `DELETE` / `PUT` 必传 `version`，缺则 400。

## 报告版本门禁

两个字段：`findings.evidence_version`、`findings.report_evidence_version`，迁移默认 0。

- 判据：写报告时 `evidence_version` 等于库内当前值 → `report_evidence_version` 同步为同值；不等 → `ErrEvidenceConflict` → HTTP 409「流量证据已变更，请刷新后重试」，本次正文不落库。
- 陈旧标记：`stale := f.Report != "" && f.EvidenceVersion != f.ReportEvidenceVersion`。命中时报告尾部写「证据已变更，详细报告待更新。」；写过 -1 的老报告必命中。
- 报告章节骨架固定：`## 关联流量证据`、`证据版本：N；绑定数量：M。`，逐条 `序号. **证据 #bindingID · role** — \`METHOD URL\`，状态码 N`，`note` 跟缩进行；单条 Markdown 追加 `evidence/<finding_id>/<binding_id>/request.http` 相对链接。
- 导出前封版：`StageFindingsExport` 在一个证据事务里读出全部绑定与两个版本号、复制私有正文副本，HTTP 响应开始之后证据再变也污染不到已冻结的包。CSV 额外两列「流量证据数量」「流量证据ID」（绑定 ID 逗号拼接）；`md-zip` 每包给 `manifest.json`、`request.http`、`response.http`、`request.bin`、`response.bin`。

## 回滚语义

- 全部写路径套 `WithEvidenceTx`：`pg_advisory_xact_lock(7337741004)` 串行化跨进程证据写入，读、导出、GC 也在这把锁下。
- 单事务整批回滚：任一绑定失败（id 不存在、正文缺失、blob 写失败、SQL 失败）本次操作全废。随上报绑定失败时连漏洞与探索节点一起回滚，四种故障（missing_id / missing_body / disk_failure / database_failure）都断言 `findings=0`、`nodes=0`，不生成部分记录，不提前触发报告 Agent。
- 已落盘 blob 允许成孤儿：`Collect` 先给无引用快照打 `unreferenced_at`，删 24 小时前的行，再按 `req_hash ∪ resp_hash` 白名单遍历 `blobs` 与 `.staging` 清 `.bin`（mtime 不足 24 小时保留）。清理器每小时跑一次。
- 无包可省略绑定：`traffic_refs` 为空照常上报与写报告，命令输出、日志留作可验证证据，正文里写清未绑原因。
- 删除漏洞级联移除绑定；共享快照因另一条绑定仍在，GC 不收，删掉一条 finding 后 `Collect(now+48h)` 仍能 `OpenBody` 读出原文。

## API 面

基址 `/api/exploration/findings/{id}/traffic`，`{id}` 是独立漏洞记录 ID；`context_task` 查询参数校验任务可见性与继承只读，请求体上限 1 MiB。

| 方法 / 相对路径 | 入参 | 出口 |
| --- | --- | --- |
| `GET` | `context_task` | 200 有序摘要 + `version` + `report_version`，头部清空 |
| `POST` | `traffic_refs[{traffic_id,role,note}]` | 200 全量清单；空数组 400「请选择流量」 |
| `PATCH /{binding_id}` | `version`、`role`、`note` | 200 回读清单 |
| `DELETE /{binding_id}` | `version` | 200 回读清单 |
| `PUT /order` | `version`、`binding_ids[]` | 200 回读清单 |
| `GET /{binding_id}` | — | 200 `binding` + 请求/响应各 8192 字节预览 |
| `GET /{binding_id}/body` | `side`、`offset`、`length`、`download=1` | 200 JSON 预览；`download=1` 回原字节 + `Content-Length` + `evidence-<binding_id>-<side>.bin` |

状态码边界：

- 400：finding id 或 binding id 非正整数、JSON 解不开、缺 `version`、`binding_ids` 缺失、`POST` 空 `traffic_refs`。
- 403：`context_task` 命中继承漏洞且为写操作 →「继承漏洞只读，请在来源任务中修改」。
- 404：漏洞不存在、上下文任务不存在、漏洞不在该任务上下文、绑定不属于该漏洞（`WithBinding` 遍历找不到 → `ErrEvidenceNotFound`）。
- 409：`evidence_version` 与库内不等、`PUT /order` 提交非全量集合、任务已删或归档排队中（`ErrTaskArchiveState`）。
- 422：其余证据错误（`evidenceError` 兜底 `StatusUnprocessableEntity`），含正文哈希校验失败、`side` 不是 `request` / `response`、`offset` / `length` 为负、`offset` 超出正文长度。

## 失败模式与判据

1. 报「流量证据已变更，请刷新后重试」→ 重跑 `GET` 拿新 `version` 重写正文，不重试同一次提交。
2. 报告尾出现「证据已变更，详细报告待更新。」→ `report_evidence_version` 落后，说明写的是旧证据集；取新版本重写。
3. `POST` 同一 `traffic_id` 回 200 但绑定数不变、`version` 不涨 → 快照已绑，按成功处理。
4. `POST` 回 409 且 `PUT /order` 也 409 → 手上绑定集合已过期，先 `GET` 全量再重排。
5. 回 403 → 该漏洞属于上游任务，写入改在来源任务上下文做。
6. 下载或 `OpenBody` 报「证据正文校验失败」→ 元数据与 blob 不符，走归档重装（`InstallSnapshots` 先校验并装正文，再事务恢复元数据与绑定），不就地改文件。
7. 删掉原流量后仍能读证据即为正确；读不到先查绑定是否真存在，再查 blob 是否被误清。
8. 大正文卡顿：下载走 `Binding` + `OpenBody` 在证据锁外流式，`WithBinding` 回调里 `io.Copy` 大文件会占着全局证据锁，堵死全进程写入。
9. 排序后条目顺序没变 → 传的是子集或漏了 id，`PUT /order` 只认全量列表。

## 与既有卡衔接

- 采集与留存口径 → `recon\evidence-hygiene`：它管截图、HAR、Cookie 该留下什么，本卡接在其后，管留下的报文怎么冻成证据。
- 报告成文与格式 → 报告渲染卡；本卡只提供版本门禁、章节骨架与导出包结构。
- 复盘一条链：原流量 → 快照（哈希）→ 绑定（用途/顺序）→ 版本（证据 vs 报告）→ 导出 zip，任一环断掉，回本卡「失败模式与判据」逐条比。
