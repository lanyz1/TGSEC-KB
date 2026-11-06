# 报告

根据扫描和资产清单生成现成的审计报告 — 包括漏洞摘要、主机摘要、漏洞列表、扫描历史以及每台主机的漏洞清单。

**打开交互式规范文档：**
- [打开 Redoc (交互式)](https://docs.vulners.com/docs/api/redoc.html)
- [打开 Swagger (交互式)](https://docs.vulners.com/docs/api/swagger.html)

---

## 概述

使用 `POST /api/v3/reports/vulnsreport/` 获取服务端生成的报告。每个请求包含一个 `reporttype` 字段。

**认证**：需要 `X-Api-Key` 请求头。

**公共参数：**

| 名称        | 位置   | 类型    | 必填 | 描述                                                                                          |
| ----------- | ------ | ------- | ---- | --------------------------------------------------------------------------------------------- |
| reporttype  | body   | string  | 是   | 可选值：vulnssummary, vulnslist, ipsummary, vulninfo, scanlist, hostvulns。                   |
| filter      | body   | object  | 否   | 过滤对象，例如 `{"OS":"Centos","OSVersion":"7"}` 或 `{"agentip":"10.2.2.2"}`。               |
| sort        | body   | string  | 否   | 排序表达式，例如 `-published`（减号表示降序）。                                               |
| skip/offset | body   | integer | 否   | 分页偏移量（从零开始）。                                                                      |
| size / limit| body   | integer | 否   | 返回的记录数量。                                                                              |

**请求：** `POST /api/v3/reports/vulnsreport/`

---

## 漏洞摘要报告

带数量和评分的聚合漏洞列表 — 适用于仪表板与优先级修复。

```bash
curl -XPOST https://vulners.com/api/v3/reports/vulnsreport/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"reporttype": "vulnssummary"}'
```

**Python：**
```python
report = vulners_api.vulnssummary_report()
```

**响应：**
```json
[
  {
    "vulnID": "CVE-2019-8457",
    "title": "CVE-2019-8457",
    "family": "cve",
    "severity": 4,
    "severityText": "high",
    "count": 2,
    "score": 7.5
  },
  {
    "vulnID": "CVE-2022-32774",
    "title": "CVE-2022-32774",
    "family": "cve",
    "severity": 2,
    "severityText": "low",
    "count": 2,
    "score": 0.0
  }
]
```

---

## 主机摘要报告

每台主机的风险摘要：基于 CVSS 的评分、按严重程度分类的漏洞数量、操作系统信息及总计。

```bash
curl -XPOST https://vulners.com/api/v3/reports/vulnsreport/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"reporttype": "ipsummary", "skip": 2, "size": 4}'
```

**Python：**
```python
report = vulners_api.ipsummary_report(limit=2, offset=4)
```

**响应：**
```json
[
  {
    "agentid": "30TS<...>LKLE",
    "agentip": "10.1.1.1",
    "agentfqdn": "somehost1",
    "osname": "windows",
    "osversion": "10.0.19045",
    "score": 16.4,
    "total": 10,
    "vulnerabilities": { "low": 9, "high": 1 }
  },
  {
    "agentid": "MVEB<...>3HCC",
    "agentip": "10.2.2.2",
    "agentfqdn": "somehost2",
    "osname": "debian",
    "osversion": "10",
    "score": 12.3,
    "total": 5,
    "vulnerabilities": { "low": 5 }
  }
]
```

---

## 已检测漏洞列表

已发现漏洞的平面列表；支持基于主机的过滤。

```bash
curl -XPOST https://vulners.com/api/v3/reports/vulnsreport/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"reporttype":"vulnslist", "filter":{"agentip": "10.2.2.2"}}'
```

**Python：**
```python
report = vulners_api.report.vulns_list(filter={"agentip": "10.2.2.2"})
```

**响应：**
```json
[{
    "vulnID": "DEBIAN:DSA-5235-1:A2B24",
    "title": "[SECURITY] [DSA 5235-1] bind9 security update",
    "family": "debian",
    "severity": 2,
    "severityText": "low",
    "agentip": "10.2.2.2",
    "agentfqdn": "somehost2",
    "cumulativeFix": "sudo apt-get --assume-yes install --only-upgrade bind9-host",
    "scanid": "Q13T<...>IQU9"
}]
```

---

## 已执行扫描列表

获取扫描元数据（扫描时间、操作系统、主机、扫描 ID、聚合 CVSS）。

```bash
curl -XPOST https://vulners.com/api/v3/reports/vulnsreport/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"reporttype":"scanlist", "sort":"-modified"}'
```

**Python：**
```python
report = vulners_api.report.scan_list(sort='-modified')
```

**响应：**
```json
[
  {
    "ipaddress": "10.3.3.3",
    "OS": "redhat",
    "fqdn": "somehost3",
    "OSVersion": "8.7",
    "modified": "2023-02-01T10:44:21",
    "id": "F8YD<...>IHFC",
    "cvss": { "score": 9.0, "vector": "AV:N/AC:L/Au:S/C:C/I:C/A:C" }
  },
  {
    "ipaddress": "10.1.1.1",
    "OS": "windows",
    "fqdn": "somehost1",
    "OSVersion": "10.0.19045",
    "modified": "2023-01-13T10:06:49",
    "id": "QJN1<...>TAIH",
    "cvss": { "score": 0.0, "vector": "NONE" }
  }
]
```

---

## 主机上的漏洞列表

以主机为中心的报表，返回漏洞 ID 数组、汇总修复命令及主机元数据。

```bash
curl -XPOST https://vulners.com/api/v3/reports/vulnsreport/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"reporttype":"hostvulns"}'
```

**Python：**
```python
report = vulners_api.report.host_vulns()
```

**响应：**
```json
[
  {
    "agentip": "10.2.2.2",
    "agentfqdn": "somehost2",
    "osname": "debian",
    "osversion": "10",
    "cumulativeFix": "sudo apt-get --assume-yes install --only-upgrade bind9-host",
    "vulnerabilities": [
      "DEBIAN:DSA-5105-1:A867B",
      "DEBIAN:DSA-5235-1:A2B24",
      "DEBIAN:DLA-2955-1:40374",
      "DEBIAN:DLA-3138-1:2F5A9",
      "DEBIAN:DLA-2955-2:CDB18"
    ],
    "published": "2023-02-23T10:55:41"
  },
  {
    "agentip": "10.1.1.1",
    "agentfqdn": "somehost1",
    "osname": "windows",
    "osversion": "10.0.19045",
    "cumulativeFix": "",
    "vulnerabilities": [
      "CVE-2022-32774", "OSV:CVE-2021-20227", "CVE-2022-37332",
      "CVE-2019-16168", "CVE-2022-42919", "CVE-2016-6153",
      "CVE-2019-8457", "CVE-2022-35737", "CVE-2022-40129", "CVE-2022-38097"
    ],
    "published": "2022-12-30T13:08:59"
  }
]
```
