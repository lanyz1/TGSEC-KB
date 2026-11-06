# 审计

审计页面介绍了 Vulners 的主机和软件审计 API——这些快速、支持 CPE 的端点可将已安装的软件、操作系统版本和 KB 列表转化为可操作的漏洞情报：匹配的公告、CVE 列表、修复命令和优先级补丁建议。

**打开交互式规范：**
- [打开 Redoc（交互式）](https://docs.vulners.com/docs/api/redoc.html)
- [打开 Swagger（交互式）](https://docs.vulners.com/docs/api/swagger.html)

---

## 软件审计 API

### 审计多个软件

允许**批量提交****多个软件条目**。每个条目可以作为**原始 CPE 字符串**或**CPE 对象**提供。

**认证**：需要 `X-Api-Key` 标头。

**参数：**

| 名称     | 位置   | 类型  | 必填   | 描述                                                                                                 |
| -------- | ------ | ----- | ------ | ---------------------------------------------------------------------------------------------------- |
| software | body   | array | 是     | 软件条目数组——可以是 CPE 对象或原始 CPE 字符串。                                                     |
| match    | body   | enum  | 否     | `partial`（默认）或 `full`。`full` 要求提供的所有字段完全匹配。                                      |
| fields   | body   | array | 否     | 返回哪些漏洞字段（默认值：title, short_description, type, href, published, modified, ai_score）        |
| catalog  | body   | enum  | 否     | 用于匹配的 CPE 目录。`official`（默认）——仅 NVD CVE 字典 CPE。`extended`——NVD + Vulners 自定义 CPE。 |

**响应模式：** 返回一个 JSON 数组，每个提交的软件条目对应一个条目。

- `input`——提交的软件条目的回显
- `matched_criteria`——输入解析为标准 CPE 2.3 字符串
- `vulnerabilities[]`——匹配的漏洞，每个包含 `id`、`reasons[]` 和请求的 `fields`

**查询：** `POST /api/v4/audit/software`

**curl：**
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

**Python：**
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

### 审计主机

在单个请求中扫描多个层次。允许指定多个软件条目以及**额外的筛选条件**（操作系统、应用程序、硬件）。

**认证**：需要 `X-Api-Key` 标头。

**参数：**

| 名称              | 位置   | 类型            | 必填       | 描述                                                                                              |
| ----------------- | ------ | --------------- | ---------- | ------------------------------------------------------------------------------------------------- |
| software          | body   | array           | 是         | 软件条目数组——CPE 对象或原始 CPE 字符串。                                                          |
| operating\_system | body   | object/string   | 条件必填   | 操作系统筛选。`operating_system` 或 `application` 至少需要一个。                                   |
| application       | body   | object/string   | 条件必填   | 应用程序筛选（例如 WordPress）。                                                                   |
| hardware          | body   | object/string   | 否         | 硬件/环境筛选。                                                                                   |
| match             | body   | enum            | 否         | `partial`（默认）或 `full`。                                                                      |
| fields            | body   | array           | 否         | 返回哪些漏洞字段。                                                                                |
| catalog           | body   | enum            | 否         | `official`（默认，仅 NVD）或 `extended`（NVD + Vulners 自定义 CPE）。                             |

**查询：** `POST /api/v4/audit/host`

**示例：Windows + .NET：**
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

**示例：Linux + Curl/SSH：**
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

**示例：WordPress + 插件：**
```bash
curl -X POST https://vulners.com/api/v4/audit/host -H "X-Api-Key: YOUR_API_KEY" -H "Content-Type: application/json" -d '{
    "software": [{ "part": "a", "vendor": "yoast", "product": "yoast seo", "version": "3.4" }],
    "application": { "part": "a", "vendor": "wordpress", "product": "wordpress" },
    "fields": ["title", "short_description"]
}'
```

### 已弃用的端点

以下端点目前仍可运行，但计划在**未来移除**：

- `POST /api/v3/burp/softwareapi/`
- `POST /api/v3/burp/packages/`

请使用新的 `/api/v4/audit/` 端点替代：
- `POST /api/v4/audit/software`
- `POST /api/v4/audit/host`

---

## 包审计 API

处理来自项目包管理器输出的依赖列表，并与 Vulners 漏洞数据库进行交叉引用。识别存在漏洞的包，建议修复版本，并列出适用的公告。

| 管理器   | 端点                            | 输入格式                             |
| -------- | ------------------------------- | ------------------------------------ |
| Maven    | /api/v4/audit/package/maven     | Maven 依赖列表（text/plain）          |
| Pip      | /api/v4/audit/package/pip       | Pip freeze 输出（text/plain）          |
| Poetry   | /api/v4/audit/package/poetry    | Poetry lock 文件内容（text/plain）    |
| NPM      | /api/v4/audit/package/npm       | package-lock.json 内容（text/plain）  |
| Golang   | /api/v4/audit/package/golang    | Go 模块列表（text/plain）             |

**认证**：需要 `X-Api-Key` 标头。

**查询参数（均为可选）：**

| 名称               | 类型    | 默认值  | 描述                                        |
| ------------------ | ------- | ------- | ------------------------------------------- |
| includeAnyVersion  | boolean | true    | 匹配所有版本的公告，无论版本如何。            |
| includeCandidates  | boolean | false   | 包含候选公告。                                |
| includeUnofficial  | boolean | false   | 包含来自非官方源的公告。                      |
| includeTransitives | boolean | false   | 包含传递引入的包。                            |

**响应格式：**
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

**Maven：**
```bash
curl -XPOST https://vulners.com/api/v4/audit/package/maven \
     -H "X-Api-Key: YOUR_API_KEY" \
     -H "Content-Type: text/plain" \
     -d "$(mvn -B -q dependency:list -DoutputFile=/dev/stdout)"
```

**Pip：**
```bash
curl -XPOST https://vulners.com/api/v4/audit/package/pip \
     -H "X-Api-Key: YOUR_API_KEY" \
     -H "Content-Type: text/plain" \
     -d "$(pip freeze)"
```

**Poetry/uv：**
```bash
curl -XPOST https://vulners.com/api/v4/audit/package/poetry \
     -H "X-Api-Key: YOUR_API_KEY" \
     -H "Content-Type: text/plain" \
     -d "$(cat poetry.lock)"
```

**NPM：**
```bash
curl -XPOST https://vulners.com/api/v4/audit/package/npm \
     -H "X-Api-Key: YOUR_API_KEY" \
     -H "Content-Type: text/plain" \
     -d "$(cat package-lock.json)"
```

**Golang：**
```bash
curl -XPOST https://vulners.com/api/v4/audit/package/golang \
     -H "X-Api-Key: YOUR_API_KEY" \
     -H "Content-Type: text/plain" \
     -d "$(go list -m all)"
```

---

## 库审计

审计通过 [PURL（包 URL）](https://github.com/package-url/purl-spec) 标识的包。发送来自任何注册表的 PURL 列表（`pkg:npm/…`、`pkg:pypi/…`、`pkg:maven/…`、`pkg:deb/…`）。

**认证**：需要 `X-Api-Key` 标头。

**参数：**

| 名称                  | 位置   | 类型            | 必填 | 描述                                                                         |
| --------------------- | ------ | --------------- | ---- | ---------------------------------------------------------------------------- |
| packages              | body   | array\[string\] | 是   | PURL 列表。1–2500 个条目。                                                    |
| include\_unofficial   | body   | boolean         | 否   | 包含来自非官方/社区源的包。默认为 false。                                    |
| include\_candidates   | body   | boolean         | 否   | 包含候选（尚未确认）受影响包。默认为 false。                                 |
| include\_any\_version | body   | boolean         | 否   | 包含匹配任何版本的记录（无特定范围）。默认为 false。                         |
| cvelist\_metrics      | body   | boolean         | 否   | 附加 CVE 列表指标。仅限付费计划。默认为 false。                              |

**查询：** `POST /api/v4/audit/library`

**curl：**
```bash
curl -XPOST https://vulners.com/api/v4/audit/library \
     -H "X-Api-Key: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"packages": ["pkg:npm/express@4.17.1", "pkg:pypi/django@3.2.0"]}'
```

**Python：**
```python
vulners_api.audit.library(
    packages=["pkg:npm/express@4.17.1", "pkg:pypi/django@3.2.0"]
)
```

---

## CVE 审计

查找受 CVE 影响的所有内容：传入 CVE 标识符，返回每个受影响的包（包含漏洞版本范围和发行版/架构范围）以及每个受影响的 CPE 配置。

**认证**：需要 `X-Api-Key` 标头。

| 名称   | 位置   | 类型   | 必填   | 描述                                                     |
| ------ | ------ | ------ | ------ | -------------------------------------------------------- |
| cve    | body   | string | 是     | CVE（或 CAN）标识符。必须匹配 C(VE\|AN)-YYYY-NNNN+。       |

**查询：** `POST /api/v4/audit/cve`

**curl：**
```bash
curl -XPOST https://vulners.com/api/v4/audit/cve \
     -H "X-Api-Key: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"cve": "CVE-2026-42945"}'
```

**Python：**
```python
vulners_api.audit.cve_audit(cve="CVE-2026-42945")
```

**批量（最多 500 个 CVE）：** `POST /api/v4/audit/cves`

```bash
curl -XPOST https://vulners.com/api/v4/audit/cves \
     -H "X-Api-Key: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"cve": ["CVE-2026-42945", "CVE-2021-44228"]}'
```

---

## SBOM 审计

审计来自上传的 SBOM（软件物料清单）中的软件组件。Vulners 解析 SBOM，提取组件，将其与已知包/版本进行匹配，并返回适用的公告。

**认证**：需要 `X-Api-Key` 标头。

**支持的格式：** SPDX（v2.x）JSON、CycloneDX（v1.x）JSON

**Content-Type：** `multipart/form-data` — 表单字段 `file`

**查询：** `POST /api/v4/audit/sbom`

**curl：**
```bash
curl -X POST "https://vulners.com/api/v4/audit/sbom" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "Accept: application/json" \
  -F "file=@/path/to/sbom.json"
```

---

## Windows 审计

### 基于 KB 的审计

通过操作系统版本 + 已安装 KB 列表快速审计 Windows 主机。

| 名称   | 位置   | 类型            | 必填   | 描述                                                           |
| ------ | ------ | --------------- | ------ | -------------------------------------------------------------- |
| os     | body   | string          | 是     | 操作系统名称/版本（例如 Windows Server 2012 R2）                |
| kbList | body   | array\[string\] | 是     | 已安装 KB ID 数组（例如 ["KB5009586","KB5009624"]）。           |

**查询：** `POST /api/v3/audit/kb/`

**curl：**
```bash
curl -XPOST https://vulners.com/api/v3/audit/kb/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "os": "Windows Server 2012 R2",
    "kbList": ["KB5009586", "KB5009624", "KB5008230", "KB5007247", "KB5005693", "KB5007205", "KB5003646"]
  }'
```

**Python：**
```python
win_vulners = vulners_api.audit.kb_audit(
    os="Windows Server 2016",
    kb_list=["KB5009586", "KB5009624", "KB5008230", "KB5007247", "KB5005693", "KB5007205", "KB5003646"]
)
need_2_install_kb = win_vulners['kbMissed']
```

### 审计已安装的 KB 和软件

更详细的 Windows 审计，包括操作系统版本、已安装的 KB 和已安装的软件。

| 名称        | 位置   | 类型   | 必填   | 描述                                                       |
| ----------- | ------ | ------ | ------ | ---------------------------------------------------------- |
| os          | body   | string | 是     | 操作系统名称（例如 windows）。                              |
| os_version  | body   | string | 是     | 操作系统版本字符串（例如 10.0.19045）。                    |
| kb_list     | body   | array  | 是     | 已安装的 KB ID。                                           |
| software    | body   | array  | 否     | 已安装软件列表，可包含可选 CPE 类属性。                    |
| platform    | body   | string | 否     | 如果提供，将 target_hw 应用于所有软件条目。                |

**查询：** `POST /api/v3/audit/winaudit/`

**curl：**
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

### KB 替换/种子信息

**查询：** `POST /api/v3/search/id/`

```bash
curl -XPOST https://vulners.com/api/v3/search/id/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"id": "KB4524135", "fields": ["superseeds", "parentseeds"]}'
```

---

## Linux 审计

分析已安装的 Linux 包（RPM、DEB、APK）并将其与 Vulners 漏洞数据库进行匹配。

**认证**：需要 `X-Api-Key` 标头。

### 支持的系统

**查询：** `GET /api/v3/audit/getSupportedOS`

```bash
curl -G "https://vulners.com/api/v3/audit/getSupportedOS" -H "X-Api-Key: YOUR_API_KEY"
```

### 审计 Linux 主机

| 字段               | 类型            | 必填   | 描述                                                                                             |
| ----------------- | --------------- | ------ | ------------------------------------------------------------------------------------------------ |
| osName            | string          | 是     | 操作系统名称或 ID（ubuntu, debian, rhel, ol, alpine 等）。                                        |
| osVersion         | string          | 是     | 操作系统版本（例如 22.04, 7, 8.6, ...）。                                                        |
| osArch            | string          | 否     | 操作系统架构（例如 x86_64, aarch64）。                                                            |
| packages          | array\[string\] | 是     | 包列表。最少 1 / 最多 2500 个条目。                                                              |
| includeUnofficial | boolean         | 否     | 包含来自非官方源的匹配。默认为 false。                                                           |
| includeCandidates | boolean         | 否     | 包含候选发现。默认为 false。                                                                     |
| includeAnyVersion | boolean         | 否     | 包含匹配任何版本的漏洞。默认为 false。                                                           |
| cvelistMetrics    | boolean         | 否     | 添加 CVE 列表指标（仅限付费计划）。默认为 false。                                                |

**查询：** `POST /api/v4/audit/linux`

**curl：**
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

**Python：**
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

**响应（简化）：**
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
