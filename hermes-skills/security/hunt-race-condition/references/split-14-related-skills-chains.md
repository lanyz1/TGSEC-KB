## Related Skills & Chains

- **`hunt-business-logic`** — Race conditions are the "concurrency arm" of every business-logic state machine. Chain primitive: business logic (coupon/promo) + race-condition single-packet attack → coupon redeemed N times → direct financial loss.
- **`hunt-mfa-bypass`** — OTP-expiry windows and replay protection are classic race targets. Chain primitive: race + MFA-validate endpoint → bypass OTP expiry by submitting N concurrent validations within the validity window.
- **`hunt-ato`** — Race conditions on password reset, email change, and account creation enable persistent ATO. Chain primitive: race on email-change endpoint + atomic-update missing → swap victim email + read reset token before user notice.
- **`hunt-api-misconfig`** — Wallet/balance/credit endpoints without atomic UPDATE are double-spend candidates. Chain primitive: race + atomic-update missing → double-spend balance → withdraw N× user balance.
- **`security-arsenal`** — Load the Turbo Intruder single-packet template, h2.cl smuggling for atomic submit, and `curl --next` parallel multi-request patterns.
- **`triage-validation`** — Apply the Statistical-Sampling gate: a single anomalous response is noise; require 1 successful + N duplicate / over-quota / stale-state demonstrations with response screenshots before reporting.

### Phase X — Connection Warming & DB Isolation

Connection warming: establish TCP+TLS before starting the race; use `curl --parallel` for simultaneous sends.
Last-byte sync: Turbo Intruder `engine=Engine.BURP2` for single-packet delivery on HTTP/2.
Database isolation: READ COMMITTED allows phantom reads between SELECT and UPDATE — test with N simultaneous spend/withdraw requests.
GraphQL parallel mutations via aliases: `mutation { a: redeem B: redeem c: redeem }` — bypasses sequential execution.
