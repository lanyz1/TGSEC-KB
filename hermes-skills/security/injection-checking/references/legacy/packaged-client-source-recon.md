<!-- archived from /root/.hermes/skills/security/packaged-client-source-recon/SKILL.md on 2026-10-21 -->

---
name: packaged-client-source-recon
description: "Use when unpacking a desktop client for backend recon."
version: 1.0.0
category: security
tags: [recon, client, pyinstaller, electron, api-map, localhost, dns-rebinding]
---

> 归档卡：原目录 `/root/.hermes/skills/security/packaged-client-source-recon`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/packaged-client-source-recon/…')`，不要相对 `references/legacy/` 解析。

# Packaged Client Source Recon

When a product ships a desktop client (installer, portable ZIP, .exe, .dmg, AppImage, MSI), that client is a map of its backend. Distributors routinely ship more than they intend — sometimes literal source code. Mine the client before fighting the server.

## When to use

- Target has a "download client / app" page, a `/releases/` path, or publishes a checksum.
- Target is a licensed / card-key product (the client holds the licensing protocol).
- The desktop app talks to a cloud API you can't reach or can't authenticate to.
- The app runs a local dashboard/daemon (usually `127.0.0.1:PORT`).

Pairs with: origin-IP discovery (to reach the real backend), API error-oracle schema discovery, and local-service / DNS-rebinding testing.

## Step 1 — Get the artifact and verify it

```bash
# the download page usually publishes version + SHA-256; grab both
curl -sk "https://target/download/" | grep -oE 'releases/[^"]+\.(zip|exe|msi|dmg|AppImage)'
curl -sk -o client.zip "https://target/download/releases/<file>"
sha256sum client.zip      # must equal the published hash
```

The published checksum is a gift: it proves you hold the official, unmodified artifact before you report anything derived from it.

**Pitfall — false tamper alarm:** an interrupted download yields a file starting with `PK\x03\x04` yet missing its central directory (`zipfile.ZipFile(p)` → "not a zip file"), and its SHA-256 will differ from the page. Re-download, re-hash, then judge. Never report a hash mismatch from a partial fetch.

## Step 2 — Unpack: look for raw source before reaching for a decompiler

```bash
python3 - <<'PY'
import zipfile, collections
z = zipfile.ZipFile('client.zip')
tops = collections.Counter(n.split('/')[2] for n in z.namelist() if n.count('/') >= 2)
print(tops.most_common(40))          # spot _internal/, resources/, app/, backend/
PY
```

- **PyInstaller onedir** → `<App>/_internal/`. Check inside for **raw `.py` files** sitting next to `__pycache__/*.pyc`. Shipping un-compiled source is common, is itself a finding, and saves all decompilation.
- **PyInstaller onefile / entry script** → no `run.py` on disk; the entry point lives inside the exe:
  ```bash
  curl -sL -o pyinstxtractor.py https://raw.githubusercontent.com/extremecoders-re/pyinstxtractor/master/pyinstxtractor.py
  cd <exe-dir> && python3 pyinstxtractor.py App.exe
  # -> App.exe_extracted/run.pyc
  ```
- **Electron** → `resources/app.asar` (`npx asar extract`); also check `app.asar.unpacked/`.
- **Nuitka / compiled** → no `.pyc`; go straight to string-mining plus native RE.

## Step 3 — Mine even with no working decompiler

A `.pyc` built by a **newer Python than yours** will not unmarshal, but **string literals survive**. Read the raw bytes:

```python
import re
data = open('run.pyc','rb').read()
for s in re.findall(rb'[\x20-\x7e]{4,160}', data):
    print(s.decode('ascii','ignore'))
```

The entry script is the single highest-value file: it carries the bind `HOST`/`PORT`, every `os.environ.get(...)` default, DB URLs, seed file names, and feature flags. This is where you learn the local service's bind address and its dangerous defaults.

## Step 4 — Mine the source for the backend map

Grep the extracted tree, in this order:

1. **Cloud base URLs** — `DEFAULT_*_BASE_URL`, `*_SERVER`, `BASE_URL`, `NAV_URL`. Gives you the API host, the licensing host, and often the operator's sibling services.
2. **Every request path** — `re.findall(r'["\'](/v1/[^"\']+)["\']', src)` plus `(post|get|put|delete)\(`. Reconstruct the full endpoint table; the client calls routes the web UI never shows.
3. **Auth scheme** — token headers, per-request signatures (what is signed, in what order, joined how), HMAC/GCM helpers, refresh endpoints, CSRF header names.
4. **Licensing / card-key protocol** — the verify endpoint and JSON body, min-length validation, machine-binding behaviour, and any *local* cache cipher. Local caches are usually reversible: `key = sha256(f"<prefix>|{machine_id}|{host}|{SECRET}")` with `SECRET` defaulting to `""`, XOR stream over HMAC-SHA256 — recoverable by the local attacker.
5. **Stored credentials** — config/backup scripts name the files (`credentials.json`, `*_profile/`, `.session`, `*.db`). Backup flags like `-IncludeCredentials` / `-IncludeProxy` / `-IncludeLoginSession` are a signed confession of what sits on disk.
6. **Infrastructure / counterparties** — every distinct hostname, including tenant subdomains (`<id>-<tag>.operator.tld`) and third-party data feeds.

## Step 5 — Verify the mapped API against the live server

The source says *what* to call; the server says *what's exposed*.

- Test **every** endpoint unauthenticated first. Clients mix public and private routes, and the public ones are often left unauthenticated server-side too.
- Recover request schemas by **error oracle**, not guessing: send `{}`, read the validation error, add the named fields, repeat. `extra_forbidden` entries enumerate the real field names.
- Hunt for the **one unauthenticated token-minting endpoint** (`activate`, `register`, `login`, `session`) — that is the door.
- Re-run authz tests **directly against the origin**, not the CDN edge: edge rate limiting hides the app's own (lack of) limits.

## Step 6 — Audit the local control service (client-side control / credential theft)

A dashboard on `127.0.0.1` is a real target: a malicious page reaches it via **DNS rebinding** whenever there is no `Origin`/`Host` check. From the extracted source, answer three questions:

1. **Any auth dependency on the routers?** Look for `Depends(`, `add_middleware`, token verification.
2. **Is `CORSMiddleware` installed?** `app.include_router(...)` with no `add_middleware(CORSMiddleware, ...)` and no `Origin` allowlist = no cross-origin protection, so a rebound page can *read* responses, not just fire requests.
3. **What does the launcher bind?** `uvicorn.run(..., host=HOST)` with `HOST = os.environ.get("APP_HOST", "127.0.0.1")`. `127.0.0.1` still loses to DNS rebinding; an env override to `0.0.0.0` exposes it to the whole LAN.

Also read the update/backup PowerShell or shell scripts: they enumerate the local API paths (`/health`, `/api/...`) and the real port, saving guesswork.

## Pitfalls

- **Top-N port scans miss the interesting port.** A custom high port (e.g. `40832`) surfaces only in a full 1–65535 sweep. Always run the full sweep against the primary host.
- **A `_internal/backend/` full of `.py` is ordinary, not exotic.** Check before reaching for a decompiler.
- **The source tells you the endpoint list; only the server tells you the auth reality.** Do not infer that an endpoint is protected because its sibling is — modules drift, and the drifted one is the finding.
- **Local-API exposure needs no server compromise.** Report it even when the cloud side stays closed.

## Reference case

`references/pc28-engine-case.md` — full worked example (PyInstaller onedir with raw source, cloud-API map, card-key protocol, localhost DNS-rebinding surface).

---

@TGSEC社区 · @TGSEC-Qtzuu 整理
