---
name: multi-tenant-saas-storage-exposure
description: "Use when multi-tenant SaaS upload dirs are exposed."
version: 0.1.0
tags: [saas, multi-tenant, uploads, autoindex, pii, ocr, attribution]
---

# 多租户 SaaS 共享存储暴露（tenant 枚举 / 目录索引 / 用户提交物取证）

适用：目标用贴牌/托管 SaaS（客服、工单、CRM、发卡、商城），文件按 `tenant` 分目录存放；或主站打不动、需要横向到其 SaaS 供应商时。核心 = **文件按租户分目录 + hash 命名（不可枚举）+ 目录索引常没关**。

## 0. 先定位存储前缀

- 从挂件 JS / SPA bundle 抽 `/(uploads|upload|files|static|storage)/` 路径与拼装方式（常为 `"/uploads/" + tenantId + "/" + hash + ext`）。
- 图片消息的渲染代码最直接：`msg_type==="image" && content.indexOf("/uploads/")===0` 这类判断直接给出前缀。
- 列表/会话接口返回相对路径时，拼上主站 host 直取。

## 1. 目录索引探测（最高性价比）

`GET /uploads/<tid>/`：

- **200 + `<pre><a href=`** = nginx autoindex 开着 → 全清单到手。
- 403 = 存在但禁列（补 `?C=N;O=D` 或 `/.` 再试一次即可，别耗）。
- 404 = 该租户无文件或不存在 → 正好当**租户存在性 oracle**。
- 根 `/uploads/` 多为 404，必须带子目录；别因为根 404 就放弃。

## 2. 租户枚举

- tid 扫 0–100，再抽 200/500/1000；`200` 即命中。
- href 以 `/` 结尾的是子目录，**必须递归**（`avatars/` 常是坐席/访客真人头像，同样是 PII）。
- 文件 hash 不可猜，但目录已给全清单 → 按 href 全量下载，命名 `<tid>_<name>` 便于分组与溯源。
- 拉取用普通 `curl`（见 Pitfalls 的指纹问题），每个文件落盘前校验非空。

## 3. 租户隔离测试（先验证再放弃）

- `enter`/`login`/`init` 类接口的 `tenant_id`/`tid` 参数**常被服务端忽略**——租户只认 `app_key` / 子域 / `Host`。
- 拿不到别家 key 时，**目录索引是唯一能跨租户取证的面**：能看到文件内容，看不到聊天/业务文本。
- 其它可试：`X-Tenant-Id` 头、`?tenant=`、JWT payload 里的 `tid`、子域枚举、错误页回显的 tenant 名。
- 客户生产租户只读；写入只在自控测试租户里做。

## 4. 内容判读（用户提交物 = 完整身份档案）

- 客服/工单附件典型内容：充值提现记录、实名认证页、假冒卡片申领表单、账单/电子回单、身份证照。
- 先抽 20–30 张视觉核对确认类型（避免把纯 UI 截图当证据），再全量 OCR：`tesseract -l chi_sim+eng --psm 6`。
- 表单定位：按 `姓名/身份证/手机号/地址/银行卡` 关键词打分，**≥2 命中 = 疑似表单**，只精读这些。
- **数字判读纪律**：18 位必须过 GB 11643 校验才算身份证（校验位算法见 `references/case-2026-10-kefu-saas.md`）；`WO179…`/`SW…` 前缀是订单号/流水号；卡号多以 `1582 **** 9753` 掩码出现，别把掩码当全号。

## 5. 归因价值（比单条 PII 更值钱）

- 一套 SaaS 的多个租户 = **运营方中台**：同一 nginx、同一构建 hash、同一 `app_key` 命名 → 组织级基础设施证据。
- 从图片里的品牌话术（"389万资产配置名单"、"涉案资金清退申报"、"一类账户审计"）反查各品牌落地域名 → 新目标池。
- 报告口径：目录索引是**真实数据泄露**（不是"配置不当"级别），必须给文件数 / 唯一身份数 / 校验通过率 / 每条的来源文件名。

## Pitfalls

- **HTTP 状态码会说谎**：高防/WAF 常用 `200` 包一个 403 HTML 页（body ~138B `<title>403 Forbidden</title>`）。只看 status 会误判"通"；必须看 body 特征再下结论。
- 同一 WAF 集群下多个域名**同时** 403 → 是**出口 IP 被封**，不是单域策略；换域名无效，只能换出口（住宅代理/跳板），且代理池常被同批封光。
- `curl_cffi impersonate="chrome"` 可能被指纹拦（空响应/异常），而同 URL 普通 `curl` 返回 200 —— 脚本"全灭"时先用 plain curl 复核，别急着判定接口不存在。
- autoindex 只在该租户**有文件**时存在；404 不代表 SaaS 没有这个租户。
- 文件名是 hash，**别爆破文件名**，只走目录索引或接口返回的路径。
- 大目录逐个下载要限速+落盘校验；空体/读失败不得记 done。

## Related

- 客服栈专门打法（RoxChat / `_MICHAT` / visitor API / 坐席在线 oracle）→ `support-chat-platform-pentest`
- 批量 OCR 流水线与 digest → `bulk-ocr-extraction`
- 对象存储桶挖掘 → `bucket-content-artifact-mining`
- WAF 拦截层分诊 → `waf-block-layer-triage`

## Support files

- `references/case-2026-10-kefu-saas.md` — 央企AI+ 案实证：6 租户 / 76 文件 / 端点与提取结果 / 已测死面。
