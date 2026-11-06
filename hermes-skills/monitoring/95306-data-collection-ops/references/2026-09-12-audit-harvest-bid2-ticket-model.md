# 2026-09-12 审计流收割层 + bid2(bid.95306.cn)模型 + 票源资格铁律

## 1. auditlog = 近实时富矿(公开无鉴权)
- 查询: findList funcId=auditlog, appId=system, condition {"operation_details":{"like":"%"}}; 行字段 operation_account/operation_time/operation_details
- 近实时(分钟级); 详情含完整跳转链与凭证, 正则:
  - bid2 JWT: token=<REDACTED>,}) —— 12h TTL, payload 有 org.name/信用码/ln
  - 32hex票: "token":"([0-9a-f]{32})" 与 serviceTicket=([0-9a-f]{32})