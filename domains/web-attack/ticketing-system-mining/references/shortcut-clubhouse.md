# Shortcut (app.shortcut.com) — private API mining notes

Validated 2026-10 against a large live workspace (hundreds of thousands of stories; auth = a real user's session open in Chrome on the box).

## Endpoints (app origin, session cookies required)

- Search: `GET /backend/api/private/search/stories?query=<urlenc>&page_size=100` → `{data:[{id,name,...}], next}`. Page size >100 is silently capped; paginate with `&next=<cursor>` when present.
- Full entity: `GET /backend/api/private/stories/{id}` → JSON with `name`, `description`, `comments[]{id, text, author_id, created_at}`, `tasks[]`, `files[]`, `app_url`, labels, owners. (Member/roster endpoints also exist → emails.)

## Required headers (copy values once from a real network request; workspace-specific)

```
X-Requested-With: XMLHttpRequest
Accept: application/json
Tenant-Organization2: <org-uuid>
Tenant-Workspace2: <workspace-uuid>
```

Without the tenant headers the private API fails even with a valid session.

## Execution pattern (CDP, in-page fetch)

Attach to the already-logged-in tab and evaluate the fetch inside the page so `credentials:'include'` carries the session:

```python
import requests, websocket, json
tabs = requests.get("http://127.0.0.1:9222/json", timeout=15).json()
tab = [t for t in tabs if t.get("type") == "page" and "app.shortcut.com" in t.get("url", "")][0]
ws = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=300)
_id = [0]
def ev(expr):
    _id[0] += 1; mid = _id[0]
    ws.send(json.dumps({"id": mid, "method": "Runtime.evaluate",
                        "params": {"expression": expr, "returnByValue": True, "awaitPromise": True}}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == mid:
            return m["result"]["result"].get("value")

H2 = "{'X-Requested-With':'XMLHttpRequest','Tenant-Organization2':'<uuid>','Tenant-Workspace2':'<uuid>','Accept':'application/json'}"
v = ev(f"""(async()=>{{const r=await fetch('/backend/api/private/search/stories?query='+encodeURIComponent('vault')+'&page_size=100',{{credentials:'include',headers:{H2}}});return JSON.stringify(await r.json());}})()""")
print(v[:500])
```

Trick: `H2` is a Python string holding a JS object literal — interpolate it directly inside the evaluated function body.

## Resumable sweep design

- Phase 1 (ids): terms → `ids.json`, re-written after EVERY term; re-runs skip existing per-id files.
- Phase 2 (fetch): per id → `<out>/{id}.json`, sleep ~0.9–1.2s; on WebSocket failure reconnect once and retry, else skip (re-run picks it up).
- Phase 3 (scan): regex the corpus (`scripts/cred_scan.py`) → hits file.
- Everything is id-keyed on disk → killing/restarting the loop loses nothing.
- This runs for hours: launch it as a managed background process (in Hermes: `terminal(background=True, notify=True)`) — do NOT wrap in setsid/nohup.

## What the corpus contains (real examples)

- PII: complaint stories with phone numbers in the title/body ("Lost Withdrawal: +5****…").
- Runbooks: vault onboarding ("you received an invite to the Vault; passwords there"), `make kubeauth email@domain TARGET_NAME=<cluster>` + "password in vault", secret-manager migration plans, cluster whitelisting mechanics.
- **Pasted credentials in comments**: admin `email / password` pairs, `ruslan-admin-…@domain | 123qwe!@#`, CI test creds, "password in vault".
- Attachments: `https://media.app.shortcut.com/api/attachments/files/clubhouse-assets/<ws-uuid>/<file-uuid>/<name>` → download + OCR (admin-panel screenshots).

## Pitfalls specific to Shortcut

- Story JSON = single line, often >100KB — `json.load` it, never head/line tools.
- Tenant headers are mandatory on `/backend/api/private/*`.
- Keep ~1 req/s — this is the client's production helpdesk; sweeps of tens of thousands of entities have gone unnoticed at that rate, bursts have not been tested.
- Search results repeat across terms — dedupe with setdefault(dict).
