# Collections

This page documents archive/collection-related endpoints: retrieving CVE archives per OS, fetching published collections from the CDN, and getting collection updates from the database. All examples use API key authentication via the X-Api-Key header.

**Open interactive specs:**
- [Open Redoc (interactive)](https://docs.vulners.com/docs/api/redoc.html)
- [Open Swagger (interactive)](https://docs.vulners.com/docs/api/swagger.html)

---

## List available collections

Return the full list of collections available in Vulners, each with a short description, current record count, and last-updated timestamp. Useful for LLM agents and integrators discovering valid `type` values before calling `/api/v4/archive/collection` or `/api/v4/archive/collection-update`.

**Auth**: `X-Api-Key` header required.

**Parameters:** None.

Returns an object with a single `result` array. Entries are sorted by `count` from largest to smallest. All timestamps are UTC.

**Usage:**

**curl:**
```bash
curl -sS "https://vulners.com/api/v4/search/collections" -H "X-Api-Key: YOUR_API_KEY" --compressed
```

**Response:**
```json
{
  "result": [
    {
      "type": "openbugbounty",
      "description": "OpenBugBounty is a community-driven platform that catalogs security advisories and vulnerabilities...",
      "count": 1261610,
      "last_updated": "2025-07-23T13:56:00"
    },
    {
      "type": "cve",
      "description": "The CVE collection from MITRE provides a comprehensive list of publicly disclosed vulnerabilities...",
      "count": 354266,
      "last_updated": "2026-05-10T08:16:08"
    },
    {
      "type": "exploitdb",
      "description": "ExploitDB is a database of exploits and vulnerable software...",
      "count": 47833,
      "last_updated": "2026-05-07T00:00:00"
    }
  ]
}
```

---

## Get CVEs for OS + version

Download a prebuilt archive (zip) of CVEs for a specific OS and version.

**Auth**: `X-Api-Key` header required.

| Name    | In    | Type   | Required | Description                    |
| ------- | ----- | ------ | -------- | ------------------------------ |
| os      | query | string | yes      | OS name (e.g. ubuntu, debian)  |
| version | query | string | yes      | OS version (e.g. 23.04, 20.04) |

**Query:** `GET /api/v3/archive/distributive/`

**curl:**
```bash
curl -G "https://vulners.com/api/v3/archive/distributive/" -H "X-Api-Key: YOUR_API_KEY" \
  --data-urlencode "os=ubuntu" \
  --data-urlencode "version=23.04" \
  --output output_data.zip
```

**Python:**
```python
vulners_api.archive.get_distributive("ubuntu", "23.04")
```

---

## Get collection by name

Fetch the full collection archive file (records) for a named collection from the CDN. Collections are updated on the CDN every 4 hours; records are sorted by `timestamps.updated` (newest → oldest). Timestamps are UTC.

**Streaming response:** Archive endpoints do **not** return JSON-wrapped responses. They stream **gzipped NDJSON** (one bulletin per line) or respond with **302 Redirect** to a CDN-hosted gzipped NDJSON URL. Free-tier API keys receive **403 Forbidden**.

| Name | In    | Type   | Required | Description                                                                                |
| ---- | ----- | ------ | -------- | ------------------------------------------------------------------------------------------ |
| type | query | string | yes      | Collection type name (e.g. exploitdb)                                                      |

**Query:** `GET /api/v4/archive/collection/`

**curl:**
```bash
curl -GOJL "https://vulners.com/api/v4/archive/collection/" -H "X-Api-Key: YOUR_API_KEY" \
    --data-urlencode "type=exploitdb"
```

**Python:**
```python
vulners_api.archive.fetch_collection(type='exploitdb')
```

---

## Get collection update by name

Get recently updated records for a collection directly from the database. Useful for incremental synchronization.

| Name  | In    | Type              | Required | Description                                                                                             |
| ----- | ----- | ----------------- | -------- | ------------------------------------------------------------------------------------------------------- |
| type  | query | string            | yes      | Collection type name (e.g. exploitdb)                                                                   |
| after | query | string (ISO 8601) | yes      | Return records updated **after** this UTC timestamp. Must not be more than 25 hours from current time. |

**Query:** `GET /api/v4/archive/collection-update/`

**curl:**
```bash
curl -GOJL "https://vulners.com/api/v4/archive/collection-update/" -H "X-Api-Key: YOUR_API_KEY" \
    --data-urlencode "type=exploitdb" \
    --data-urlencode "after=2025-05-21T13:14:26"
```

**Python:**
```python
vulners_api.archive.fetch_collection_update(type='exploitdb', after="2025-05-21T13:14:26")
```

---

## Get collection state

Return the current sync cursor and metadata for a CDN-cached collection. Pair with `Get collection update by name` to drive incremental syncs.

| Name | In    | Type   | Required | Description                                                                                |
| ---- | ----- | ------ | -------- | ------------------------------------------------------------------------------------------ |
| type | query | string | yes      | Collection type name (e.g. exploitdb)                                                      |

**Query:** `GET /api/v4/archive/collection-state/`

**curl:**
```bash
curl -G "https://vulners.com/api/v4/archive/collection-state/" -H "X-Api-Key: YOUR_API_KEY" \
    --data-urlencode "type=exploitdb"
```

**Response:**
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

## Get collection family

Like `Get collection by name`, but selects a **family** of collections by name instead of a single collection type. Streaming gzipped NDJSON (or 302 redirect).

| Name | In    | Type   | Required | Description                  |
| ---- | ----- | ------ | -------- | ---------------------------- |
| name | query | string | yes      | Collection family identifier |

**Query:** `GET /api/v4/archive/family/`

**curl:**
```bash
curl -GOJL "https://vulners.com/api/v4/archive/family/" -H "X-Api-Key: YOUR_API_KEY" \
    --data-urlencode "name=exploits"
```

---

## Get collection family update

Like `Get collection update by name`, but selects a **family** of collections. `after` must not be more than 25 hours from current time.

| Name  | In    | Type              | Required | Description                                                              |
| ----- | ----- | ----------------- | -------- | ------------------------------------------------------------------------ |
| name  | query | string            | yes      | Collection family identifier                                             |
| after | query | string (ISO 8601) | yes      | Return records updated **after** this UTC timestamp (≤ 25 h in the past) |

**Query:** `GET /api/v4/archive/family-update/`

**curl:**
```bash
curl -GOJL "https://vulners.com/api/v4/archive/family-update/" -H "X-Api-Key: YOUR_API_KEY" \
    --data-urlencode "name=exploits" \
    --data-urlencode "after=2025-05-21T13:14:26"
```

---

## Get collection family state

Return the current sync cursor and metadata for a collection family.

| Name | In    | Type   | Required | Description                  |
| ---- | ----- | ------ | -------- | ---------------------------- |
| name | query | string | yes      | Collection family identifier |

**Query:** `GET /api/v4/archive/family-state/`

**curl:**
```bash
curl -G "https://vulners.com/api/v4/archive/family-state/" -H "X-Api-Key: YOUR_API_KEY" \
    --data-urlencode "name=exploits"
```

**Response:**
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
