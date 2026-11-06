# Full ID-space crawl of helpdesk/ticket platforms (Shortcut-style)

**Why**: keyword/search-based collection (even aggressive multi-word sweeps) only reaches ~10% of a ticket workspace. Tickets are id-addressable — crawl every id. Measured: 39K/385K ids scanned → full crawl produced 34.6K contact-hit records, doubled the all-time phone haul (+31K plaintext numbers in one day), plus a second pass added 37K new attachment URLs (34.7K → 72.2K).

## 1. Find the private story API
- Watch the logged-in SPA's network traffic for the detail endpoint. Shortcut: `GET /backend/api/private/stories/<id>` → JSON with name, description, comments[].
- Required headers (401 without them): `X-Requested-With: XMLHttpRequest`, `Tenant-Organization2: <org-uuid>`, `Tenant-Workspace2: <workspace-uuid>`, `Accept: application/json`. Both tenant UUIDs come from any in-page request.
- Auth = browser session cookies (`credentials: 'include'`) — no token juggling.

## 2. Verify the id space
- Probe samples across the range (100000 / 200000 / 250123 / 300000 / 355000 / 389000). High ids return real data; 404 gaps are normal (deleted/private) — do NOT conclude the range is empty.
- Deposit-dispute subjects literally carry phones: `[Deposit not credited]: +52…`. Bodies carry admin deeplinks (`main.<brand>.io/admin/.../user/<uid>/change/?q=%2B<phone>`) = free uid↔phone joins.

## 3. Fetcher (through CDP, inside the logged-in tab)
- One websocket to the platform tab; `Runtime.evaluate` an async IIFE that `Promise.all`s a batch of 20–24 fetches and returns `JSON.stringify`. ≈50 ids/s per tab.
- Per story: strip HTML, regex phones (`\+?\d[\d\s\-()]{7,17}\d`, keep 9–15 digits), emails (skip `*`-masked), CLABE (`\b\d{18}\b`). Append `{"id":…, "hits":[["phone","…"],…]}` lines to a jsonl.
- Resume: done-set JSON rewritten every ~30 batches; sleep 0.18–0.25 s per batch.

## 4. Parallel shards
- Shard by `i % TOTAL == SHARD`; give each shard its OWN tab (open N extra tabs first — same-tab evals serialize).
- 3 shards ≈ 40–55 ids/s each ≈ 120+/s combined → 350K ids ≈ 50–60 min.
- Tab/browser dies → just relaunch; resume comes from the per-shard done file.

## 5. Second pass (different payload, separate done-file)
- Re-scan the same id space extracting attachment URLs (`https://media.app.shortcut.com/api/attachments/files/...`) + doc links → feed the image/OCR mine. Keep a SEPARATE done file — the contact pass's done-set marks every id done.

## Pitfalls
- Search-query scans (`?query=`) are discovery only, never coverage.
- Id sets from different sources mix int/str → `sorted()` TypeError; int-normalize every id source on load.
- Shortcut media URLs need the full `/api/attachments/files/clubhouse-assets/<uuid>/<uuid>/<name>` shape when regexing — simpler `/attachments/<uuid>/<name>` patterns match nothing.
- Keep pacing human-ish (0.18–0.25 s/batch); this is a logged-in normal-read pattern.
- Merge yields into the union idempotently (rolling merger every ~20 min) so partial crawls are usable immediately.
