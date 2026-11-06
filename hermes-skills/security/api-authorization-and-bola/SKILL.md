---
name: api-authorization-and-bola
description: >-
  API authorization and BOLA testing playbook. Use when APIs expose object identifiers, nested resources, hidden writable fields, or weak function-level authorization.
tags: [type=1, 内部视图]
---

# SKILL: API Authorization and BOLA — Object Access, Function Access, and Mass Assignment

> **AI LOAD INSTRUCTION**: Use this skill when an API exposes object IDs, nested resources, or role-sensitive functions and you need a focused authorization test path: BOLA, BFLA, method abuse, and hidden field control.

## 1. CORE TEST LOOP

1. Create Account A and Account B.
2. As Account A, capture create, read, update, and delete flows.
3. Replay with Account B's token.
4. Test sibling endpoints, nested endpoints, and alternate HTTP verbs.

## 2. TEST SURFACES

| Surface | Example |
|---|---|
| object read | `/api/v1/orders/123` |
| nested object | `/api/v1/users/1/invoices/9` |
| admin or internal function | `/api/v1/admin/users` |
| update path | `PUT`, `PATCH`, `DELETE` variants |
| hidden JSON fields | `role`, `org`, `verified`, `tier` |

## 3. QUICK PAYLOADS

```json
{"role":"admin"}
{"isAdmin":true}
{"org":"target-company"}
{"verified":true}
```

## 4. WHAT TESTERS MISS

- object IDs in headers, cookies, GraphQL args, and nested objects
- alternate methods sharing the same route but weaker authz
- parent check present, child resource check missing
- admin docs revealing extra writable fields

## 5. NEXT ROUTING

- For JWT or token-layer abuse: [api auth and jwt abuse](../api-auth-and-jwt-abuse/SKILL.md)
- For GraphQL and hidden parameter discovery: [graphql and hidden parameters](../graphql-and-hidden-parameters/SKILL.md)
- For broader IDOR patterns outside APIs: [idor broken object authorization](../idor-broken-object-authorization/SKILL.md)

## type=1 内部视图开关（2026-10 TikTokMall / 跳蚤市场）
- 列表接口的 `type`/`scope`/`view` 参数：`type=1` 常是“内部/管理视角”，返回全量而非当前用户
- 探法：同一接口依次传 `0/1/2/all/admin/internal`，对比返回条数与字段数；条数突变即命中
- 配套差分：先不带参数记基线，再逐字段增删，观察哪些字段被服务端当白名单重置（写回后未传字段变 null = mass-assignment）
- 判据：`total` 从个位数变千位数 = 越权视图开关
## 只校验会话、不校验角色（2026-09 博彩平台实战）
- 玩家会话（`roletype=player`）带 `uuid+sid` 直接调管理侧接口 → 200，服务端只判会话有效性
- 同类：`level`、`apitoken`、`userInfo` 字段信任前端；`updateuserinfo` 用 key 白名单挡掉提权但其余字段可改
- 判法：用最低权账号的会话，把管理 API 全集过一遍，按 200/403 分组；200 的全部复测是否写入
- 放大：`roletype` 由服务端下发却在 JWT/会话里明文 → 试着改 `player→admin` 看是否重校验
