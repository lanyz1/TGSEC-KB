<!-- archived from /root/.hermes/skills/security/flowise-internal-header-rce/SKILL.md on 2026-10-21 -->

---
name: flowise-internal-header-rce
description: >-
 授权目标上 Flowise（LLM 低代码编排）内部头密钥泄露衔接到 NodeVM 面：
 CVE-2025-58434 变体（GET /api/v1/apikey + x-request-from: internal）与
 CVE-2026-46442（/api/v1/node-custom-function）。用户提到 Flowise、
 x-request-from、apikey 未授权、NodeVM 沙箱、CVE-2025-58434、CVE-2026-46442 时使用。
 授权内全链（指纹→内部头密钥→NodeVM 逃逸→IMDS）。
 广谱 1day 仍走 1day-nuclei-kit；CVE 入库走 cve-daily-intel。
---

> 归档卡：原目录 `/root/.hermes/skills/security/flowise-internal-header-rce`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/flowise-internal-header-rce/…')`，不要相对 `references/legacy/` 解析。

# Flowise 内部头 → 密钥 → NodeVM（Cursor Skill）

## 何时用

- 标题/体出现 Flowise，或路径 `/api/v1/apikey` `/api/v1/node-custom-function`
- 用户点名 CVE-2025-58434 / CVE-2026-46442 / `x-request-from: internal`
- `nday_route` hit `flowise`
- `llm_surface_probe` 认出 flowise

## 真源（按序）

1. `docs/playbooks/Flowise内部头密钥与NodeVM逃逸手法.md`
2. `tools/ops/flowise_probe.py`
3. `tools/1day-kit/custom-templates/flowise-apikey-internal-header.yaml`
4. 学习样本：SAE-20260827-822f5b-A005-PUB
5. 同族 Langflow → `langflow-unauth-rce`

## 强制步骤

1. 目标在 `config/scope*.json`。
2. L1 + L2：
 ```bash
 python3 tools/ops/nday_route.py -u <URL> --case <案卷>
 python3 tools/ops/flowise_probe.py detect -u <URL> --case <案卷>
 python3 tools/1day-kit/od_kit.py nuclei --url <URL> --case <案卷> \
   -t tools/1day-kit/custom-templates/flowise-apikey-internal-header.yaml
 ```
3. **L2**：无头 vs `x-request-from: internal` 打 `/api/v1/apikey`。阳性 = JSON 含 Key/Secret（值打码）。
4. 授权内直接 POST `node-custom-function` 沙箱逃逸 + `169.254.169.254` IMDS。
5. 证据：`测绘/1day/` · STATUS 写版本、内部头差分、是否 ≤3.1.2。

## 成功口径

| 级 | 口径 |
|----|------|
| L1 | 版本/首页确认 Flowise |
| L2 | 带内部头未认证读到 apikey（打码） |
| L3 | 授权内受控命令回显（直接做） |

影响：≤3.1.2。修 **> 3.1.2**。

## 不要做

- 未授权扫公网 Flowise
- 只报 CVE 号结案
- 公开桶只列不拖全量

## 衔接

- 得 shell → `linux-post-exploit` / `cloud-metadata-harvesting`（授权内直接做）
- 同机 Langflow → `langflow-unauth-rce`
- 广谱 LLM 面 → `llm_surface_probe` · `LLM与Agent安全手法.md`
- 入库 → `cve-daily-intel`


---

## 外部库增量（2026-10-11 分享包）

## Flowise MCP 环境变量大小写绕过（同族第三条，研究 PoC）

面：MCP 节点的环境变量/变量名**大小写**校验不一致（过滤用一套写法，实际执行用另一套）→ 绕过变量注入黑名单。
试法：把被拦的变量名换大小写/混写（`HTTP_Proxy` / `http_proxy` / `HtTp_Proxy`），再试同一注入点。
**类级**：任何“变量名/键名黑名单”都要做大小写、全半角、下划线/连字符、重复参数的差分。
`poc-db/exploitarium/flowise-mcp-env-case-bypass-poc`（本机未复现）；全 39 条 → `1day-nuclei-kit` 的 `references/exploitarium-pattern-index.md`。
