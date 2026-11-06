# EC Markets H5 API System

## Base URL
`https://api.ecmarkets.com.au/api/h5/`

Separate from IB API (`/api/ib/`). Used by registration page and mobile flows.

## Authentication
- IB token (`eyJ...`) does NOT work for H5 API
- H5 API returns `{"code":"2000","message":"Not logged in."}` or `"Login invalid, please log in again."` without valid H5 auth
- Registration page uses Firebase + cookie-based session (different from IB Bearer token)

## Public Endpoints (no auth required)

| Endpoint | Method | Body | Response |
|----------|--------|------|----------|
| `/user/validateInviteCode` | POST | `{"inviteCode":"U17FZ"}` | `{"body":true}` — only validates existence, no owner info |
| `/country/all` | GET | — | Country list with dial codes |
| `/page/baseInfo` | GET | — | Page footer/header content |
| `/gadCampaignid/whitelist` | GET | — | GAD campaign whitelist |
| `/commonConfig` | GET | — | Withdrawal rate, livechat key, MT type, server offset |

## Auth-Required Endpoints (return "Not logged in" without valid token)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/user/inviteCode/info` | POST | Query invite code details (would return owner if authenticated) |
| `/user/inviteCode/detail` | POST | Invite code detail |
| `/user/inviteInfo` | POST | Invite info |
| `/user/getInviterInfo` | POST | Get inviter/parent info |
| `/user/getParentInfo` | POST | Get parent user info |
| `/user/getSuperiorInfo` | POST | Get superior/manager info |
| `/user/registerFillPhone/{countryId}` | POST | Registration phone form config |
| `/user/sendEmailCode` | POST | Send email verification code |

## Invitation Code Flow

```
User clicks invite link:
https://i.ecmarkets.com.au/api/client/pm/2/{CODE}
  → 302 redirect to:
https://crm.ecmarkets.com.au/sign/register?8c={CODE}&8d=2
  → 308 → 307 → final URL:
https://crm.ecmarkets.com.au/en-US/sign/register/?8c={CODE}&8d=2
```

- `i.ecmarkets.com.au` is CloudFront-distributed Next.js app
- `8c` = invite code parameter, `8d` = landing page ID (2 = default)
- Code stored in cookie after first visit: `document.cookie = "inviteCode={CODE}; max-age=259200"`
- `validateInviteCode` only returns `true`/`false` — owner data is NOT exposed client-side

## Registration Page Tech Stack
- Framework: Next.js (React SSR)
- Domain: `crm.ecmarkets.com.au` (NOT the ASP.NET CRM at `crm.ecmarkets.co.uk`)
- Build output: `/_next/static/chunks/pages/sign/register-{hash}.js`
- States: `inviteCode` from URL `8c` param, stored in cookie for 3 days
- Registration sends inviteCode along with email/password to backend

## Key Limitation
Invite code owner information is NOT returned to the frontend at any point during registration. The owner lookup is purely server-side. To find who owns `U17FZ`, you need:
1. Admin backend access (`admin.ecmarkets.co.uk` — currently 503)
2. Database access (PostgreSQL on AWS RDS, security group blocks external)
3. Direct API query with valid H5 auth token
