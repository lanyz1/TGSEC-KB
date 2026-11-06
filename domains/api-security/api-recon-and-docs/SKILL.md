---
name: api-recon-and-docs
description: >-
  API reconnaissance and documentation review playbook. Use when discovering endpoints, schemas, versions, OpenAPI specs, hidden docs, and surface area for API testing.
---

# SKILL: API Recon and Docs — Endpoints, Schemas, and Version Surface

> **AI LOAD INSTRUCTION**: Use this skill first when the target is a REST, mobile, or GraphQL API and you need to enumerate endpoints, documentation, versions, and hidden surface area before exploitation.

## 1. PRIMARY GOALS

1. Discover all reachable API entrypoints.
2. Extract schemas, optional fields, and role differences.
3. Identify old versions, mobile paths, GraphQL endpoints, and undocumented parameters.

## 2. RECON CHECKLIST

### JavaScript and client mining

```bash
curl https://target/app.js | grep -oE '(/api|/rest|/graphql)[^"'\'' ]+' | sort -u
```

### Common documentation and schema paths

```text
/swagger.json
/openapi.json
/api-docs
/docs
/.well-known/
/graphql
/gql
```

### Version and product drift

```text
/api/v1/
/api/v2/
/api/mobile/v1/
/legacy/
```

## 3. WHAT TO EXTRACT FROM DOCS

- optional and undocumented fields
- admin-only request examples
- deprecated endpoints that may still be active
- schema hints like `additionalProperties: true`
- parameter names tied to filtering, sorting, IDs, roles, or tenancy

## 4. NEXT ROUTING

| Finding | Next Skill |
|---|---|
| object IDs everywhere | [api authorization and bola](../api-authorization-and-bola/SKILL.md) |
| JWT, OAuth, role claims | [api auth and jwt abuse](../api-auth-and-jwt-abuse/SKILL.md) |
| GraphQL or hidden fields | [graphql and hidden parameters](../graphql-and-hidden-parameters/SKILL.md) |
| strong auth boundary but suspicious business flow | [business logic vulnerabilities](../../business-logic/business-logic-vulnerabilities/SKILL.md) |

## 5. RUNTIME HARVEST（无凭据把 SPA 壳撑开）

清单式侦察到这一步会撞墙：SPA 主 bundle >500KB、登录后才发业务 XHR、401 直接跳 `/login`。这条路用**运行时**补齐：

| 层 | 产出 | 上限 |
|---|---|---|
| 静态（JS bundle） | 全量 endpoint 路径、路由草案、组包点字段候选 | 无 HTTP 方法；参数须二次逆向；漏掉运行时拼接 URL |
| 运行时（活会话） | 方法 + body + 响应 + 动态 URL + WS/SSE | 页面须实际渲染才会发请求；单样本定不了必填/可选 |

**壳撑开三步**：`preload.js` hook 登录/权限/菜单 bootstrap 接口 → 回**结构正确、业务码成功、数据为空**的 mock body → 前端在无后端或 401 下仍渲染登录后页面，从而把后续 outbound 全部录下来。空表格、占位 UI 是预期结果。

完整打法（Phase 0-5、双门禁、参数触发矩阵、权限树还原、脚本改动约束）见 [api-recon-runtime-harvest](../api-recon-runtime-harvest/SKILL.md)，浏览器驱动命令见 [browser-automation-playwright-cli](../../recon/browser-automation-playwright-cli/SKILL.md)，采到的流量要变成证据见 [finding-traffic-evidence-chain](../../recon/finding-traffic-evidence-chain/SKILL.md)。