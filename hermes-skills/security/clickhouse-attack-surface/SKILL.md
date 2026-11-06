---
name: clickhouse-attack-surface
description: "Use when ClickHouse exposed: default creds, file()/Executable walls, url() SSRF pivot."
---

# ClickHouse 高权限攻击面

**适用**: 暴露的 ClickHouse（8123/9000/9440）——从查询权限推向宿主面。
来源: 2026-10 HEIYT 案（差临门一脚：user_scripts 墙）。

## 链

1. `default` 弱口令 → `CREATE USER` 建高权用户（access_management）
2. `file()` 写: 可写 `user_files/`（marker / SSH pubkey 实战写过）
3. `CREATE EXECUTABLE` 语法允许但**运行时仅加载 `user_scripts/` 目录** → `file()` 无法穿越（**Code 291 = 该墙**；Code 482 = 预置 EXECUTABLE 字典缺失）
4. `url()` SSRF 存活 → 打内网服务 / IMDS（联动内网面）
5. named collections: 全 `display_secrets=0`（拿不到明文）→ 换角度
6. MySQL 引擎 `ENGINE=MySQL(...)` 错误泄用户名（1045）
7. **本机 Redis 经 CH 可达** → MARKER INSERT 验证（CH 当 pivot）
8. 数据面: `system.tables` / `system.users` / `system.settings` 自查权限与库存

## 判据

- 起步: `SELECT version()` + `system.users` 摸权限面
- exec 路线不通时评估: config.xml 可写? → 重载/重启点；`user_scripts/` 目录本身可否写（file() 只到 user_files）
- CH 常与 Grafana/Metabase/Airflow/OpenMetadata 混部（数据平台套装）—— 服务面互打

## When to reuse

- 案例: `domains/web-security/case-lessons/heiyt-gfast-scrm-clickhouse.md`
- 邻域: `openmetadata-pentest` / `apache-airflow-pentest`（同套装）
