---
name: llm-tool-exec-container-root
description: "Use when an LLM gateway exposes tool execution: sandbox → container root + tunnel persist."
---

# LLM 工具执行沙箱 → 容器 root

**适用**: LLM 网关/编排器暴露 `/tools/execute` 类工具执行接口（白名单绕法）。
来源: 2026-10 xiniuzi Shannon 栈案。

## 链

1. 发现工具执行面: `/tools/execute`（或 `/execute` `/run`）——白名单常见形态: bash 禁元字符，但 `python3` / `file_write` 放行
2. **白名单绕法**: 用放行的 `python3 -c` 做完整命令执行；`file_write` 直落文件
3. 容器身份确认: `id` → 常为 uid=0（容器 root）
4. **持久化**: 装 sshd + `ssh -R 1823` 反向隧道 = 可重复进入（不依赖工具接口存活）
5. 凭据面: Postgres `auth.users` 改密 → 登录 orchestrator / daemon（LLM 基础设施凭据层）
6. 网关侧: NewAPI/one-api 专属 Key 外网可用 + billing soft_limit 极大 = 白嫖/盗用面
7. daemon 面: `:8080` daemon JWT 下 `tools/execute` 同样可用（多入口冗余）

## 判据（诚实口径）

- **容器 root ≠ 宿主 root**：无 docker.sock / 无 SYS_ADMIN / volume 写入未落宿主 → 明确定性，勿吹
- 逃逸评估清单: docker.sock、CapEff、cgroup v1、宿主 SSH loopback、共享 FS、K8s SA

## When to reuse

- 命中「LLM 网关 + tools/execute + 容器化编排」→ 本卡
- 案例: `domains/llm-ai-security/case-lessons/xiniuzi-shannon-llm-container-root.md`
- 邻域: `ai-agent-runtime-pentest`（dsh/harness）· `llm-gateway-pentest`（网关侧）
