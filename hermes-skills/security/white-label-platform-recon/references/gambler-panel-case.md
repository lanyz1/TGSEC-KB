# GAMBLER PANEL — worked example (2026-09)

White-label crypto-casino SaaS. One brand (`nezawin.com`, registered 3 days
before testing) turned into the whole fleet: ~412 domains sharing a signature
(27 live / 249 dead / 222 unique IPs) per third-party threat intel, one shared
origin, one operator panel, one image CDN, one public docs site.

## Discovered API surface (from the frontend config object)

```js
{ wsLink: "/api/ws", api: "/api",
  localApi: IS_DOCKER ? "http://host.docker.internal:80/api" : "http://localhost:3001",
  paymentsApi: "/payser", slotsApi: "/api/slots",
  picturesApi: e => `https://pictures-cdn.is/${e.replace(/^\//,"")}` }
```

Note `/payser` — a real API prefix outside `/api/`. Frontend route list also
leaked: `/profile/bonuses`, `/profile/deposit`, `/profile/withdraw`,
`/profile/verification`, `/vip`, `/payser`, `/slots/slot`.

## Player-side endpoints worth knowing

| Endpoint | Note |
|---|---|
| `POST /api/auth/register` `{email,password,promocode?}` | per-IP `multi_account_detected` — bypassable by rotating exits |
| `POST /api/auth/login` `{email,password}` | error split is an account-existence oracle: `invalid_password` (<8 chars, length check), `wrong_password` (exists), `invalid_email` (absent) |
| `GET /api/user/profile` | 39 fields incl. `twoFactorCode` plaintext, `fakeWithdrawalEnabled`, `promoAbuseEnabled`, `banned`, `regIp`, `rakebackPercent`, `vipStatus`, `referralCode` |
| `POST /api/user/promo/activate` `{promo}` | `BONUS` granted `{amount:"2700.00",requiresWager:false,type:"BALANCE"}`; re-claimable on a fresh account |
| `GET /api/user/kyc` / `POST /api/user/kyc/submit` | plain-text `{firstName,lastName,countryCode,dateOfBirth}` → `SUBMITTED` → ~35 s later `APPROVED`; no document, no face, no third party |
| `POST /api/user/2fa/enable` `{code}` | works with a TOTP derived from the plaintext `twoFactorCode` |
| `GET /api/user/deposit/settings` | operator payment config: `paymentMode`, region policy, provider priority, 17 disabled providers, `depositAutosum:"200"` |
| `POST /api/user/payment/create` | `checkoutMode` `direct` is the only valid value; per-provider rate limit → `429` |
| `POST /api/user/withdrawal` | see gate below |
| `GET /api/extra/postback` | unauthorised but empty (partner postback config) |
| `GET /api/user/payment` | unauthenticated payment landing page; params echo into a `payload` literal |

Withdrawal gate (the blocker):

```json
{"status":"canceled","errorCode":1,"titleKey":"before_verification",
 "amount":"2700.00",
 "errorVariables":{"sum_afterverif":"2700.00","verif_sum":"200",
                   "verif_need_lvl":"Bronze","verif_need_xp":"200"}}
```

Valid currency×network pairs found by enumeration: `usdt`×`trc20|erc20|bep20`,
`usdc`×`erc20|bep20|sol`, `eth`×`erc20`, `btc`×`btc`, `bnb`×`bep20`, `sol`×`sol`.
Address validation passes with a real address; `method` must be `crypto`.

## Route/stack oracle in action

```
POST /api/auth/login  (form-encoded)
-> 415 "Cannot transform this request's content to
        gambler.gambcode.me.server.routes.auth.AuthDto"
```

→ Dart backend (`pkg.module.server.routes.<module>` naming), and the vendor's own
namespace `gambcode.me` from which the product is developed. 488-path enumeration
through this oracle + a standard wordlist yielded exactly three live routes:
`/api/auth/login`, `/api/me`, `/api/ws`.

## Operator panel

- Panel front door: `/auth/login` (all panel routes `307` there when unauthenticated:
  `/users`, `/stats`, `/deposits`, `/wallets`, `/offers`, `/networks`, `/campaigns`,
  `/traffic`, `/support`, `/settings`).
- `GET /api/me` → `401 {"success":false,"error":"Unauthorized"}`.
- All `/me/*` → `401`; the API key shown in the vendor docs is redacted and also `401`.
- Login fields are `{login,password}`; 18 default/weak pairs → `Invalid login or password`.
- Docs state: send your server IP to the admins (**IP allowlist**) and using
  undocumented endpoints gets you banned.

## WebSocket

Docs: `wss://<panel>/api/ws?token=Worker <authToken>&connectionType=bot`,
ping every 5 s, reply `{"name":"pong"}`.

Observed: handshake returns **`101 Switching Protocols` for every token,
including nonsense**, and the server then sends a close frame (`op=8`)
immediately. Authentication happens after upgrade — 101 is not access.

Documented events (the fraud model, verbatim shapes):

```js
newDeposit { id, mammothId, mammothLogin, mammothCountry, mammothPromo, token,
             amount, amountUsd, workerPercent: 60, domain, txHash }

newDrain   { info: { mammothId, mammothPromo, domain,
                     network: "private key" | "phrase" },
             balances: [{ token, usd }] }

newMessage { id, mammothId, text | picture, side: "mammoth" | "worker",
             login, country, domain, promo, createdAt }
```

Vocabulary: `mammoth` = victim, `worker` = affiliate/promoter (60% cut),
`drain` = emptying the victim's wallet across chains.

## Documented panel API (all require `Authorization:` + IP allowlist)

```
GET|POST|PATCH|DELETE /me/promo            promo CRUD { name, amount, shouldWager }
GET  /me/domains                           domain list
POST /me/domains                           { webVersion, domain, template, pixelId }
POST /me/domains/verify
POST /me/domains/template                  landing template switch
POST /me/domains/geoblock                  { domain, countries[] }   -- jurisdiction evasion
POST /me/domains/ai                        { domain, useAI }         -- AI live support
POST /me/domains/regpage                   { domain, value: RegPage }
GET  /api/me/extra/crash                   { startsAt, multiplier }  -- next-round prediction
GET  /api/me/mammoths/:id/txs/wallets      [{ network, address }]    -- victim wallets
```

Landing template vocabulary (280+) spans celebrity impersonation
(`donald_trump`, `elon_musk`, `drake`, `messi`, `kylie_jenner`, `xqc`),
adult lures (`naked_1..33`, `gay_1..4`, `trans_1..9`, `brazzers`), and slot/game
graphics. The `crash` prediction endpoint directly contradicts the brand's public
"Provably Fair Games" tagline.

## External corroboration

- Registrar `Trustname.com / Fewmoretaps OU` — named in public research as a
  "bulletproof" registrar serving scam casinos; matches the brand's whois.
- Threat-intel network pages grouped ~412 domains under one signature, headed
  "Crypto Casino Verification Deposit Scams" (i.e. the deposit-to-unlock-winnings trap).
- On-page contact channels: `t.me/<brand>_info`, `t.me/<brand>_panel_bot`,
  `t.me/<brand>workmain`.
- Sibling brands on the same origin answered differently to the same request
  (`200` for the tested brand, `666`/`403` for others) — one shared box, many brands.
