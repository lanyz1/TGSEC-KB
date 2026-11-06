## Verification

Run this self-test to confirm the toolkit is operational:

1. **Core tool check** — verify essential Go binaries are installed:
   ```bash
   which subfinder httpx nuclei katana ffuf dalfox gau waybackurls 2>/dev/null
   ```

2. **FFUF calibration test** — confirm `-ac` auto-calibrate works:
   ```bash
   ffuf -w /usr/share/seclists/Discovery/Web-Content/common.txt -u https://example.com/FUZZ -ac -timeout 5 2>&1 | head -5
   ```

3. **Subfinder connectivity** — verify passive sources are reachable:
   ```bash
   subfinder -d example.com -silent -timeout 30 2>&1 | head -3
   ```

4. **HackerOne API reachability** — confirm GraphQL endpoint is accessible:
   ```bash
   curl --max-time 30 --connect-timeout 10 -s "https://hackerone.com/graphql" -o /dev/null -w "%{http_code}" && echo " PASS" || echo " FAIL"
   ```

5. **Semgrep install check** — confirm static analysis is available:
   ```bash
   semgrep --version >/dev/null 2>&1 && echo "PASS: semgrep available" || echo "FAIL: pip3 install semgrep"
   ```

All 5 tests should pass for a fully operational toolkit.

---

