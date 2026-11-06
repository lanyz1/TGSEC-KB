<!-- archived from /root/.hermes/skills/security/ollama-unauth/SKILL.md on 2026-10-21 -->

---
name: ollama-unauth
description: >-
  授权目标上 Ollama HTTP API 未授权：/api/version、/api/tags 列模型。
  HITCON ZD-2026-00572 同类。用户提到 Ollama、11434、/api/tags、本地大模型未授权、
  CVE-2024-37032、CVE-2026-7020 时使用。默认只 GET。广谱 1day 走 1day-nuclei-kit。
---

> 归档卡：原目录 `/root/.hermes/skills/security/ollama-unauth`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/ollama-unauth/…')`，不要相对 `references/legacy/` 解析。

# Ollama 未授权 API

**前提**：目标在 `config/scope*.json`。默认 **只 GET**。禁止 pull/push/真对话。

| 档 | 成立 | 不算 |
|----|------|------|
| L1 | `/api/version` JSON `version`，或标题 Ollama | 空 200 / 只开了端口 |
| L2 | 未授权 `GET /api/tags` 列出 `models` | 空数组当已接管 |
| L3 | 路径穿越写文件（CVE-2024-37032 / 7020） | 先问；探针不默认做 |

```bash
python3 tools/ops/ollama_unauth_probe.py --base https://授权站 --case <案卷>
# 假模型探 generate 鉴权（仍不 pull）
python3 tools/ops/ollama_unauth_probe.py --base https://授权站 --case <案卷> --deep
```

## 四刀

1. **口** — `:11434`，反代常在 `/` 或 `/ollama/`  
2. **GET** — `/api/version` → `/api/tags` → `/api/ps`  
3. **鉴权** — `--deep` 对不存在模型 POST `/api/generate`：400/404 且无 401 = 写面裸奔  
4. **停** — 列到模型就交差；不要 `pull` 占磁盘，不要对真实模型 `generate`

## 投毒验证（授权内，L3+）

如需证明写面开放（已授权），可做**标记模型投毒**：
```bash
POST /api/create -d '{"model":"pt-marker-<hash>","from":"<最小已有模型>"}'
# 写入→读回→删除
POST /api/delete -d '{"model":"pt-marker-<hash>"}'
```

### ⚠️ 坑位（188台实战踩出）

1. **CPU推理的 Ollama 做27B生成会打瘫主机**——`/api/tags` 45s超时，连清理都做不了
2. **投毒验证用最小模型** / `num_predict=1`，或只做「写入→读回」不做 generate
3. **磁盘满** = 无法建模型（不是鉴权，是环境限制）
4. **清理残留**：若 `/api/delete` 超时拿不到回执，保留披露，后台循环重试

真源：`docs/playbooks/Ollama未授权API手法.md`
