---
name: blackbox-api-surface-recovery
description: "Use when a black-box JSON API hides endpoints or fields."
version: 1.0.0
tags: [pentest, api, fuzzing, parameter-discovery, error-oracle, middleware]
---

# Black-box JSON API surface recovery

Load when you hold a live JSON API with no docs and no usable client: every error is generic
(`参数错误`, `invalid params`, `请升级APP到最新版本`, `token不能为空`), the SPA bundle exposes one
call, and the APK is unavailable. The way in is not a bigger wordlist — it is treating the server's
own error strings as a schema oracle.

## 0. Ground rules

- **Everything answers HTTP 200.** Filter and decide on body strings, never on status codes.
- **Send the real client's header set on every probe.** Missing one envelope header makes every
  path answer the middleware error and looks like a broken target.
- **Probe with your own freshly registered fixture account.** It keeps every request authorized and
  makes a destructive slip impossible. Never explore write fields against a real user's object.

## 1. Recover the transport envelope first

- A blanket "upgrade the app" / "客户端版本过低" is usually a **presence** check on a version
  header, not a comparison. Enumerate custom header names against a known-good endpoint
  (`X-App-Version`, `app-version`, `version`, `platform`, `X-Client-*`, `token`); any parseable
  value (`9.9.9`) commonly passes.
- **A uniform error on EVERY path is a global filter, not a route verdict.** If a nonexistent path
  also answers `token不能为空` / `未授权`, the filter runs before route matching. Send a
  syntactically valid token: the same path must flip to the route-not-found code before you trust
  any auth error. Concluding "the admin module exists" from a pre-routing filter wastes hours.

## 2. Find endpoints inside the whitelisted namespace

- Only one prefix is exempt from auth (e.g. `/api/index/*`); every other prefix answers the
  middleware error for both real and fake paths. Enumerate under the exempt prefix only.
- Enumerate with ffuf using `-fr '<not-found msg>|<middleware msg>'`, **not `-fs <size>`** — error
  bodies differ by a few bytes between routes, so size filtering either misses hits or drowns you.
- POST with a literal `{}` body; a route that exists but needs params answers with a distinct
  message, which is the hit.

## 3. Field-name recovery: the error ladder

- Post `{}`. The message names the next missing field in the server's own vocabulary
  (`请输入姓名`, `请输入正确的身份证号`, `请输入邀请码`).
- Add ONE plausible key and re-post. The message advancing to the *next* requirement proves the key
  was consumed.
- If the message does **not** advance, the key is either unknown to the server or its value was
  rejected — resolve that ambiguity before adding more keys (see §5).
- When the next field's *key name* is unknown, do not iterate candidates one at a time.

## 4. All-keys + bisect — the fast path

1. Build the candidate set: English, pinyin, abbreviations, casing variants (`inviteCode`,
   `invite_code`, `yqCode`, `sharecode`, `pid`, `tjCode`, …).
2. Send **all** candidates at once, each with a syntactically valid value.
3. If the "missing" message disappears, the key is somewhere in the set.
4. **Binary search the set**: send half; whichever half keeps the message away contains it.
   O(log n) requests — 512 keys in 9 probes instead of 512.
5. **Expect lowercase.** The recovered tag is often `sharecode`, not `inviteCode`; the camelCase
   form the UI implies can be ignored by the binding layer entirely.

`scripts/keyname_bisect.py` implements steps 2–4 (and falls back to linear scan when a key only
works alongside a partner key).

## 5. Type and value gates

- Same key, different JSON types: string / int / array / object / null. A hard 500/panic where the
  other types return the friendly error means the key WAS parsed and only the type was wrong —
  that is a name confirmation even when no value succeeds.
- A format gate is separate from a presence gate. ID-card fields validate a checksum, phone fields
  validate a prefix. Generate format-valid fixtures (18-digit CN ID with correct checksum, a
  country-plausible mobile) or you will read "field missing" forever while the server is actually
  rejecting the value.
- **Invite/referral codes are usually checked for existence, not ownership.** Any existing user's
  `sharecode` — including your own fixture account's — passes. Get one valid code, then reuse it for
  every fixture registration instead of enumerating the code space.
- Uniqueness checks are oracles too: a "this ID is already registered" response confirms the value
  reached the query, and a fresh format-valid value that also gets rejected means the check is
  broken/global rather than per-record — stop treating it as a duplicate signal.
- Acceptance at one endpoint does not transfer: a field the register endpoint takes may be
  re-validated (real-name verification) at the action endpoint that matters.

## 6. Adjacent oracle: existence by timing

When the string oracle collapses ("账号或密码错误" for both unknown user and wrong password), the
password hash still separates them. Measure 3× per candidate against a random-name baseline: an
existing user costs one bcrypt verify (~50–100 ms) more. Treat a clean gap as a username oracle;
treat noise as noise and do not build a spray on it.

## 7. Persist as you go

- Write the full success response to disk, never only stdout: tokens and ids get truncated in tool
  output, and `uid`/`sharecode`/balance fields are the pivot for every later step. **The truncation
  may be your own tooling's secret redaction, not the server's** — a JWT displayed as `eyJhbG...iubo`
  can be complete in the saved file. Print `len()` and base64-decode the three segments from the file
  before concluding "the server masks tokens"; a redacted display mistaken for server behaviour sends
  the next hour down the wrong path.
- Record each recovered endpoint as a row — method, required keys, types, the exact error string
  that identified it. The next session inherits none of this context.

## Pitfalls

- **Your own loop cap is silent data truncation.** A `while pages < N` enumerator returns a round
  number and looks complete; log the last item and re-run with a bigger cap or per-prefix queries
  before quoting the count as the total.
- Don't report "route exists" from `token不能为空`; see §1.
- Don't treat "field accepted" as "value valid"; identical strings often cover both.
- Don't spend a spray on a version middleware — solve it with a header, not with requests.
