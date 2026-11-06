# PentAGI 中国网络部署实战记录 (2026-07-21)

## 环境
- Windows 10, Docker Desktop 29.6.2
- CPU: AMD Ryzen 7 9800X3D (SVM enabled)
- 网络: 中国大陆 (GFW)
- 目标: deploy pentAGI + run automated penetration test

## 关键发现

### 1. Docker Hub / ghcr.io 完全不可达
所有镜像拉取卡在 "Pulling fs layer" → 无下载进度。
解决方案: Docker Hub 代理 (127.0.0.1:10808) + registry-mirrors。

### 2. WSL2 问题
即使 BIOS SVM 已开启、Windows Features 已启用，WSL 仍报 "virtualisation is not enabled"。
最终无需 WSL — Docker Desktop 通过 Hyper-V 后端正常工作。

### 3. `DEEPSEEK_PROVIDER` 陷阱
`DEEPSEEK_PROVIDER=deepseek` → 模型名变 `deepseek/deepseek-v4-flash` → DeepSeek API 400。
必须留空。

### 4. bcrypt $2a vs $2b
Python bcrypt 生成 `$2b$10$...`，Go bcrypt 只认 `$2a$10$...`。不替换前缀则登录失败。
写 SQL 必须用文件 pipe（`cat file.sql | docker exec -i pgvector psql`），避免 shell 的 `$` 变量插值。

### 5. `.env` 更改不生效
`docker compose restart` 不重新读取 `.env`。必须 `--force-recreate`。

### 6. DuckDuckGo 搜索被限流
返回 202。替代方案: 自建 SearXNG 容器（searxng/searxng:latest）加入 pentagi-network。
SearXNG 默认 CSRF 保护拦截 JSON API → 需配置 `settings.yml` 设置 `limiter: false` + `formats: [html, json]`。

### 7. pentAGI 搜索 Agent 循环
`duckduckgo 202` + `searxng 429/403` → `search` 失败 → 重试循环。
Agent 永远不会执行到 terminal 命令阶段。需要用 DB 命令直接清理卡住的 flow。

### 8. Kali 容器工具缺失
`nslookup`, `curl`, `nmap`, `nc` 均需手动安装。使用 tuna.tsinghua 镜像加速 apt。

## 修复后的正常状态

```bash
# 4 containers running
docker ps
# pentagi, pgvector, scraper, pgexporter

# 验证 API
curl -sk https://localhost:8443/api/v1/providers/
# {"data":[{"name":"deepseek",...}]}

# 验证 SearXNG
curl "http://localhost:8888/search?q=test&format=json"
# {"query":"test","results":[...]}
```
