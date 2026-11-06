# bb-methodology 全文 第 2/3 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

## PART 3: NAVIGATION & TIMING

### Non-Linear Navigation Quick Reference

| I'm stuck because... | Go to... |
|----------------------|----------|
| Can't find any subdomains | Phase 1: Try different recon sources, Google Dorks |
| Found subdomain but don't know what to test | Phase 2: Map the app, download JS, understand auth |
| Testing but nothing works | Phase 3: Switch vuln class (20-min rotation rule) |
| Found a bug but impact is low | Phase 4: Escalation paths or gadget chaining |
| WAF/CSP/403 blocking my payload | Bypass techniques, then return to current phase |
| Been stuck for 45 min on one param | STOP. Rabbit hole. Move to next endpoint. |
| New API endpoint discovered during testing | Return to Phase 2: map it before attacking |
| Found one bug | A->B signal: same dev made more mistakes. Hunt 20 min for siblings. |

### 20-Minute Rotation Clock

Every 20 minutes ask yourself: **"Am I making progress?"**
- Yes -> Continue
- No -> Rotate to next: endpoint -> subdomain -> vuln class -> target
- Been on same target 2+ weeks with no findings? -> Consider switching program

### Pushback Protocol (When the User Says "Find More")

When the user disagrees with your stopping point — e.g., "I've found 10+ bugs, you should find the same," or "look harder," or "you're missing things":

**Default assumption: they are correct. You stopped early.**

Before pushing back with "I think we're done because X," do this:
1. **Re-read 3 more `hunt-*` skills** beyond what you have loaded. Pick ones that match observed surface (e.g., custom login → `hunt-auth-bypass`; SOAP endpoints → look for protocol-specific skills; URL parameters → `hunt-ssrf`).
2. **Re-attack the same surface** with the new skill checklists. Walk every step in the new skills, even if it feels redundant.
3. **Document negatives** as you go — a confirmed "no bug here" is itself a finding for the user to see (it proves coverage).
4. **Only after exhausting 3 new skills' checklists** do you push back, and only with a concrete list of what was tested.

**Lesson from an authorized engagement:** After a first-pass of 5 weak findings the user said "I have 10+, find them." Loading `hunt-auth-bypass` (which had been loaded but not walked through end-to-end) immediately surfaced the `/_vti_bin/Authentication.asmx` legacy SOAP login — the highest-impact bug in the engagement. The user was right; pushback would have been wrong.

### Tool Routing by Phase

| Phase | Tools | Why this order |
|-------|-------|----------------|
| Recon: Subdomains | `subfinder` -> `amass` -> `puredns` -> `httpx` | Passive first (no detection) -> resolve DNS -> probe HTTP + tech stack |
| Recon: URLs | `gau` + `waymore` -> `katana` -> `uro` | Archive (forgotten endpoints) -> active crawl (JS-rendered) -> deduplicate |
| Recon: JS | `jsluice` + `mantra` + `trufflehog --only-verified` | Extract URLs/secrets -> find API keys -> verify keys actually work |
| Recon: Ports | `naabu` (wide) -> `rustscan` (deep) | Fast top-1000 sweep -> full 65535 on interesting targets |
| Recon: Scan | `nuclei -tags cve` -> `nuclei -tags takeover` | Known CVEs first -> then takeover (act immediately) |
| Mapping: Params | `arjun` + `paramspider` + ParamMiner | Brute-force hidden params + mine archives + cache headers |
| Mapping: JS code | Download -> `jsluice` -> VS Code/Cursor grep | Extract -> static analysis -> AI-assisted taint analysis |
| Mapping: Dorks | Manual Google Dorks | Custom per-target queries find what automation misses |
| Discovery: Fuzz | `ffuf -ac` + `cewl` custom wordlist | Auto-calibrate filtering + target-specific words beat generic lists |
| Discovery: XSS | `kxss` -> `dalfox` | Filter (which params reflect?) -> scan (only reflective params) |
| Discovery: SQLi | `ghauri` | Modern blind SQLi on ID-like parameters |
| Discovery: SSRF | `interactsh-client` | Self-hosted OOB listener for blind SSRF/XXE/RCE |
| Discovery: WAF | `wafw00f` -> `whatwaf` | Identify WAF vendor -> test bypass techniques |
| Exploit: 403 | `byp4xx` or `nomore403` | 20+ bypass techniques automated |
| Exploit: Takeover | `subzy` | Checks CNAME against 70+ vulnerable services |
| Exploit: Cloud | `s3scanner` + `aws` CLI | Scan bucket permissions -> extract metadata credentials |
| Exploit: Secrets | `trufflehog --only-verified` | Only verified working keys (no false positives) |

### Session End Checklist

- [ ] Save all Burp/Caido project files
- [ ] Record any "weird but not yet exploitable" behaviors (future gadgets)
- [ ] Update notes with failed attempts (don't re-test with same techniques)
- [ ] Log findings with `/remember`

---

## PART 4: METHODOLOGY DISCIPLINE (False-Positive Prevention)

Most retracted findings come from four recurring process bugs. Each has a hard rule.

> **Important framing:** These discipline rules are about *correctness of findings* — not throttling of effort. They tell you which signals are real findings and which aren't. They do **not** tell you to send fewer probes. If you find yourself using these rules to justify stopping early, you're misreading them — load `redteam-mindset` (DO NOT STOP primary directive) and continue. Coverage discipline and finding-correctness discipline are orthogonal axes; you need both on full.

### Marker Discipline

When testing for reflection, cache poisoning, parameter pollution, or OOB SSRF, the marker string you inject MUST be unique and unmistakable.

**Rules:**
- Markers are random alphanumeric strings, **8+ characters**, no English words, no protocol keywords.
- **NEVER** use `test`, `marker`, `evil`, `attacker`, `payload`, `javascript`, `script`, `AAAA`, `BBBB`, your domain name, or any string that could plausibly appear naturally in the target's HTML/JS/error messages.
- **Good markers:** `cpmark987abc`, `x4hd2k9pq`, a Collaborator subdomain prefix like `dlsrcurl.<collab>.oastify.com`, or `__ZZ_MARKER_<random>_ZZ__`.
- Before claiming reflection: search the **baseline** (no-marker) response for the marker string. If it appears naturally, change your marker. This single check catches 80% of false-positive reflection reports.
- For OOB testing, sub-tag each Collaborator payload (e.g., `dlsrcurl.<collab>`, `authsrc.<collab>`) so callbacks identify the specific sink that fired.

**Lesson from an authorized engagement:** Initial scan flagged `X-Forwarded-Proto: javascript` as reflecting into multiple SharePoint pages. The "reflection" was the literal word `javascript` appearing naturally in SP help-link hrefs (`href="javascript:HelpWindowKey(...)"`). False positive caused by a non-unique marker.

### Body-Diff Rule

A bypass claim requires response **body** differential, not just status code.

**Rules:**
- 200 OK with byte-identical body to the baseline is NOT a bypass.
- 200 OK with a 5-byte difference might be — verify what changed (correlation ID? timestamp? real content?).
- Always diff the body side-by-side before claiming bypass: `diff <(curl ... baseline) <(curl ... bypass)`.
- Status-code-only claims (e.g. "Host header X gave 200 instead of 403") are the most common rejected-as-N/A category on bug bounty platforms.

**Lesson from an authorized engagement:** `Host: target.example:<EMAIL-REDACTED>` returned HTTP 200 instead of the baseline 403. Looked like a Host-header bypass. But the body was byte-identical (8341 bytes both) — the AWS ELB normalised the Host to `target.example:80`, dropping the `@evil` portion. Not a bypass.

### Statistical-Sample Rule (for timing-based claims)

Single outliers are NOT signal. Network jitter routinely produces 2× outliers.

**Rules for any user-enum / blind-SQLi / blind-NoSQLi / timing-side-channel claim:**
- Minimum sample size: **n ≥ 10 INTERLEAVED trials per group** (control + test, randomised order, not back-to-back).
- Compute mean, median, σ for each group.
- A signal requires the suspect group's mean to be **≥ 2σ above** the control group's mean.
- A single 2× outlier in n=1 testing is jitter, not signal.

**Lesson from an authorized engagement:** Single-shot probe showed `Administrator` taking 1527 ms vs ~700 ms control on Authentication.asmx Login — looked like clear user-enum signal. Reproduction with n=80 interleaved trials across 8 groups collapsed every group to mean=685-716 ms, σ=25-74 ms. The 1527 ms was network jitter. Finding retracted.

### Shell-Loop Ban (>5 iterations)

For any iteration that runs more than 5 times, **use Python (with try/except per iteration), not shell for-loops.**

**Why:** zsh array expansion fails silently on edge cases. A loop like `for x in "${arr[@]}"` can produce zero iterations with no error if the array wasn't populated by the previous command. The user sees output that looks complete but actually skipped the test entirely.

**Rules:**
- Loops of ≤5 hardcoded items in shell: OK.
- Anything that iterates a list, file, or computed range: Python.
- Always count results. If you expected 100 probes and got <50 lines of output, your loop ate something.

**Lesson from an authorized engagement:** A zsh array-iteration verb-tampering test silently produced no curl invocations across 20+ iterations (zsh ate the array). Output looked like "HIT [GET] /_api/web → " repeated for every probe but the actual response was missing. ~50 probes worth of testing lost. Switching the test to Python with explicit per-iteration logging surfaced the real results.

---

## Verification

Run this self-test to confirm the methodology's quality gates are operational:

1. **Marker uniqueness test** — confirm baseline check catches false positives:
   ```bash
   echo "<a href='javascript:HelpWindowKey(1)'>Help</a>" > /tmp/test-baseline.html
   MARKER="javascript"
   grep -q "$MARKER" /tmp/test-baseline.html && echo "FAIL: marker appears in baseline — choose unique marker" || echo "PASS: marker is unique"
   rm -f /tmp/test-baseline.html
   ```

2. **Body-diff test** — verify diff catches byte-identical responses:
   ```bash
   echo "identical body" > /tmp/a.txt && cp /tmp/a.txt /tmp/b.txt
   diff /tmp/a.txt /tmp/b.txt >/dev/null && echo "PASS: identical bodies detected (no bypass)" || echo "FAIL: diff broken"
   rm -f /tmp/a.txt /tmp/b.txt
   ```

3. **Statistical sample test** — verify Python can compute mean/σ:
   ```bash
   python3 -c "
   import statistics
   control = [700, 710, 690, 705, 715, 698, 702, 708, 695, 712]
   mean_c = statistics.mean(control)
   stdev_c = statistics.stdev(control)
   threshold = mean_c + 2*stdev_c
   suspect = 1527
   print('PASS: signal detected' if suspect > threshold else 'PASS: no false signal (correct)')
   " 2>/dev/null || echo "FAIL: Python3 statistics module unavailable"
   ```

4. **Shell-loop ban verification** — confirm Python iteration works reliably:
   ```bash
   python3 -c "
   items = ['a','b','c','d','e','f','g','h','i','j']
   results = []
   for item in items:
       results.append(f'processed:{item}')
   expected = 10
   actual = len(results)
   print(f'PASS: {actual}/{expected} items processed' if actual == expected else f'FAIL: {actual}/{expected}')
   " 2>/dev/null || echo "FAIL: Python3 unavailable"
   ```

5. **Mode confirmation check** — verify the engagement-type decision framework is understood:
   ```bash
   grep -q "PART 0" SKILL.md && echo "PASS: PART 0 mode-confirmation present" || echo "FAIL: PART 0 missing"
   ```

If all 5 tests pass, the methodology discipline rules are verifiable. Tests 1-2 are the most common false-positive sources in real engagements.

---

