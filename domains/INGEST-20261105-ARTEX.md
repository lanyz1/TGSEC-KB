# INGEST-20261105-ARTEX — 自主渗透框架吸收（13 张卡）

> 日期：2026-11-05 · 批次：`artex-20261105`
> 原则：原文与二进制不入库；只落可复用手法、机制判据与可跑脚本。

## 1. 来源与体量

- 本机路径：`C:\Users\Administrator\Desktop\ARTEX`（只读，未改一字节）
- 体量：**595 个文件 / 11.89 MB**；`.go` 327 · `.tsx` 152 · `.ts` 35 · `.md` 19 · `.png` 17 · `.py` 4 · `.mjs` 4
- 栈：Go 1.26.3（`pgx` / `modernc.org/sqlite` / `go-mitmproxy` / `creack/pty` + `vt10x` / `dnsx` / `bluemonday`）+ Next.js 前端
- 结构：`agent/`（52 文件）· `server/`（103）· `db/`（97）· `web/`（210）· `traffic/` · `intercept/` · `guard/` · `evidence/` · `llmpool/` · `sidequestion/` · `mcphttp/` · `notify/`（24）· `selfupdate/` · `skills/`（3 套技能包）

## 2. 吸收清单（13 张卡 / 155,726 字节）

| 域 | slug | 来源 | 拿走什么 |
|---|---|---|---|
| api-security | `api-recon-runtime-harvest` | `skills/api-recon/`（17.9KB + reference 19.5KB + 6 脚本） | 无凭据把 SPA 壳撑开：hook 登录/权限/菜单 bootstrap 接口 + 结构正确的空 mock → 只录 outbound；Phase 0-5、双门禁、参数触发矩阵、权限树还原 |
| recon | `browser-automation-playwright-cli` | `skills/playwright-cli/`（12.3KB + 9 篇 reference） | playwright-cli 全命令手册：storage-state 复用登录态、request mocking、tracing、video、test generation |
| recon | `finding-traffic-evidence-chain` | `docs/漏洞流量证据.md` + `evidence/store.go` + `report/` | 快照 = 规范化 JSON 的 SHA-256；绑定 role/note/order + 版本乐观锁；证据变动拒旧报告写入 |
| recon | `asset-platform-sync` | `skills/scopesentry/` + `enrich/` + `server/sync_*` | 外部资产平台 API Key 对接、类型映射、部分唯一索引去重、归属优先级 |
| post-exp-tools | `mitm-traffic-capture-and-reclaim` | `traffic/`（traffic.go 77KB + archive/evidence/reclaim） | 录制闸门（256KiB 内联 / 8KiB 预览 / 4MiB 入索引）、blob 分片、WAL 索引、归档与回收预算 |
| redteam-framework | `tool-gate-approval-interception` | `intercept/`（21.7+15.2+6KB）+ `guard/` | PreToolUse/PostToolUse 双钩子、规则存 DB 可删可禁、allow/deny/ask、pending 原子收口、审计与失败归因 |
| redteam-framework | `autonomous-pentest-agent-architecture` | `agent/`（planner 32.9 / worker 30.9 / tools 91.3KB 等） | 六角色分工、工具目录 DB 化但 handler 死绑、`goal_met` 默认不绑、压缩阈值、收官判据 |
| redteam-framework | `pentest-platform-data-model` | `db/schema.sql`（49 张表）+ repository | 任务-会话-资产-发现-流量-证据的实体关系、部分唯一索引、继承只读、幂等播种 |
| ai-infra-security | `llm-key-pool-failover` | `llmpool/` + `agent/provider.go` | 健康打分、软/硬熔断、1m/5m/30m 冷却、幂等安全窗、429→402 改判 |
| ai-infra-security | `side-question-context-budget` | `sidequestion/`（CONTEXT_BUDGET + VALIDATION + 语料） | 侧问题隔离、预算切分与裁剪顺序、断言口径 |
| ai-infra-security | `notify-channel-secret-masking` | `notify/`（mask/redact/ssrf/sign 测试齐全） | `__masked__` 保留末 6 位、字节 vs 字符两套截断、SSRF 网段判据、钉钉与飞书签名反序 |
| ai-infra-security | `hardened-self-update` | `selfupdate/`（含 stage/bootstrap） | 源写死 + 5 host 白名单 + 逐跳重定向校验 + SHA256SUMS + 三次回滚标记 |
| ai-infra-security | `mcp-http-sse-client` | `mcphttp/client.go` | Streamable HTTP 与 legacy SSE 两套关联、8MB 单行上限、三层错误面 |

随卡入库的可跑脚本（`api-recon-runtime-harvest/scripts/`，8 文件）：`harvest_static.py` · `spider_mpa.py` · `build_perm_tree.py` · `extract_route_map.py` · `runtime_harvest.js` · `preload.js` · `package.json` · `package-lock.json`。语法复核：4 个 Python 编译通过、2 个 JS `node --check` 通过；`puppeteer-core ^23.11.1` 由 `scripts/package.json` 声明，卡内第 302 行给出 `cd recon && npm install`。

## 3. 升级的卡

- `api-security/api-recon-and-docs` —— 1.8KB → 3.1KB，新增第 5 节「RUNTIME HARVEST（无凭据把 SPA 壳撑开）」：静态/运行时两层模型、壳撑开三步、三张关联卡指路。
- 顺手修掉该卡一条历史死链：`../business-logic-vulnerabilities/SKILL.md` → `../../business-logic/business-logic-vulnerabilities/SKILL.md`。

## 4. 未吸收

| 源 | 体量 | 处置 |
|---|---|---|
| `web/` | 210 文件 4.9MB | 业务前端，与卡库无关 |
| `server/` | 103 文件 1.1MB | API handler 与业务耦合，只取模式 |
| `db/` | 97 文件 1.1MB | sqlc 生成物，只抽表关系 |
| `screenshots/` | 15 文件 3.4MB | 图不做素材 |
| `CHANGELOG.md` | 76.8KB | 只在写「演进决策」案例时回读 |
| `cmd/` `config/` `*.sh` `docker-compose*` | 小 | 部署壳 |
| 作者自有 agent 库（`norma`） | 外部依赖 | 只参考设计，不入库 |

## 5. 投毒与供应链审计

- 外联面：全仓引用域名只有通知渠道（`oapi.dingtalk.com` / `api.telegram.org` / `qyapi.weixin.qq.com` / `open.feishu.cn`）、GitHub 更新链路，其余为 `example.com` / `acme.com` / `attacker.tld` / `fixture.invalid` / `10.10.10.20` 等测试串。
- 遥测：`telemetry` / `analytics` / `usage_report` / `license_key` / `activate` / `beacon` / `device_id` 全仓 0 命中。
- 动态执行：327 个 `.go` 里 `exec.Command` 0 命中；`os.system` / `subprocess` / `child_process` / `eval(` 0 命中；终端能力走 `creack/pty` + `vt10x`。
- 供应链点甲：`install.sh:22` 是 `curl -fsSL https://get.docker.com | sh`（标准 Docker 引导），已在 `hardened-self-update` 卡内以对照写法记录。
- 供应链点乙：`selfupdate` 把发布源写成常量、带 5 域名白名单与逐跳校验——正面样板，已整段吸收。
- 供应链点丙：依赖作者自有库 `norma v0.4.3`，单点上游；只读参考，不引入。

## 6. 署名剥离

入库前扫过并改写的上游痕迹：产品名与仓库名（`ARTEX` / `artex` / `artex.local` / `artex.example.com` / demo 站）、作者名与账号（`Autumn-27`）、自有库名（`norma`）、文档内交叉引用的三个第三方项目名（漏洞上报工具指引、审批详情组件统一改写为「上游参考实现」；资产同步平台改写为「Scopesentry 类资产平台」，仅保留其真实 API 路由前缀 `/api/sync/scopesentry/` 与 `get_project` 等调用名——那是集成协议事实，不是来源署名）。

保留的只有协议事实：`api.github.com` / `github.com` / `objects.githubusercontent.com` / `release-assets.githubusercontent.com` / `raw.githubusercontent.com`、四个通知渠道端点、`MCP-Protocol-Version: 2025-06-18`。

软化词复核：13 张卡 + reference + 脚本全量扫描，`建议|可能|通常|理论上|风险|授权|请确保` 仅在两处命中且均为代码/自然词——`preload.js` 的登录页正则里 `未授权|授权`（匹配字面量）、`尽可能完整地发现`（祈使句）。正文无 hedging。

## 7. 检索注册与验收

- 镜像：13 张卡 → `hermes-skills/security/<slug>/`（含 `api-recon-runtime-harvest` 的 10 个文件与 `browser-automation-playwright-cli` 的 10 个文件）。
- 索引重建：`arsenal_build.py` → **2,349 → 2,362 张卡**，`term_df` **355,701** 词项，库体 **354 MB**；旧库备份 `arsenal/arsenal.db.bak-20261105161653`。
- 状态还原：重建后按旧库快照回填 `status`，`disabled` 仍是 **1,774**（与重建前逐条一致，归档卡的检索权重不变）。
- 回归：`selftest.py` **29/30**，与重建前基线**逐条一致**（唯一 miss 是历史项 `confluence rce`，重建前后返回同一组卡）。
- Windows 侧记：`selftest.py` 用 `text=True` 读子进程，控制台默认 GBK 会把子进程 UTF-8 输出读崩 → 0/30 假阴性。跑法必须带 `PYTHONUTF8=1`（`cardfind.cmd` 里的 `PYTHONIOENCODING=utf-8` 只管直接输出，管不到子进程）。
- 命中实测（`cardfind.cmd`，13 条自然问句）：`api-recon-runtime-harvest` 1025.9、`hardened-self-update` 1480.4、`finding-traffic-evidence-chain` 1129.4、`mcp-http-sse-client` 2198.0、`browser-automation-playwright-cli` 982.7、`asset-platform-sync` 1120.8、`side-question-context-budget` 1481.5、`llm-key-pool-failover` 1253.4、`mitm-traffic-capture-and-reclaim` 900.5、`pentest-platform-data-model` 1014.7、`autonomous-pentest-agent-architecture` 861.5、`notify-channel-secret-masking` 1353.9、`tool-gate-approval-interception` 1472.1（最后两张用「钉钉 飞书 通知 webhook 去密」「PreToolUse PostToolUse 钩子 审计」问句命中 TOP1）。

## 8. 未做的动作

- 未 `git add` / 未 commit / 未 push（推送等指令）。
- `MASTER.md` 主题表未改；域内 `README.md` 的计数已按实际文件重算，并追加「2026-11-05 增量（框架吸收）」小节；`ai-infra-security` 原本缺 README，按同格式新建。
- 上游若发新版或插件被覆盖，`api-recon-runtime-harvest/scripts/` 与各卡正文需按本文件重跑一次。

---

@TGSEC社区 · @TGSEC-Qtzuu 整理
