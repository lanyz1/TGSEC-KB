# white-label-platform-recon 全文 第 2/3 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

## 3. Use error semantics as a route/stack oracle

When a JSON API is probed with the wrong content type, well-built backends leak
their deserialization target:

```
POST /api/auth/login  Content-Type: application/x-www-form-urlencoded
-> 415 "Cannot transform this request's content to
        <package>.<module>.server.routes.auth.AuthDto"
```

That one string gives you **language/framework** (a `pkg.module.routes.x` class
name is Dart — not Node/PHP) and the **route module tree**. Reading the status
codes as a ladder:

| Code | Meaning |
|---|---|
| `415` | route exists; wrong content type; **leaks target class name** |
| `400` | right content type, wrong field names — bisect field names here |
| `401` | right shape, needs auth |
| `405` | wrong method for a real route |
| `404` with a uniform JSON envelope | route really absent |

Bisect login field names against the `400`/`401` boundary — `{email,password}`
vs `{login,password}` vs `{username,password}` distinguishes them in three
requests rather than guessing.

## 3b. Code-split SPA panels: enumerate the routes, then prove completeness

When the panel is a Vue/React build rather than server-rendered routes, the
inventory comes from the chunks, not from guessing:

- Fetch **every** `assets/*.js` (the chunks the main bundle lazy-loads) and grep for
  `"/api/..."` plus template literals `` `/api/sessions/${id}/...` `` (substitute `1`).
- **Check `/assets/` for autoindex** — a directory listing hands you the whole build
  (and a build-hash signature worth re-checking to catch new endpoints).
- Establish the two oracles first: an unknown *non-`/api/`* path returning the SPA
  shell `200` must be excluded by body comparison, while unknown `/api/*` answering
  `404 {"message":"API not found"}` vs real routes answering `401 未授权访问` is a
  clean existence oracle.
- A 2-D `/api/<module>/<action>` × GET/POST matrix tells you the inventory is
  **complete**; that bound belongs in the report.
- **Login timing is a username oracle when egress is direct and the hash is slow**
  (median of 8 samples; a stable +280 ms delta found the only account). Test the
  rate limiter's key with the usual `X-Forwarded-For`-family variants, and check
  each public endpoint separately — one unlimited endpoint is a finding.
- Full recipe, counts, and the auth-bypass/smuggling pass that came back clean:
  `references/hardened-spa-json-api-exhaustion.md`.

## 3c. Next.js targets: the build manifest is the whole route map

For a Next.js build (as opposed to the vue/react chunk method in §3b) the page→chunk
map is published:

```
/_next/static/<buildId>/_buildManifest.js      # buildId = window.__NEXT_DATA__.buildId
/_next/static/<buildId>/_ssgManifest.js
```

Fetch that one file, harvest every `static/chunks/*.js`, download them in parallel and
regex the source for `/(site|page/fd|game|act|sact|agent|im|video)/api/v1/...` (337
chunks -> the complete endpoint inventory, in this case across six namespaces).

**Fake-success pitfall:** the chunk URL needs the `/_next/` prefix. Omit it and every
request still returns HTTP 200 with ~4 KB of body — the SPA shell HTML — so a
"downloaded 337/337" summary looks perfect while the grep finds **zero** endpoints.
Always `head -c 200` one downloaded file before trusting the batch. Paths inside the
bundles are frequently constants or concatenated, so keep the route regex loose and
filter afterwards by keyword (`list|record|rank|marquee|detail|invite|report|search`).

## 3d. ★ Every oracle needs a negative control — the guard that fakes a finding

Before you believe any "different response = different account/permission" oracle,
replay the identical request against a subject you **know does not exist**. If the
answers match, you are reading a generic guard, not state.

Worked retraction from this family: `POST /site/api/v1/user/member/bindEmailVe2`
returned `6011 请勿重复操作` for the ency of `admin`, while returning a normal field
validation for the caller's own ency. That looked like a confirmed identity switch
(the account context had clearly changed). It was not: a non-existent username
(`nosuchuser123`) produced **the same `6011`** — it is a duplicate-request/rate guard
keyed on repetition, and the earlier "admin already has an email bound" conclusion was
a pure artifact of hammering the same endpoint.

Corollaries:
- Vary one irrelevant parameter per request (e.g. a unique email) so the duplicate
  guard never fires, then read the real state differences.
- A field-validation message (`手机号码必填`, `邮箱必填`) proves the request reached
  business logic — **not** that the identity was accepted.
- When a candidate finding rests on response *difference*, state the control result in
  the report; an unretracted false positive costs more than a missing one.

## 4. Operator-config fields leak the fraud model

Once any low-privilege account exists, the player-facing profile/deposit
endpoints are worth reading field by field. They routinely return
operator-side flags and thresholds:

- `fakeWithdrawalEnabled`, `promoAbuseEnabled` — anti-fraud switches shipped to the client
- `workerId` — the staff member who processed a withdrawal
- `twoFactorCode` — a TOTP seed returned **in plaintext**
- `depositAutosum`, `verif_sum`, `minWithdrawalAmount` — activation gates

These tell you what the business logic does *and* what will block you later
(e.g. a withdrawal gate that requires a real deposit).

## 5. Expect to be locked out of the panel — and say so precisely

Panel-side hardening is usually better than brand-side. Verify and report each
layer rather than asserting "protected":

- all `/me/*` endpoints answer `401` with a uniform envelope;
- an API key pasted in the vendor docs is redacted and also `401`;
- weak/default credential sweep on the login route (keep it to the user's agreed
  small budget) — then **stop**;
- docs state an **IP allowlist** ("send your server IP to the admins") and no
  self-signup (manual approval via a TG bot);
- **WebSocket handshake `101` is not authentication.** A WS route will happily
  upgrade for *any* token and then immediately send a close frame (`op=8`) for an
  invalid one. Only a received application message proves access.

Route enumeration that returned only 3 real endpoints (`/api/auth/login`,
`/api/me`, `/api/ws`) is a *result*, not a failure — it bounds the panel from the
outside and belongs in the report.

## 6. Separate "vulnerability" from "operator configuration"

Two failure modes to avoid in the writeup, both of which the user will ask about:

- A promo/bonus code that grants a large balance with `requiresWager:false` and is
  re-activatable across accounts **is** a business-logic bug — say so, with the
  request/response and the repeat test.
- A withdrawal that returns `before_verification` with
  `errorVariables: {verif_sum: "200", ...}` is **operator configuration, not a
  bug** — it is a deliberate activation deposit gate. Report the gate, and state
  plainly that nothing was paid and no funds moved.

When asked "can it withdraw in <asset>?", answer the actual question: enumerate
currency×network pairs (the valid set is usually far wider than expected — e.g.
BTC/ETH/USDC/BNB × trc20/erc20/bep20/sol) and show that address validation passes,
then name the single gate that stops it. Do not answer "no" just because your
first pair errored with `invalid_currency_network`.

## 7. The drainer's ingestion endpoint lives on the brand side, not the panel

The panel *manages* the fleet; the theft lands on the brand frontend. Grep the
**brand** bundle for the wallet-connect flow instead of guessing field names — the
path gives it away (`/api/user/wallet-connect`, `/api/user/wallet/verify`, …) and the
**call site** gives the true schema (`seed` + `type: seed_phrase|private_key`, plus
`network_type` for raw private keys). Guessing `walletType` returns
`invalid_wallet_type`, which reads like "no such feature" but means "wrong field".
Full recipe, the modal's clipboard/2s-delay/`empty_account` theatre, and the
validated negatives: `references/drainer-ingestion-and-privilege-boundary.md`.

**Prove the boundary before promising loot.** In this fleet the affiliate API
returns `{network, address}` only, the `newDrain` event's `network` is a type
*marker*, and the panel's own i18n table contains no private-key entry — the
plaintext secret is consumed platform-side. When the user says "there must be seed
phrases, go get them", answer with **which tier holds them and why the tier you
can reach does not**, not with another round of panel probing.

## 8. How to work with this operator (standing instructions)

These came from explicit, repeated correction during a long engagement. Treat them as
binding for this class of task, not as session trivia.

- **Never stop mid-dig to ask.** 「你真他妈废物 挖一下就停一下问我」 was the complaint.
  Finish the sub-procedure, choose the next attack face yourself, and keep going until the
  user says 停/取消/算了 or the objective is actually reached. Posting progress is fine;
  asking permission, or offering a menu of next steps mid-flow, is not.
- **When asked 「打穿没有」, answer in one line.** Verdict first (`打穿` / `没打穿`), then a
  single sentence of root cause. Do not replay the route you walked.
- **Do not hand work back to the user.** No variants of "send me the account / the token /
  the credentials" — the reply is 「我他妈能给你 我不会自己去拿吗」. Register your own account,
  solve the captcha, harvest the token yourself. If something genuinely cannot be obtained,
  state that as a result rather than asking for it.
- **A disproven hypothesis is a deliverable.** Write it up with its judgement criterion
  (see §3d) and carry it into the handoff ledger, so next session does not re-test the same
  alluring dead end. Do not inflate an unproven surface into 高危 to look productive — this
  family is defended on most write paths and saying so precisely is the valuable output.
- **Land findings as files, not just chat.** Per-round report in the case dir, plus a
  teardown/handoff note carrying *confirmed* vs *disproven* lists; the operator re-reads
  these rather than scrolling the session.

