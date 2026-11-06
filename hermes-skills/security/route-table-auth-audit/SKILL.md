---
name: route-table-auth-audit
description: "Use when app source is available: audit its route table."
---

# Route-Table Auth Audit (whitebox)

Source in hand beats guessing. One read of the route-registration file replaces an entire
directory-enumeration phase, and it is the only way to answer "have we exhausted this?"
with evidence instead of vibes.

Full recipe: `references/audit-recipe.md`

## When to run this

- Upstream/framework source is available (public repo, `.git` leak, deployment bundle).
- Blackbox enumeration has stalled and you need to know what you have *not* tried yet.
- Someone asks whether the target is "fully covered" / "打通了没" / "are all methods exhausted".

## Standing rules

**1. Registration order IS the auth boundary.** Routes registered before the
`Group()`/`app.use()` that attaches auth middleware are unauthenticated. Read the order,
not the intent — a handler named `admin.*` sitting above the auth group is public.

**2. Copy the real method+path from source; never guess it.** A handler registered as
`user.PUT("", UpdateProfile)` under `Group("/user")` at root `/api/v1` answers on
`PUT /api/v1/user`. Guessing `PUT /api/v1/user/profile` returns 404.
**Treat every 404 as a wrong guess, never as "feature does not exist."** Concluding
"no vulnerability" from a 404 on a guessed path silently deletes a live attack surface.

**3. One layer past the route, read the key source.** Follow handler → service to find
where the signing secret comes from. That converts guesses into verdicts:

| Key source | Verdict |
|---|---|
| `crypto/rand` at boot | Information-theoretic dead end — do not run hash cracking |
| Env var, no default | Unforgeable without leak |
| Env var with default / settings row | **Go find the leak** — this is the live path |
| `subtle.ConstantTimeCompare`, no empty-skip | Signature compare itself has no bypass |
| AES-GCM / HMAC capability token w/ purpose prefix | Unforgeable without the key |

**4. Record the 判据, not just the verdict.** Every ruled-out path needs its code
location, key source, or config switch (`OAUTH_DISABLED`) recorded, so the next session
does not re-run it. A dead end without a citation is indistinguishable from a gap.

**5. Distinguish "feature closed" from "attack not found."** A route returning
`OAUTH_DISABLED` is a configuration fact; a route returning 404 on a guessed path is
your own error. They must never be filed under the same heading.

## Deliverable

A three-column table — route / auth owner / conclusion — plus a separate group of
"blocked pending new input" entries, each naming exactly what input is needed (a
credential, a freshly-created object because old ones expired, a config value).
That table *is* the answer to "is this exhausted?", so build it as you go, not at the end.

## Pitfalls

- **Guessed paths produce false negatives.** See rule 2. This is the single most expensive
  mistake in this workflow — it silently converts an untested surface into a closed one.
- **Expired objects masquerade as missing features.** Payment/order lookups commonly purge
  after a short TTL, so testing a historical ID returns "not found" and looks like a
  closed endpoint. Create a fresh object and retest before concluding anything.
- **A `200` on a guessed path is not proof of the vulnerability.** Confirm the response
  actually carries the other party's data before writing it up.
- **Credential and existence oracles are different severities.** "This ID exists and is
  paid" and "this ID's amount and owner" are not one finding. Report them separately.
- **Prove IDOR against objects you own first.** Establish the 200 baseline with your own
  expired record and the 404 control with a random value, then reason about reach — do not
  use a third party's identifier as the test.
- **One key is often reused across purposes.** If the same `encryptionKey` signs an
  AES-GCM token in one place and an HMAC token elsewhere, leaking either breaks both —
  note the reuse when ruling a path dead, since it changes the priority of hunting it.
