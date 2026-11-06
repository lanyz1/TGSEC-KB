## 1. Order of operations

1. Fingerprint the blocking layer (§0).
2. Recover the exact API contract from the client binary (§7) — every payload written before this
is a guess, and a single wrong field name makes every candidate fail identically.
3. Recover the client's hardcoded server list (§6) — alternate entries often have no WAF rule.
4. For a few path-blocked endpoints: browser in-page fetch (§2). Reconnaissance only.
5. For bulk work: source-IP rotation (§3) + a correct harness (§4) + the lockout model (§5).

