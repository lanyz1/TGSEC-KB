<!-- archived from /root/.hermes/skills/security/langflow-unauth-rce/SKILL.md on 2026-10-21 -->

---
name: langflow-unauth-rce
description: >-
 授权目标上 Langflow（Python LLM 工作流）未授权 RCE：CVE-2025-3248
 （/api/v1/validate/code 装饰器面）、CVE-2026-9198（auto_login→validate/code）、
 CVE-2026-0770（exec_globals）。用户提到 Langflow、validate/code、auto_login、
 CVE-2025-3248、CVE-2026-9198、%0a WAF 换行绕过时使用。
 403 先做路径编码差分；授权内全链（exec / IMDS 直接做）。
 广谱 1day 仍走 1day-nuclei-kit。
---

> 归档卡：原目录 `/root/.hermes/skills/security/langflow-unauth-rce`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/langflow-unauth-rce/…')`，不要相对 `references/legacy/` 解析。

# Langflow 未授权 RCE（Cursor Skill）

## 何时用

- 标题/体出现 Langflow，或 `/api/v1/auto_login` `/api/v1/validate/code`
- 用户点名 CVE-2025-3248 / CVE-2026-9198 / CVE-2026-0770 / CVE-2024-37393
- nginx 对 `/api/v1/validate` 返回 403，怀疑 `%0a` 路径绕过
- `nday_route` hit `langflow`

## 真源（按序）

1. `docs/playbooks/Langflow未授权RCE手法.md`
2. `tools/ops/langflow_probe.py`
3. `tools/1day-kit/custom-templates/langflow-unauth-rce-cve-2026-9198.yaml`
4. `tools/1day-kit/custom-templates/langflow-validate-unauth-cve-2025-3248.yaml`
5. 学习样本：SAE-20260827-822f5b-A003-PUB（WAF `%0a` + 3248 + 云横向）

## 强制步骤

1. 目标在 `config/scope*.json`。
2. 指纹 + 三条并行面：
 ```bash
 python3 tools/ops/langflow_probe.py detect -u <URL> --case <案卷>
 python3 tools/1day-kit/od_kit.py nuclei --url <URL> --case <案卷> \
   -t tools/1day-kit/custom-templates/langflow-unauth-rce-cve-2026-9198.yaml \
   -t tools/1day-kit/custom-templates/langflow-validate-unauth-cve-2025-3248.yaml
 ```
3. **L2**：`auto_login` 出 token **或** 无票 `validate/code` 对无害表达式有业务响应。  
   普通路径 403 时，detect 会做 `%0a` 路径差分（不发破坏代码）。
4. **L3** 授权内直接做 `exploit` / IMDS。RCE 后云横向走 `cloud-metadata-harvesting`。
5. 证据：`测绘/1day/` · 票打码 · STATUS 写版本、WAF 差分、哪条 CVE 面成立。

## 成功口径

| 级 | 口径 |
|----|------|
| L1 | `/api/v1/version` 或前端确认 Langflow |
| L2 | 超管 JWT **或** 无票 code 端点可达 **或** `%0a` 把 403 打成业务响应 |
| L3 | 授权内受控回显（直接做） |

9198 修复线：≥1.10.1。3248 为更早验证端点面，升级到厂商修复版。

## 2026新增CVE（188台实战补充）

| CVE | 性质 | 在野速度 |
|---|---|---|
| CVE-2026-33017 | 公开 flow-build 端点→**未授权RCE** | **20小时**（早于公开PoC） |
| CVE-2026-5027 | `/api/v2/files` 路径穿越→文件写入→RCE | 正在被活跃利用 |
| CVE-2026-105740 | <1.9.0 **已认证** RCE: MCP server transport=Stdio, `command` 直接进 `bash -c "exec {command}"` 零校验/零沙箱; `env` 可注 LD_PRELOAD。拉取 server list 时立即执行 | 需任意已认证账号; 修复 1.9.0 |

**坑**：1.4.0/1.6.0 已强制 API key（`No valid api key found.` 是设计不是漏洞），版本线必须实测。

## 不要做

- 未授权扫公网 7860
- 只报 CVE 号 / 只扫 health 结案
- 耗余额/删站/改原超管密码先问

## 衔接

- 得 shell → `linux-post-exploit` / `cloud-metadata-harvesting`
- 同机 Flowise → `flowise-internal-header-rce`
- 广谱 LLM → `llm_surface_probe`
- 入库 → `cve-daily-intel`
