# EC Markets IB Portal — API Reconnaissance & User Hierarchy Enumeration

> Session 2026-07-25 — Forex broker IB (Introducing Broker) partner portal

## Target

- **App URL**: `https://ib.ecmarkets.com.au/` (Umi.js SPA)
- **API Base URL**: `https://api.ecmarkets.com.au/api/ib/`
- **Auth**: JWT in `token` cookie, sent as custom `token:` header + `platform: IB`, `X-API-VERSION: 2.44.0`
- **CDN**: AWS CloudFront (ib.ecmarkets.sc → ib.ecmarkets.com → 302 → ib.ecmarkets.com.au)

## Domain Chain Discovery

The `.sc` and `.com` domains both 302 redirect to the main marketing site. Real portal is on `.com.au`:
```
ib.ecmarkets.sc     → 302 → ib.ecmarkets.com
ib.ecmarkets.com   → 302 → www.ecmarkets.co.uk  (marketing site)
ib.ecmarkets.com.au → 200  (Umi.js SPA — real IB portal!)
```

## Token Extraction

```javascript
// Token is in cookie, NOT localStorage
var token = <REDACTED>;]+)/)[1];
// → eyJhbGciOiJSUzI1NiJ9...  (JWT)

// Decode payload:
// {"id":1073981,"loginName":"<EMAIL-REDACTED>",
//  "name":"东刘","expire":1787577639078,
//  "platform":"IB","readOnly":false,
//  "scope":["IB","WEB_CLIENT"]}
```

## API Call Format

```bash
# Required headers
curl -X POST "https://api.ecmarkets.com.au/api/ib/heartbeat/recording/ping" \
  -H "token: <JWT>" \
  -H "platform: IB" \
  -H "X-API-VERSION: 2.44.0" \
  -H "browserfingerprint: <userId>" \
  -H "lang: zh-CN" \
  -H "Content-Type: application/json" \
  -H "origin: https://ib.ecmarkets.com.au" \
  -H "referer: https://ib.ecmarkets.com.au/"
```

**IMPORTANT**: The token header is `token:` (NOT `Authorization: Bearer`). The `browserfingerprint` header value is the user's numeric `userId` from the JWT.

## Key API Endpoints for User Hierarchy Enumeration

### Current User Info
```bash
GET /api/ib/user/current/info
# → userId, uid, loginName, parentAgentUserId (null = top-level)
```

### User Search
```bash
GET /api/ib/user/agentSearch/field?field=<uid>
# → body array [key, val] — search results (often empty)
```

### Subordinate/Relationship List (CRITICAL — user hierarchy)
```bash
GET /api/ib/user/relationship/page?userId=<sysId>&page=1&size=10
```

**Response format**:
```json
{
  "header": {"code": "0000", "message": "SUCCESS"},
  "body": {
    "pageNum": 1, "pageSize": 10, "total": 166, "totalPage": 17,
    "list": [
      {
        "userId": 1126115,
        "uid": "CN30270070",
        "firstname": "明*",
        "lastname": "王",
        "phoneSuffix": "18745******",
        "email": "861******@qq.com",
        "createTime": 1779545520000
      }
    ]
  }
}
```

### User Basic Info
```bash
GET /api/ib/user/getBasicInfo?userId=<uid>
# → countryId, firstname, lastname, sex, phonePrefix, phoneSuffix, dob
```

### Other Hierarchy APIs (POST, params vary)
```bash
POST /api/ib/user/relationship/detail/info/<sysId>      # Detail info (needs params)
POST /api/ib/user/relationship/detail/page/<sysId>       # Detail page (needs params)
POST /api/ib/user/relationship/detail/selector/<sysId>   # Selector (needs params)
POST /api/ib/user/relationship/detail/total/<sysId>      # Total count (needs params)
```

### Dashboard / Summary APIs
```bash
GET /api/ib/dashboard/basic/info
# → {receivingCusTotalCount, cusTotalCount, cusNotKycCount, cusKycAndDepositCount,
#     soldOpportunityCount, rebateBalance, equity, balance, profit, freeMargin, margin}

GET /api/ib/dashboard/header
# → {equity, deposit, withdraw, lots, inviteCusNumber, rebate, tradingIncome}

POST /api/ib/dashboard/count  (needs startTime/endTime params)
# → Requires date range parameters — returns 1200 "开始时间不能为空" without them
#   Body: {"duration": {"startTime": <epoch_ms>, "endTime": <epoch_ms>}}
```

## Customer / User List APIs (POST with session parameters)

### Ordinary Customer List (POST)
```bash
POST /api/ib/user/manages/ordinary/type
# Body: {"pageNum": 1, "pageSize": 10, "duration": {"startTime": <epoch_ms>, "endTime": <epoch_ms>}}
# → Returns PAGINATED customer list with agent info:
#   {pageNum, pageSize, total, totalPage, list: [{
#     userId, uid, registerTime, phone, email,
#     firstname, lastname, ky
#     cStatus,
#     agentUserId, agentLoginName, agentFirstname, agentLastname,  # ← WHO THIS USER'S AGENT IS
#     isAgent, registerType, depositStatus,
#     totalAssets, equity, balance, profit, rebateReward
#   }]}
# 🔑 KEY FIELD: agentUserId reveals who is the parent agent for each customer
```

### Ordinary Customer Totals (POST)
```bash
POST /api/ib/user/manages/ordinary/total
# Body: same duration format
# → {totalAssets, currency, digital, equity, balance, profit,
#     rebateWallet, rebateReward, rebateDelivered, followEquity}
```

### Agent Performance / Sub-Agent List (POST)
```bash
POST /api/ib/rebate/getAgentPerformanceStatistics
# Body: {
#   "direct": 1,           # 1 = direct only
#   "type": 4,             # 4 = sub-agent type
#   "pageNum": 1,
#   "pageSize": 10,
#   "duration": {"startTime": <epoch_ms>, "endTime": <epoch_ms>}
# }
# → Returns SUB-AGENTS with performance metrics:
#   {pageNum, pageSize, total, totalPage, list: [{
#     userId, uid, parentUserId (usually null),
#     firstname, lastname, type, lots, profit, deposit, withdraw, equity, balance,
#     agentsAmount,       # How many sub-agents this agent has
#     directAmount,       # How many direct customers
#     rebate, loginName
#   }]}
# 🔑 Shows the current user's SUB-AGENT hierarchy with performance data
```

### Child Account Management
```bash
GET /api/ib/childAccount/listChildAccountInIB
# → Returns current user's own child account record:
#   {id, userId, registerAccount, firstname, lastname, roleId, roleName, status,
#    childLevel, direct, noDirect, childAccount}
# → user.agentAuthority includes "subAccount", "subAccount.list", "subAccount.list.add"
```

### Promotion / Invitation Link Management
```bash
GET /api/ib/popularize/link/page?pageNum=1&pageSize=10
# → Returns the current user's own invitation links with remarks:
# {landingPageId, link:"https://i.ecmarkets.com.au/api/client/pm/2/<CODE>",
#  invitationCode, remark, defaultStatus, enable, updateTime,
#  mt4List: [{mt4Id, serverInternalName, bigGroupName, clientAccount}]}
```

### Check User Has Children
```bash
POST /api/ib/user/checkUserHasChild/<sysId>
```

### Customer Management (needs valid params)
```bash
POST /api/ib/user/manages/pageAllCustomers        # All customers
POST /api/ib/user/manages/preCreateAgentList       # Agent list
POST /api/ib/user/manages/getUserDataStatisticsIb  # Statistics
POST /api/ib/user/manages/ibAgentButtonShow/       # Agent button visibility
```

### Commission/Rebate Rules (CONFIRMS parent-child commission links)
```bash
GET /api/ib/user/manages/agentRebateRule/<sysId>
# → Returns rebate rules with ruleId, mt4GroupName, list of rebate rates per asset class
# → If User A can query User B's rebate rules from User A's token,
#   there IS likely a commission/referral relationship even if parentAgentUserId is null
```

## API Response Codes

| Code | Message | Meaning |
|------|---------|---------|
| 0000 | SUCCESS | OK |
| 1000 | 无效参数 | Invalid parameters |
| 1000 | 权限不足 | Insufficient permissions (e.g. user can't view own rebate rules) |
| 1000 | 数据未找到 | Data not found (user not in parent's scope) |
| 1200 | (no message) | pageAllCustomers needs specific manageType param |
| 2000 | 登录状态失效，请重新登录 | Token expired |
| 9999 | 服务器繁忙，请稍后重试 | Server busy (retry later) |

Authentication failure: returns SPA HTML page (not JSON error).

## Umi.js Bundle API Extraction

```bash
# Extract all API routes
curl -sk "https://ib.ecmarkets.com.au/umi.dd814d91.js" \
  | grep -oP '"/api/ib/[^"]+' | sort -u
```

## User Enumeration Workflow

```python
import httpx

TOKEN = "<JWT-from-cookie>"
HEADERS = {
    "token": TOKEN,
    "platform": "IB",
    "X-API-VERSION": "2.44.0",
    "browserfingerprint": "<userId>",
    "lang": "zh-CN",
    "origin": "https://ib.ecmarkets.com.au",
    "referer": "https://ib.ecmarkets.com.au/",
}
BASE = "https://api.ecmarkets.com.au/api/ib"

s = httpx.Client(verify=False, headers=HEADERS)

# 1. Current user
r = s.get(f"{BASE}/user/current/info")
user = r.json()["body"]
print(f"UID={user['uid']}, Name={user['lastname']}{user['firstname']}, parent={user['parentAgentUserId']}")

# 2. Get subordinates (note: pagination is broken — all pages return same 10 users)
r = s.get(f"{BASE}/user/relationship/page?userId={user['userId']}&page=1&size=10")
body = r.json().get("body", {})
total = body.get("total", 0)
subs = body.get("list", [])
print(f"Total {total} subordinates (API returns {len(subs)}):")
for sub in subs:
    print(f"  {sub['uid']} {sub['lastname']}{sub['firstname']} phone={sub.get('phoneSuffix','?')}")

# 3. Get basic info
r = s.get(f"{BASE}/user/getBasicInfo?userId=<uid>")
info = r.json()["body"]
print(f"  DOB={info['dob']}, Sex={info['sex']}")

# 4. Verify commission relationship (when parentAgentUserId=null but user claims parent exists)
for target_id in [1089517, 1126115]:
    r = s.get(f"{BASE}/user/manages/agentRebateRule/{target_id}")
    resp = r.json()
    code = resp.get("header", {}).get("code")
    if code == "0000":
        print(f"  User {target_id}: REBATE RULE VISIBLE = commission link exists!")
    else:
        msg = resp.get("header", {}).get("message", "")
        print(f"  User {target_id}: {code} - {msg}")
```

## Backend System Discovery (Subdomain Brute Force)

Beyond the IB portal, additional EC Markets systems were discovered via subdomain brute force:

| System | URL | Tech Stack | Status |
|--------|-----|------------|--------|
| **IB Portal** | `ib.ecmarkets.com.au` | Umi.js (React) + nginx | ✅ Accessible |
| **IB API** | `api.ecmarkets.com.au` | nginx | ✅ With token |
| **CRM (Client)** | `crm.ecmarkets.co.uk` | ASP.NET + Vue.js 2 | ✅ 200 SPA |
| **Backend API** | `backend.ecmarkets.co.uk` | nginx | 🔒 401 all |
| **Admin Panel** | `admin.ecmarkets.co.uk` | IIS/ASP.NET | ❌ 503 |

### Subdomain Brute Force Method
Tested ~20 subdomains (`admin`,`backend`,`crm`,`manage`,`portal`,`system`,`internal`,`staff`,`partner` etc.) across 4 TLDs (`.com.au`,`.com`,`.co.uk`,`.sc`). Results: 3 hits from 80 combos.

### CRM (crm.ecmarkets.co.uk)
Client-facing portal for account opening/KYC/deposits. ASP.NET + Vue 2 SPA. API endpoints use `/api/{Controller}/{Action}` pattern (e.g. `/api/Public/Login`, `/api/MyAccount/Index`, `/api/MoneyPay/BankList`). All paths return 200 SPA — Vue catches all routes.

### Backend (backend.ecmarkets.co.uk)
**Spring Boot application** (nginx reverse proxy). All endpoints return **401** except:
- `GET /actuator/health` → **200** (public!) — leaks **2 PostgreSQL databases**: `ec1DataSource` and `traderEvolutionDataSource`
- `GET /actuator/info` → **200** (public!) — `{"environment":"prod","app":{"name":"EC1 Backend","version":"1.0.0"}}`

Blocked endpoints (401): `/actuator/env`, `/actuator/beans`, `/actuator/mappings`, `/actuator/heapdump`, `/actuator/loggers`, `/actuator/httptrace`, `/swagger-ui.html`, `/swagger.json`, `/v2/api-docs`, `/v3/api-docs`, `/graphql`, `/actuator/prometheus`, `/.env`, `/WEB-INF/web.xml`.

All return 401 uniformly — Spring Security blanket filter (not selective). This also means Swagger/API docs exist but are behind auth.

Spring Boot bypass techniques (path traversal, header spoofing, method override) **do NOT work** — properly configured.

### Admin Panel (admin.ecmarkets.co.uk)
**IIS/ASP.NET application** behind Cloudflare. Returns **503 Service Unavailable** for ALL paths. The 503 page is the standard IIS 503 HTML. App pool appears stopped or crashed. Monitor for recovery.

### CRM (crm.ecmarkets.co.uk) — Technical Details
Cloudflare + ASP.NET Core + Vue.js 2 SPA. The `/api/Public/Login` endpoint:
- Accepts: `GET`, `HEAD`, `OPTIONS`, `TRACE` (NOT POST)
- `Allow: GET, HEAD, OPTIONS, TRACE` from 405 response
- CORS: `Access-Control-Allow-Origin: *`, `Access-Control-Allow-Headers: *`
- All frontend routes (`/admin`, `/api/admin`, `/api/IB`, `/api/IBAdmin`) return 200 SPA HTML — Vue catch-all
- Real API pattern: `/api/{Controller}/{Action}` (ASP.NET REST)
- Login with browser-like headers needed (Cloudflare WAF blocks curl POST)
- Response includes Cloudflare headers + ASP.NET `X-Powered-By`

### Source IPs
Behind CloudFront AWS: `18.135.148.246` and `16.61.121.89` (London region, EC2 t3/type). Direct HTTP access returns AWS 401. Database ports (MySQL 3306, PostgreSQL 5432, Redis 6379, MongoDB 27017) nmap-show as OPEN but AWS security groups block direct connections. Only ports 80/443 respond to external traffic.

### Commission/API Fuzzing Summary
| API | Result |
|-----|--------|
| `agentRebateRule/{ownId}` GET | **权限不足** |
| `agentRebateRule/{targetId}` GET | ✅ SUCCESS if parent → child |
| `pageAllCustomers` POST | **无效参数** (needs manageType) |
| `getUserDataStatisticsIb` POST | **无效参数** |
| `ibRebateExport` POST/GET | 405 or 服务器繁忙 |
| `preCreateAgentList` GET | ✅ empty list |

## Commission vs IB Tree — Two Separate Relationship Systems

**CRITICAL DISTINCTION**: In forex broker IB systems, there are TWO separate relationship trackers:

| System | Field/API | Tracks | Visibility |
|--------|-----------|--------|------------|
| IB Agent Tree | `parentAgentUserId` | Formal IB sponsorship | Visible in `/user/current/info` |
| Commission/Rebate Link | Via invitation code → rebate rules | Commission from trading activity | Partially via `agentRebateRule/{userId}` |

**How parentAgentUserId=null can coexist with commission relationships**:
- The user is top-level in the formal IB agent tree
- BUT they still have a commission/referral relationship through invitation code (e.g., `4KZP2`)
- When a subordinate (CN29611306) registered using the parent's invitation code, the system linked them for commission purposes
- This link is stored separately from the IB tree

**How to detect commission links**:
Query `GET /api/ib/user/manages/agentRebateRule/{targetUserId}` from the claimed parent's token:
- Code `0000` with rebate data → Commission relationship EXISTS (parent can see child's rules)
- Code `1000` "数据未找到" → No relationship
- Code `1000` "权限不足" → Can't view own rule (try querying another user's ID)

**Confirmed case from this session**: CN29331658 (userId=1073981, parentAgentUserId=null) could see CN29611306 (userId=1089517)'s rebate rules, confirming the commission link despite null parent field.

## LIMITATIONS

### parentAgentUserId: null Does NOT Mean "No Manager"

When `parentAgentUserId: null`, the user is **top-level in the IB agent tree only**. The sales manager who created the account is tracked in a **separate CRM system** NOT exposed by the IB API:
- User fields hinting at this: `registerType: 2`, `source: null`, `customerType: null`
- The 经理 (manager) is NOT the IB parent agent
- To find the manager, you'd need access to the internal CRM

### Pagination Is Broken

The `/user/relationship/page` API returns at most **10 records total** regardless of:
- `size` parameter (50/100/166 all return 10)
- `page` parameter (pages 2+ return the same 10 users as page 1)
- The `total` field shows larger numbers (e.g., 166) but the API never returns more than 10

### Token Expiration

Tokens are short-lived. When API calls return `code: 2000` ("登录状态失效"), ask the user to refresh the page and re-extract:
```javascript
document.cookie.match(/token=([^;]+)/)[1]
```

## Complete User Fields (from /user/current/info)

```json
{
  "userId": 1073981,            // System numeric ID
  "uid": "CN29331658",          // User-facing UID
  "nickName": "Nickname",
  "invitationCode": "4KZP2",    // Invite code for referrals
  "loginName": "<EMAIL-REDACTED>",
  "isReadOnly": false,
  "registerStatus": 2,
  "registerType": 2,
  "kycStatus": 3,
  "hasPassword": 1,
  "inviteCodeStatus": 1,
  "phone": "<PHONE-REDACTED>",
  "email": "<EMAIL-REDACTED>",
  "lastname": "刘",
  "firstname": "东",
  "parentAgentUserId": null,    // IB tree parent
  "isAgent": 1,
  "agentType": 1,
  "agentAccountType": 1,
  "toAgent": null,
  "source": null,
  "timezone": "Asia/Shanghai",
  "domainPrefix": "ib",
  "domainValue": "ecmarkets.co",
  "platform": ["IB", "WEB_CLIENT"],
  "agentAuthority": [
    "commission.deposit", "commission.rebateReport",
    "ibRelationTree", "ibRelationTreeDetail",
    "user.subAgent", "user.subAgent.addAgent",
    "userInfo.agentInformation",
    ...
  ]
}
```
