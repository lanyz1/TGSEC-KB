---
name: waf-evasion-and-credential-attack
description: "Use when WAF or rate limits block API/credential attacks."
version: 1.1.0
tags: [pentest, waf, ratelimit, bruteforce, credential-attack, tor, redteam]
---

# WAF evasion & credential-attack harness

Load this when an edge WAF, a CDN bot rule, or an application rate limit blocks API probing or
credential testing — or when a brute-force run finishes suspiciously fast, "hits" on an error
page, or the target account locks out after a handful of attempts.

<!-- split-index -->

## Section index

- [Precondition gate (standing user rule)](references/split-01-precondition-gate-standing-user-rule.md)
- [0. Identify which layer blocked you — before choosing a bypass](references/split-02-0-identify-which-layer-blocked-you-befor.md)
- [1. Order of operations](references/split-03-1-order-of-operations.md)
- [2. A few blocked paths — browser in-page fetch](references/split-04-2-a-few-blocked-paths-browser-in-page-fe.md)
- [2b. SafeLine (雷池/Chaitin) specific — measured behaviour](references/split-05-2b-safeline-chaitin-specific-measured-be.md)
- [3. Bulk — source-IP rotation by SOCKS credential isolation](references/split-06-3-bulk-source-ip-rotation-by-socks-crede.md)
- [4. Harness engineering (every run)](references/split-07-4-harness-engineering-every-run.md)
- [5. Lockout vs rate limit — model both before a big run](references/split-08-5-lockout-vs-rate-limit-model-both-befor.md)
- [6. Client-side server list = alternate, often weaker, entry points](references/split-09-6-client-side-server-list-alternate-ofte.md)
- [7. Recover the contract from the client binary before writing payloads](references/split-10-7-recover-the-contract-from-the-client-b.md)
- [8. Depth notes](references/split-11-8-depth-notes.md)
