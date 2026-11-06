<!-- archived from /root/.hermes/skills/security/api-auth-and-jwt-abuse/SKILL.md on 2026-10-21 -->

---
name: api-auth-and-jwt-abuse
description: >-
  API authentication and JWT abuse playbook. Use when testing bearer tokens, API keys, claim trust, header spoofing, rate limits, and API auth boundary weaknesses.
---

> 归档卡：原目录 `/root/.hermes/skills/security/api-auth-and-jwt-abuse`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/api-auth-and-jwt-abuse/…')`，不要相对 `references/legacy/` 解析。

# SKILL: API Auth and JWT Abuse — Token Trust, Header Tricks, and Rate Limits

> **AI LOAD INSTRUCTION**: Use this skill when APIs rely on JWT, bearer tokens, API keys, or weak request identity signals. Focus on token trust boundaries, claim misuse, header spoofing, and rate-limit bypass.

## 1. TOKEN TRIAGE

Inspect:

- `alg`, `kid`, `jku`, `x5u`
- role, org, tenant, scope, or privilege claims
- issuer and audience mismatches
- reuse of mobile and web tokens across products

## 2. QUICK ATTACK PICKS

| Pattern | First Test |
|---|---|
| `alg:none` acceptance | unsigned token with trailing dot |
| RS256 confusion | switch to HS256 using public key as secret |
| `kid` lookup trust | path traversal or injection in `kid` |
| remote key fetch trust | attacker-controlled `jku` or `x5u` |
| weak secret | offline crack with targeted wordlists |

## 3. HIDDEN FIELDS AND BATCH ABUSE

### Mass assignment field picks

```text
role
isAdmin
admin
verified
plan
tier
permissions
org
owner
```

### Rate limit and batch abuse picks

```text
X-Forwarded-For: 1.2.3.4
X-Real-IP: 5.6.7.8
Forwarded: for=9.9.9.9
```

GraphQL or JSON batch abuse candidates:

- arrays of login mutations
- bulk object fetches with varying IDs
- repeated password reset or verification calls in one request

## 4. RATE LIMIT BYPASS FAMILIES

```text
X-Forwarded-For
X-Real-IP
Forwarded
User-Agent rotation
Path case / slash variants
```

## 5. NEXT ROUTING

- For GraphQL batching and hidden parameters: [graphql and hidden parameters](../graphql-and-hidden-parameters/SKILL.md)
- For default credential and brute-force planning: [authentication bypass](../authbypass-authentication-flaws/SKILL.md)
- For full JWT and OAuth depth: [jwt oauth token attacks](../jwt-oauth-token-attacks/SKILL.md)
- For OAuth or OIDC configuration flaws in browser and SSO flows: [oauth oidc misconfiguration](../oauth-oidc-misconfiguration/SKILL.md)
- For credentialed browser reads and origin trust bugs: [cors cross origin misconfiguration](../cors-cross-origin-misconfiguration/SKILL.md)

## 2026-10 情报批增量（“仅凭一个头”验收缺陷）

- **No Username. No Password. Just a Header — A $3,000 Authentication Bypass**：仅凭 `Authorization: Basic` 头（空值/畸形值）让部分系统“已认证”判断成立 —— 只检查头存在性/格式，不校验凭据内容。
- 三态对照测试：无头 → 空值 `Authorization: Basic` → 畸形（`Basic Og==` / 随机 base64），对比 401→200 / 跳转消失 / 数据回包差异。
- 案例全文：medium.com/@0xalr/no-usernam…（@CyberWarship 转引，@ethical_h4ck3r_ 2026-09 批）。
