# Search — API Reference

Search endpoints: full-text search (Lucene), fetch full record by id, and public exploits lookup.

**Open interactive specs:**
- [Open Redoc (interactive)](https://docs.vulners.com/docs/api/redoc.html)
- [Open Swagger (interactive)](https://docs.vulners.com/docs/api/swagger.html)

---

## Search in Database

The database search is similar to the search on the [Vulners website](https://vulners.com/search).

**Auth:** `X-Api-Key` header required.

**Parameters:**

| Name   | In   | Type            | Required | Description                                                                                                                                                                                |
| ------ | ---- | --------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| query  | body | string          | yes      | Lucene query string                                                                                                                                                                        |
| skip   | body | integer         | no       | Offset (pagination)                                                                                                                                                                        |
| size   | body | integer         | no       | Page size, default 20, **max 100** (configurable per deployment via search:maxSearchSize; the actual cap is returned in the response's data.maxSearchSize so clients can size pagination). |
| fields | body | array\[string\] | no       | Fields to include in the response. Use `["*"]` to request all fields. Omitting returns default subset.                                                                                    |

**Query:** `POST /api/v3/search/lucene/`

**Usage:**

**curl:**
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

**Python:**
```python
database_search_1 = vulners_api.search.search_bulletins_all(
    "Fortinet AND RCE order:published", limit=5, fields=["published", "title", "description", "cvelist"])
```

**Response (truncated):**
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

## Get Bulletin by ID (Full Data by ID)

Retrieve full/bulk information for one or more bulletins (CVE or other object) by identifier(s). Returns rich metadata (scores, CVSS, references, affected software, configurations, extras).

**Auth:** `X-Api-Key` header required.

**Parameters:**

| Name            | In   | Type                      | Required | Description                                                                                                                                       |
| --------------- | ---- | ------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| id              | body | string or array\[string\] | yes      | Bulletin or object identifier (single id or list of ids; **max 100 ids per request**). E.g. `CVE-2023-6548` or `["CVE-2023-6548","CVE-2023-6549"]`. |
| references      | body | boolean                   | no       | If true, the response also includes a references map of source-type to bulletin objects related to each requested id.                              |
| referenceFields | body | array\[string\]           | no       | Field filter applied to bulletins under references (independent of the top-level fields filter).                                                  |
| fields          | body | array\[string\]           | no       | Fields to include in the response. Use `["*"]` to request all fields. Omitting returns default subset.                                           |

**Query:** `POST /api/v3/search/id/`

**Usage:**

**curl (single ID):**
```bash
curl -XPOST https://vulners.com/api/v3/search/id -H "X-Api-Key: YOUR_API_KEY" -H 'Content-Type: application/json' -d '{
"id": "CVE-2024-21762", 
"fields": ["*"]
}'
```

**curl (multiple IDs):**
```bash
curl -XPOST https://vulners.com/api/v3/search/id -H "X-Api-Key: YOUR_API_KEY" -H 'Content-Type: application/json' -d '{
"id": ["CVE-2023-6548", "CVE-2023-6549"], 
"fields": ["*"]
}'
```

**Python (single):**
```python
CVE_2024_21762 = vulners_api.search.get_bulletin("CVE-2024-21762", fields=["*"])
```

**Python (multiple):**
```python
multiple_cves = vulners_api.search.get_multiple_bulletins(
    id=["CVE-2023-6548", "CVE-2023-6549"], fields=["*"])
```

**Response (truncated):**
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

## Get Public Exploits

Specify a vulnerability or software identifier to obtain publicly available exploits from the Vulners database.

**Auth:** `X-Api-Key` header required.

**Parameters:**

| Name   | In   | Type            | Required | Description                                                                                             |
| ------ | ---- | --------------- | -------- | ------------------------------------------------------------------------------------------------------- |
| query  | body | string          | yes      | Lucene query string                                                                                     |
| skip   | body | integer         | no       | Offset                                                                                                  |
| size   | body | integer         | no       | Number of results                                                                                       |
| fields | body | array\[string\] | no       | Fields to include in the response. Use `["*"]` to request all fields. Omitting returns default subset. |

**Query:** `POST /api/v3/search/lucene/`

**Usage:**

**curl (by software identifier):**
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

**curl (by CVE):**
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

**Python:**
```python
cisco_exploits = vulners_api.search.search_exploits_all("cisco ios xe")
cve_exploits = vulners_api.search.search_exploits_all("CVE-2023-20198", limit=5)
```

**Response (truncated):**
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
