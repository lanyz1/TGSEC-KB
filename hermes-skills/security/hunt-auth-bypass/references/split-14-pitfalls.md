## Pitfalls

- **Confusing "no auth" with "auth bypass"** — an endpoint that requires no authentication is a design choice, not a bypass. A bypass requires an auth check that can be evaded.
- **IP whitelist bypass via headers only** — `X-Forwarded-For: 127.0.0.1` may change the response status but doesn't prove access. Verify the response body contains privileged data.
- **JWT alg:none without server acceptance** — many servers reject alg:none by default. Test on the actual production endpoint with a forged token.
- **401 on direct access but 200 via proxy path** — some apps have `/internal/` paths that bypass auth when accessed via specific routes. Map the full routing tree.
- **Header-based auth that conflicts with cookie auth** — if both `Authorization: Bearer` and session cookie are sent, one may override the other. Test each independently.
- **Step-up auth bypass** — bypassing 2FA/MFA after initial login is the most common auth-bypass pattern. Test direct navigation to post-login URLs.


---

