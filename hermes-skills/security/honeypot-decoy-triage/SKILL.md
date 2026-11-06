---
name: honeypot-decoy-triage
description: "Use when targets expose bait creds or honeytoken files."
version: 1.0.0
revision_date: 2026-10-18
category: security
tags: [honeypot, decoy, credentials, false-positive, triage]
---

# Honeypot & Decoy Triage

A credential file that is *too easy* is not a win. It may be a planted decoy whose
only purpose is to identify you, burn the engagement, or waste your time on a fake
admin plane. Treat every unsolicited credential as hostile until it survives a
cross-source consistency check.

**Core rule: never authenticate with, write to, or exfiltrate from a suspected decoy.**
Discovery is read-only. Classify first, pivot second.

## When to Use

- A web root exposes `/.env`, `/.git/config`, logs, backups, or “leaked” credentials.
- An admin panel returns credentials, upload successes, or hidden routes that look
  suspiciously convenient.
- The same credential appears in several files with the same prefix or wording.
- A vendor/FOFA result points to a management console you cannot normally reach.
- Before using any credential found in a target's own files.

## Decoy Signals

| Signal | What It Suggests | Check |
|---|---|---|
| `.env` contains “honeypot”, “decoy”, “fake”, or a `honeytoken` remote | Planted bait | Do not use; preserve a redacted sample |
| `.git/config` exists but `.git/HEAD`, `.git/index`, `.git/refs/*`, `.git/objects/*` are 404 | Fake repository, not a source leak | Fetch the missing objects; if absent, treat config as bait |
| Log entries contain credentials that match the `.env` values | Fabricated leak chain | Compare timestamps with your own requests |
| Credentials all carry the same artificial prefix (`Hp...`, `test_...`) | Generated bait | Do not spray; record as decoy |
| Admin menu is real but most routes return the same byte-identical shell | Catch-all dashboard, not hidden features | Compare body length/hash across routes |
| Upload returns `{"success":true,"path":"..."}` but the path is fixed and not web-accessible | Mock upload handler | Re-request with a different harmless filename/content type; check the returned path |
| “Domain For Sale” / parking page on a newly resolved IP | Old DNS or unrelated asset | Do not pivot; stop that branch |
| A leaked DB password produces `using password: YES` but every real attempt fails | User exists, password is bait or stale | Do not expand the dictionary; check repo history/config consistency |

A single signal is not proof. Three independent signals (e.g. `.env` wording +
`honeytoken` remote + log entries matching your actions) justify a **decoy** label.

## Procedure

### 1. Freeze before use

- Do not paste the credential into any login form, DB client, SMTP client, or API.
- Record only a redacted fingerprint (source, field name, length, prefix) in the case file.
- Preserve the raw response hash/body in the evidence directory if scope permits.

### 2. Inventory all leak sources

Compare values across:

- `.env`, `.env.*`, config files, backups, `composer.json`, `.git/config`
- application logs, web server logs, CI logs
- admin UI “settings” pages and exported files

Ask: are the values identical, or does the same artificial prefix recur? Are the
log lines timestamped around your own probing? A real leak is usually inconsistent
and partial; a decoy is often complete and too neat.

### 3. Test artifact completeness

- `.git`: only a `config` file is not a repository. Check `HEAD`, `index`,
  `refs/heads/*`, `objects/*`; if they are all 404, classify as fake.
- `.env`: check whether the file explicitly says it is a decoy, and whether the
  application actually uses those values (compare config/runtime behavior).
- Logs: check whether entries exist before your first request. If the “leak” only
  appears after you start testing, it is likely planted or app-generated bait.

### 4. Confirm mock vs real endpoint

Before treating an upload/save endpoint as a write primitive:

1. Send a harmless unique marker; record the response.
2. Change only the filename/content type, not the content class.
3. Fetch the returned path from the web root.
4. If the path is fixed (`products/up.jpg`) and the file is not retrievable, call it
   **mock**, not an upload vulnerability.

Do not overwrite a real template to “prove” it. A mock endpoint will not prove RCE.

### 5. Classify and pivot

- **Real credential**: works against the intended service and is consistent across
  at least two independent sources; still use the minimum possible access.
- **Decoy**: any three signals above; do not use, do not report as a leak, pivot.
- **Stale/old credential**: service gone or password rotated; record as stale, stop.
- **Mock endpoint**: response is canned; record as a non-finding and move on.

Pivot to real attack surface: actual admin routes discovered from the app's menu/JS,
origin IPs from certificate/FOFA pivots, and reachable management APIs. Do not spend
more requests “confirming” the decoy.

## Pitfalls

- **200 on `/.env` is not a leak.** It may be an intentional decoy; read the content
  before celebrating.
- **A `.git/config` alone is not source code.** Missing object store = no repository.
- **A log line can be planted.** Do not trust “SQLSTATE” or a DB password just because
  it appears in `laravel.log`.
- **`success: true` is not a write.** Check the returned path and fetch it.
- **A byte-identical catch-all is not a hidden admin feature.** Hash the body across
  routes; a real page has distinct content and state.
- **Do not use decoy credentials to “test” them.** That is exactly the alert the
  decoy exists to trigger; it also contaminates the case.
- **Do not report the decoy's contents.** Report the decoy mechanism and the real
  surface you pivoted to, with credentials redacted.

## Verification

- Decoy classification is supported by at least three independent signals.
- No login, DB connection, SMTP send, or write was performed with the suspect value.
- The mock endpoint was tested with a harmless marker and a second filename variant.
- The case file contains redacted evidence and a clear “do not use” note.

## References

- `references/aime-honeypot-case.md` — sanitized field example of a Laravel admin
  with a planted `.env`, `honeytoken` remote, fabricated log credentials, and a
  mock upload handler.
