---
name: ghsa-diff-unauth-mining
description: Use when 已知产品版本要挖未修补漏洞. 上游advisory差分+实证.
---

# GHSA 版本差分矿脉开采

> 面向「手上有一批已知产品+版本的资产」的**批量未修补漏洞发掘**。
> 触发：资产池要复测 / 之前判负的目标要复核 / 被问"能不能自研 0day" / 版本差分。

## 0. ★第零铁律：判负必须做版本差分，禁止"试一个 CVE 就判负"

一台产品同时有 **20 个漏洞是常态**。挑 1–2 个已知 CVE 试 PoC、不通就把整台判负 —— 这是**假判负**，会把打穿的机器写进台账"判负"。
**版本号必须实测**（§2），禁止沿用日志/印象/上轮记录的版本 —— 版本记错会让全部后续推理失效（曾把 Langflow 1.12.2 记成 1.6.0，反推出"已修补"的错误结论）。

## 1. 三步流水线

### S1 拉上游 advisory 全库（含修补版本 = 差分基准）
```bash
# 每仓库 1 次请求, 未认证 60/h 配额, 省着用; -L 跟随 301, per_page=30, 大响应给足 -m
curl -sL -m 90 -x $PROXY -o ghsa/<repo>.json \
  "https://api.github.com/repos/{owner}/{repo}/security-advisories?per_page=30"
# 完整性自检: 大 JSON 常被 -m 截断 -> tail -c 2 | grep ']' 才算完整
```
返回字段：`ghsa_id` / `cve_id` / `severity` / `state` / `vulnerabilities[].vulnerable_version_range` / `patched_versions` / `description`（**含完整 PoC、端点、curl**）。

### S2 实测目标真实版本（全部走公开端点，见 §3）

### S3 差分 + 实证
`目标版本 ∈ vulnerable_version_range` ⇒ 输出「未修补清单 + 端点」，再逐条**实证**（§4 判据）。
脚本：`ghsa_diff.py`（差分/命中）、`ghsa_detail.py`（提取 PoC 详情）。

## 2. 常用版本端点（均为公开端点）

| 产品 | 端点 | 返回 |
|---|---|---|
| Langflow | `/api/v1/version` | `{"version":"1.6.0","package":"Langflow"}` |
| Open WebUI | `/api/version` | `{"version":"0.x.x"}` |
| Gitea | `/api/v1/version` | `{"version":"1.27.3"}` |
| n8n | `/rest/settings` | JSON 内 `versionCli` |
| Qdrant | `/` | `{"title":"qdrant - vector search engine","version":"1.x.x"}` |
| Ollama | `/api/version` | `{"version":"0.x.x"}` |
| Evolution API | `/` | `{"message":...,"version":"2.3.7"}` |
| Dify | `/console/api/version` 或首页 bundle | — |
| Flowise | `/api/v1/version` | — |

**同机多产品**：一台 IP 上常见多产品共存（如 7860=Langflow、另一端口=Flowise）。**产品↔端口必须逐个实测绑定，不许按端口号猜产品**。

## 3. ★判据铁律：零写入证明"无鉴权"

> **空参请求 → 返回"缺参数/对象不存在"(422/500/400 业务错误) = handler 已执行 = 无鉴权**
> **返回 401/403 = 有鉴权**

**必须打对照组**：同时打 3 个"已知需鉴权"端点（`/users/whoami`、列表类端点、key 类端点），**全部 403 才说明差分干净**。只看目标端点的报错不足以定性。

## 4. 纪律（本面的写操作几乎为零）
- **纯 GET 优先**：不写文件、不建账号、不留下载
- **数据不外带第三方**：需要 OOB 回显时用**自己跳板机**，或最优先"**写回目标自身的未认证读端点**"（如把结果写回目标 monitor/messages，再用无鉴权 GET 取回）——自洽闭环、无外部监听、不外泄
- **RCE 验证只跑 `id` / `hostname` / `uname`**，不落文件、不改数据；触发前先评估该路径**是否会产生写残留**（如 Langflow `build_public_tmp` 成功会给匿名用户复制一份 flow）
- **限时预算**：单轮脚本把"页数×超时"算进总时长，否则超 terminal 上限（420s）白跑
- **术语边界（不许吹）**：`0day`＝厂商未知/无补丁/无编号；`厂商未公开`＝advisory 库 `state != published`（API 实测通常 0 条，因其只暴露已发布）；本流水线产出的是**"已公开但我们此前漏判"** ⇒ 报告写「**本次实测确认的已公开面（对应 CVE-xxxx）**」，**禁止写"自主发现/首发"**
- **★假阳防线（差分必踩两处）**：① GitHub `vulnerable_version_range` **常只有单边**（如 `> 2.16.1` 无上界），单靠 range 会把已修版本判成命中 ⇒ **必须加 `patched_versions` 二次判定**（`range 命中 且 实测版本 < patched` 才算真命中）——
- **★SPA fallback 陷阱**：SPA 对未知 API 路径回 index.html(200)，GET 探测会把不存在的端点标成"存在" ⇒ 判据须验 `Content-Type`/首字符，**RCE 类端点一律用 POST 复测**。
- **去重陷阱**：`new=[x for x in got if x not in fids]; fids+=new` 在同页有重复 ID 时会把重复项全部计入 ⇒ 对同一目标重复发请求（曾对同一 flow 发 240 次 POST）。用 `set`。

## 5. 实战案例（2026-09-22）

**上游库**：12 仓库（Flowise/Typebot/Coolify/Gitea/FastGPT/n8n/Open WebUI/Langflow 各 30，Dify 21，Chatwoot 4，Qdrant 1，Evolution 0）⇒ **差分命中 146 条**。

**Langflow 1.6.0 `100.29.254.125`（原台账判负 ⇒ 推翻）**：
- ★ `GET /api/v1/monitor/messages` → **200，64 条真实生产会话**（CVE-2026-21445，≤1.7.0）；跨 2025-09→2026-09，含 PII；业务为 Jira 工单 AI 集成
- `GET /api/v1/monitor/transactions?flow_id=<uuid>` → 200（无鉴权）
- `POST /api/v1/upload/<任意uuid>` 空参 → **422 Field required** = 无鉴权（CVE-2026-55450 面）
- `GET /api/v1/files/images/<flow>/<name>` → **500 not found** = 无鉴权（CVE-2026-33484 IDOR 面）
- 对照 `whoami`/`flows/`/`api_key/` → **403**（差分干净）
- ❌ RCE 判负**有依据**：`build_public_tmp` 需 `AUTO_LOGIN=true` 或 **PUBLIC flow**，6 个 flow 全 `403 Flow is not public` ⇒ 提前不成立，且零残留
- 结论：P0 未认证数据泄露，RCE 不可达

**Flowise 3.0.13**：`GHSA-fhxm-xxcx-g6x3` —— **任何组织成员可未授权读 owner 密码哈希**（patched 3.1.4）；`GHSA-7x8x-vv46-4579` 跨租户/跨组织授权缺失。

### 5.1 池内全量差分（第二轮：任务 1+2）

**流程**：`ver_diff_scan.py`（跳板机批量取版本，12 并发）→ `diff_local.py`（本机对 ghsa 全库差分）→ `diff_priority.json`（筛未认证 + 无修补）。

**结果**：68 台探测 / **28 台拿到精确版本** / **命中 265 条 / 16 台 / 8 台含 critical**。

| 面 | 实测收口 |
|---|---|
| Langflow 公共流 RCE（`CVE-2026-48519`/`33017`）| **判负**：1.6.0 六个 flow + 1.4.0 唯一 flow 全 `403 Flow is not public`；无 cookie `400`。**两次拒绝都在创建对象前 ⇒ 零残留** |
| Flowise 未认证 RCE | **面开、触发不了**：`/api/v1/public-chatflows` 无鉴权(412/404)，但 ID 只走路径参数、HTML 无 UUID、UUIDv4 不可枚举 ⇒ 判负 |
| 「厂商承认漏修」四条 | **全部需认证**（API key / 成员身份）⇒ 未认证路径判负 |

**★ 铁律：差分命中数 ≠ 可打洞数。** 265 条里未认证可真实利用的只有**监控数据泄露**一类（实证 Langflow **1.4.0** `32.192.23.34:8000`：**240 条消息 / 61 session / 6 处 PII**，2026-01-22→02-11）。**未认证面探尽后，增量在认证面或路线 C。**

## 6. 真 0day 的三条路线（不要混进上面的产出）
| 路线 | 概率 | 成本 | 抓手 |
|---|---|---|---|
| **A 补丁绕过** | 中高 | 低 | advisory 正文里常有厂商**自己承认"修补不完整"**的相关绕过（如 Langflow `GHSA-4f6c-2vvp-gw82` 承认 `rate_limit_trust_proxy=true` + 重复 XFF 头时仍可绕）。有该配置即可打出未编号新绕过 |
| **B 未审计新面** | 中 | 中 | AI 栈新功能：Ollama `/api/push`·`/api/blobs`、Qdrant snapshot/API-key、Dify plugin daemon gRPC、Evolution `/manager` |
| **C 源码审计+fuzz** | 低 | 高 | 真 0day 唯一正路，需本地起环境与持续投入 |
