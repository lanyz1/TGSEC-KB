# Audit

The Audit page describes Vulners' host- and software-auditing APIs — fast, CPE-aware endpoints to convert installed software, OS versions and KB lists into actionable vulnerability intelligence: matched advisories, CVE lists, remediation commands and prioritized patch recommendations.

**Open interactive specs:**
- [Open Redoc (interactive)](https://docs.vulners.com/docs/api/redoc.html)
- [Open Swagger (interactive)](https://docs.vulners.com/docs/api/swagger.html)

---

## Software Audit API

### Audit Multiple Software

Allows a **batch submission** of **multiple software entries**. Each entry can be provided either as a **raw CPE string** or as a **CPE object**.

**Auth**: `X-Api-Key` header required.

**Parameters:**

| Name     | In   | Type  | Required | Description                                                                                                                                 |
| -------- | ---- | ----- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| software | body | array | yes      | Array of software entries — either CPE objects or raw CPE strings.                                                                          |
| match    | body | enum  | no       | `partial` (default) or `full`. `full` requires exact match for all provided fields.                                                         |
| fields   | body | array | no       | Which vulnerability fields to return (defaults: title, short_description, type, href, published, modified, ai_score)                        |
| catalog  | body | enum  | no       | CPE catalog to match against. `official` (default) — only NVD CVE Dictionary CPEs. `extended` — NVD + Vulners custom CPEs.                  |

**Response schema:** Returns a JSON array with one entry per submitted software item.

- `input` — echo of the submitted software entry
- `matched_criteria` — canonical CPE 2.3 string the input resolved to
- `vulnerabilities[]` — matched vulnerabilities, each with `id`, `reasons[]`, and requested `fields`

**Query:** `POST /api/v4/audit/software`

**curl:**
```bash
curl -X POST https://vulners.com/api/v4/audit/software -H "X-Api-Key: YOUR_API_KEY" -H "Content-Type: application/json" -d '{
    "software": [
        { "vendor": "ivanti", "product": "connect_secure", "version": "22.7", "update": "r2.4" },
        { "vendor": "sonicwall", "product": "SMA 200 firmware", "version": "10.2.1.5-34sv" }
    ],
    "match": "partial",
    "fields": ["title", "short_description"]
}'
```

**Python:**
```python
vulners_api.audit.software(
    software=[
        { "part": "a", "vendor": "ivanti", "product": "connect_secure", "version": "22.7", "update": "r2.4" },
        { "vendor": "sonicwall", "product": "SMA 200 firmware", "version": "10.2.1.5-34sv" }
    ],
    fields=["title", "short_description"],
    match='partial'
)
```

---

### Audit Host

Scan multiple layers in one request. Allows you to specify multiple software items plus **additional filtering criteria** (OS, application, hardware).

**Auth**: `X-Api-Key` header required.

**Parameters:**

| Name              | In   | Type          | Required    | Description                                                                                                  |
| ----------------- | ---- | ------------- | ----------- | ------------------------------------------------------------------------------------------------------------ |
| software          | body | array         | yes         | Array of software entries — CPE objects or raw CPE strings.                                                  |
| operating\_system | body | object/string | conditional | OS filter. At least one of `operating_system` or `application` is required.                                  |
| application       | body | object/string | conditional | Application filter (e.g., WordPress).                                                                        |
| hardware          | body | object/string | no          | Hardware/environment filter.                                                                                 |
| match             | body | enum          | no          | `partial` (default) or `full`.                                                                               |
| fields            | body | array         | no          | Which vulnerability fields to return.                                                                        |
| catalog           | body | enum          | no          | `official` (default, NVD only) or `extended` (NVD + Vulners custom CPEs).                                   |

**Query:** `POST /api/v4/audit/host`

**Example: Windows + .NET:**
```bash
curl -X POST https://vulners.com/api/v4/audit/host \
     -H "Content-Type: application/json" \
     -H "X-Api-Key: YOUR_API_KEY" \
     -d '{
       "software": [
         { "part": "a", "vendor": "microsoft", "product": ".net_framework", "version": "3.6" },
         { "part": "a", "vendor": "microsoft", "product": ".net_framework", "version": "4.8.1" }
       ],
       "operating_system": { "part": "o", "vendor": "microsoft", "product": "windows_server_2022_23h2" },
       "fields": ["title", "short_description"]
     }'
```

**Example: Linux + Curl/SSH:**
```bash
curl -X POST https://vulners.com/api/v4/audit/host -H "X-Api-Key: YOUR_API_KEY" -H 'Content-Type: application/json' -d '{
    "software": [
        { "part": "a", "vendor": "haxx", "product": "libcurl", "version": "8.8" },
        { "part": "a", "vendor": "openbsd", "product": "openssh", "version": "8.5" }
    ],
    "operating_system": { "part": "o", "vendor": "redhat", "product": "enterprise_linux", "version": "9.4" },
    "fields": ["title", "short_description"],
    "match": "partial"
}'
```

**Example: WordPress + Plugin:**
```bash
curl -X POST https://vulners.com/api/v4/audit/host -H "X-Api-Key: YOUR_API_KEY" -H "Content-Type: application/json" -d '{
    "software": [{ "part": "a", "vendor": "yoast", "product": "yoast seo", "version": "3.4" }],
    "application": { "part": "a", "vendor": "wordpress", "product": "wordpress" },
    "fields": ["title", "short_description"]
}'
```

### Deprecated Endpoints

The following endpoints remain operational for now but are slated for **future removal**:

- `POST /api/v3/burp/softwareapi/`
- `POST /api/v3/burp/packages/`

Use the new `/api/v4/audit/` endpoints instead:
- `POST /api/v4/audit/software`
- `POST /api/v4/audit/host`

---

## Package Audit API

Processes dependency lists from your project's package manager output and cross-references them against Vulners' vulnerability database. Identifies vulnerable packages, suggests fixed versions, and lists applicable advisories.

| Manager | Endpoint                     | Input format                           |
| ------- | ---------------------------- | -------------------------------------- |
| Maven   | /api/v4/audit/package/maven  | Maven dependency list (text/plain)     |
| Pip     | /api/v4/audit/package/pip    | Pip freeze output (text/plain)         |
| Poetry  | /api/v4/audit/package/poetry | Poetry lock file content (text/plain)  |
| NPM     | /api/v4/audit/package/npm    | package-lock.json content (text/plain) |
| Golang  | /api/v4/audit/package/golang | Go modules list (text/plain)           |

**Auth**: `X-Api-Key` header required.

**Query parameters (all optional):**

| Name               | Type    | Default | Description                                    |
| ------------------ | ------- | ------- | ---------------------------------------------- |
| includeAnyVersion  | boolean | true    | Match advisories regardless of version.        |
| includeCandidates  | boolean | false   | Include candidate advisories.                  |
| includeUnofficial  | boolean | false   | Include advisories from unofficial feeds.      |
| includeTransitives | boolean | false   | Include transitively-introduced packages.      |

**Response format:**
```json
{
    "result": {
        "issues": [
            {
                "package": "junit:junit",
                "version": "4.12",
                "fixedVersion": "4.13.1",
                "scopes": ["test"],
                "applicableAdvisories": [
                    { "id": "OSV:GHSA-269G-PWP5-87PP", "match": ">=4.7,<4.13.1" }
                ]
            }
        ],
        "totalPackages": 42
    }
}
```

**Maven:**
```bash
curl -XPOST https://vulners.com/api/v4/audit/package/maven \
     -H "X-Api-Key: YOUR_API_KEY" \
     -H "Content-Type: text/plain" \
     -d "$(mvn -B -q dependency:list -DoutputFile=/dev/stdout)"
```

**Pip:**
```bash
curl -XPOST https://vulners.com/api/v4/audit/package/pip \
     -H "X-Api-Key: YOUR_API_KEY" \
     -H "Content-Type: text/plain" \
     -d "$(pip freeze)"
```

**Poetry/uv:**
```bash
curl -XPOST https://vulners.com/api/v4/audit/package/poetry \
     -H "X-Api-Key: YOUR_API_KEY" \
     -H "Content-Type: text/plain" \
     -d "$(cat poetry.lock)"
```

**NPM:**
```bash
curl -XPOST https://vulners.com/api/v4/audit/package/npm \
     -H "X-Api-Key: YOUR_API_KEY" \
     -H "Content-Type: text/plain" \
     -d "$(cat package-lock.json)"
```

**Golang:**
```bash
curl -XPOST https://vulners.com/api/v4/audit/package/golang \
     -H "X-Api-Key: YOUR_API_KEY" \
     -H "Content-Type: text/plain" \
     -d "$(go list -m all)"
```

---

## Library Audit

Audit packages identified by [PURL (Package URL)](https://github.com/package-url/purl-spec). Send a list of PURLs from any registry (`pkg:npm/…`, `pkg:pypi/…`, `pkg:maven/…`, `pkg:deb/…`).

**Auth**: `X-Api-Key` header required.

**Parameters:**

| Name                  | In   | Type            | Required | Description                                                                    |
| --------------------- | ---- | --------------- | -------- | ------------------------------------------------------------------------------ |
| packages              | body | array\[string\] | yes      | List of PURLs. 1–2500 entries.                                                 |
| include\_unofficial   | body | boolean         | no       | Include packages from unofficial / community sources. Default false.           |
| include\_candidates   | body | boolean         | no       | Include candidate (not-yet-confirmed) affected packages. Default false.        |
| include\_any\_version | body | boolean         | no       | Include records that match any version (no specific range). Default false.     |
| cvelist\_metrics      | body | boolean         | no       | Attach CVE-list metrics. Paid plans only. Default false.                       |

**Query:** `POST /api/v4/audit/library`

**curl:**
```bash
curl -XPOST https://vulners.com/api/v4/audit/library \
     -H "X-Api-Key: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"packages": ["pkg:npm/express@4.17.1", "pkg:pypi/django@3.2.0"]}'
```

**Python:**
```python
vulners_api.audit.library(
    packages=["pkg:npm/express@4.17.1", "pkg:pypi/django@3.2.0"]
)
```

---

## CVE Audit

Look up everything affected by a CVE: pass a CVE identifier and get back every affected package (with vulnerable version range and distro/arch scope) and every affected CPE configuration.

**Auth**: `X-Api-Key` header required.

| Name | In   | Type   | Required | Description                                                              |
| ---- | ---- | ------ | -------- | ------------------------------------------------------------------------ |
| cve  | body | string | yes      | CVE (or CAN) identifier. Must match C(VE\|AN)-YYYY-NNNN+.                |

**Query:** `POST /api/v4/audit/cve`

**curl:**
```bash
curl -XPOST https://vulners.com/api/v4/audit/cve \
     -H "X-Api-Key: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"cve": "CVE-2026-42945"}'
```

**Python:**
```python
vulners_api.audit.cve_audit(cve="CVE-2026-42945")
```

**Batch (up to 500 CVEs):** `POST /api/v4/audit/cves`

```bash
curl -XPOST https://vulners.com/api/v4/audit/cves \
     -H "X-Api-Key: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"cve": ["CVE-2026-42945", "CVE-2021-44228"]}'
```

---

## SBOM Audit

Audit software components from an uploaded SBOM (Software Bill of Materials). Vulners parses the SBOM, extracts components, matches them to known packages/versions, and returns applicable advisories.

**Auth**: `X-Api-Key` header required.

**Supported formats:** SPDX (v2.x) JSON, CycloneDX (v1.x) JSON

**Content-Type:** `multipart/form-data` — form field `file`

**Query:** `POST /api/v4/audit/sbom`

**curl:**
```bash
curl -X POST "https://vulners.com/api/v4/audit/sbom" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "Accept: application/json" \
  -F "file=@/path/to/sbom.json"
```

---

## Windows Audit

### KB-based audit

Quick audit of Windows hosts by OS version + installed KB list.

| Name   | In   | Type            | Required | Description                                                    |
| ------ | ---- | --------------- | -------- | -------------------------------------------------------------- |
| os     | body | string          | yes      | OS name/version (e.g., Windows Server 2012 R2)                 |
| kbList | body | array\[string\] | yes      | Array of installed KB IDs (e.g., ["KB5009586","KB5009624"]).   |

**Query:** `POST /api/v3/audit/kb/`

**curl:**
```bash
curl -XPOST https://vulners.com/api/v3/audit/kb/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "os": "Windows Server 2012 R2",
    "kbList": ["KB5009586", "KB5009624", "KB5008230", "KB5007247", "KB5005693", "KB5007205", "KB5003646"]
  }'
```

**Python:**
```python
win_vulners = vulners_api.audit.kb_audit(
    os="Windows Server 2016",
    kb_list=["KB5009586", "KB5009624", "KB5008230", "KB5007247", "KB5005693", "KB5007205", "KB5003646"]
)
need_2_install_kb = win_vulners['kbMissed']
```

### Audit installed KBs and software

More detailed Windows audit including OS version, installed KBs, and installed software.

| Name        | In   | Type   | Required | Description                                                |
| ----------- | ---- | ------ | -------- | ---------------------------------------------------------- |
| os          | body | string | yes      | OS name (e.g., windows).                                   |
| os_version  | body | string | yes      | OS version string (e.g., 10.0.19045).                      |
| kb_list     | body | array  | yes      | Installed KB IDs.                                          |
| software    | body | array  | no       | Installed software list with optional CPE-like attributes. |
| platform    | body | string | no       | Applies target_hw to all software entries if provided.     |

**Query:** `POST /api/v3/audit/winaudit/`

**curl:**
```bash
curl -XPOST https://vulners.com/api/v3/audit/winaudit/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "os": "windows",
    "os_version": "10.0.19045",
    "kb_list": ["KB5009586", "KB5009624", "KB5008230", "KB5007247", "KB5005693", "KB5007205", "KB5003646"],
    "software": [
        {"software": "7-Zip", "version": "19.00", "target_sw": "windows", "target_hw": "x64"},
        {"software": "Git", "version": "2.33.0.2", "target_sw": "windows", "target_hw": "x64"}
    ]
  }'
```

### KB superseding/seed info

**Query:** `POST /api/v3/search/id/`

```bash
curl -XPOST https://vulners.com/api/v3/search/id/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"id": "KB4524135", "fields": ["superseeds", "parentseeds"]}'
```

---

## Linux Audit

Analyze installed Linux packages (RPM, DEB, APK) and match them against the Vulners vulnerability database.

**Auth**: `X-Api-Key` header required.

### Supported Systems

**Query:** `GET /api/v3/audit/getSupportedOS`

```bash
curl -G "https://vulners.com/api/v3/audit/getSupportedOS" -H "X-Api-Key: YOUR_API_KEY"
```

### Audit Linux Hosts

| Field             | Type            | Required | Description                                                                                                                       |
| ----------------- | --------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------- |
| osName            | string          | yes      | OS name or ID (ubuntu, debian, rhel, ol, alpine, etc.).                                                                           |
| osVersion         | string          | yes      | OS version (e.g. 22.04, 7, 8.6, ...).                                                                                             |
| osArch            | string          | no       | OS architecture (e.g. x86_64, aarch64).                                                                                           |
| packages          | array\[string\] | yes      | List of packages. Min 1 / Max 2500 entries.                                                                                       |
| includeUnofficial | boolean         | no       | Include matches from unofficial sources. Default false.                                                                           |
| includeCandidates | boolean         | no       | Include candidate findings. Default false.                                                                                        |
| includeAnyVersion | boolean         | no       | Include vulnerabilities matching any version. Default false.                                                                      |
| cvelistMetrics    | boolean         | no       | Add CVE list metrics (paid plans only). Default false.                                                                            |

**Query:** `POST /api/v4/audit/linux`

**curl:**
```bash
curl -sS -X POST "https://vulners.com/api/v4/audit/linux" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -d '{
    "osName": "ubuntu",
    "osVersion": "22.04",
    "packages": [
      "bash 5.1-6ubuntu1.2 amd64",
      "openssl 3.0.2-0ubuntu1.10 amd64",
      "nginx 1.18.0-0ubuntu1 amd64"
    ]
  }'
```

**Python:**
```python
api.audit.linux_audit(
    os_name="ubuntu",
    os_version="22.04",
    packages=[
        "bash 5.1-6ubuntu1.2 amd64",
        "openssl 3.0.2-0ubuntu1.10 amd64",
        "nginx 1.18.0-0ubuntu1 amd64"
    ]
)
```

**Response (abbreviated):**
```json
{
    "result": {
        "issues": [
            {
                "package": "nginx 1.18.0-0ubuntu1 amd64",
                "fixedPackage": "nginx_1.18.0-6ubuntu14.7_noarch.deb",
                "applicableAdvisories": [
                    { "id": "USN-5371-2", "operator": "lt", "version": "1.18.0-6ubuntu14.1" },
                    { "id": "USN-5722-1", "operator": "lt", "version": "1.18.0-6ubuntu14.3" }
                ]
            }
        ],
        "errors": []
    }
}
```
