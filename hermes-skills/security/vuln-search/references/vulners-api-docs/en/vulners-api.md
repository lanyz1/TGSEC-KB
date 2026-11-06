---
description: Vulnerability intelligence — search, audit, collections
---

# Reference — API Overview

Read this page first. It collects the small set of concepts that appear everywhere across the Reference: authentication, response fields, and how to identify software/OS using CPE. These concepts are intentionally platform-agnostic — useful whether you call the REST endpoints directly (curl) or use the [Python SDK](https://github.com/vulnersCom/api).

Vulners APIs return targeted vulnerability intelligence for software, operating systems and KB lists. To get accurate results you usually need to provide:

- What you're scanning (software packages, installed KBs, or OS).
- How you describe them (raw CPE string or structured CPE object).
- Optional filters (fields to return, partial vs full matching).

It's recommended to skim this page once so endpoint examples make sense.

This section contains the complete API reference, organized by service:
- Search
- Collections
- Audit
- Notifications
- Reporting

Use the interactive viewers to explore the OpenAPI spec:

- [Open Redoc (interactive)](https://docs.vulners.com/docs/api/redoc.html)
- [Open Swagger (interactive)](https://docs.vulners.com/docs/api/swagger.html)

---

## Authentication

All private endpoints require an API key. Send your key in the header:

```
X-Api-Key: YOUR_API_KEY
```

---

## Response format

v3 endpoints return:

```json
{
  "result": "OK",
  "data": { ... }
}
```

On error, `result` is `"error"` and `data` is `{ "error": "<message>", "errorCode": <int> }`.

v4 endpoints return:

```json
{
  "result": { ... }
}
```

The [Python SDK](https://github.com/vulnersCom/api) unwraps this for you. Direct HTTP callers read `data.*` on v3 and `result.*` on v4.

Archive endpoints — `/api/v4/archive/collection*` and `/api/v4/archive/family*` — stream gzipped NDJSON or return a `302` redirect to a CDN URL instead. Free-tier keys get `403`.

---

## Default response fields

Most examples and SDK calls return a compact, practical set of fields by default. If you need more data, use the fields parameter to request additional properties.

| Field Name | Description | Link |
|---|---|---|
| id | Unique identifier for each document or item in the database. | [id](https://vulners.com/docs/api_reference/database_fields/#id) |
| title | Title of the bulletin providing a concise summary. | [title](https://vulners.com/docs/api_reference/database_fields/#title) |
| description | Detailed description of the bulletin's content. | [description](https://vulners.com/docs/api_reference/database_fields/#description) |
| short_description | Short description of the bulletin's content based on AI. | [description](https://vulners.com/docs/api_reference/database_fields/#description) |
| type | Vendor or source type of the bulletin (e.g., "Debian", "RedHat"). | [type](https://vulners.com/docs/api_reference/database_fields/#type) |
| bulletinFamily | Category or family of the bulletin (e.g., "Unix", "Exploit"). | [bulletinFamily](https://vulners.com/docs/api_reference/database_fields/#bulletinFamily) |
| cvss | Common Vulnerability Scoring System metrics. | [cvss](https://vulners.com/docs/api_reference/database_fields/#cvss) |
| published | Publication date of the bulletin. | [published](https://vulners.com/docs/api_reference/database_fields/#date) |
| modified | Last modification date of the bulletin. | [modified](https://vulners.com/docs/api_reference/database_fields/#date) |
| lastseen | Timestamp indicating the last update by the system. | [lastseen](https://vulners.com/docs/api_reference/database_fields/#lastseen) |
| href | URL link to the source or reference of the bulletin. | [href](https://vulners.com/docs/api_reference/database_fields/#href) |
| sourceHref | URL link to the original source of the bulletin data. | [sourceHref](https://vulners.com/docs/api_reference/database_fields/#sourceHref) |
| sourceData | Additional data for exploit or scanner bulletins (e.g., code snippets). | [sourceData](https://vulners.com/docs/api_reference/database_fields/#sourceData) |
| cvelist | List of CVE identifiers addressed in the bulletin. | [cvelist](https://vulners.com/docs/api_reference/database_fields/#cvelist) |

Public endpoints are marked where authentication is not required.

---

## CPE Usage in Vulners API

Vulners accepts software/OS identifiers as **raw CPE strings** or as **structured CPE objects**. Use whichever is easier — objects are friendlier when you want partial matching or to add attributes.

### What is CPE?

Common Platform Enumeration (CPE) is a structured naming scheme for IT systems, software, and packages. A CPE name (a.k.a. URI) like:

```
cpe:<cpe_version>:<part>:<vendor>:<product>:<version>:<update>:<edition>:<language>:<sw_edition>:<target_sw>:<target_hw>:<other>
```

or the shortest can be like:

```
cpe:2.3:a:microsoft:windows_10:21h2
```

consists of:

- **part** — `a` (application), `o` (operating system), or `h` (hardware)
- **vendor** — who makes/distributes the software/hardware (e.g., `microsoft`)
- **product** — the product name (e.g., `windows_10`)
- **version** — version number or label (e.g., `21h2`)

CPE objects can include **additional attributes** such as `update`, `sw_edition`, `target_sw`, `target_hw`, and `language`. The official [NISTIR 7695](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7695.pdf) standard describes valid values and usage for these fields.

Below is a summary of additional fields supported in the Vulners API, which you can provide to refine the search accuracy:

- **update (str)**: Specifies the software update version to refine the search for vulnerabilities related to a specific update level. Examples include `service packs` (e.g `sp1`) for Windows, patch versions, hotfixes, or other minor updates.
  Official [NIST 7695](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7695.pdf) for `update`
  Values for this attribute SHOULD be vendor-specific alphanumeric strings characterizing the particular update, service pack, or point release of the product. Values for this attribute SHOULD be selected from an attribute-specific valid-values list, which MAY be defined by other specifications that utilize this specification.

- **language (str)**: Defines the language edition of the software, if applicable. Use this to target vulnerabilities in localized versions of the software.
  Official [NIST 7695](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7695.pdf) for `language`
  Values for this attribute SHALL be valid language tags as defined by [RFC5646], and SHOULD be used to define the language supported in the user interface of the product being described. Although any valid language tag MAY be used, only tags containing language and region codes SHOULD be used.

- **sw_edition (str)**: Indicates the specific edition of the software. (e.g., `home_premium` for Windows, `continuous` for Acrobat Reader, or `server` for Linux)
  Official [NIST 7695](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7695.pdf) for `sw_edition`
  Values for this attribute SHOULD characterize how the product is tailored to a particular market or class of end users. Values for this attribute SHOULD be selected from an attribute-specific valid-values list, which MAY be defined by other specifications that utilize this specification. Any character string meeting the requirements for WFNs (cf. 5.3.2) MAY be specified as the value of the attribute.

- **target_sw (str)**: Specifies the platform where the software runs, such as `windows`, `macOS`, `linux`, or other environments like `java`, `chrome`, `azure`, etc. If not specified, the search will include software that runs on any `*` platforms.
  Official [NIST 7695](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7695.pdf) for `target_sw`
  Values for this attribute SHOULD characterize the software computing environment within which the product operates. Values for this attribute SHOULD be selected from an attribute-specific valid-values list, which MAY be defined by other specifications that utilize this specification.

- **target_hw (str)**: Identifies the hardware platform for the software, such as `x86`, `x64`, `arm`, or specific devices like `router` or `mobile`.
  Official [NIST 7695](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7695.pdf) for `target_hw`
  Values for this attribute SHOULD characterize the instruction set architecture (e.g., `x86`) on which the product being described or identified by the WFN operates. Bytecode-intermediate languages, such as Java bytecode for the Java Virtual Machine or Microsoft Common Intermediate Language for the Common Language Runtime virtual machine, SHALL be considered instruction set architectures.

### Using CPE in Requests

Throughout this documentation, it'll show how to specify **software** via CPE in the following (or similar) ways:

- **Full raw CPE** string, e.g.:
```json
{"software": "cpe:2.3:a:mozilla:firefox:117.0:*:*:*:*:*:*:*"}
```

- **Object with separate fields** (recommended for partial matching or additional attributes):
```json
{
  "part": "a",
  "vendor": "mozilla",
  "product": "firefox",
  "version": "117.0",
  "update": "sp1",
  "language": "en",
  "sw_edition": "home_premium",
  "target_sw": "windows",
  "target_hw": "x64"
}
```

Both approaches are valid in different endpoints. See the corresponding sections for exact syntax.
