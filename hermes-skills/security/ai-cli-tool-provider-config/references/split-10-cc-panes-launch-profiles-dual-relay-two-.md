## CC-Panes Launch Profiles — dual relay (two 中转, pick per session)

CC-Panes (Tauri app) can run Claude Code against DIFFERENT relays in parallel sessions:
create one Provider + one Launch Profile per relay, then pick the profile when starting a
session. This is the "方案 B" answer to "终端输入 claude1 走中转1 / claude2 走中转2" — CC-Panes
has NO terminal-alias mechanism (`LaunchProfile.alias` is display-only).

### Key facts (from cc-panes source, Aug 2026)

- Config files live in the app data dir (`~/.cc-panes/` release, `~/.cc-panes-dev/` debug):
  - `providers.json` — `{"providers": [...], "defaultIsSystem": false}`
  - `launch-profiles.json` — `{"schemaVersion": 1, "profiles": [...]}`
- Provider JSON shape: `{"id","name","providerType":"proxy","apiKey","baseUrl","isDefault":false}`
  (camelCase). `providerType: "proxy"` injects `ANTHROPIC_API_KEY` + `ANTHROPIC_BASE_URL`
  into the launched CLI.
- **CRITICAL: CC-Panes injects `ANTHROPIC_API_KEY`, not `ANTHROPIC_AUTH_TOKEN`** — but
  new-api-family relays (fkcodex, etc.) accept the relay token as a Bearer `ANTHROPIC_API_KEY`
  header. Verified live: `POST {base}/v1/messages` with `Authorization: Bearer <relay token>`
  returns 200. So reuse the same token in `apiKey`.
- Launch Profile JSON shape:
  `{"id","name","alias","providerId","targetTools":["claude"],"targetRuntime":null,"yoloMode":false,"mcpPolicy":{...},"skillPolicy":{...},"isDefault":false,"createdAt","updatedAt"}`
- `ProviderService` calls `refresh_from_file()` before every read → providers.json edits are
  picked up live. `LaunchProfileService` loads at startup → **restart the app after writing
  launch-profiles.json** (and it's safer to restart for providers too; the frontend caches).
- Verification without GUI: the bundled web server exposes the same API at
  `http://127.0.0.1:18080/` (release) — `GET /api/providers`, `GET /api/launch-profiles`,
  `POST /api/launch-profiles/preview {"profileId":"...","cliTool":"claude"}` returns the
  resolved provider binding.

### Setup script pattern (read tokens from CC-Switch DB, write both files)

```python
import sqlite3, json, datetime
db = sqlite3.connect(r'C:\Users\Administrator\.cc-switch\cc-switch.db')
rows = db.execute("SELECT name, settings_config FROM providers WHERE app_type='claude'").fetchall()
# find each relay's env.ANTHROPIC_AUTH_TOKEN + ANTHROPIC_BASE_URL from settings_config JSON
providers = [{"id":"relay-1","name":"Claude中转1","providerType":"proxy",
              "apiKey":tok1,"baseUrl":url1,"isDefault":False}, {...relay-2}]
json.dump({"providers":providers,"defaultIsSystem":False}, open(r'~\.cc-panes\providers.json','w'))
profiles = [{"id":"relay-1-p","name":"Claude-中转1","alias":"claude1","providerId":"relay-1",
             "targetTools":["claude"],"mcpPolicy":{"mode":"default"},"skillPolicy":{"mode":"core"},
             "isDefault":False,"createdAt":now,"updatedAt":now}, {...}]
json.dump({"schemaVersion":1,"profiles":profiles}, open(r'~\.cc-panes\launch-profiles.json','w'))
```

### Pitfalls

- **Balance check**: relays built on new-api expose balance at `/api/user/self` but it needs
  the WEB-LOGIN session cookie, NOT the API key (API key → "Unauthorized, invalid access
  token"). `/dashboard/billing/credit_grants` returns the SPA HTML, not JSON. So CC-Panes /
  CC-Switch / API key cannot show relay balance — user must log into the relay's web panel.
- **HTTP 503 "No available accounts"** from a relay = the relay's own account pool is empty
  (auth passed, 401 would be auth failure). Not a config bug; tell the user to wait/top up.
- **WAF on Chinese relays**: plain `urllib` gets `403 error code: 1010` (Cloudflare) — send a
  desktop Chrome `User-Agent` header.
- 70.39-style bare relays (no dashboard, no /v1/models even) only serve `/v1/messages`-style
  endpoints; there is no balance API at all.

