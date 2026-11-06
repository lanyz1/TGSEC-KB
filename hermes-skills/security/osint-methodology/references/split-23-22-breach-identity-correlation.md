## 22. Breach × Identity Correlation

This is the highest-ROI single technique for external red teams. Execute it on every engagement.

### 22.1 Source stack

| Source | Tier | Notes |
|---|---|---|
| **Hudson Rock Cavalier** | FREE | Infostealer-log corpus; very high signal for corp SSO. |
| **Have I Been Pwned** | Free + paid | Domain-wide existence + Pwned Passwords (k-anonymity). |
| **DeHashed** | Paid | Searchable per-record API. |
| **IntelX** | Free + paid | Aggregator; phonebook search. |
| **Local breach corpus** | Operator-supplied | Whatever's on disk. |

### 22.2 Domain-level severity

| Stat | Severity |
|---|---|
| ≥10 employees compromised | CRITICAL |
| 1–9 employees compromised | HIGH |
| ≥1 end-user (non-employee) compromised | MEDIUM |
| Domain seen in breach with 0 named accounts | INFO |

### 22.3 SSO_EXPOSURE correlation

After Stage 3 has run identity-fabric mapping AND breach lookups have completed: for every discovered IdP tenant, intersect with breach corpus on the tenant's domain. Non-empty intersection → `SSO_EXPOSURE` finding, severity **CRITICAL**. Evidence: tenant ID + product + employee count + per-account source attribution.

### 22.4 Operational handling of stealer logs

- Treat as PII; encrypt at rest.
- SHA-256 every artifact; record source URL + acquisition timestamp.
- Never paste plaintext passwords into cloud LLMs.
- Document chain of custody.
- For client reports: redact passwords by default; offer the operator a separate encrypted credential bundle for raw data.

---

