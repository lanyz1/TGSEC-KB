# Error-oracle patterns — transcript shapes

Concrete shapes for turning framework/application errors into information. Values are
illustrative; treat any real credential as `[REDACTED]`.

## 1. Line-number enumeration (identical messages)

```
POST /adminapi/login  {"username":"admin"}       -> {"code":1055,"msg":"account or password error","data":{"file":".../SystemAdminServices.php","line":612}}
POST /adminapi/login  {"username":"some_other"}  -> {"code":1055,"msg":"account or password error","data":{"file":".../SystemAdminServices.php","line":600}}
```

Same `msg`, different `line` → 612 = exists / wrong password, 600 = does not exist. Build the
candidate list from the client bundle, docs and brand names; a hit proves the account exists even
when the product refuses to say so.

## 2. Length wall

```
len(pwd) <= 120  -> line 612 (hash compared)
len(pwd) >= 126  -> line 608 (length guard)
```

Bisect the boundary with 2–3 requests before mass-submitting. A length wall usually means the
plaintext is RSA-encrypted or HMAC'd before compare — switch the candidate *encoding* (raw
`NoPadding` RSA vs PKCS#1, base64 vs hex) instead of growing the wordlist.

## 3. Encoding mismatch looks exactly like a wrong password

If a client bundle calls something like `encryptionPassword(pwd)` before submit, a correct password
sent unencrypted is indistinguishable from a bad one. Reproduce the client transform (reuse the
bundle's own crypto lib in Node, or port it) before concluding a credential is bad.

## 4. Route existence vs authorization

```
GET /agentapi/agent/teamlist (valid signature)      -> HTTP 404, empty body            # no such route
GET /channelapi/system/...   (valid signature)      -> "cannot identify request origin" # route exists, origin wall
GET /channelapi/package/getPackageList (signed)     -> {"success":true,"data":[]}        # open endpoint, no data
```

Always capture the **status line and headers** when a signed request returns "empty" — empty is
often a 404, not an auth failure, and the two demand opposite next moves.

## 5. Hit verification discipline

A background spray that writes a hit file on *any* anomaly produces false positives. Real example:
two "admin password found" files contained
`{"code":1055,"msg":"Failed sending data to the peer"}` — a transport error, not a login.

Rules:

- Whitelist success criteria (expected success field/status), never "anything unusual".
- Explicitly filter transport noise: `Failed sending`, `Couldn't resolve`, `Connection timed`,
  `Empty reply`, `timed out`, JSON parse errors, intermediary 5xx.
- Re-verify each hit with a fresh single request before reporting; archive retracted ones as
  `*.FALSE_<candidate>.txt` so nobody re-reports them.
- Judge a spray by its *hit rate over completed units*, not by wall-clock time (connections that
  complete per second reveal whether the list is even being consumed).

## 6. False-positive leak shapes

- `DSN only` — a config "hit" containing `sqlsrv:Database=...;Server=...` but no user/password.
- `echo` — the debug page reflecting your own request parameters, looking like server config.
- `SPA/debug console` — an HTTP 200 page that is just a client-side debug view.
- `string in source` — a function *name* inside a source window misread as an executed call site.
