---
name: atlassian-dc-preauth-file-read
description: "Use when 打 Atlassian DC：`::` 路径穿越预认证读文件。"
---

# Atlassian Data Center 预认证任意文件读（CVE-2026-21589）

**CVSS 4.0 = 9.3**，`PR:N / UI:N / VC:H`。影响 **Bitbucket / Confluence / Jira (Software + JSM) / Bamboo / Crowd / Crucible / Fisheye** 全系列 Data Center 与 on-prem。**Atlassian Cloud 已修**，只打自托管。

源：`murrez/CVE-2026-21589`（PoCbit），验证标记 `POCBIT-21589-OK`，PoC 已在 Jira/Confluence/Bitbucket 三路上验过。

## 外部可迁移原语：解码顺序错

共享库 **`atlassian-plugins-webresource`** 在 `/download/resources/...` 下供静态资源。漏洞在**处理顺序**：

```
① Router 先路由（以此时看到的路径判定读哪个资源）
② 路由之后 Router.unescapeSlashes() 才把 :: 换成 /
③ 于是形如 ..:: 的段在②之后变成 ../
④ 斜杠剥离（getResourceRelativeToWebResource）在①之后就做过了 → 被绕过
⑤ 落到 ResourceFactory 的任意文件读
```

**这就是全部：安全检查与解码不在同一个阶段。** 任何「先判权限/路径，后做 URL 解码」的组件都可套这个模型。同族思路：双重编码、`;` 矩阵参数、`%2e%2e%2f` 在 WAF 后解码。

## 限制（别报错口径）

- **无目录列举**：必须已知精确文件路径才能读
- **只能读 web 应用根目录内**（Tomcat context 内），不是全盘任意读
- **只读**，不是 webshell 原语；能不能继续取决于配置

## 最高价值目标

```
WEB-INF/classes/crowd.properties      # Crowd SSO 凭据（application.password / application.name）
WEB-INF/classes/confluence-init.properties
WEB-INF/classes/jira-application.properties
WEB-INF/web.xml
```

拿到 Crowd 凭据后可打整个 SSO 域：Crowd 是 Atlassian 全家的认证中心，一份 `application.password` 能横向到同域其他产品。

## 判据与用法

```bash
python3 poc.py check   -u https://<host>              # WEB-INF 探针 + 产品 marker
python3 poc.py exploit -u https://<host> --read /WEB-INF/classes/crowd.properties
python3 poc.py -j hosts.txt --jsonl out.jsonl           # 批量
```

成功回显带 `POCBIT-21589-OK`；`hits.txt` / `exploited.txt` 分开记录“能读”与“真读到敏感文件”。

## 修复版本（判活直接对表）

| 产品 | 修于 ≥ |
|---|---|
| Jira Software / JSM DC | **9.12.40 / 10.3.26 / 11.3.12** |
| Confluence DC | **9.2.26 / 10.2.19** |
| Bitbucket DC | **9.4.26 / 10.2.8 / 10.5.1** |
| Bamboo DC | **10.2.24 / 12.1.12** |
| Crowd DC | **6.3.7 / 7.0.3 / 7.1.7 / 7.2.4** |
| Crucible / Fisheye | **4.9.15** |

版本取 `/rest/api/2/serverInfo`（Jira）、`/rest/api/space`（Confluence）、`/rest/api/1.0/application-properties`（Bitbucket），不要只看登录页。

## 坑

- 无目录列举 —— 猜不到路径就打不出东西，先拿 `/WEB-INF/web.xml` 做存在性验证（这个路径恒定）。
- Cloud 打不了（厂商已修），看到 `*.atlassian.net` 直接跳过。
- 读不到 `crowd.properties` 不代表没洞：很多部署不用 Crowd，改读 `dbconfig.xml`（数据库口令）。
- 只读 → 报告里不要写成 RCE。要升级到 RCE 必须另找写入面或凭据复用。
