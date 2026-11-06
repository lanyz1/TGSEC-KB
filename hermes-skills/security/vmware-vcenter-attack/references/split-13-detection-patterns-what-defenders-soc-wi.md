## Detection patterns (what defenders/SOC will see)

- Excessive 404s on `/ui/vropspluginui/*` — IDS signature
- POST to `/sdk` from non-management IP
- `<EMAIL-REDACTED>` auth failures
- TLS handshake fingerprint changes
- Plugin upload to vRealize endpoint

Pair with `mid-engagement-ir-detection` skill — vCenter is monitored heavily in mature SOCs.

---

