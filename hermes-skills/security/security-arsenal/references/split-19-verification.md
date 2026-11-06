## Verification

1. **Payload catalog** — confirm payload breadth:
   ```bash
   grep -c "XSS\|SQLi\|SSRF\|XXE\|SSTI\|LFI" SKILL.md && echo "PASS: multiple vuln classes covered" || echo "FAIL"
   ```
2. **WAF bypass** — confirm bypass payloads exist:
   ```bash
   grep -q "bypass\|filter\|WAF\|encoding" SKILL.md && echo "PASS: bypass payloads present" || echo "FAIL"
   ```
All tests verify security arsenal readiness.

---

