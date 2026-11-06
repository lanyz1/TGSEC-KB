# NVD CLI 命令行参考手册

## 概述

NVD CLI 是一个基于 NVD REST API v2.0 的命令行查询工具，用于检索 CVE 漏洞信息和变更历史记录。支持批量查询、多线程并发、自动限流和本地缓存。

**运行方式：**

```
python main.py <command> [options]
```

**数据来源：**

- CVE 查询: `https://services.nvd.nist.gov/rest/json/cves/2.0`
- 变更历史: `https://services.nvd.nist.gov/rest/json/cvehistory/2.0`

**API 限流策略：**

| 认证方式 | 限流额度 |
|---------|---------|
| 无 API Key | 5 次 / 30 秒 |
| 有 API Key | 50 次 / 30 秒 |

建议通过 `nvd config set api_key <your-key>` 配置 API Key 以提升限流额度。API Key 可在 https://nvd.nist.gov/developers/request-an-api-key 免费申请。

---

## 全局选项

以下选项适用于所有子命令：

| 选项 | 缩写 | 说明 |
|------|------|------|
| `--version` | `-v` | 显示版本号并退出 |
| `--verbose` | | 启用详细日志输出（DEBUG 级别），用于排查问题 |
| `--help` | | 显示帮助信息并退出 |

**通用查询选项**（适用于 `cve get`、`cve search`、`cve latest`、`history get`、`history search`）：

| 选项 | 说明 |
|------|------|
| `--output` / `-o` | 输出格式：`table`（默认）、`json`、`csv` |
| `--api-key` | 本次请求使用的 NVD API Key，覆盖配置文件中的值 |
| `--no-cache` | 禁用本地缓存，强制从 API 获取最新数据 |

---

## 命令结构

```
nvd
  cve
    get         按编号查询 CVE 详情
    search      按条件搜索 CVE
    latest      查询最近 N 天发布的新 CVE
  history
    get         按编号查询 CVE 变更历史
    search      按条件搜索变更记录
  config
    set         设置配置项
    get         查看单个配置项
    show        显示所有配置项
```

---

## cve get

按 CVE 编号查询漏洞详细信息。

### 语法

```
nvd cve get [CVE_IDS...] [OPTIONS]
nvd cve get --file <path> [OPTIONS]
nvd cve get - [OPTIONS]
```

### 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `CVE_IDS` | 否 | 一个或多个 CVE 编号，如 `CVE-2021-44228`。传入 `-` 表示从标准输入读取 |

### 选项

| 选项 | 缩写 | 默认值 | 说明 |
|------|------|--------|------|
| `--file` | `-f` | | 从文本文件读取 CVE ID 列表，每行一个 |
| `--output` | `-o` | `table` | 输出格式：`table`、`json`、`csv` |
| `--api-key` | | | 本次请求使用的 API Key |
| `--no-cache` | | `false` | 禁用缓存 |

### 输入方式

支持三种输入方式，优先级从高到低：

1. **文件输入** `--file ids.txt`：从文本文件读取，每行一个 CVE ID，支持 `#` 开头的注释行
2. **标准输入** `-`：从管道或重定向读取，每行一个 CVE ID
3. **命令行参数**：直接在命令行上指定一个或多个 CVE ID

### 批量查询行为

- 1-2 个 ID：直接请求，不启用线程池
- 3 个以上 ID：自动启用多线程批量查询，每批最多 100 个 ID
- 多批次结果自动去重

### 文件格式

```
CVE-2021-44228
CVE-2021-45046
# 这是注释行，会被忽略
CVE-2023-44487
```

### 示例

```bash
# 查询单个 CVE
nvd cve get CVE-2021-44228

# 查询多个 CVE
nvd cve get CVE-2021-44228 CVE-2021-45046 CVE-2023-44487

# 从文件批量查询
nvd cve get --file ids.txt

# 从标准输入批量查询（管道）
cat ids.txt | nvd cve get -

# JSON 格式输出
nvd cve get CVE-2021-44228 -o json

# CSV 格式输出并重定向到文件
nvd cve get --file ids.txt -o csv > results.csv
```

---

## cve search

按条件搜索 CVE 漏洞。支持关键词、严重度、CPE、CWE、日期范围等多种筛选条件，也支持从 JSON 文件读取多组查询条件批量搜索。

### 语法

```
nvd cve search [OPTIONS]
nvd cve search --file <path> [OPTIONS]
```

### 筛选选项

#### 关键词与匹配

| 选项 | 缩写 | 说明 |
|------|------|------|
| `--keyword` | `-k` | 关键词搜索 CVE 描述文本 |
| `--exact` | | 精确匹配关键词短语（需配合 `--keyword` 使用） |

#### CPE 与受影响产品

| 选项 | 说明 |
|------|------|
| `--cpe` | 按 CPE 名称筛选，如 `cpe:2.3:a:apache:log4j` |
| `--is-vulnerable` | 仅返回标记为受影响的 CPE（需配合 `--cpe` 使用） |
| `--virtual-match` | CPE 虚拟匹配字符串 |
| `--version-start` | 版本范围起始（需配合 `--virtual-match`） |
| `--version-start-type` | 起始版本类型：`including` / `excluding` |
| `--version-end` | 版本范围结束（需配合 `--virtual-match`） |
| `--version-end-type` | 结束版本类型：`including` / `excluding` |

#### CVSS 严重度

| 选项 | 说明 |
|------|------|
| `--severity-v2` | CVSSv2 严重度：`LOW` / `MEDIUM` / `HIGH` |
| `--severity-v3` | CVSSv3 严重度：`LOW` / `MEDIUM` / `HIGH` / `CRITICAL` |
| `--severity-v4` | CVSSv4 严重度：`LOW` / `MEDIUM` / `HIGH` / `CRITICAL` |

> **注意：** `--severity-v2` / `--severity-v3` / `--severity-v4` 参数基于 NVD API 的 `cvssV2Severity` / `cvssV3Severity` / `cvssV4Severity` 字段过滤，NVD API 本身可能返回不完全匹配指定严重度的结果，这是 NVD 的已知行为。工具会在客户端对三种严重度参数做二次过滤，确保结果严格匹配。

#### CVSS 向量

| 选项 | 说明 |
|------|------|
| `--cvss-v2-metrics` | CVSSv2 向量字符串 |
| `--cvss-v3-metrics` | CVSSv3 向量字符串 |
| `--cvss-v4-metrics` | CVSSv4 向量字符串 |

#### 弱点分类

| 选项 | 说明 |
|------|------|
| `--cwe` | 按 CWE ID 筛选，如 `CWE-79`、`CWE-287` |

#### 标志与来源

| 选项 | 说明 |
|------|------|
| `--has-kev` | 仅返回在 CISA Known Exploited Vulnerabilities 目录中的 CVE |
| `--has-cert-alerts` | 仅返回包含 US-CERT 技术警报的 CVE |
| `--has-cert-notes` | 仅返回包含 CERT/CC 漏洞说明的 CVE |
| `--no-rejected` | 排除已拒绝（Rejected）的 CVE |

#### 日期范围

所有日期参数格式为 `YYYY-MM-DD`，内部自动转换为 NVD 要求的 ISO-8601 格式。日期范围超过 120 天时会自动拆分为多个请求。

| 选项 | 说明 |
|------|------|
| `--pub-start` | CVE 发布开始日期 |
| `--pub-end` | CVE 发布结束日期 |
| `--mod-start` | CVE 最后修改开始日期 |
| `--mod-end` | CVE 最后修改结束日期 |
| `--kev-start` | CISA KEV 添加开始日期 |
| `--kev-end` | CISA KEV 添加结束日期 |

> **重要：** `--pub-start` 与 `--pub-end` 必须成对使用，`--mod-start` 与 `--mod-end`、`--kev-start` 与 `--kev-end` 同理。日期范围不得超过 120 天，超出部分会自动拆分。

#### 状态与标签

| 选项 | 说明 |
|------|------|
| `--status` | 漏洞状态筛选，可多次指定。可选值：`Analyzed`、`Modified`、`Deferred`、`Rejected` 等 |
| `--cve-tag` | CVE 标签筛选，如 `disputed`、`unsupported-when-assigned` |
| `--source` | 数据来源标识符筛选 |

### 输出控制选项

| 选项 | 缩写 | 默认值 | 说明 |
|------|------|--------|------|
| `--limit` | `-l` | `0` | 最大返回数量，`0` 表示返回全部结果（自动翻页） |
| `--file` | `-f` | | 从 JSON 文件读取多组查询条件进行批量搜索 |
| `--output` | `-o` | `table` | 输出格式：`table`、`json`、`csv` |
| `--api-key` | | | 本次请求使用的 API Key |
| `--no-cache` | | `false` | 禁用缓存 |

### 批量搜索 JSON 文件格式

`--file` 选项接受一个 JSON 数组文件，每个元素是一组独立的查询条件。多组查询结果会自动去重合并。

```json
[
  {
    "keyword": "openssl",
    "severity_v3": "CRITICAL",
    "limit": 5
  },
  {
    "keyword": "nginx",
    "pub_start": "2024-01-01",
    "pub_end": "2024-12-31"
  },
  {
    "cwe": "CWE-79",
    "severity_v3": "HIGH",
    "limit": 10
  }
]
```

**JSON 字段名与命令行选项的对应关系：**

| JSON 字段名 | 命令行选项 | 类型 | 说明 |
|-------------|-----------|------|------|
| `keyword` | `--keyword` / `-k` | string | 关键词 |
| `exact` | `--exact` | boolean | 精确匹配 |
| `cpe` | `--cpe` | string | CPE 名称 |
| `is_vulnerable` | `--is-vulnerable` | boolean | 仅受影响 |
| `severity_v2` | `--severity-v2` | string | CVSSv2 严重度 |
| `severity_v3` | `--severity-v3` | string | CVSSv3 严重度 |
| `severity_v4` | `--severity-v4` | string | CVSSv4 严重度 |
| `cvss_v2_metrics` | `--cvss-v2-metrics` | string | CVSSv2 向量 |
| `cvss_v3_metrics` | `--cvss-v3-metrics` | string | CVSSv3 向量 |
| `cvss_v4_metrics` | `--cvss-v4-metrics` | string | CVSSv4 向量 |
| `cwe` | `--cwe` | string | CWE ID |
| `has_kev` | `--has-kev` | boolean | CISA KEV |
| `has_cert_alerts` | `--has-cert-alerts` | boolean | CERT 警报 |
| `has_cert_notes` | `--has-cert-notes` | boolean | CERT 说明 |
| `pub_start` | `--pub-start` | string | 发布开始日期 |
| `pub_end` | `--pub-end` | string | 发布结束日期 |
| `mod_start` | `--mod-start` | string | 修改开始日期 |
| `mod_end` | `--mod-end` | string | 修改结束日期 |
| `kev_start` | `--kev-start` | string | KEV 开始日期 |
| `kev_end` | `--kev-end` | string | KEV 结束日期 |
| `status` | `--status` | string | 漏洞状态 |
| `cve_tag` | `--cve-tag` | string | CVE 标签 |
| `source` | `--source` | string | 数据来源 |
| `virtual_match` | `--virtual-match` | string | 虚拟匹配 |
| `version_start` | `--version-start` | string | 版本起始 |
| `version_start_type` | `--version-start-type` | string | 起始类型 |
| `version_end` | `--version-end` | string | 版本结束 |
| `version_end_type` | `--version-end-type` | string | 结束类型 |
| `no_rejected` | `--no-rejected` | boolean | 排除已拒绝 |
| `limit` | `--limit` / `-l` | integer | 最大返回数量 |

### 示例

```bash
# 按关键词搜索
nvd cve search -k log4j

# 关键词 + 严重度筛选
nvd cve search -k log4j --severity-v3 CRITICAL

# 按 CWE 筛选
nvd cve search --cwe CWE-79 --severity-v3 HIGH

# 按日期范围搜索
nvd cve search --pub-start 2024-01-01 --pub-end 2024-06-30

# 按 CPE 筛选受影响产品
nvd cve search --cpe "cpe:2.3:a:apache:log4j" --is-vulnerable

# 仅查询 CISA KEV 中的漏洞，CSV 输出
nvd cve search --has-kev --no-rejected -o csv

# 限制返回数量
nvd cve search -k openssl --severity-v3 CRITICAL -l 10

# 从 JSON 文件批量搜索
nvd cve search --file queries.json

# 批量搜索并导出为 JSON
nvd cve search --file queries.json -o json > results.json
```

---

## cve latest

查询最近 N 天内发布的新 CVE。本质上是 `cve search` 的快捷方式，自动计算日期范围，并自动排除已拒绝（Rejected）的 CVE。

### 语法

```
nvd cve latest [OPTIONS]
```

### 选项

| 选项 | 缩写 | 默认值 | 说明 |
|------|------|--------|------|
| `--days` | `-d` | `7` | 查询最近 N 天内发布的 CVE |
| `--severity` | `-s` | | 按严重度筛选：`LOW` / `MEDIUM` / `HIGH` / `CRITICAL` |
| `--limit` | `-l` | `50` | 最大返回数量 |
| `--output` | `-o` | `table` | 输出格式：`table`、`json`、`csv` |
| `--api-key` | | | 本次请求使用的 API Key |
| `--no-cache` | | `false` | 禁用缓存 |

### 示例

```bash
# 最近 7 天的新 CVE（默认）
nvd cve latest

# 最近 30 天
nvd cve latest -d 30

# 最近 7 天的严重漏洞
nvd cve latest -d 7 -s CRITICAL

# 最近 30 天的严重漏洞，限制 20 条
nvd cve latest -d 30 -s CRITICAL -l 20

# 导出到 CSV
nvd cve latest -d 90 -o csv > latest.csv
```

---

## history get

按 CVE 编号查询变更历史记录。

### 语法

```
nvd history get [CVE_ID] [OPTIONS]
nvd history get --file <path> [OPTIONS]
nvd history get - [OPTIONS]
```

### 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `CVE_ID` | 否 | 单个 CVE 编号，如 `CVE-2021-44228`。传入 `-` 表示从标准输入读取 |

### 选项

| 选项 | 缩写 | 默认值 | 说明 |
|------|------|--------|------|
| `--file` | `-f` | | 从文本文件读取 CVE ID 列表，每行一个 |
| `--output` | `-o` | `table` | 输出格式：`table`、`json`、`csv` |
| `--api-key` | | | 本次请求使用的 API Key |
| `--no-cache` | | `false` | 禁用缓存 |

### 输入方式

与 `cve get` 类似，支持文件、标准输入和命令行参数三种方式。但并发策略不同：单个 ID 直接查询，2 个以上 ID 时自动启用多线程并发查询，结果自动去重。

### 示例

```bash
# 查询单个 CVE 的变更历史
nvd history get CVE-2021-44228

# 从文件批量查询
nvd history get --file ids.txt

# 从标准输入批量查询
cat ids.txt | nvd history get -

# JSON 格式输出
nvd history get CVE-2021-44228 -o json

# 批量查询并导出为 CSV
nvd history get --file ids.txt -o csv > history.csv
```

---

## history search

按日期范围和事件类型搜索 CVE 变更记录。

### 语法

```
nvd history search [OPTIONS]
```

### 选项

| 选项 | 缩写 | 默认值 | 说明 |
|------|------|--------|------|
| `--start` | | | 变更开始日期，格式 `YYYY-MM-DD` |
| `--end` | | | 变更结束日期，格式 `YYYY-MM-DD` |
| `--event` | | | 事件类型筛选 |
| `--limit` | `-l` | `0` | 最大返回数量，`0` 表示返回全部 |
| `--output` | `-o` | `table` | 输出格式：`table`、`json`、`csv` |
| `--api-key` | | | 本次请求使用的 API Key |
| `--no-cache` | | `false` | 禁用缓存 |

> **注意：** `--start` 与 `--end` 必须成对使用。日期范围超过 120 天会自动拆分。不指定日期范围时将查询所有变更记录，数据量可能非常大。

### 常见事件类型

| 事件名称 | 说明 |
|---------|------|
| `Initial Analysis` | NVD 首次分析 |
| `CVE Modified` | CVE 记录被修改 |
| `CVE Rejected` | CVE 被拒绝 |
| `New CVE Received` | 新 CVE 提交 |
| `CVE Translated` | CVE 描述被翻译 |

### 示例

```bash
# 按日期范围搜索
nvd history search --start 2024-01-01 --end 2024-01-31

# 按事件类型筛选
nvd history search --event "CVE Rejected" --start 2024-06-01 --end 2024-06-30

# 组合筛选并限制数量
nvd history search --event "Initial Analysis" --start 2024-01-01 --end 2024-03-31 -l 50

# 导出到 CSV
nvd history search --start 2024-01-01 --end 2024-12-31 -o csv > history.csv
```

---

## config set

设置配置项的值。配置保存到项目目录下的 `config.toml` 文件。

### 语法

```
nvd config set <KEY> <VALUE>
```

### 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `KEY` | 是 | 配置项名称 |
| `VALUE` | 是 | 配置项值，自动进行类型转换 |

### 可配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `api_key` | string | `""` | NVD API Key。设置后限流额度从 5 次/30 秒提升到 50 次/30 秒 |
| `cache_enabled` | bool | `true` | 是否启用本地 HTTP 缓存。布尔值接受 `true`/`false`、`1`/`0`、`yes`/`no` |
| `cache_dir` | string | 项目目录下 `cache/` | 缓存文件存放目录 |
| `cache_ttl` | int | `1800` | 缓存过期时间（秒），默认 30 分钟 |
| `timeout` | int | `30` | HTTP 请求超时时间（秒） |
| `max_retries` | int | `3` | 请求失败后最大重试次数 |
| `max_threads` | int | `0` | 批量查询最大线程数。`0` 表示自动计算（CPU 核数 x 4） |
| `thread_delay` | float | `0.6` | 线程启动间隔（秒），避免瞬间打满限流窗口 |

### 示例

```bash
# 设置 API Key
nvd config set api_key a9a30619-9294-423d-9286-1f79037f63d5

# 修改缓存过期时间为 1 小时
nvd config set cache_ttl 3600

# 禁用缓存
nvd config set cache_enabled false

# 设置最大线程数
nvd config set max_threads 8

# 设置线程启动间隔
nvd config set thread_delay 1.0
```

---

## config get

查看单个配置项的值。

### 语法

```
nvd config get <KEY>
```

### 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `KEY` | 是 | 配置项名称 |

### 示例

```bash
nvd config get api_key
nvd config get max_threads
nvd config get cache_ttl
```

---

## config show

显示所有配置项。API Key 会脱敏显示（仅显示前 4 位和后 4 位），`max_threads` 为 0 时显示自动计算的实际值。

### 语法

```
nvd config show
```

### 示例

```bash
nvd config show
```

---

## 输出格式

所有查询命令均支持三种输出格式，通过 `--output` / `-o` 选项指定。

### table（默认）

使用 Rich 库渲染的彩色表格，适合终端交互查看。

- `cve get` 单条结果时显示详细信息（描述、CWE、CISA KEV、CPE、参考链接等）
- 多条结果时显示摘要表格（CVE-ID、CVSS、Severity、Status、Published、Description）
- `history` 显示变更历史表格（CVE-ID、Event、Time、Source、Details）

### json

结构化 JSON 输出，适合程序间传递或进一步处理。字段名使用 camelCase（与 NVD API 原始格式一致），空值字段不输出。

### csv

逗号分隔值格式，适合导入电子表格或数据库。

CVE 输出字段：`CVE-ID`、`CVSS`、`Severity`、`Status`、`Published`、`Description`

变更历史输出字段：`CVE-ID`、`Event`、`Time`、`Source`、`Action`、`Type`、`OldValue`、`NewValue`

---

## 批量查询

### CVE ID 批量查询（cve get / history get）

通过文件或标准输入提供多个 CVE ID，工具自动启用多线程并发查询。

**文本文件格式：**

```
CVE-2021-44228
CVE-2021-45046
# 注释行
CVE-2023-44487
```

**并发策略：**

- 1-2 个 ID：直接请求，不启用线程池
- 3 个以上 ID：启用线程池，每批最多 100 个 ID
- 每批内部使用 NVD API 的 `cveIds` 参数一次性查询
- 结果自动按 CVE-ID 去重

### 条件批量搜索（cve search --file）

通过 JSON 文件提供多组查询条件，每组条件独立执行，结果自动去重合并。

**JSON 文件格式：**

```json
[
  {
    "keyword": "openssl",
    "severity_v3": "CRITICAL",
    "limit": 5
  },
  {
    "keyword": "nginx",
    "pub_start": "2024-01-01",
    "pub_end": "2024-12-31"
  },
  {
    "cwe": "CWE-79",
    "severity_v3": "HIGH",
    "limit": 10
  }
]
```

---

## 日期范围处理

NVD API 要求日期范围不超过 120 天。本工具自动处理此限制：

- 输入的 `YYYY-MM-DD` 格式日期会自动转换为 NVD 要求的 ISO-8601 格式（`YYYY-MM-DDT00:00:00.000`）
- 日期范围超过 120 天时，自动拆分为多个不超过 120 天的子范围
- 拆分后的子范围逐个请求，结果自动合并
- 适用于 `--pub-start/--pub-end`、`--mod-start/--mod-end`、`--kev-start/--kev-end`、`--start/--end`（history search）

---

## 缓存机制

工具默认启用本地文件缓存，以减少对 NVD API 的重复请求。

- **缓存位置：** 项目目录下 `cache/` 目录
- **缓存策略：** 以请求 URL + 参数的 SHA256 哈希为文件名，存储 JSON 响应
- **缓存过期：** 默认 1800 秒（30 分钟），可通过 `cache_ttl` 配置
- **缓存禁用：** 命令行 `--no-cache` 或配置 `cache_enabled = false`

---

## 限流与重试

### 限流

工具内置令牌桶限流器，根据是否配置 API Key 自动调整策略：

| 认证方式 | 限流窗口 | 最大请求数（工具内部值） |
|---------|---------|----------------------|
| 无 API Key | 30 秒 | 4 次（留余量） |
| 有 API Key | 30 秒 | 45 次（留余量） |

限流器在多线程环境下线程安全，通过互斥锁保护时间戳列表。

### 重试

请求失败时自动重试，策略如下：

- 最大重试次数：3 次（可通过 `max_retries` 配置）
- 重试间隔：指数退避，第 n 次重试等待 2^n 秒
- 触发重试的 HTTP 状态码：403（限流）、429（请求过多）、503（服务不可用）
- 连接错误和读取超时同样触发重试

---

## 线程安全

- HTTP 客户端使用 `threading.local()` 为每个线程创建独立的 `httpx.Client` 实例
- 限流器和缓存存储内部使用互斥锁保护共享状态
- 批量查询结果通过互斥锁保护的结果列表收集

---

## 退出码

| 退出码 | 含义 |
|--------|------|
| `0` | 成功（`cve latest` 无结果时也返回 0） |
| `1` | 查询失败、未找到结果、参数错误 |

---

## 项目结构

```
nvd-cli/
  main.py                入口脚本
  requirements.txt       Python 依赖
  config.toml            配置文件（自动生成）
  cache/                 HTTP 缓存目录（自动生成）
  src/
    __init__.py          版本号定义
    main.py              typer 应用注册与全局选项
    config.py            配置管理（AppConfig）
    models.py            Pydantic 数据模型
    client.py            NVD API 客户端（限流、缓存、重试、分页）
    formatters.py        输出格式化（table/json/csv）
    batch.py             批量查询（输入解析、线程池、去重）
    commands/
      __init__.py
      cve.py             cve 子命令（get/search/latest）
      history.py         history 子命令（get/search）
      config_cmd.py      config 子命令（set/get/show）
```

---

## 依赖

| 包名 | 版本要求 | 用途 |
|------|---------|------|
| `typer` | >= 0.12.0 | CLI 框架 |
| `httpx` | >= 0.27.0 | HTTP 客户端 |
| `pydantic` | >= 2.0 | 数据模型与校验 |
| `rich` | >= 13.0 | 终端表格渲染 |
| `tomli_w` | >= 1.0 | TOML 写入 |
| `tomli` | >= 2.0 | TOML 读取（仅 Python < 3.11） |

**安装依赖：**

```bash
pip install -r requirements.txt
```

**运行要求：** Python >= 3.10
