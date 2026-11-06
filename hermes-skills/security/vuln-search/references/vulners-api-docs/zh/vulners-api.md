---
description: 漏洞情报 — 搜索、审计、集合
---

# 参考 — API 概述

请先阅读此页。它汇集了在参考文档中随处可见的核心概念：认证、响应字段以及如何使用 CPE 标识软件/操作系统。这些概念有意设计为平台无关 — 无论你是直接调用 REST 端点（curl）还是使用 [Python SDK](https://github.com/vulnersCom/api)，它们都同样有用。

Vulners API 返回针对软件、操作系统和 KB 列表的定向漏洞情报。要获得准确的结果，通常需要提供：

- 你正在扫描的目标（软件包、已安装的 KB 或操作系统）
- 你如何描述它们（原始 CPE 字符串或结构化 CPE 对象）
- 可选过滤器（要返回的字段、部分匹配还是完全匹配）

建议快速浏览本页一次，以便端点示例更容易理解。

此部分包含完整的 API 参考文档，按服务组织如下：
- 搜索（Search）
- 集合（Collections）
- 审计（Audit）
- 通知（Notifications）
- 报告（Reporting）

使用交互式查看器浏览 OpenAPI 规范：

- [打开 Redoc（交互式）](https://docs.vulners.com/docs/api/redoc.html)
- [打开 Swagger（交互式）](https://docs.vulners.com/docs/api/swagger.html)

---

## 认证

所有私有端点都需要 API 密钥。在请求头中发送你的密钥：

```
X-Api-Key: YOUR_API_KEY
```

---

## 响应格式

v3 端点返回：

```json
{
  "result": "OK",
  "data": { ... }
}
```

出错时，`result` 为 `"error"`，`data` 为 `{ "error": "<message>", "errorCode": <int> }`。

v4 端点返回：

```json
{
  "result": { ... }
}
```

[Python SDK](https://github.com/vulnersCom/api) 会为你解包。直接调用 HTTP 的用户在 v3 中读取 `data.*`，在 v4 中读取 `result.*`。

归档端点 — `/api/v4/archive/collection*` 和 `/api/v4/archive/family*` — 会流式传输 gzip 压缩的 NDJSON，或返回 `302` 重定向到 CDN URL。免费版密钥将收到 `403`。

---

## 默认响应字段

大多数示例和 SDK 调用默认返回一组精简实用的字段。如果需要更多数据，请使用 `fields` 参数请求额外属性。

| 字段名 | 描述 | 链接 |
|---|---|---|
| id | 数据库中每个文档或项的唯一标识符。 | [id](https://vulners.com/docs/api_reference/database_fields/#id) |
| title | 公告的标题，提供简洁摘要。 | [title](https://vulners.com/docs/api_reference/database_fields/#title) |
| description | 公告内容的详细描述。 | [description](https://vulners.com/docs/api_reference/database_fields/#description) |
| short_description | 基于 AI 的公告内容简短描述。 | [description](https://vulners.com/docs/api_reference/database_fields/#description) |
| type | 公告的供应商或来源类型（例如 "Debian"、"RedHat"）。 | [type](https://vulners.com/docs/api_reference/database_fields/#type) |
| bulletinFamily | 公告的类别或系列（例如 "Unix"、"Exploit"）。 | [bulletinFamily](https://vulners.com/docs/api_reference/database_fields/#bulletinFamily) |
| cvss | 通用漏洞评分系统指标。 | [cvss](https://vulners.com/docs/api_reference/database_fields/#cvss) |
| published | 公告的发布日期。 | [published](https://vulners.com/docs/api_reference/database_fields/#date) |
| modified | 公告的最后修改日期。 | [modified](https://vulners.com/docs/api_reference/database_fields/#date) |
| lastseen | 系统最后更新的时间戳。 | [lastseen](https://vulners.com/docs/api_reference/database_fields/#lastseen) |
| href | 指向公告来源或参考的 URL 链接。 | [href](https://vulners.com/docs/api_reference/database_fields/#href) |
| sourceHref | 指向公告数据原始来源的 URL 链接。 | [sourceHref](https://vulners.com/docs/api_reference/database_fields/#sourceHref) |
| sourceData | 利用或扫描器公告的附加数据（例如代码片段）。 | [sourceData](https://vulners.com/docs/api_reference/database_fields/#sourceData) |
| cvelist | 公告中涉及的 CVE 标识符列表。 | [cvelist](https://vulners.com/docs/api_reference/database_fields/#cvelist) |

公开端点会在不需要认证的位置进行标注。

---

## Vulners API 中的 CPE 使用

Vulners 接受 **原始 CPE 字符串** 或 **结构化 CPE 对象** 形式的软件/操作系统标识符。使用哪种更方便就用哪种 — 当你需要部分匹配或添加属性时，对象形式更友好。

### 什么是 CPE？

通用平台枚举（CPE）是一种用于 IT 系统、软件和包的结构化命名方案。CPE 名称（也称为 URI）如下所示：

```
cpe:<cpe_version>:<part>:<vendor>:<product>:<version>:<update>:<edition>:<language>:<sw_edition>:<target_sw>:<target_hw>:<other>
```

或者最短形式可以是：

```
cpe:2.3:a:microsoft:windows_10:21h2
```

由以下部分组成：

- **part** — `a`（应用程序）、`o`（操作系统）或 `h`（硬件）
- **vendor** — 软件/硬件的制造/分发方（例如 `microsoft`）
- **product** — 产品名称（例如 `windows_10`）
- **version** — 版本号或标签（例如 `21h2`）

CPE 对象可以包含**附加属性**，如 `update`、`sw_edition`、`target_sw`、`target_hw` 和 `language`。官方 [NISTIR 7695](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7695.pdf) 标准描述了这些字段的有效值和使用方法。

以下是 Vulners API 支持的附加字段摘要，你可以提供这些字段以提高搜索精度：

- **update（字符串）**：指定软件更新版本，用于细化特定更新级别的漏洞搜索。示例包括 Windows 的 `service packs`（如 `sp1`）、补丁版本、热修复或其他小更新。
  `update` 的官方 [NIST 7695](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7695.pdf)
  该属性的值应为供应商特定的字母数字字符串，用于描述产品的特定更新、服务包或小版本发布。该属性的值应从特定于属性的有效值列表中选择，该列表可由使用此规范的其他规范定义。

- **language（字符串）**：定义软件的语言版本（如适用）。用于定位特定语言版本软件中的漏洞。
  `language` 的官方 [NIST 7695](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7695.pdf)
  该属性的值应为 [RFC5646] 定义的有效语言标签，并应用于描述所描述产品用户界面支持的语言。虽然可以使用任何有效的语言标签，但应仅使用包含语言和地区代码的标签。

- **sw_edition（字符串）**：指示软件的特定版本（例如 Windows 的 `home_premium`、Acrobat Reader 的 `continuous` 或 Linux 的 `server`）。
  `sw_edition` 的官方 [NIST 7695](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7695.pdf)
  该属性的值应描述产品如何针对特定市场或最终用户类别进行定制。该属性的值应从特定于属性的有效值列表中选择，该列表可由使用此规范的其他规范定义。任何符合 WFN 要求（参见 5.3.2）的字符串都可以作为该属性的值指定。

- **target_sw（字符串）**：指定软件运行平台，如 `windows`、`macOS`、`linux` 或其他环境（如 `java`、`chrome`、`azure` 等）。如果未指定，搜索将包含在任何 `*` 平台上运行的软件。
  `target_sw` 的官方 [NIST 7695](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7695.pdf)
  该属性的值应描述产品运行的软件计算环境。该属性的值应从特定于属性的有效值列表中选择，该列表可由使用此规范的其他规范定义。

- **target_hw（字符串）**：标识软件的硬件平台，如 `x86`、`x64`、`arm` 或特定设备（如 `router` 或 `mobile`）。
  `target_hw` 的官方 [NIST 7695](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7695.pdf)
  该属性的值应描述 WFN 所描述或标识的产品运行的指令集架构（例如 `x86`）。字节码中间语言（如 Java 虚拟机的 Java 字节码或公共语言运行时虚拟机的 Microsoft 公共中间语言）应被视为指令集架构。

### 在请求中使用 CPE

在本文档中，你将看到通过以下（或类似）方式使用 CPE 指定**软件**的方式：

- **完整原始 CPE** 字符串，例如：
```json
{"software": "cpe:2.3:a:mozilla:firefox:117.0:*:*:*:*:*:*:*"}
```

- **包含独立字段的对象**（推荐用于部分匹配或附加属性）：
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

这两种方式在不同端点中均有效。具体语法请参见相应章节。
