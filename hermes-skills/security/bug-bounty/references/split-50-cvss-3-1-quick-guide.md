## CVSS 3.1 Quick Guide

| Factor | Low (0-3.9) | Medium (4-6.9) | High (7-8.9) | Critical (9-10) |
|--------|-------------|----------------|--------------|-----------------|
| Attack Vector | Physical | Local | Adjacent | Network |
| Privileges | High | Low | None | None |
| User Interaction | Required | Required | None | None |
| Impact | Partial | Partial | High | High (all 3) |

### Typical Scores by Bug Class

| Bug | Typical CVSS | Severity |
|----|------|---------|
| IDOR (read PII) | 6.5 | Medium |
| IDOR (write/delete) | 7.5 | High |
| Auth bypass -> admin | 9.8 | Critical |
| Stored XSS | 5.4-8.8 | Med-High |
| SQLi (data exfil) | 8.6 | High |
| SSRF (cloud metadata) | 9.1 | Critical |
| Race condition (double spend) | 7.5 | High |
| GraphQL auth bypass | 8.7 | High |
| JWT none algorithm | 9.1 | Critical |

---

# ALWAYS REJECTED -- Never Submit These

Missing CSP/HSTS/security headers, missing SPF/DKIM/DMARC, GraphQL introspection alone, banner/version disclosure without working CVE exploit, clickjacking on non-sensitive pages, tabnabbing, CSV injection, CORS wildcard without credential exfil PoC, logout CSRF, self-XSS, open redirect alone, OAuth client_secret in mobile app, SSRF DNS-ping only, host header injection alone, no rate limit on non-critical forms, session not invalidated on logout, concurrent sessions, internal IP disclosure, mixed content, SSL weak ciphers, missing HttpOnly/Secure cookie flags alone, broken external links, pre-account takeover (usually), autocomplete on password fields.

**N/A hurts your validity ratio. Informative is neutral. Only submit what passes the 7-Question Gate.**

