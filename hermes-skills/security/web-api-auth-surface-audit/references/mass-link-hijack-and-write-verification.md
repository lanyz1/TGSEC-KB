# Mass Link/Redirect Hijack & Write Verification

Use when the task is "change every link / jump / download to X" on an admin panel you already control. The
tempting move is one batch update; the failure is a 200 response with the old values still live. Each surface
stores and serves the URL differently.

## 1. Surface inventory before writing

| Surface | Typical storage | Verification |
|---|---|---|
| Product / merchant | one `url` field | re-fetch all products; `url == target` count |
| Ad / banner | often no URL; `pid` points to a product | change the product; count product `url` |
| Channel entry | `channelLink`, often derived from domain + entry path + number, but may be stored/bot-maintained | re-read one channel; per-object edit may no-op and a setting change may not rewrite it |
| Global settings | `WEB_DOMAIN`, `LANDING_DOMAIN`, `LANDING_DOWNLOAD_DOMAIN`, promo domain | read settings back; check whether stored rows change |
| Live entry page | `/entry/<cid>` rendered from DB | count target occurrences in page source |
| Old static page | `/<cid>.html` generated file | size + MD5 + target count before/after |
| APK / download | link inside the package or a fixed download route | not a web redirect; state so |

Pull the complete object shape from the admin list API or Swagger definition before writing. A field that
looks like a URL in the UI may be read-only; a field that looks absent may be covered by the product relation.

## 2. Write, then read back every object

```python
def mass_update(path, ids, field, target, batch=50):
    for chunk in [ids[i:i+batch] for i in range(0, len(ids), batch)]:
        post(f"/api/{path}/batch_update", {"ids": chunk, field: target})
    rows = post(f"/api/{path}/list", {"pageNum": 1, "pageSize": 10000})["data"]["data"]
    hit = sum(1 for r in rows if r.get(field) == target)
    assert hit == len(rows), (hit, len(rows))
```

- `code:0,data:0` from an edit or batch endpoint is **success-with-no-op**, not proof. A single-object edit can
  return 200 and leave the value unchanged when the field is computed, bot-maintained, or outside the write
  whitelist.
- Test one object, re-read it, then broadcast or retire the field. Do not loop the same no-op over 37 rows.
- Count target occurrences in the rendered page, not in the write response: the entry page's inline config or
  preloaded JSON is the ground truth for what a click will resolve.
- Count the old value too; the goal is `target == N` **and** `old == 0` on every surface you claim.

## 3. Derived and read-only fields

A `channelLink`-style field is commonly `WEB_DOMAIN + entry path + number`, maintained by a bot or computed on
read. Symptoms:

- `channel/edit/{id}` with only the link field returns `success` / `data:0`, value unchanged.
- Changing the global `WEB_DOMAIN` or `LANDING_DOMAIN` does **not** rewrite rows already stored with the old
  domain.
- The UI field is disabled or annotated as maintained by another service.

Test one row, re-read it, and if unchanged, record the field as not-editable via the API and stop. The click
target is usually the product `url`, not the channel entry link; say which one you changed.

## 4. Static/legacy pages, generators, and CDN

- Old `/<cid>.html` pages can be legacy output, separate from the live `/entry/<cid>` renderer. They may keep
  old links for days; the live entry can already be fully new.
- A generator/injector can be dead: `gen_html` / `landing_inject` returning `data:0` while the file's size,
  MD5 and target count are unchanged proves it did nothing. Record it as a dead generator, not as a success.
- When the origin changes but the CDN still serves the old page, the cache header (`x-ccdn-cachettl` measured in
  seconds) explains it. Use a cache-buster and the direct origin for verification; if there is no purge API,
  report the cache TTL and the live-vs-legacy split instead of claiming the old page changed.
- If the task is "all", a legacy page that still resolves old is an explicit exception in the report.

## 5. File write vs file create (adjacent primitive)

Before building any chain that needs a file at a fixed path (scheduler script, cron drop-in, config include):

1. Point the writer at a **fresh filename** and check the filesystem/URL directly.
2. A writer that only replaces a placeholder inside an existing `index.html` will not create the fresh file
   (404, `data:0`, or no write). It is an **edit** primitive, not a **create** primitive.
3. Upload endpoints that rename to a timestamp/UUID cannot satisfy a fixed-name requirement.
4. Only after proving creation, build the chain. For a config-to-command path: the runtime may execute the
   configured program directly without a shell (Java `ProcessBuilder` passes the whole string as one executable
   path). Set the configured path to a benign binary such as `/bin/echo` to dump the exact argv into the job
   history; `/bin/tee` or `/bin/touch` reveals option parsing. A fixed operand that names a missing file (an
   architecture binary, a runner, a template) strands every shell-interpreter substitution until that file
   exists in the process working directory.

## 6. Report shape

Use a per-surface table, not a narrative (counts below are an example; replace them with yours):

| Surface | Total | Target | Old | Status |
|---|---:|---:|---:|---|
| products | 239 | 239 | 0 | changed |
| entry/1001 | — | 523 occurrences | 0 | changed |
| channelLink | 37 | 0 | 37 | derived/read-only |
| old /1001.html | — | 0 | all | dead generator + CDN cache |

State each exception with its mechanism (derived field, dead generator, CDN cache, missing file) and never
write "all redirects changed" while a row in the table is old.
