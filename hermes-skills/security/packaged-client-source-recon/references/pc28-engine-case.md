# Case: PC28-Engine betting bot — client download → full source → cloud API map

Worked example of the whole chain. Useful as a shape to copy, not as a target list.

## Entry point

A single static page on an IP returned a marketing site with no backend. TLS on that IP
leaked two hostnames in its SAN, which turned out to be the **origin server** for a
CDN-fronted product — direct `Host:` header against the IP bypassed the CDN entirely and
returned live API JSON. That is how a throwaway landing page became a full application.

Lesson: when a page on an IP has a Let's Encrypt cert, always read the SAN and then test
each name as a `Host` header against that IP.

## What the client turned out to be

`<Product>-Engine-portable-<version>-<build>.zip` (~340 MB), published on the download page
with a SHA-256. Inside:

```
Product-Engine.exe            17 MB   PyInstaller onefile bootloader
_internal/                 ~358 MB   ALL dependencies + the app itself
  backend/app/**/*.py       190 raw .py source files   <-- the whole product
  backend/app/**/__pycache__/*.cpython-313.pyc
  backend/app/**/__pycache__/*.cpython-314.pyc
  frontend/dashboard/*.js
  {asyncpg,pydantic,playwright,redis,sqlalchemy,websockets,yaml}/...
```

Raw `.py` shipped next to the `.pyc` for two Python versions. No decompilation needed.

## Extraction commands that worked

```bash
curl -sk -o client.zip "https://<origin>/download/releases/<file>.zip"
sha256sum client.zip     # matches the page hash ONLY on a complete download

# pull just the source tree out of the archive
python3 - <<'PY'
import zipfile, os
z = zipfile.ZipFile('client.zip')
for n in z.namelist():
    if '/__pycache__/' in n or n.endswith('/'):
        continue
    if '/backend/' in n or '/frontend/' in n:
        dest = 'src/' + n.split('_internal/', 1)[-1].replace('/', '__')
        open(dest, 'wb').write(z.read(n))
PY

# entry script when it is NOT on disk: pyinstxtractor -> run.pyc -> string mine
python3 pyinstxtractor.py Product-Engine.exe
python3 -c "import re;d=open('Product-Engine.exe_extracted/run.pyc','rb').read();\
print('\n'.join(s.decode('ascii','ignore') for s in re.findall(rb'[\x20-\x7e]{4,160}',d)))"
```

The `.pyc` was Python 3.14 against a 3.11 host — unmarshalling failed, string mining did not.

## What the entry script gave up

```python
APP_HOST = os.environ.get("APP_HOST", "127.0.0.1")
APP_PORT = 8000
LIVE_ORDER_ENABLED = "true"                    # on by default
REQUIRE_MANUAL_CONFIRM_FOR_LIVE = "false"      # no human confirmation
LICENSE_SERVER = "https://<license-host>/api/v1"
# seed files: credentials.json, browser_proxy.json, smart_plans.json, *.db
```

Plus `uvicorn.run("app.main:app", host=HOST, port=PORT)`.

## What grepping the source gave up

- **Cloud base URL** for the agent API, and a **second, separate licensing host**.
- **~50 admin routes + ~13 agent routes**, recovered from the bundled admin SPA plus the
  agent client. Highest value entries were the credential-reveal route and the device
  command route — i.e. the console was a fleet C2 for the betting clients.
- **The signature scheme**: `[METHOD, pathname+search, address, timestamp_ms, sha256(canonical_json(body))].join("\n")`, signed with `personal_sign`, transported in three `x-wallet-*` headers. Knowing this immediately explained why write endpoints rejected everything ("Invalid address" was the address extracted from the JWT, not the sent header).
- **Card-key protocol**: `POST {license_host}/api/v1/verify` with
  `{license_key, machine_id, app_version, platform}`; `200 valid:false` = not found,
  `401` = invalid, `403` = bound to another machine. Keys are server-issued, so enumeration
  is pointless — but the endpoint had no rate limit at all.
- **Local cache cipher**: `key = sha256(f"<prefix>|{machine_id}|{hostname}|{SECRET}")`,
  `SECRET` defaulting to `""`, then XOR against `HMAC-SHA256(key, salt+counter)`. Fully
  reconstructable by anyone with local access → offline license forgery.
- **Infrastructure**: the operator's data feed domains, three gambling-platform tenant
  subdomains, and a local Clash proxy port — none reachable from the web UI.

## The local API finding

Extracted `app/main.py` showed:

```python
app = FastAPI(title="...")          # no CORSMiddleware, no auth dependency
app.include_router(smart_plans_router)   # full control API, wide open
```

Bound to `127.0.0.1` by default, but with no `Origin` check and no CORS policy — so a
rebound malicious page could read and write the full control surface (betting plans, stored
platform credentials, live order state). Local API paths were handed over for free by the
shipped update/test scripts.

## What did NOT work (do not re-run these as if they were the plan)

Session-cookie forgery across three cookie formats and ~40 candidate secrets; `alg:none`
and mass-assignment on the DTOs; prototype pollution; SQL/NoSQL injection on the verify and
login endpoints; path-normalisation bypass of the admin guard; enumerating the license keys.
All properly implemented. The value came from **reading the source**, not from fuzzing.

@TGSEC社区 · @TGSEC-Qtzuu 整理
