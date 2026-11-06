## IDOR -- Insecure Direct Object Reference

> #1 most paid web2 class -- 30% of all submissions that get paid.

### IDOR Variants (10 Ways to Test)

| Variant | What to Test |
|---------|-------------|
| V1: Direct | Change object ID in URL path `/api/users/123` -> `/api/users/456` |
| V2: Body param | Change ID in POST/PUT JSON body `{"user_id": 456}` |
| V3: GraphQL node | `{ node(id: "base64(OtherType:123)") { ... } }` |
| V4: Batch/bulk | `/api/users?ids=1,2,3,4,5` -- request multiple IDs at once |
| V5: Nested | Change parent ID: `/orgs/{org_id}/users/{user_id}` |
| V6: File path | `/files/download?path=../other-user/file.pdf` |
| V7: Predictable | Sequential integers, timestamps, short UUIDs |
| V8: Method swap | GET returns 403? Try PUT/PATCH/DELETE on same endpoint |
| V9: Version rollback | v2 blocked? Try `/api/v1/` same endpoint |
| V10: Header injection | `X-User-ID: victim_id`, `X-Org-ID: victim_org` |

### IDOR Testing Checklist
- [ ] Create two accounts (A = attacker, B = victim)
- [ ] Log in as A, perform all actions, note all IDs in requests
- [ ] Log in as B, replay A's requests with A's IDs using B's auth
- [ ] Try EVERY endpoint with swapped IDs -- not just GET, also PUT/DELETE/PATCH
- [ ] Check API v1/v2 differences
- [ ] Check GraphQL schema for node() queries
- [ ] Check WebSocket messages for client-supplied IDs
- [ ] Test batch endpoints (can you request multiple IDs?)
- [ ] Try adding unexpected params: `?user_id=other_user`

### IDOR Chains (higher payout)
- IDOR + Read PII = Medium
- IDOR + Write (modify other's data) = High
- IDOR + Admin endpoint = Critical (privilege escalation)
- IDOR + Account takeover path = Critical
- IDOR + Chatbot (LLM reads other user's data) = High

