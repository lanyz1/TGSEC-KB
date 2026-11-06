---
name: sap-overpass-s4get-rce
description: SAP ICM/Web Dispatcher/disp+work EPP栈溢出Pre-Auth RCE (CVE-2026-44756 CVSS 10.0) + NetWeaver Message Server未授权接管 (CVE-2026-58240 CVSS 9.8)；SAP Kernel Notes 3747649+3759472
---
# Skill: sap-overpass-s4get-rce

## 元数据

```yaml
id: sap-overpass-s4get-rce
name: SAP OVERPASS + S4GET Pre-Auth RCE
cve: [CVE-2026-44756, CVE-2026-58240]
cvss: 10.0 / 9.8
disclosed: 2026-09-08
kev: false
in_wild: confirmed (CERT-EU 2026-011)
affected:
  - SAP ICM (Internet Communication Manager)
  - SAP Web Dispatcher
  - SAP disp+work (ABAP application server)
  - SAP NetWeaver Message Server
trigger: >
  CVE-2026-44756: SAP / ICM / Web Dispatcher / disp+work / EPP /
  extended passport / OVERPASS / SAP stack / NGRFC / Onapsis /
  SAP Security Note 3747649
  CVE-2026-58240: SAP NetWeaver Message Server / S4GET / BC-CST-MS /
  SAP Security Note 3759472
playbook: docs/playbooks/SAP-OVERPASS-S4GET-PreAuth-RCE手法.md
```

---

## 作战摘要

**CVE-2026-44756 OVERPASS**：SAP Kernel 中 EPP（Extended Passport）处理代码存在**栈溢出**，认证前触发，影响 ICM / Web Dispatcher / disp+work 三个组件。CVSS 10.0，Pre-Auth RCE（SAP 安装账号权限）。

**CVE-2026-58240 S4GET**：SAP NetWeaver Message Server 缺失认证检查，未授权攻击者可注册伪造 AS 组件并在 SAP 应用环境中执行未授权操作。CVSS 9.8。

两个漏洞独立，均为未授权。

---

## 快速流程

### 阶段 1：指纹识别

```bash
# SAP ICM / Web Dispatcher 存活
curl -sk https://TARGET/sap/bc/ping -v
curl -sk https://TARGET:8000/sap/bc/ping -v   # 内网端口
curl -sk https://TARGET/sapbwp/ -o /dev/null -w "%{http_code}"

# 典型 SAP 端口扫描
nmap -n -Pn --open -p 443,8000,8001,8443,8080,50000,50013,3200,3600,3900,8101 TARGET

# Message Server 端口
curl -sk http://TARGET:8101/msgserver/html/logon -v
curl -sk http://TARGET:3900/ -v
```

### 阶段 2：版本评估

```bash
# SAP Kernel 版本（不需认证的路径）
curl -sk https://TARGET/sap/public/bc/ur/nw07_40/include/userContextObj.js | head -3

# SAP Web Dispatcher 版本信息
curl -sk https://TARGET/sap/public/info -H "Accept: application/json"
```

### 阶段 3：暴露面确认

```bash
# CVE-2026-44756：ICM 对外暴露？
# 外部访问 ICM HTTPS 端口（通常 443/8443）即为暴露面
# 无需额外步骤，HTTP 请求即触达 EPP 处理路径

# CVE-2026-58240：Message Server 端口暴露？
nc -zv TARGET 8101 2>&1
nc -zv TARGET 3900 2>&1
```

### 阶段 4：利用路径

> **注意**：无公开完整 PoC（Onapsis 负责任披露）。  
> 本节为技术路径分析，用于评估暴露面和制作授权测试 payload。

**CVE-2026-44756 三条入口路径**：

```
路径 A（优先）：
  HTTPS 端口 → ICM/Web Dispatcher
  → crafted HTTP request with malformed EPP header
  → 边界验证缺失 → 栈溢出

路径 B（无 canary）：
  WebSocket upgrade on TLS port → NGRFC endpoint
  → NGRFC login envelope → inner TLV with crafted EPP
  → 触达 disp+work dialog work process（认证前）
  → 无 canary 确认 → 可控溢出

路径 C：SAP GUI (DIAG) / 经典 RFC
  → 同样 EPP 处理路径
```

**CVE-2026-58240 路径**：

```
网络访问 Message Server 端口（3900/8101）
  → 伪造 AS 组件注册报文
  → Message Server 接受注册
  → 在 SAP 环境内执行未授权操作
```

### 阶段 5：利用后（取得 SAP 安装账号权限）

```bash
# SAP 安装账号通常是 <sid>adm（如 oradm, d01adm, s4hadm）
id

# 读取 SAP 数据库连接配置
cat /usr/sap/*/SYS/global/security/rsecssfs/data/SSFS_*.DAT  # SecureStore
cat /sapmnt/*/profile/DEFAULT.PFL | grep -iE "dbs|db/|dbs/ora"

# 读取环境变量中的数据库凭据
env | grep -iE "dbs|dbpass|sap_|hana"

# HANA DB 连接（SAP HANA 场景）
cat /usr/sap/*/hdbclient/jdbc/ngdbc.jar  # HANA JDBC 驱动确认
# hdbuserstore LIST  # HANA 用户存储

# 横向：SAP 内部 RFC 信任体系
# 取得 SAP 安装账号后可直接访问 ABAP 系统内部接口
```

---

## 关键侦察命令

```bash
# FOFA 指纹
"sap/bc/ping" || "sap/public/info" || title="SAP Web Application Server"

# Shodan
http.title:"SAP" port:443,8000,50000

# Censys
services.http.response.html_title:"SAP"
```

---

## 踩坑

| 坑 | 说明 |
|----|------|
| Kernel 补丁级别 | SPAM/SAINT 应用级升级不够；需要 Kernel 打 SAP Note 3747649 |
| NGRFC = 内网变外网 | NGRFC 共享 HTTPS 端口 → RFC 流量也可从外部触达 disp+work |
| Message Server 内部？ | SAP 架构中 Message Server 传统上在内部网络；但内网横向仍可利用 |
| 无 PoC 不等于安全 | 暴露面确认（指纹+版本+端口）已足够定损 |

---

## 真源

- Playbook: `docs/playbooks/SAP-OVERPASS-S4GET-PreAuth-RCE手法.md`
- CERT-EU 2026-011: https://cert.europa.eu/publications/security-advisories/2026-011/
- Full Disclosure: https://seclists.org/fulldisclosure/2026/Sep/65
- SAP Note 3747649 (CVE-2026-44756)
- SAP Note 3759472 (CVE-2026-58240)
