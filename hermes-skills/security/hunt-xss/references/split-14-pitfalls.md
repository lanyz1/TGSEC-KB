## Pitfalls
- **Self-XSS** — XSS that only affects the attacker's own session is informational. Need stored XSS or reflected XSS affecting other users.
- **XSS without HttpOnly bypass** — if the session cookie is HttpOnly, XSS can't steal it. Need to demonstrate impact via other means (CSRF token theft, keylogging, page modification).
- **DOM XSS without exploitable sink** — `location.hash` reaching `innerHTML` is exploitable. `location.hash` reaching `console.log` is not.
- **CSP bypass without XSS** — finding a CSP bypass technique is not a vulnerability without working XSS to bypass. Distinguish the two.
- **MIME-type confusion** — uploading HTML as image/png that renders as HTML is MIME confusion, not classic XSS. May be blocked by X-Content-Type-Options.

---

