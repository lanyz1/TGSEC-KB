---
name: debug-page-oracle-recon
description: Use when an app leaks debug pages or stack traces.
category: security
---

# Debug-Page Oracle Recon

A verbose error page is not just a leak — it is a queryable interface. Force framework error
rendering, then *interrogate* it: extract schemas, DSNs, absolute paths and source, and convert
near-identical failures into oracles.

## When to use

- The target renders rich error pages: ThinkPHP trace, Laravel Ignition/Whoops, Django
  `DEBUG=True`, Spring Whitelabel + Actuator, Rails, Next.js error overlays.
- An endpoint answers with a generic "参数错误 / 系统错误 / system error" and you need to know
  *which* branch it took.
- You need table schemas, a DSN, absolute paths, or a framework source file and have no shell.
- An API refuses everything and you suspect a signature/origin/token middleware rather than bad
  credentials (pairs with `api-contract-mining`).

## Core loop

1. **Force the error branch.** Send valid-looking but semantically wrong input (nonexistent
   user, oversized value, missing field, wrong content type) instead of guessing credentials.
2. **Ask for HTML.** Add `Accept: text/html`. Many APIs gate verbose rendering on the Accept
   header — a JSON client gets a sanitized one-line error, an HTML client gets the trace.
3. **Read tab by tab.** ThinkPHP 6 ships 基本 / 文件 / 流程 / SQL / 调试 / 错误; Laravel ships
   stack + context; Django ships settings. Grep the body for the wins:
   `SELECT`, `INSERT`, `sqlsrv`, `mysql`, `Database=`, `Server=`, `/www/wwwroot`, `.php`.
4. **Harvest in one pass:** every executed SQL statement (schema *and* parameterization proof),
   the DSN, absolute paths, the throwing function's source, the loaded-class list.
5. **Convert the leak into an oracle** (below) — that is what makes it repeatable.

## Oracle patterns

### Line-number oracle
When the user-visible message is identical but the leaked frame moves, the *line number* is the
oracle. Example: a ThinkPHP admin login returned the same "账号或密码错误" for both cases, but
`data.line` was **600 = user does not exist** vs **612 = password mismatch** → full user
enumeration without any information in the message itself.

### Length-wall oracle
Passwords that are too long fail earlier in the same function. In the example above, ≤120 chars
reached the hash compare (line 612) while ≥126 chars tripped a length wall (line 608) — which
discards whole classes of candidates without submitting them, and fingerprints the (unknown)
hash/encryption step.

### Source-window oracle
Forcing a *re-declaration* fatal (`Cannot declare class A\B`, `Cannot redeclare fn()`) makes the
engine print the body of the already-loaded symbol. Include the same file from different paths
or params to slide the window, then stitch contiguous windows to reconstruct the file. This is
how middleware and controller source gets recovered when no shell exists.

### Parameterization oracle
The SQL tab prints the statement with its bindings. Seeing `username = @P1` — or an escaped
`admin\'` echo — is *proof* the sink is parameterized: stop burning hours on SQLi there and
pivot. (Equally useful in reverse: an unbound literal confirms injection immediately.)

### Type-juggling oracle
Send deliberately mis-typed values into a JSON array/object parameter and read the driver error.
It fingerprints the database **and** rules SQLi in or out, in one shot:

```
{"ids": [[52207]]}  -> {"message": "Error binding parameter 1 - probably unsupported type."}
{"ids": 52207}      -> {"message": "'int' object is not iterable"}
{"ids": {"$gt": 0}} -> {"count": 0, "success": true}     # quietly consumed as a value
```

`binding parameter` is **sqlite3's own wording** -> SQLite backend + the query is
**parameterized** (the driver is binding `?` placeholders). Treat that as a NEGATIVE SQLi verdict:
stop burning time on that field and go find a string-interpolated sink elsewhere.
`'int' object is not iterable` is a bare Python type error - the handler iterates input without
validating it: an input-shape map (and maybe a DoS primitive), not injection.

Contrast with a positive: a raw `OperationalError` / `syntax error` **with true/false arms that
differ** would be real. Mirror this against the JSON-array-vs-scalar probe in
`references/source-disclosure-endpoint-fuzz.md`.

### Failure-vs-success differential
Replay the same request with one field changed and diff the *whole* response (status line,
headers, trace, timing), not just the message. "Framework 404 body" vs "200 with empty data" is
the difference between "route does not exist" and "route exists, you are unauthenticated" —
guessing wrong there wastes entire sessions.

## Source-disclosure endpoints (`debug_<name>`)

Some FastAPI/Flask admin builds ship a **debug route that returns file contents as JSON** - no
auth, no parameter, path hardcoded server-side. You find it by fuzzing a word list:

```
GET /debug_k11
-> {"file": "/opt/<app>/k11_adapter.py", "src": "def k11_get_weekly_bill(session, username...):\n ..."}
```

**Build the word list from the app itself**, then pad with generic names:

- every adapter/platform id the UI exposed (`/adapter/platforms`, `/lottery/families`, config
  `supported_adapters`, `<select>` options) -> `debug_<each_id>` (this is the one that hit)
- generic: `app main config settings auth control master worker node token secret env utils db
  models schemas router api server wsgi asgi session crypto fernet jwt security backup restore
  deploy console adapter platform account bet queue monitor keepalive import export`
- both shapes: `/debug_<word>` and `/debug/<word>`

**What the leak is worth** (real case: `/debug_k11` gave the full `/opt/<app>/k11_adapter.py`):

- **Absolute install path** (`/opt/<app>/`) - anchors every later path/traversal/backup attempt.
- **Internal call patterns** of the app's own upstream integrations: the exact upstream endpoints
  it hits and the response fields it trusts (helps logic abuse, not just recon).
- Business rules (how bills/settlements are computed).

**Discipline:** the *response shape* is the tell - a JSON object with `file` + `src` keys is a
source leak; `{"ok":false,"error":"..."}` is just a gated API. A 200 page at `/console` is not
control of the console: its APIs still answer `401`.

Runnable fuzzer + real transcript: `references/source-disclosure-endpoint-fuzz.md`.

## ThinkPHP 5.0.5 invokefunction + 宝塔 WAF（2026-09-23）

调试页证实 gadget 路由进了应用层之后，**不要停在调试信息**。宝塔单杀查询串 `invokefunction` / `_method=__construct` / `<?php` / `.php` 文件名 / 明文 `select *`。

活链：PATH_INFO `/index.php/index/think\app/invokefunction` + JSON
`{"function":"file_put_contents","vars":[path, data, 0, null]}` 写 txt，再
`{"function":"think\\__include_file","vars":[path]}` 执行。
`think\__include_file` 要带命名空间；4 参 `vars`（`context=null`）才过反射。
nginx 散落 `.php` 直接 404 → gadget 就是壳。SQL 走 include txt + `base64_decode`。

全链 + WAF 表 + 微交易 otype=3：`references/thinkphp505-baota-invokefunction.md`。

## Language-pack LFI (ThinkPHP family)

`Lang::get($name, $vars, $range)` funnels into `switchLangSet($range)` → `include $range`. Any
request parameter that reaches the **third** argument is an arbitrary local file include, not a
translation switch. Practical notes:

- Which carrier reaches it is framework plumbing: a query-string `lang` may be stripped by the
  URL filter while the **body** `lang=` passes through to `Lang::get($msg, [], $request->lang)`.
  Test the query, body, and cookie (`think_lang`) carriers — the cookie may bypass the filter.
- PHP *includes* the target but prints nothing: the loaded array only surfaces if the exception
  **message** matches an array key. To *prove* the include, point at a real language pack (whose
  keys are the app's own messages), then point at config/interceptor files.
- `Lang::get` resolves dotted keys (`connections.*`) against the loaded array, so a message
  shaped like `section.key` can read nested config — but only if a code path throws a message
  you control. Hunt for one instead of assuming it exists.
- Calibrate `../` depth against a file you know exists; expect `open_basedir` to cap reach at the
  webroot plus `/tmp`.

## Operating discipline

- Long probes/sprays belong in **background** — foreground runs are capped (~600s) and long
  explicit timeouts are rejected outright.
- **Never let transport noise become a hit.** Filter `Failed sending data to the peer`, empty
  replies, DNS/connection errors and JSON parse failures out of hit detection, and re-verify
  every hit file before believing it. A file named `*_HIT` is a hypothesis, not a finding.
- Probe modules must be import-safe: module-level requests fire on import, so a test script that
  imports a helper can accidentally spray a target. Guard with `if __name__ == "__main__":`.
- Keep spray state (already-tried candidates) on disk so restarted batches do not re-spend
  lockout budget.
- Findings that leave the machine get credentials redacted to `[REDACTED]` — keep the technique,
  drop the plaintext.

## Known false positives to check before celebrating

- A "config leak" whose payload is only a DSN (`sqlsrv:Database=...;Server=...`) with no credential.
- Your own request parameters echoed back in a debug page, mistaken for server-side config.
- A SPA/debug console page returned with HTTP 200, mistaken for a successful exploit.
- A function *name* inside a source window read as an executed call site.
- **A command-substitution payload (`$(id)`, backticks, `${...}`) that your OWN shell expanded
  before the request left the machine.** It shows up in the target's business data looking exactly
  like RCE. Re-verify every injection through a non-shell HTTP client (`http.client`/`requests`) -
  the payload must land or echo back byte-for-byte. See `pentest-execution` ->
  `references/injection-payload-false-positive.md`.

## References

- `references/thinkphp6-trace-page.md` — TP6 trace page tabs/fields, forcing render, source
  windows, lang-param LFI chain, SQL-panel schema extraction.
- `references/thinkphp505-baota-invokefunction.md` — TP5.0.5 JSON `invokefunction` +
  `think\__include_file` 绕宝塔；4-arg `file_put_contents`；nginx 散落 php 404；微交易 otype=3 INSERT。
- `references/error-oracle-patterns.md` - transcript shapes for the line/length/differential
  oracles, plus hit-verification discipline.
- `references/source-disclosure-endpoint-fuzz.md` - `debug_<word>` source-leak fuzzer, word-list
  construction, real transcript, and the JSON type-juggling DB/parameterization oracle.

## Related

- `api-contract-mining` — mining the client bundle for the request signature scheme and the full
  route surface; the usual next step when a debug page exposes a middleware wall.
