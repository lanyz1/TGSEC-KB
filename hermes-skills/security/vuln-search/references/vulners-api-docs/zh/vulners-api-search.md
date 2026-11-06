# 搜索 — API 参考

搜索端点：全文搜索（Lucene）、按 ID 获取完整记录以及公开漏洞查询。

**打开交互式规范：**
- [打开 Redoc（交互式）](https://docs.vulners.com/docs/api/redoc.html)
- [打开 Swagger（交互式）](https://docs.vulners.com/docs/api/swagger.html)

---

## 数据库搜索

数据库搜索类似于 [Vulners 网站](https://vulners.com/search) 上的搜索。

**认证：** 需要 `X-Api-Key` 头。

**参数：**

| 名称   | 位置 | 类型            | 必填 | 描述                                                                                                                                                                                         |
| ------ | ---- | --------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| query  | body | string          | 是   | Lucene 查询字符串                                                                                                                                                                            |
| skip   | body | integer         | 否   | 偏移量（分页）                                                                                                                                                                               |
| size   | body | integer         | 否   | 每页大小，默认 20，**最大 100**（可通过部署配置的 `search:maxSearchSize` 调整；实际上限会在响应的 `data.maxSearchSize` 中返回，以便客户端进行分页）。                                        |
| fields | body | array\[string\] | 否   | 响应中包含的字段。使用 `["*"]` 请求所有字段。省略则返回默认字段子集。                                                                                                                        |

**请求：** `POST /api/v3/search/lucene/`

**用法：**

**curl：**
```bash
curl -XPOST https://vulners.com/api/v3/search/lucene -H 'Content-Type: application/json' -H "X-Api-Key: YOUR_API_KEY" -d '{
"query": "Fortinet AND RCE order:published", 
"skip": 0, 
"size": 5, 
"fields": [
    "id", 
    "published", 
    "description", 
    "type", 
    "title", 
    "cvelist"]
}'
```

**Python：**
```python
database_search_1 = vulners_api.search.search_bulletins_all(
    "Fortinet AND RCE order:published", limit=5, fields=["published", "title", "description", "cvelist"])
```

**响应（已截断）：**
```json
[
    {
        "cvelist": ["CVE-2024-20674", "CVE-2024-20677", "CVE-2024-20700"],
        "description": "Microsoft has issued patches for 48 security vulnerabilities...",
        "published": "2024-01-10T18:07:38",
        "type": "malwarebytes",
        "title": "Patch now! First patch Tuesday of 2024 is here"
    }
    /* ... additional results omitted for brevity ... */
]
```

---

## 按 ID 获取公告（通过 ID 获取完整数据）

通过一个或多个标识符检索一个或多个公告（CVE 或其他对象）的完整/批量信息。返回丰富的元数据（评分、CVSS、参考信息、受影响软件、配置、扩展信息）。

**认证：** 需要 `X-Api-Key` 头。

**参数：**

| 名称            | 位置 | 类型                      | 必填 | 描述                                                                                                                              |
| --------------- | ---- | ------------------------- | ---- | --------------------------------------------------------------------------------------------------------------------------------- |
| id              | body | string 或 array\[string\] | 是   | 公告或对象标识符（单个 ID 或 ID 列表；**每次请求最多 100 个 ID**）。例如 `CVE-2023-6548` 或 `["CVE-2023-6548","CVE-2023-6549"]`。   |
| references      | body | boolean                   | 否   | 如果为 true，响应还会包含一个引用映射，列出与每个请求 ID 相关的公告对象的源类型映射。                                                 |
| referenceFields | body | array\[string\]           | 否   | 应用于 references 下公告的字段过滤器（独立于顶层字段过滤器）。                                                                        |
| fields          | body | array\[string\]           | 否   | 响应中包含的字段。使用 `["*"]` 请求所有字段。省略则返回默认字段子集。                                                               |

**请求：** `POST /api/v3/search/id/`

**用法：**

**curl（单个 ID）：**
```bash
curl -XPOST https://vulners.com/api/v3/search/id -H "X-Api-Key: YOUR_API_KEY" -H 'Content-Type: application/json' -d '{
"id": "CVE-2024-21762", 
"fields": ["*"]
}'
```

**curl（多个 ID）：**
```bash
curl -XPOST https://vulners.com/api/v3/search/id -H "X-Api-Key: YOUR_API_KEY" -H 'Content-Type: application/json' -d '{
"id": ["CVE-2023-6548", "CVE-2023-6549"], 
"fields": ["*"]
}'
```

**Python（单个）：**
```python
CVE_2024_21762 = vulners_api.search.get_bulletin("CVE-2024-21762", fields=["*"])
```

**Python（多个）：**
```python
multiple_cves = vulners_api.search.get_multiple_bulletins(
    id=["CVE-2023-6548", "CVE-2023-6549"], fields=["*"])
```

**响应（已截断）：**
```json
{
    "CVE-2023-6548": {
        "id": "CVE-2023-6548",
        "type": "cve",
        "bulletinFamily": "NVD",
        "title": "CVE-2023-6548",
        "description": "Improper Control of Generation of Code ('Code Injection') in NetScaler ADC and NetScaler Gateway...",
        "published": "2024-01-17T20:15:50",
        "modified": "2024-01-25T16:45:58",
        "cvss": { "score": 6.5, "vector": "AV:N/AC:L/Au:S/C:P/I:P/A:P" },
        "cvss3": {
            "cvssV3": {
                "version": "3.1",
                "vectorString": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H",
                "baseScore": 8.8,
                "baseSeverity": "HIGH"
            }
        },
        "cvelist": ["CVE-2023-6548"]
    }
}
```

---

## 获取公开漏洞

指定漏洞或软件标识符，从 Vulners 数据库中获取公开可用的漏洞利用代码。

**认证：** 需要 `X-Api-Key` 头。

**参数：**

| 名称   | 位置 | 类型            | 必填 | 描述                                                                                              |
| ------ | ---- | --------------- | ---- | ------------------------------------------------------------------------------------------------- |
| query  | body | string          | 是   | Lucene 查询字符串                                                                                 |
| skip   | body | integer         | 否   | 偏移量                                                                                            |
| size   | body | integer         | 否   | 结果数量                                                                                          |
| fields | body | array\[string\] | 否   | 响应中包含的字段。使用 `["*"]` 请求所有字段。省略则返回默认字段子集。                              |

**请求：** `POST /api/v3/search/lucene/`

**用法：**

**curl（按软件标识符）：**
```bash
curl -XPOST https://vulners.com/api/v3/search/lucene/ -H "X-Api-Key: YOUR_API_KEY" -H 'Content-Type: application/json' -d '{
"query": "bulletinFamily:exploit AND '\''cisco ios xe'\''",
"skip": 0, 
"size": 100, 
"fields": [
    "id", "title", "description", "type", "bulletinFamily", "cvss", 
    "published", "modified", "lastseen", "href", "sourceHref", "sourceData", "cvelist"]
}'
```

**curl（按 CVE）：**
```bash
curl -XPOST https://vulners.com/api/v3/search/lucene/ -H "X-Api-Key: YOUR_API_KEY" -H 'Content-Type: application/json' -d '{
"query": "bulletinFamily:exploit AND '\''CVE-2023-20198'\''",
"skip": 0, 
"size": 100, 
"fields": [
    "id", "title", "description", "type", "bulletinFamily", "cvss", 
    "published", "modified", "lastseen", "href", "sourceHref", "sourceData", "cvelist"]
}'
```

**Python：**
```python
cisco_exploits = vulners_api.search.search_exploits_all("cisco ios xe")
cve_exploits = vulners_api.search.search_exploits_all("CVE-2023-20198", limit=5)
```

**响应（已截断）：**
```json
[
    {
        "lastseen": "2024-09-12T13:39:16",
        "bulletinFamily": "exploit",
        "cvelist": ["CVE-2023-20198", "CVE-2023-20273"],
        "description": "# CVE-2023-20198\nExploit PoC for CVE-2023-20198...",
        "modified": "2024-09-12T06:33:33",
        "id": "943D5962-14B3-5410-8106-BD5EEA778153",
        "published": "2023-11-16T16:39:38",
        "href": "https://github.com/smokeintheshell/CVE-2023-20198",
        "type": "githubexploit",
        "title": "Exploit for Unprotected Alternate Channel in Cisco Ios Xe",
        "cvss": { "score": 10.0, "severity": "CRITICAL", "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H", "version": "3.1" }
    }
]
```
