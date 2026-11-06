# 告警

管理新增或更新记录的自动化通知——添加、列出、修改订阅，或使用**轮询**按需获取更新。

**打开交互式规范：**
- [打开 Redoc（交互式）](https://docs.vulners.com/docs/api/redoc.html)
- [打开 Swagger（交互式）](https://docs.vulners.com/docs/api/swagger.html)

---

## 工作原理

告警基于**订阅**构建——即保存的搜索查询和投递设置。订阅评估和投递按照 `crontab` 定义的时间表执行。

### 投递方式

| 方式        | 工作原理                                                                                                                      |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **邮件**   | 根据 cron 表达式按计划投递（HTML 或 JSON）。                                                                 |
| **Webhook** | 根据 crontab（最短每分钟一次）向你的端点定时发送 HTTP POST 请求。                                                   |
| **轮询** | 结果存储在 Vulners 端；你的应用通过拉取端点获取。                                                    |

### 时间戳来源

`timestamp_source` 参数定义 Vulners 根据哪个时间戳来判断公告是"新增"还是"已更新"。

| timestamp_source 值            | 触发时机…                                            |
| -------------------------------- | --------------------------------------------------------- |
| published                        | 公告刚刚发布。                              |
| modified                         | 任何核心公告字段发生变更（默认）。                              |
| timestamps.updated               | 核心内容已刷新。                                   |
| timestamps.enriched              | AI 增强、链接或关联已添加。                                             |
| timestamps.metricsUpdated        | CVSS、EPSS、AI 评分已重新计算。                        |
| timestamps.webApplicabilityUpdated | Web 适用性标志已变更。                        |
| timestamps.reviewed              | 审核/QA 检查已完成。                                |

### 查询类型

| 类型         | 含义                                      |
| ------------ | -------------------------------------------- |
| query        | 经典 Lucene 查询                         |
| software     | 基于 CPE 的软件查询                     |
| host/generic | 通用主机（软件 + 可选应用/操作系统/硬件） |
| host/linux   | Linux 主机（操作系统 + 软件包列表）       |
| host/windows | Windows 主机（操作系统 + KB 列表 + 软件包）       |

---

## 订阅（v4）

### 创建订阅

**认证**：需要 `X-Api-Key` 标头。

**请求：** `POST /api/v4/subscriptions/create/`

```bash
curl -X POST "https://vulners.com/api/v4/subscriptions/create/" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Critical Linux vulns",
    "query": { "type": "query", "query": "cvss:[7 TO *] AND family:cve" },
    "delivery": { "type": "webhook", "address": "https://example.com/webhook", "crontab": "0 * * * *" },
    "bulletin_fields": ["id", "title", "description", "cvss"],
    "timestamp_source": "modified",
    "is_active": true,
    "send_empty_result": false
  }'
```

### 列出订阅

**请求：** `GET /api/v4/subscriptions/list/`

```bash
curl -G "https://vulners.com/api/v4/subscriptions/list/" -H "X-Api-Key: YOUR_API_KEY"
```

### 获取订阅

**请求：** `GET /api/v4/subscriptions/get/`

```bash
curl -G "https://vulners.com/api/v4/subscriptions/get/" -H "X-Api-Key: YOUR_API_KEY" \
  --data-urlencode "subscription_id=subscription-uuid"
```

### 更新订阅

**请求：** `PUT /api/v4/subscriptions/update/`

```bash
curl -X PUT "https://vulners.com/api/v4/subscriptions/update/" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "subscription-uuid",
    "name": "Updated name",
    "query": { "type": "query", "query": "package:nginx severity:high" },
    "delivery": { "type": "webhook", "address": "https://example.com/webhook", "crontab": "*/30 * * * *" },
    "sendEmptyResult": "true"
  }'
```

### 删除订阅

**请求：** `DELETE /api/v4/subscriptions/delete/`

```bash
curl -X DELETE "https://vulners.com/api/v4/subscriptions/delete/?id=subscription-uuid" \
  -H "X-Api-Key: YOUR_API_KEY"
```

---

## 轮询（v3）

### 添加轮询订阅

**请求：** `POST /api/v3/subscriptions/addWebhookSubscription/`

```bash
curl -XPOST https://vulners.com/api/v3/subscriptions/addWebhookSubscription/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"query": "viewCount:[50 TO *] order:viewCount last 8 days"}'
```

**Python：**
```python
new_webhook = vulners_api.add_webhook("viewCount:[50 TO *] order:viewCount last 8 days")
```

### 列出轮询订阅

**请求：** `GET /api/v3/subscriptions/listWebhookSubscriptions/`

```bash
curl -G "https://vulners.com/api/v3/subscriptions/listWebhookSubscriptions/" -H "X-Api-Key: YOUR_API_KEY"
```

### 启用/禁用轮询

**请求：** `POST /api/v3/subscriptions/enableWebhookSubscription/`

```bash
curl -XPOST https://vulners.com/api/v3/subscriptions/enableWebhookSubscription/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"subscriptionid": "{subscription id}", "active": false}'
```

### 读取轮询订阅

**请求：** `GET /api/v3/subscriptions/webhook/`

```bash
curl -G "https://vulners.com/api/v3/subscriptions/webhook/" \
  -H "X-Api-Key: YOUR_API_KEY" \
  --data-urlencode "subscriptionid={subscription-id}" \
  --data-urlencode "newest_only=false"
```

---

## 邮件通知

### 列出邮件订阅

**请求：** `GET /api/v3/subscriptions/listEmailSubscriptions/`

```bash
curl -X GET 'https://vulners.com/api/v3/subscriptions/listEmailSubscriptions/' \
  -H "X-Api-Key: YOUR_API_KEY"
```

### 添加邮件订阅

**请求：** `POST /api/v3/subscriptions/addEmailSubscription/`

```bash
curl -X POST 'https://vulners.com/api/v3/subscriptions/addEmailSubscription/' \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "viewCount:[50 TO *] order:viewCount last 5 days",
    "email": "<EMAIL-REDACTED>",
    "format": "html",
    "crontab": "0 0 * * *",
    "query_type": "lucene"
  }'
```

### 编辑邮件订阅

**请求：** `POST /api/v3/subscriptions/editEmailSubscription/`

```bash
curl -X POST 'https://vulners.com/api/v3/subscriptions/editEmailSubscription/' \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "subscriptionid": "{subscription id}",
    "format": "json",
    "crontab": "0 1 * * *",
    "active": "false"
  }'
```

### 删除邮件订阅

**请求：** `POST /api/v3/subscriptions/removeEmailSubscription/`

```bash
curl -X POST 'https://vulners.com/api/v3/subscriptions/removeEmailSubscription/' \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"subscriptionid": "{subscription id}"}'
```
