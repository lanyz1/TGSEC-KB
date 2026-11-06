---
name: unauth-rce-2026-11-pack
description: "Use when 撞到 2026-11 未授权 RCE 集中包。"
---

# 2026-11 未授权 RCE 速查包（6 条，均为预认证、无需账号）

只收**读过完整 PoC 文档**的。每条给「机制 → 判据 → 入口」，不给没验证的 payload。

---

## 1. CVE-2026-82222 — GiveWP (WordPress) PHP Object Injection

**CVSS 9.8**，向量带 **`S:C`**（scope changed，逃出插件自己的信任域）。

- 机制：插件里存在未受控的 `unserialize()` 入口，反序列化链落到 RCE。
- 入口：GiveWP 的公开捐赠 / 表单端点，**无凭据**。
- 现成工具：`GhostlyrootB2H/CVE-2026-82222` —— mass scan + auto-detect + 多线程 + 交互式 shell。
- 判据：页面/接口有 GiveWP 指纹（`give-` 前缀资源、`/wp-json/give-api/` 路径）。

---

## 2. CVE-2026-31816 — Budibase 认证绕过 → RCE

**未锚定正则 + 把带 query 的 URL 拿去匹配。** 这是本轮最可迁移的一条。

```
服务端用未锚定正则识别合法 webhook 端点，但它匹配的对象是 Koa 的 ctx.request.url —— 包含 query string。
于是：/api/integrations?/webhooks/trigger
这个请求根本没打 webhook 端点，但校验从 query 里看到了 /webhooks/trigger，判定为合法 webhook 请求。
```

- 判据：Budibase 实例 + 任一需要鉴权的 `/api/*`；把 `?/webhooks/trigger` 拼在 query 里，鉴权是否消失。
- **通用原语**：任何「用正则识别端点」的鉴权中间件，都要看三件事：正则是否锚定（`^...$`）、匹配对象是全 URL 还是 path、是否包含 query。三条错一条就能绕。

---

## 3. CVE-2026-29014 — MetInfo CMS ≤ 8.1 未授权 RCE

- 机制：未授权写原语 → 落到 **`cache/weixin/Array.php`** → 访问即执行。6 个 payload 变体。
- 可迁移点：**缓存目录当 webshell 落点**。`cache/`、`runtime/`、`tmp/`、`storage/framework/` 这类目录往往不在上传限制内、但可被 PHP 执行。
- 判据：`/cache/weixin/Array.php` 可访问；MetInfo 版本 ≤ 8.1。

---

## 4. CVE-2026-6516 — ManageEngine ADAudit Plus 预认证 RCE

**CVSS 10.0**，`AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:L`。

- 关键：**洞在 Agent API，不在 console**。盯着管理控制台找会白费——要去探 Agent 侧的接口面。
- 可迁移点：企业软件的「管理面」和「Agent 面」是两套鉴权。管理面硬化了，Agent 面往往没跟上。同类产品（ADManager、Endpoint Central、OpManager）都有这个结构。
- 扫描器：`t3chn0t3s-org/cve-2026-6516-scanner`（单文件无依赖，v2.3.4，可从 nmap 输出直接喂）——HTTP 指纹 + Agent API 探测 + 未鉴权 UI 判定 + 版本比对。

---

## 5. CVE-2026-24423 — SmarterTools SmarterMail `ConnectToHub` 未授权 RCE

- 机制：`ConnectToHub` 功能让服务器**主动连出去**——把攻击者当 Hub。属于「服务器反连」类，不是传统注入。
- 利用形态：`MalHub.py` 起假 Hub（配 LHOST/LPORT/HUB_PORT）→ 目标连过来 → 回 shell。
- 可迁移点：**回调型 RCE**——不用打进目标，目标自己连你。防火墙只挡入站时这类洞特别值钱。

---

## 6. CVE-2026-76268 — Splunk Enterprise SHC Patroni REST 未授权 RCE

**CWE-306**（关键功能缺鉴权），CVSS 9.8，公告 **SVD-2026-1001**。

- 组件：**search head cluster 成员的 PostgreSQL sidecar → Patroni REST API**。
- 影响：**10.2.0 – 10.2.6**、**10.4.0 – 10.4.2**；修 **10.2.7 / 10.4.3**；**10.0.x 与 9.4.x 不受影响**（别把能扫到的旧版当洞）。
- 只影响 **SHC 成员**，单独 indexer / standalone 不算。
- 可迁移点：主产品加固了，**sidecar 组件（Patroni/etcd/consul/exporter）没鉴权**。看到 Splunk/ES/K8s 集群，先扫 sidecar 端口。

---

## 同批还在队列里（已入库，未读全文，不写机制）

WordPress 系：SiteSkite ≤2.1.8（96349）、LatePoint ≤5.7.0 存储型 XSS（92966）、Super Forms ≤6.3.3 未授权提权（15989）、DevKit Pro ≤2.3.0 管理员接管（14378）
Joomla / PrestaShop：OS CCK 8.3.15 未授权 SQLi（102428）、MyPresta gmfeed ≤2.3.9（85520）
其他：Pluck CMS 全站 CSRF（70376，fail-open Referer）、Rejetto HFS PRNG session 伪造（61500）、D-Link DIR-825M 栈溢出（82592）、Hitachi RTU500 固件绕过（8065）、Spinnaker GitRepo（32604）、Atlassian DC 预认证文件读（21589）、SAP NetWeaver（31324）、OFBiz XML-RPC（49070）

**这些只有标题与摘要，没读到 PoC 全文——别当已核实。** 要打先回 `exploitgrid-poc-index` 查源 URL 读 README。
