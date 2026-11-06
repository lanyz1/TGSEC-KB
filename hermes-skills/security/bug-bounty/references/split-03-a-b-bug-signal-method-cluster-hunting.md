## A->B BUG SIGNAL METHOD (Cluster Hunting)

**When you find bug A, systematically hunt for B and C nearby.** This is one of the most powerful methodologies in bug bounty. Single bugs pay. Chains pay 3-10x more.

### Known A->B->C Chains

| Bug A (Signal) | Hunt for Bug B | Escalate to C |
|----------------|---------------|---------------|
| IDOR (read) | PUT/DELETE on same endpoint | Full account data manipulation |
| SSRF (any) | Cloud metadata [REDACTED_IP] | IAM credential exfil -> RCE |
| XSS (stored) | Check if HttpOnly is set on session cookie | Session hijack -> ATO |
| Open redirect | OAuth redirect_uri accepts your domain | Auth code theft -> ATO |
| S3 bucket listing | Enumerate JS bundles | Grep for OAuth client_secret -> OAuth chain |
| Rate limit bypass | OTP brute force | Account takeover |
| GraphQL introspection | Missing field-level auth | Mass PII exfil |
| Debug endpoint | Leaked environment variables | Cloud credential -> infrastructure access |
| CORS reflects origin | Test with credentials: include | Credentialed data theft |
| Host header injection | Password reset poisoning | ATO via reset link |

### Cluster Hunt Protocol (6 Steps)

```
1. CONFIRM A     Verify bug A is real with an HTTP request
2. MAP SIBLINGS  Find all endpoints in the same controller/module/API group
3. TEST SIBLINGS Apply the same bug pattern to every sibling
4. CHAIN         If sibling has different bug class, try combining A + B
5. QUANTIFY      "Affects N users" / "exposes $X value" / "N records"
6. REPORT        One report per chain (not per bug). Chains pay more.
```

### Real Examples

**Coinbase S3->Bundle->Secret->OAuth chain:**
```
A: S3 bucket publicly listable (Low alone)
B: JS bundles contain OAuth client credentials
C: OAuth flow missing PKCE enforcement
Result: Full auth code interception chain
```

**Vienna Chatbot chain:**
```
A: Debug parameter active in production (Info alone)
B: Chatbot renders HTML in response (dangerouslySetInnerHTML)
C: Stored XSS via bot response visible to other users
Result: P2 finding with real impact
```

---

# TOP 1% HACKER MINDSET

