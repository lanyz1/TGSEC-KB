<!-- archived from /root/.hermes/skills/security/deployed-webapp-nday-hunting/SKILL.md on 2026-10-21 -->

---
name: deployed-webapp-nday-hunting
description: Use when attacking a self-hosted web app or panel.
---

> 归档卡：原目录 `/root/.hermes/skills/security/deployed-webapp-nday-hunting`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/deployed-webapp-nday-hunting/…')`，不要相对 `references/legacy/` 解析。

# Deployed web app: client recon -> version pin -> upstream diff

Use this on any branded self-hosted panel (mail, admin console, shop, chat backend) whose
upstream source may be public. Pinning the exact upstream release turns a black-box target
into a white-box one; that is almost always faster than guessing payloads.

## 1. Harvest the API surface from the client build, not from guesses

The client ships the whole backend contract. Get it before probing anything.

- **Flutter web** (page loads `main.dart.js`, multi-MB, `<title>` is often the app name):
  - `grep -oE '[a-z]+Api/[A-Za-z]+' main.dart.js` lists the endpoint families.
  - Find the base-URL selector: usually a small `switch` over a "network mode" enum that
    returns the same host for most modes and a CDN config URL for the last one. That host is
    the real API host and is frequently **different from the site you were given, and not
    behind the same WAF**.
  - Disassembled Dart keeps request bodies legible. Just before the request builder sits the
    literal map with field names and enum values as strings, e.g.
    `A.u(["userName",p.e,"code",p.Q,"type","2","serverId",p.fy],...)`. Recover login/OTP/
    reset bodies from here instead of guessing field names.
- **JS bundles**: grep for `"/api/`, `url:`, and the axios/fetch interceptor. The interceptor
  shows how auth is attached and whether a second token is required.
- **APK**: unzip, run `strings` plus a decompiler over the Retrofit/OkHttp interface for the
  full endpoint list, including endpoints the web client never calls. If strings are
  obfuscated by a local helper, recover the helper's key and re-run the decode.

From here on keep **two** request paths for every endpoint: the public/front host, and the
origin IP with an explicit `Host:` header. They routinely enforce different rules.

## 2. Pin the deployed version

1. Identify the upstream project from unique strings, static asset filename hashes, error
   text, or a repo link left in a bundle.
2. `git clone --depth 1 <upstream> && git fetch --unshallow --tags`.
3. Build a fingerprint table across tags over files that are both security-relevant and
   observable: the auth/permission middleware, route registration files, the config-response
   builder.
4. Probe the live host for version-distinguishing behaviour instead of trusting headers: a
   route that only exists in newer tags returns 404; a route renamed in release X still
   answers on its old name; a permission entry added in release Y is still missing so the
   endpoint still returns data. A handful of probes pins the tag.

## 3. Diff the deployed tag against the newest tag

`git diff <deployed_tag> <latest_tag> -- <server_src>`, then read every hunk of the auth
middleware and the route list. Recurring bug classes:

- Route registered but absent from the permission map -> free for any authenticated user.
- Route whitelisted out of auth by prefix, then guarded by a *second* comparison a few lines
  later (a token/secret compare). **Read the middleware top to bottom — "excluded" does not
  mean "open".**
- Permission->route maps keyed by literal path: a renamed route leaves the old key in the map
  and the new path unchecked.
- A permission list shorter than the route list. The delta is your attack surface.

## 4. Convert validation ordering into oracles

Send the request with everything blank, then add one field per round trip and collect the
missing-field messages. The order and wording tell you what the server already knows:

- An identity/privilege check that fires **before** the record lookup is an identity oracle.
  Iterate candidates and watch for the response flipping from "not privileged" to
  "record not found" or "wrong value".
- Three-state answers (no record / record present but value wrong / value correct) narrow a
  search far more than any wordlist. Build the oracle before brute-forcing anything.

## 5. Defaults, bootstrap routes, shipped config

- Read the repo's dev/test config file and any `[vars]` / `.env.example`. Operators copy
  them. Test the shipped default `jwt_secret`, admin identity, encryption key and API key
  against the live deployment **before** spending time on brute force.
- Docs that tell operators to randomise a secret are telling you the default is known.
- `/init`-style bootstrap routes are unauthenticated by design and often guarded by nothing
  but a secret you can now test directly.

## 6. Storage-write primitives

Any handler that takes a list of objects straight from the request body into an object store
or KV bucket is a candidate arbitrary-write primitive. Read the storage helper before
counting on it: when the key is re-derived as `prefix + content_hash + extension`, the
extension is still caller-controlled but the prefix normally blocks escaping into unrelated
keys. Confirm the derivation, then move on.

## Pitfalls

- Never conclude "this deployment has no admin" from a failed guess. A missing env var and a
  wrong guess look identical — build the Step 4 oracle and let it decide.
- A `403` from the edge and a `403` from the app are different findings. Check the body (WAF
  block pages carry their own template), then separate "the edge blocked me" from "the app
  refused me". If the edge is IP-based, a different egress gives a clean second opinion on
  the identical request.
- Hammering one endpoint escalates into a platform-wide rate limit that poisons every later
  probe on that egress. Keep probes serial and slow; use concurrency only on endpoints
  already proven to tolerate it.
- After an IP cooldown the same request frequently just works. Retry once before declaring a
  dead end.
- Field names are not their JSON spelling. Enumerate `snake_case`, `camelCase` and
  `PascalCase` for every token/device field and send a superset in one request, instead of
  one guess per round trip.
- Tokens are host-scoped and time-scoped: a token accepted at the origin may be rejected at
  the front host, and a token that worked days ago is often expired now. Re-validate any
  stored token before building a chain on it.
- Re-login flows spend the token: a session token consumed by one call reads as
  "expired or reused" on the next. Re-mint immediately before each attempt.

## Supporting files

- `references/cloud-mail-pangu-mail.md` — worked example on a Cloudflare Workers + D1 + KV
  mail panel: how the version was pinned, the permission gaps found by tag diff, the admin
  identity oracle, and the storage-write analysis.
- `references/otp-login-recipe-replay.md` — replaying an app's OTP login: exact body fields,
  delivery-channel selection, per-shard pitfalls.
