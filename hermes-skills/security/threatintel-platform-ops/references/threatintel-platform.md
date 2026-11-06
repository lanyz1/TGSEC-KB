# 威胁情报平台工程参考（MISP / OpenCTI / TheHive / TAXII-STIX / IOC 生命周期 / APT 归因）

> 上游来源：Hi-FullHouse/CyberSecurity-Skills `29-威胁情报-ThreatIntelligence/skills/*.md`（4 张卡）。
> 标注约定：**【实测】**= 本机跑通或已核对真实返回/源码签名；**【上游】**= 上游原文保留、未复测；**【未验证】**= 需在目标环境复测。
> 本文件不写磁盘/内存取证方法论。需要时交叉引用本库已有卡：`digital-forensics`、`traffic-analysis-pcap`、`host-ir-check`、`incident-response`、`malware-analysis`。

## 0. 平台分工（最小可用组合）

| 角色 | 平台 | 定位 |
|:---|:---|:---|
| IOC 库 + 共享分发 | MISP | 事件/属性/feed/TAXII server，PyMISP 可编程【实测】 |
| 知识图谱 + 关联分析 | OpenCTI | STIX 2.1 原生，connector 拉外部源【实测仓库】 |
| 案件 + 分析器 | TheHive 5 / Cortex | 案例、任务、observable、富化【实测 API 路径】 |
| 编排自动化 | Shuffle（Tines/XSOAR 同类） | webhook → 富化 → 阻断/隔离/建案【实测部署命令】 |
| 检测面 | Splunk / Elastic | IOC lookup 与狩猎查询，见 `ir-hunting-platform.md` |

## 1. MISP Docker 部署【实测仓库 + 官方命令文本】

```bash
# 前置（上游 README 实测要求）：Docker Engine 25+ 或 Podman 4.9+，Compose plugin 2.17+，可拉 ghcr.io 与 Docker Hub
git clone https://github.com/MISP/misp-docker && cd misp-docker
cp template.env .env          # 仓库根目录实测存在 template.env 与 docker-compose.yml
docker compose pull           # 用官方预构建镜像，不必 build
docker compose up  -d
# 默认入口 http://localhost  <EMAIL-REDACTED> / admin   ← 首次登录后立刻改
```

- `.env` 关键项（官方 README 实测列出）：`MYSQL_HOST/USER/PASSWORD/DATABASE`（密码必须是字母数字，含特殊字符要改 config 文件）、`MISP_MODULES_FQDN=http://misp-modules`、`SMTP_PORT`、`NUM_WORKERS_*`。
- 防误共享泄露：可选 `MISP-Guard`（mitmproxy 插件）——`COMPOSE_PROFILES=misp-guard` + `PROXY_ENABLE=true` / `PROXY_HOST=misp-guard` / `PROXY_PORT=8888`，规则在 `guard/config.json`【实测 README】。
- 同类仓库别混用：`MISP/misp-docker`（394★，master，官方 production ready，MISP 与 misp-modules 拆两个镜像）；`harvard-itsecurity/docker-misp`（174★，活跃社区版）。**未验证**：网上流传的手写 `docker run misp/misp-docker ...` 组合，本机只核对了仓库文件存在性与 README 命令，未实际起容器。
- REST 鉴权：`Authorization: <API_KEY>`（MISP 惯例，本机未连服务器复测）；共享前先建 sharing group 并定 TLP。

## 2. PyMISP 真实用法【实测：2.5.34.4 安装 + 方法签名 + 离线对象构造】

```python
from pymisp import PyMISP, MISPEvent, MISPAttribute, MISPObject
misp = PyMISP('https://misp.local', 'API_KEY', ssl=False)   # ssl 参数实测存在于 __init__

# 建 event + 属性：必须用 MISPEvent().add_attribute(type, value, **kwargs)
e = MISPEvent()
e.info = 'IR-2026-001 C2 IOC'; e.distribution = 0; e.threat_level_id = 2
e.add_attribute('ip-dst', '185.220.101.50', to_ids=True, comment='C2')   # 实测返回 MISPAttribute
e.add_attribute('domain', 'evil.example.com')
e.add_tag('tlp:amber')                     # 实测返回 MISPTag
e = misp.add_event(e)                      # 在线时返回带 id/uuid 的事件

# 也支持先造对象再挂：PyMISP.add_attribute(event, attribute: MISPAttribute | Iterable[str], break_on_duplicate=True)
a = MISPAttribute(); a.type = 'sha256'; a.value = 'a' * 64
misp.add_attribute(e, a, break_on_duplicate=True)   # 默认 True=重复即报错；False=更新已存在属性

o = MISPObject('file'); o.add_attribute('filename', 'x.exe')   # 实测可构造
# 反例（实测 TypeError）：MISPAttribute(type='ip-dst', value='x') 不接受关键字构造
```

批量导入与 galaxy【均为实测存在的方法；在线行为未复测】：

```python
misp.freetext(e, '1.2.3.4 evil.example.com', adhereToWarninglists=True)  # 自由文本抽 IOC，warninglist 挡公共域名
misp.upload_stix(e, open('bundle.json', 'rb'))                            # STIX 导入
misp.feeds(); misp.enable_feed(fid); misp.fetch_feed(fid); misp.fetch_all_feeds()
misp.load_default_feeds()          # 首装灌默认 feed，量大，注意配额
misp.tag(e, 'misp-galaxy:mitre-attack-pattern="Command and Scripting Interpreter - T1059"')
cid = misp.search_galaxy_clusters(...)          # 先查 cluster id，别硬编码名称（misp-galaxy 会变）
misp.attach_galaxy_cluster(e, cid, local=False) # 签名实测：attach_galaxy_cluster(misp_entity, galaxy_cluster, local=False)
misp.search(controller='attributes', value='185.220.101.50', type_attribute='ip-dst', to_ids=True, pythonify=True)
misp.search(controller='events', tags=['tlp:amber'], published=True)
misp.attribute_exists('ip-dst', '1.2.3.4'); misp.publish(e); misp.add_sighting(sighting)
```

## 3. TAXII 2.1 采集【实测：MITRE ATT&CK 公共源全链路跑通】

```bash
curl -s -H 'Accept: application/taxii+json;version=2.1' https://attack-taxii.mitre.org/taxii2/
# 实测返回 {"title":"MITRE ATT&CK TAXII 2.1","default":"/api/v21","api_roots":["/api/v21",...]}
curl -s -H 'Accept: application/taxii+json;version=2.1' https://attack-taxii.mitre.org/api/v21/collections/
# 实测 3 个集合：Enterprise / ICS / Mobile ATT&CK，id 形如 x-mitre-collection--1f5f1533-f617-4ca8-9ab4-6a02367fa019
```

```python
# taxii2-client 2.3.0（PyPI 包名实测仍是 taxii2-client；上游 OASIS 仓库已改名 cti-taxii-client）
from taxii2client.v21 import Server           # 实测签名 Server(url, user=None, password=None, verify=True, proxies=None, auth=None, cert=None)
srv = Server("https://attack-taxii.mitre.org/taxii2/")        # 需认证的源：Server(url, user, password)
col = [c for c in srv.api_roots[0].collections if 'Enterprise' in c.title][0]
print(col.id, col.title, col.media_types)      # Collection 实测方法含 get_objects/get_object/get_manifest/add_objects
page = col.get_objects(limit=50)               # 实测返回 {'more': True, 'objects': [...]}
for o in page['objects']:
    if o['type'] == 'indicator':
        print(o['name'], o['pattern'], o.get('valid_from'))
page = col.get_objects(added_after='2026-09-01T00:00:00.000Z', limit=100)   # 增量
# 翻页：while page.get('more'): page = col.get_objects(next=page['next'], limit=100)
```

Pitfalls【实测】：① 必须带 `Accept: application/taxii+json;version=2.1`；② 翻页靠响应 `more`/`next`，不是 offset；③ 单次实测出现过 502 Bad Gateway，重试即恢复 → 采集端加指数退避；④ `https://limo.anomali.com/api/v1/taxii2/`（guest/guest）本次网络不可达【未验证】；⑤ OpenCTI 自带只读 `/taxii2/` 端点，凭据要求随版本变化【未验证】。

## 4. STIX 2.1 对象结构与 IOC 提取【实测：stix2 3.0.2 离线 round-trip】

```python
from stix2 import Indicator, Malware, Bundle, parse
ind = Indicator(name='C2 IP', pattern="[ipv4-addr:value = '185.220.101.50']", pattern_type='stix',
                valid_from='2026-09-01T00:00:00Z', labels=['malicious-activity'],
                indicator_types=['malicious-activity'])
raw  = Bundle(objects=[ind, Malware(name='Emotet', is_family=True)]).serialize(pretty=True)
back = parse(raw, allow_custom=True)           # 实测回读 types: ['indicator','malware']
```

- 必填字段坑【实测】：Indicator 需 `pattern`/`pattern_type`/`valid_from`；Malware 需 `is_family`；缺失直接抛 `MissingPropertiesError`。
- 常用对象：`indicator`（STIX pattern）、`malware`、`threat-actor`、`campaign`、`infrastructure`、`identity`、`observed-data`（包 SCO）、`relationship`（关系对象，需自行 join）、`report`、`note`。
- IOC 提取：`[ipv4-addr:value='x']` / `[domain-name:value='y']` / `[file:hashes.'SHA-256'='z']`。粗提正则 `(\w[\w-]*):\w+\s*=\s*'([^']+)'`【实测可用】；严谨解析走 `stix2.pattern_visitor` 的 AST。
- 关系补全：threat-actor/campaign 与 malware/indicator 之间要靠 `relationship(relationship_type='uses'|'targets')` 连边，否则图里全是孤岛。
- 数据实况：MITRE Enterprise collection 一次 50 条抽样实测为 `campaign 35 / course-of-action 14 / x-mitre-collection 1` —— 按 `type` 过滤再入库，别默认全是 IOC。

## 5. OpenCTI / TheHive / Cortex 联动

OpenCTI【实测仓库文件】：

```bash
git clone https://github.com/OpenCTI-Platform/docker.git && cd docker
cp .env.sample .env     # 实测存在 .env.sample 与 docker-compose.yml
docker compose up -d    # 官方文档 https://docs.opencti.io/latest/deployment/installation/#using-docker
```

注意【实测 README】：新版 stack 默认捆绑 XTM One（`xtm-one`/`xtm-one-worker`/`pgsql-xtm-one`，`XTM_ONE_PORT` 默认 8090），用 `PLATFORM_REGISTRATION_TOKEN` 做跨平台注册；只想跑 OpenCTI 本体需按官方文档裁剪服务。

TheHive 5 + Cortex（StrangeBee）：

- 旧法作废：上游写的 `docker run -d --name thehive -p 9000:9000 thehiveproject/thehive:latest` 是 TheHive 3 时代镜像；`TheHive-Project/TheHive` 仓库已 archived【实测】，改用 `StrangeBeeCorp/docker`（compose profile 同时拉起 TheHive + Cortex）。
- 客户端：`pip install thehive4py`（2.1.0，summary "Python client for TheHive5"），`TheHiveApi(url, apikey=...)`【实测签名】。
- 实测存在的 REST 路径（来自 thehive4py 2.1.0 源码，共 104 条）：`POST /api/v1/case`、`/api/v1/case/{case_id}/observable`、`/api/v1/case/{case_id}/task`、`/api/v1/case/{case_id}/timeline`、`/api/v1/case/{case_id}/comment`、`/api/v1/alert/{alert_id}/case`（告警升案）、`/api/v1/alert/{alert_id}/observable`、`/api/v1/task/{task_id}/log`、`/api/v1/observable/_bulk`、`/api/v1/query`。
- 联动要点（补充，**未验证**端到端）：MISP→TheHive 用官方 connector 推 IOC；TheHive→Cortex 把 observable 送分析器富化后回写 observable；Shuffle webhook 串起 MISP 查询 + VT 富化 + TheHive 建案（剧本见 `ir-hunting-platform.md` §5）。

## 6. IOC 生命周期：采集 → 标准化 → 去重 → 丰富 → 分发 → 退役

**采集**（下表 URL 的状态码/字段为本次实测）：

| 源 | URL | 实测结果 |
|:---|:---|:---|
| abuse.ch Feodo Tracker | `https://feodotracker.abuse.ch/downloads/ipblocklist.txt`（另有 `.csv`） | 200，逐行纯 IP |
| abuse.ch ThreatFox | `https://threatfox.abuse.ch/export/csv/recent/` | 200 |
| abuse.ch URLhaus | `https://urlhaus.abuse.ch/downloads/csv_recent/` | 200，字段 id,date_added,url,url_status,last_online,threat,tags,urlhaus_link,reporter |
| stamparm/ipsum | `https://raw.githubusercontent.com/stamparm/ipsum/master/ipsum.txt` | 200，行尾数字=命中黑名单数 |
| OpenPhish | `https://openphish.com/feed.txt` | 302，必须 `curl -L` |
| AlienVault OTX | `https://otx.alienvault.com/api/v1/indicators/export` | 403，需 `X-OTX-API-KEY` |
| AbuseIPDB | `https://api.abuseipdb.com/api/v2/blacklist` | 401，需 Key |
| MalwareBazaar | `POST https://mb-api.abuse.ch/api/v1/` `query=...` | 401；带假 `Auth-Key` 头 → 403 `{"query_status":"unknown_auth_key"}`，**即现在必须注册 abuse.ch Auth-Key，上游"匿名可用"已失效** |

```bash
curl -sL -o feodo.txt https://feodotracker.abuse.ch/downloads/ipblocklist.txt
grep -vE '^#' feodo.txt | head            # 实测输出真实 C2 IP
```

- **标准化**：域名小写、去尾点/去 `www.`；IP 去前导零与方括号；defang↔refang（`hxxp`→`http`、`[.]`→`.`）；hash 统一小写（十六进制哈希大小写不敏感，与 base64/口令不同）；URL 去 utm 与 fragment；时间一律 UTC ISO8601。入 MISP 时 `adhereToWarninglists=True`【实测签名】挡公共域名/CDN。
- **去重**：复合主键 `(type, normalized_value)`；MISP 侧 `break_on_duplicate`（默认 True=重复报错）与 `attribute_exists()`【实测签名】；同一 IOC 多来源时只加 `source/confidence/first_seen`，不新增行。
- **丰富**：VT（`x-apikey`，实测无 key 报 `X-Apikey header is missing`）；misp-modules 容器做 whois/域名/样本富化；Cortex analyzer。
- **分发**：MISP feed / TAXII server → OpenCTI connector → SIEM lookup（Splunk lookup、Elastic threat-intel index）→ 防火墙/EDR 阻断表；分发前定 TLP 与 sharing group。
- **退役**：按 `valid_until` 或衰减模型（`misp.decaying_models()`【实测存在】）；C2 IP 类高漂移 IOC 建议 TTL 7–30 天，域名/哈希可放长；退役必须同步下发通道的**删除**，否则 SIEM 永久误报。

```python
# 归一+去重最小实现（本机实测可跑）
import re
def norm(t, v):
    v = v.strip().strip('.,;')
    if t in ('domain', 'hostname', 'url'):
        v = re.sub(r'^www\.', '', v.lower().rstrip('.'))
    if t == 'ip': v = v.strip('[]')
    if t == 'sha256': v = v.lower()
    return (t, v)
seen = set(); out = []
for t, val in [('ip','185.220.101.50'), ('ip','185.220.101.50'), ('domain','Evil.Example.com.')]:
    k = norm(t, val)
    if k not in seen: seen.add(k); out.append(k)
print(out)   # [('ip','185.220.101.50'), ('domain','evil.example.com')]
```

## 7. APT 归因方法与真实数据源 API

方法（取自上游 29-003 的三层证据模型；**丢弃**其"APTProfile/AttributionAnalysis"演示类代码，只留方法）：

- 技术层：编译路径/PDB/语言字符串、代码复用（loader、加密算法）、C2 基础设施重叠（同 IP 段/ASN/证书/sink 记录）、工具重叠、YARA 家族命中。
- 运营层：目标画像（行业、地域、时间窗对齐工作时段）、投递话术模板、扫描节奏与基础设施轮换周期。
- 战略层：动机、地缘背景、受害者学（victimology）。
- 置信度：上游用权重求和成百分数【上游，公式未验证】——可作**排序**，不可当概率；对外结论必须写 `confidence: low/medium/high` 并附反证。
- 输出物：ATT&CK 技术映射表 + 工具/恶意软件表 + 基础设施表 + 证据清单 + 检测建议（Sigma/YARA/IOC）+ TLP。

```bash
# VirusTotal v3（端点与 header 名实测：无 key → 401「X-Apikey header is missing」）
curl -s -H "x-apikey: $VT_KEY" https://www.virustotal.com/api/v3/files/<sha256>
curl -s -H "x-apikey: $VT_KEY" https://www.virustotal.com/api/v3/ip_addresses/185.220.101.50
curl -s -H "x-apikey: $VT_KEY" https://www.virustotal.com/api/v3/domains/evil.example.com
# MITRE ATT&CK：TAXII 2.1（见 §3）或 https://github.com/mitre-attack/attack-stix-data
# Malpedia（恶意软件家族关联）：https://malpedia.caad.fkie.fraunhofer.de/  —— API 细节【未验证】
```

已失真、别照抄上游：`PassiveTotal` 已并入 Microsoft Defender Threat Intelligence，旧 API 下线【未验证，按现产品文档确认】；MalwareBazaar 免鉴权调用已失效（见 §6）。

## 8. 情报质量评估指标

| 指标 | 定义 | 备注 |
|:---|:---|:---|
| IOC 时效 | now − first_seen（建议看中位数并分类型） | 【上游】按 lifetime 求均值 |
| 分发覆盖率 | 已下发检测面 IOC / 入库 IOC | 【补充】没下发等于没收 |
| 命中率 | 产生匹配的 IOC / 下发 IOC | 【上游】`intel_match_rate` |
| 误报率 | 匹配判假数 / 全部匹配 | 【上游】目标 <5% |
| 富化率 | 带家族/行为体/多源上下文的 IOC 占比 | 【补充】 |
| 响应时效 | alert → block 分钟数 | 【上游】`alert_to_block_time` |
| 退役卫生 | 到期已回收的 IOC 占比；检索被复用次数 | 【补充】 |
