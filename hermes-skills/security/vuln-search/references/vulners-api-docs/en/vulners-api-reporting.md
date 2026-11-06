# Reporting

Generate ready-made audit reports from your scans and inventory — vulnerability summaries, host summaries, vulnerability lists, scan histories, and per-host vulnerability listings.

**Open interactive specs:**
- [Open Redoc (interactive)](https://docs.vulners.com/docs/api/redoc.html)
- [Open Swagger (interactive)](https://docs.vulners.com/docs/api/swagger.html)

---

## Overview

Use `POST /api/v3/reports/vulnsreport/` to fetch server-generated reports. Each request includes a `reporttype` field.

**Auth**: `X-Api-Key` header required.

**Common Parameters:**

| Name         | In   | Type    | Required | Description                                                                                       |
| ------------ | ---- | ------- | -------- | ------------------------------------------------------------------------------------------------- |
| reporttype   | body | string  | yes      | One of: vulnssummary, vulnslist, ipsummary, vulninfo, scanlist, hostvulns.                        |
| filter       | body | object  | no       | Filtering object, e.g. `{"OS":"Centos","OSVersion":"7"}` or `{"agentip":"10.2.2.2"}`.             |
| sort         | body | string  | no       | Sort expression, e.g. `-published` (minus = descending).                                          |
| skip/offset  | body | integer | no       | Pagination offset (zero-based).                                                                   |
| size / limit | body | integer | no       | Number of records to return.                                                                      |

**Query:** `POST /api/v3/reports/vulnsreport/`

---

## Vulnerability Summary Report

Aggregated list of vulnerabilities with counts and scores — good for dashboards and prioritized remediation.

```bash
curl -XPOST https://vulners.com/api/v3/reports/vulnsreport/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"reporttype": "vulnssummary"}'
```

**Python:**
```python
report = vulners_api.vulnssummary_report()
```

**Response:**
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

## Host Summary Report

Per-host risk summary: CVSS-based score, vulnerability counts by severity, OS info and totals.

```bash
curl -XPOST https://vulners.com/api/v3/reports/vulnsreport/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"reporttype": "ipsummary", "skip": 2, "size": 4}'
```

**Python:**
```python
report = vulners_api.ipsummary_report(limit=2, offset=4)
```

**Response:**
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

## List of Detected Vulnerabilities

Flat list of discovered vulnerabilities; supports host-based filtering.

```bash
curl -XPOST https://vulners.com/api/v3/reports/vulnsreport/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"reporttype":"vulnslist", "filter":{"agentip": "10.2.2.2"}}'
```

**Python:**
```python
report = vulners_api.report.vulns_list(filter={"agentip": "10.2.2.2"})
```

**Response:**
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

## List of Performed Scans

Retrieve scan metadata (when scans were performed, OS, host, scan id, aggregated CVSS).

```bash
curl -XPOST https://vulners.com/api/v3/reports/vulnsreport/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"reporttype":"scanlist", "sort":"-modified"}'
```

**Python:**
```python
report = vulners_api.report.scan_list(sort='-modified')
```

**Response:**
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

## List of Vulnerabilities on a Host

Host-centric report returning an array of vulnerability IDs, summary fix command, and host metadata.

```bash
curl -XPOST https://vulners.com/api/v3/reports/vulnsreport/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"reporttype":"hostvulns"}'
```

**Python:**
```python
report = vulners_api.report.host_vulns()
```

**Response:**
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
