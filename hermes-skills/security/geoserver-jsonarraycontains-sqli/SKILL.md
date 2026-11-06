---
name: geoserver-jsonarraycontains-sqli
description: >-
 授权目标上 GeoServer jsonArrayContains 预认证 SQLi（2026-08 在野、尚无 CVE/补丁）：
 WFS/WMS OGC Filter → PostGIS/Oracle 注入；库超管时可衔 RCE。
 用户提到 GeoServer、jsonArrayContains、GeoTools、WFS GetFeature、
 地理服务器预认证注入时使用。广谱 1day 走 1day-nuclei-kit；
 CVE 入库走 cve-daily-intel。默认只做 SQLi 证明，不做 COPY TO PROGRAM。
---

# GeoServer jsonArrayContains 预认证 SQLi（Cursor Skill）

## 何时用

- 指纹/标题出现 GeoServer、`/geoserver/web`、WFS/WMS GetCapabilities
- 用户点名 jsonArrayContains、2026-08 GeoServer 零日、Hadrian 分析
- `nday_route` hit `geoserver`
- FOFA/空间测绘命中 GeoServer 且目标已在 scope

## 真源（按序）

1. `docs/playbooks/GeoServer-jsonArrayContains预认证SQLi手法.md`
2. `tools/1day-kit/custom-templates/geoserver-jsonarraycontains-sqli.yaml`
3. `docs/playbooks/CVE日报-2026-08-14.md` §1
4. https://hadrian.io/blog/here-be-dragons-geoserver-pre-auth-sql-injection-to-rce

## 强制步骤

1. 目标在 `config/scope*.json`。
2. 指纹：
 ```bash
 python3 tools/ops/nday_family_probe.py --family geoserver --base https://授权站 --case <案卷>
  ```
3. **L2（授权内）**：按 Playbook §2 
 - 取 WFS 图层，经 `jsonArrayContains` 做布尔/报错/短延时差分 
 - 默认 **不** 打 `COPY … TO PROGRAM` / OS 命令 
4. 证据：`exports/bot-recovery/<案卷>/测绘/1day/geoserver_*` 
5. 更新 `STATUS.md`（版本、图层、是否广告该函数、L2 结论）。

## 成功口径

| 级别 | 口径 |
|------|------|
| L1 | 确认 GeoServer；GetCapabilities 或欢迎页 |
| L2 | 可复现注入差分（长度/报错/延时） |
| 修复线 | 等 OSGeo 补丁；此前关公网 WFS 或禁用该函数 |

影响：约 `>= 2.25.3` + 受影响 GeoTools；需 PostGIS/Oracle 图层。尚无 CVE（2026-08-14）。

## 不要做

- 未授权公网扫 GeoServer
- 只报「有 GeoServer」不验证 Filter 面
- 默认 RCE / 写矿工 / 持久化
- 把本洞和 CVE-2023-25157 旧族混成功口径

## 衔接

- 打到库凭据/内网 → 按栈切 Actuator/假支付/提权
- 得 shell → `linux-post-exploit` / `internal-tunnel`
- 情报入库 → `cve-daily-intel`
- 广谱 → `1day-nuclei-kit`
