# 集合

本文档记录了与归档/集合相关的端点：检索各操作系统的CVE归档、从CDN获取已发布的集合，以及从数据库获取集合更新。所有示例均通过 `X-Api-Key` 标头使用API密钥认证。

**打开交互式规范：**
- [Open Redoc (交互式)](https://docs.vulners.com/docs/api/redoc.html)
- [Open Swagger (交互式)](https://docs.vulners.com/docs/api/swagger.html)

---

## 列出可用集合

返回Vulners中所有可用集合的完整列表，每个集合包含简短描述、当前记录数以及最后更新时间戳。适用于LLM代理和集成人员在调用 `/api/v4/archive/collection` 或 `/api/v4/archive/collection-update` 之前发现有效的 `type` 值。

**认证**：需要 `X-Api-Key` 标头。

**参数：** 无。

返回一个包含单个 `result` 数组的对象。条目按 `count` 从大到小排序。所有时间戳均为UTC。

**用法：**

**curl：**
```bash
curl -sS "https://vulners.com/api/v4/search/collections" -H "X-Api-Key: YOUR_API_KEY" --compressed
```

**响应：**
```json
{
  "result": [
    {
      "type": "openbugbounty",
      "description": "OpenBugBounty 是一个社区驱动的平台，收录安全公告和漏洞...",
      "count": 1261610,
      "last_updated": "2025-07-23T13:56:00"
    },
    {
      "type": "cve",
      "description": "来自MITRE的CVE集合提供了全面的公开披露漏洞列表...",
      "count": 354266,
      "last_updated": "2026-05-10T08:16:08"
    },
    {
      "type": "exploitdb",
      "description": "ExploitDB 是一个包含漏洞利用和易受攻击软件的数据库...",
      "count": 47833,
      "last_updated": "2026-05-07T00:00:00"
    }
  ]
}
```

---

## 获取指定操作系统及版本的CVE

下载特定操作系统和版本的预构建CVE归档文件（zip）。

**认证**：需要 `X-Api-Key` 标头。

| 名称    | 位置    | 类型   | 必填 | 描述                        |
| ------- | ----- | ------ | -------- | ------------------------------ |
| os      | query | string | 是      | 操作系统名称（例如 ubuntu, debian）  |
| version | query | string | 是      | 操作系统版本（例如 23.04, 20.04） |

**查询：** `GET /api/v3/archive/distributive/`

**curl：**
```bash
curl -G "https://vulners.com/api/v3/archive/distributive/" -H "X-Api-Key: YOUR_API_KEY" \
  --data-urlencode "os=ubuntu" \
  --data-urlencode "version=23.04" \
  --output output_data.zip
```

**Python：**
```python
vulners_api.archive.get_distributive("ubuntu", "23.04")
```

---

## 按名称获取集合

从CDN获取指定集合的完整归档文件（记录）。集合每4小时在CDN上更新一次；记录按 `timestamps.updated` 排序（最新→最旧）。时间戳为UTC。

**流式响应：** 归档端点**不会**返回JSON包装的响应。它们流式传输**gzip压缩的NDJSON**（每行一条公告），或响应**302重定向**到CDN托管的gzip压缩NDJSON URL。免费套餐的API密钥将收到**403 Forbidden**。

| 名称 | 位置    | 类型   | 必填 | 描述                                                                                |
| ---- | ----- | ------ | -------- | ------------------------------------------------------------------------------------------ |
| type | query | string | 是      | 集合类型名称（例如 exploitdb）                                                      |

**查询：** `GET /api/v4/archive/collection/`

**curl：**
```bash
curl -GOJL "https://vulners.com/api/v4/archive/collection/" -H "X-Api-Key: YOUR_API_KEY" \
    --data-urlencode "type=exploitdb"
```

**Python：**
```python
vulners_api.archive.fetch_collection(type='exploitdb')
```

---

## 按名称获取集合更新

直接从数据库获取集合中最近更新的记录。适用于增量同步。

| 名称  | 位置    | 类型              | 必填 | 描述                                                                                             |
| ----- | ----- | ----------------- | -------- | ------------------------------------------------------------------------------------------------------- |
| type  | query | string            | 是      | 集合类型名称（例如 exploitdb）                                                                   |
| after | query | string (ISO 8601) | 是      | 返回在此UTC时间戳**之后**更新的记录。距离当前时间不得超过25小时。 |

**查询：** `GET /api/v4/archive/collection-update/`

**curl：**
```bash
curl -GOJL "https://vulners.com/api/v4/archive/collection-update/" -H "X-Api-Key: YOUR_API_KEY" \
    --data-urlencode "type=exploitdb" \
    --data-urlencode "after=2025-05-21T13:14:26"
```

**Python：**
```python
vulners_api.archive.fetch_collection_update(type='exploitdb', after="2025-05-21T13:14:26")
```

---

## 获取集合状态

返回CDN缓存集合的当前同步游标和元数据。与「按名称获取集合更新」配合使用以驱动增量同步。

| 名称 | 位置    | 类型   | 必填 | 描述                                                                                |
| ---- | ----- | ------ | -------- | ------------------------------------------------------------------------------------------ |
| type | query | string | 是      | 集合类型名称（例如 exploitdb）                                                      |

**查询：** `GET /api/v4/archive/collection-state/`

**curl：**
```bash
curl -G "https://vulners.com/api/v4/archive/collection-state/" -H "X-Api-Key: YOUR_API_KEY" \
    --data-urlencode "type=exploitdb"
```

**响应：**
```json
{
    "result": {
        "cursor": "2025-05-21T13:14:26Z",
        "upload_time": "2025-05-21T13:18:00Z",
        "write_time": "2025-05-21T13:14:30Z",
        "total_docs": 47238
    }
}
```

---

## 获取集合系列

与「按名称获取集合」类似，但按名称选择**系列**的集合而非单个集合类型。流式传输gzip压缩的NDJSON（或302重定向）。

| 名称 | 位置    | 类型   | 必填 | 描述                  |
| ---- | ----- | ------ | -------- | ---------------------------- |
| name | query | string | 是      | 集合系列标识符 |

**查询：** `GET /api/v4/archive/family/`

**curl：**
```bash
curl -GOJL "https://vulners.com/api/v4/archive/family/" -H "X-Api-Key: YOUR_API_KEY" \
    --data-urlencode "name=exploits"
```

---

## 获取集合系列更新

与「按名称获取集合更新」类似，但选择**系列**的集合。`after` 距离当前时间不得超过25小时。

| 名称  | 位置    | 类型              | 必填 | 描述                                                              |
| ----- | ----- | ----------------- | -------- | ------------------------------------------------------------------------ |
| name  | query | string            | 是      | 集合系列标识符                                             |
| after | query | string (ISO 8601) | 是      | 返回在此UTC时间戳**之后**更新的记录（距今 ≤ 25 小时） |

**查询：** `GET /api/v4/archive/family-update/`

**curl：**
```bash
curl -GOJL "https://vulners.com/api/v4/archive/family-update/" -H "X-Api-Key: YOUR_API_KEY" \
    --data-urlencode "name=exploits" \
    --data-urlencode "after=2025-05-21T13:14:26"
```

---

## 获取集合系列状态

返回集合系列的当前同步游标和元数据。

| 名称 | 位置    | 类型   | 必填 | 描述                  |
| ---- | ----- | ------ | -------- | ---------------------------- |
| name | query | string | 是      | 集合系列标识符 |

**查询：** `GET /api/v4/archive/family-state/`

**curl：**
```bash
curl -G "https://vulners.com/api/v4/archive/family-state/" -H "X-Api-Key: YOUR_API_KEY" \
    --data-urlencode "name=exploits"
```

**响应：**
```json
{
    "result": {
        "cursor": "2025-05-21T13:14:26Z",
        "upload_time": "2025-05-21T13:18:00Z",
        "write_time": "2025-05-21T13:14:30Z",
        "total_docs": 102441
    }
}
```
