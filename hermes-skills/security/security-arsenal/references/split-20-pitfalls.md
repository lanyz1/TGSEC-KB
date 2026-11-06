## Pitfalls
- **Using payloads without understanding** — `<script>alert(1)</script>` is the most-blocked payload. Understand why bypasses work before using them.
- **Assuming all payloads work on all targets** — XSS payloads for React differ from Angular, PHP, or classic HTML. Match payload to technology.
- **One payload per test** — different WAFs/encodings/contexts require different payloads. Test at least 5 variants per vulnerability class.
- **Stale payload lists** — WAF rules update. A bypass that worked last month may be patched. Test payloads against the current target.
- **Payloads without context markers** — always use unique markers (8+ random chars) to confirm the payload was reflected, not just coincidence.


---

