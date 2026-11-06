## Anti-patterns

- **DO NOT spray vCenter SSO** — lockout is aggressive; one chance often
- **DO NOT execute file-upload PoCs without explicit OK** — they create persistent webshells; cleanup overhead and audit trail
- **DO NOT confuse ESXi-management-on-internet with vCenter** — different attack surfaces; ESXi Open SLP CVEs target port 427
- **DO NOT skip SSL handshake banner check** — VMware exposes versions there; this is the lowest-noise initial probe

---

