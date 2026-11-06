# ag.61995q.com BetWin CMS Login Hunt

## Target Profile

| Field | Value |
|-------|-------|
| Domain | `ag.61995q.com` |
| CMS | BetWin (biying template) |
| Agent Login | `https://ag.61995q.com/app/daili/login.php` |
| Management Port | `:7777/cl/index.php?module=X&method=Y` |
| Mobile SPA | `https://ag.61995q.com:7777/m/` |
| WAF | ModSecurity (406) + Path-level DROP (000) |
| CDN | `kfc.jfwdpc.com/1/`, `nxy.ycybbx.com/1/` |
| Related Domains | 9581kk.com, 9580.com, 9581.com, 95zz.com |

## Account Registration Flow

### Registration Site: 9581kk.com

The user registered an agent account on `9581kk.com` — the registration form was labeled "代理注册". After registration, it instructed the user to log in at `ag.61995q.com`.

### Account Credentials Used

```
Username: fan54251
Password: <REDACTED>
```

### Login Attempts

| Endpoint | Method | Result |
|----------|--------|--------|
| `ag.61995q.com/app/daili/login.php` | POST username+password | ❌ "LOGIN ERROR" |
| `ag.61995q.com:7777/api/Public/main/index.php?service=User.Login` | POST with username+password+website | ❌ Missing `client_id` |
| `9581kk.com/app/daili/login.php` | POST username+password | ❌ 404 (no agent login on 9581kk.com) |

### Why Login Failed

The mobile SPA login API (`User.Login`) requires a `client_id` parameter (32+ characters). This `client_id` can only be obtained from `Server.GetCompany`, which requires a `website` parameter that maps to an internal tenant identifier in BetWin's database. All tested domain values (`ag.61995q.com`, `9581kk.com`, `9580.com`, etc.) returned `416: "请求的website不存在"`.

Possible explanations:
1. The BetWin multi-tenant database has a `website` record that is NOT the actual DNS domain
2. The registration on 9581kk.com created the account in a database shared with ag.61995q.com but the API gateway requires explicit tenant configuration per deployment
3. Account needs manual activation by an admin before first login

### Key Takeaways

- Even with a real registered account, the API layer's `website`/`client_id` gating can prevent login automation
- The agent login (`/app/daili/login.php`) and member login (`User.Login`) are separate systems with different auth requirements
- BetWin deployments may share a membership database but the API authentication is deployment-isolated
- `User.Login` endpoint exists and responds — correct API name is NOT `Uc.Login`
