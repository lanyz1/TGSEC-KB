## CONDITIONALLY VALID — REQUIRES CHAIN

These are valid ONLY when combined with a chain that proves real impact:

| Standalone Finding | Chain Required | Result if Chained |
|---|---|---|
| Open redirect | + OAuth code theft via redirect_uri abuse | ATO (Critical) |
| Clickjacking | + sensitive action + working PoC (not just login) | Medium |
| CORS wildcard | + credentialed request exfils user data | High |
| CSRF | + sensitive action (transfer funds, change email) | High |
| Rate limit bypass | + OTP/token brute force succeeding | Medium/High |
| SSRF DNS-only | + internal service access + data retrieval | Medium |
| Host header injection | + password reset email uses it | High |
| Prompt injection | + reads other user's data (IDOR) OR exfil OR RCE | High |
| S3 bucket listing | + JS bundles with API keys/OAuth secrets | Medium/High |
| Self-XSS | + CSRF to trigger it on victim | Medium |
| Subdomain takeover | + OAuth redirect_uri registered at that subdomain | Critical |
| GraphQL introspection | + auth bypass mutation or IDOR on node() | High |

**Rule:** Build the chain first, confirm it works end-to-end, THEN report. Never report A and say "could chain with B" — prove it.

---

