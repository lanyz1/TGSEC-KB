# Barracuda ESG / CUI admin login

## Fingerprint
- `Server: BarracudaHTTP 4.0`; admin UI at `/cgi-mod/index.cgi`; JS assets `/cui/main.min.js`, `/js_functions.js`, `/cui/LAB.js`; `/css/emailswitch.css` → Email Security Gateway class.
- Device is slow — use 40-60s timeouts and space out attempts.

## Login flow (verified to reach credential validation)
1. `GET /cgi-mod/index.cgi` — keep the session cookie; scrape hidden `enc_key` and `et` values from the form.
2. Implement `obfuscatePassword` (from page inline JS: base64 over UTF-8 bytes XORed with a 85/170/51 cycle):

```python
import base64

def bc_encode(pw: str) -> str:
    x = bytearray()
    for i, b in enumerate(pw.encode()):
        r = i % 3
        x.append(b ^ (85 if r == 0 else 170 if r == 1 else 51))
    return base64.b64encode(bytes(x)).decode()
```

3. `POST /cgi-mod/index.cgi` form fields: `user`, `password_entry` (plaintext), `password` (bc_encode output), `enc_key`, `et`, `enctype=bc`, `form=f`, `login_page=1`, `login_state=out`, `locale=en_US`, `Submit=Sign in`.
4. Wrong creds → ~13.9KB page containing "Invalid Username or Password" (flow is correct, creds wrong). Success → different length / logout or dashboard markers.
