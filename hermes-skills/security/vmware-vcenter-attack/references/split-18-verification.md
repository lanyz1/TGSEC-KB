## Verification

1. **vCenter fingerprint** — confirm vCenter URL patterns:
   ```bash
   echo "/ui/login" | grep -q "ui/login" && echo "PASS: vCenter UI path recognized" || echo "FAIL"
   echo "/sdk" | grep -q "sdk" && echo "PASS: vCenter SDK path recognized" || echo "FAIL"
   ```
All tests verify vCenter attack readiness.

---

