## Verification

1. **Passive recon tools** — confirm key tools are installed:
   ```bash
   which subfinder amass whois 2>/dev/null | head -3
   ```
2. **CT log access** — confirm crt.sh reachability:
   ```bash
   curl --max-time 30 --connect-timeout 10 -s "https://crt.sh/?q=example.com&output=json" -o /dev/null -w "HTTP %{http_code}" && echo " PASS" || echo " FAIL"
   ```
All tests verify OSINT methodology readiness.

---

