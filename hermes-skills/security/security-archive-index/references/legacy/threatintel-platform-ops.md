<!-- archived from /root/.hermes/skills/security/threatintel-platform-ops/SKILL.md on 2026-10-21 -->

---
name: threatintel-platform-ops
description: "Use when 搭情报平台/狩猎:MISP、TAXII、IOC生命周期、SOAR。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/threatintel-platform-ops`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/threatintel-platform-ops/…')`，不要相对 `references/legacy/` 解析。

# 威胁情报平台工程与情报驱动运营（threatintel-platform-ops）

## 何时用

- 要**搭/运维情报平台**：MISP、OpenCTI、TheHive 5 + Cortex、Shuffle 的部署、接源、共享分发。
- 要**接 TAXII/STIX 情报**：TAXII 2.1 采集、STIX 2.1 对象入库、IOC 提取与归一。
- 要**做 IOC 治理**：采集→标准化→去重→丰富→分发→退役 全流程与去重规则。
- 要**归因**：APT/家族分析的方法与真实数据源 API（VT、MITRE ATT&CK、MISP Galaxy）。
- 要**情报驱动狩猎/SOC 平台化**：假设与 PDCA、DNS 隧道/Beaconing 查询、事件分级、SOAR 剧本、IR 复盘与证据链。

## 不写什么（边界）

磁盘/内存/浏览器取证、PCAP 深挖、主机应急排查、恶意样本分析**不在本卡**：分别用 `digital-forensics`、`traffic-analysis-pcap`、`host-ir-check`、`malware-analysis`、`incident-response`。本卡只做"平台工程 + 情报流 + 狩猎/响应流程落地"，取证处只写交叉引用。

## 工作流

1. **定盘子**：MISP 存 IOC 与共享；OpenCTI 做图谱与关联；TheHive/Cortex 收案与富化；Shuffle 做编排。
2. **起平台**：MISP 用官方 `MISP/misp-docker`（`cp template.env .env` → `docker compose pull/up -d`，默认 `<EMAIL-REDACTED>/admin`，首登即改）；OpenCTI 用 `OpenCTI-Platform/docker`（`cp .env.sample .env`）；TheHive 5 用 `StrangeBeeCorp/docker`，别用 TheHive 3 时代的 `docker run thehiveproject/thehive`（仓库已 archived）。
3. **接源**：低频 feed 用 MISP feed（`enable_feed/fetch_feed`），带鉴权的源走 connector；TAXII 2.1 用 `taxii2-client` 的 v21 客户端按 `added_after` 增量拉。
4. **治理**：入库前用 warninglist 挡公共域名/CDN，按 `(type, 归一化值)` 去重，设 `valid_until`/衰减模型，退役要同步下发通道删除。
5. **承接到狩猎**：把 IOC/假设置成 Splunk/Elastic 查询，命中即转检测规则（Sigma），并把结果回写案件 task log。
6. **闭环**：事件按 L1–L4 分级 → 三级流程处置 → 复盘出改进项（带 owner/deadline）→ 改进项反哺检测规则与情报源。

## 命令速查

```bash
# MISP（官方 docker 编排）
git clone https://github.com/MISP/misp-docker && cd misp-docker && cp template.env .env
docker compose pull && docker compose up -d      # 默认 http://localhost  <EMAIL-REDACTED> / admin

# 免鉴权情报源（实测可用）
curl -sL -o feodo.txt  https://feodotracker.abuse.ch/downloads/ipblocklist.txt   # C2 IP 逐行
curl -sL -o tf.csv     https://threatfox.abuse.ch/export/csv/recent/
curl -sL -o uh.csv     https://urlhaus.abuse.ch/downloads/csv_recent/
# 需 key：OTX(X-OTX-API-KEY)、AbuseIPDB、VirusTotal(x-apikey)、MalwareBazaar(Auth-Key) —— 匿名调用已失效

# TAXII 2.1（实测）
curl -s -H 'Accept: application/taxii+json;version=2.1' https://attack-taxii.mitre.org/taxii2/
curl -s -H 'Accept: application/taxii+json;version=2.1' https://attack-taxii.mitre.org/api/v21/collections/

# Shuffle（实测官方 install-guide）
git clone https://github.com/Shuffle/Shuffle && cd Shuffle && docker compose up -d   # UI :3001
```

```python
from pymisp import PyMISP, MISPEvent, MISPAttribute
misp = PyMISP('https://misp.local', 'API_KEY', ssl=False)
e = MISPEvent(); e.info = 'IR-2026-001 IOC'; e.distribution = 0
e.add_attribute('ip-dst', '185.220.101.50', to_ids=True); e.add_tag('tlp:amber')
e = misp.add_event(e)
a = MISPAttribute(); a.type = 'sha256'; a.value = 'a'*64
misp.add_attribute(e, a, break_on_duplicate=True)     # 默认 True=重复报错；False=更新
misp.freetext(e, '1.2.3.4 evil.example.com', adhereToWarninglists=True)
misp.attach_galaxy_cluster(e, cluster_id)             # galaxy cluster id 用 search_galaxy_clusters 查

from taxii2client.v21 import Server
srv = Server("https://attack-taxii.mitre.org/taxii2/")
col = [c for c in srv.api_roots[0].collections if 'Enterprise' in c.title][0]
page = col.get_objects(added_after='2026-09-01T00:00:00.000Z', limit=100)   # 翻页看 more/next
```

```splunk
index=windows EventCode=4624 LogonType=10
| stats count by Account_Name, WorkstationName, IpAddress | where count > 10 | sort -count
```

## Pitfalls

- **PyMISP 构造方式变了**：属性用 `MISPEvent().add_attribute(type, value, **kw)` 或 `PyMISP.add_attribute(event, MISPAttribute|list)`；`MISPAttribute(type=..., value=...)` 会 `TypeError`（实测）。
- **`add_attribute` 的 `break_on_duplicate` 默认 True**（重复即报错），批量灌库时想"重复即更新"要显式设 False。
- **TAXII**：必须带 `Accept: application/taxii+json;version=2.1`；翻页用响应里的 `more`/`next`；会出现 502，采集端要退避重试。
- **STIX 必填字段**：Indicator 需 `pattern/pattern_type/valid_from`，Malware 需 `is_family`，缺字段直接抛异常；threat-actor 与 malware 之间用 `relationship` 连边，否则图谱是孤岛。
- **别照抄旧法**：`docker run thehiveproject/thehive:latest`（TheHive 3）与"MalwareBazaar 匿名可用"都已失效；PassiveTotal 旧 API 已并入 Microsoft Defender Threat Intelligence（未验证替代路径）。
- **上游脚本坑**：Zeek 日志是 TSV 带 `#fields` 头，pandas 必须 `sep='\t', comment='#'`；取列用 `zeek-cut 列名`，不要 awk 数第几列；上游 Suricata 规则里的 `dns.resp_len` 不是官方关键字，装规则前先 `suricata -T`。
- **别把启发式当规则**：分级评分、熵阈值（>3.5）、Beaconing CV（<0.5）都是经验值，按环境调；Beaconing 一定要过滤更新检查/CDN/遥测，否则误报淹没。
- **自动化只自动可逆动作**：隔离/禁用/删除类动作加人工确认闸，剧本要幂等（alert id 作键）并写字回案件 task log。

## 参考文件

- `references/threatintel-platform.md`：MISP/OpenCTI/TheHive 部署与 API、PyMISP、TAXII 2.1、STIX 2.1、IOC 生命周期与去重、APT 归因数据源、情报质量指标。
- `references/ir-hunting-platform.md`：狩猎假设与 PDCA、Splunk/Elastic 查询、DNS 隧道与 Beaconing（Zeek/Suricata/tcpdump/RITA）、SOC 分级与三级流程、SOAR 剧本、复盘骨架、证据链与时间线。
- `references/provenance-and-unverified.md`：来源核对（哪些命令搬自上游 / 哪些是补充 / 未验证清单）。
