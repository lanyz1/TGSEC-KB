## Disclosed Report Citations (Backfill +9 — 2016-2024)

The following real, verified bug-bounty / coordinated-disclosure cases extend this skill. Four cases (#4, #11, #12, plus the bonus reference) use the modern **HTTP/2 single-packet attack** technique (Kettle DEF CON 31, 2023; Flatt Security expansion 2024) — the technique that makes most modern race exploits viable today.

4. **GitLab — CVE-2022-4037 email-verification race (Kettle DEF CON 31 case study)** ([NVD](https://nvd.nist.gov/vuln/detail/CVE-2022-4037) · [PortSwigger Research](https://portswigger.net/research/smashing-the-state-machine))
    - Subclass: password-reset / email-change token race (TOCTOU on email verification)
    - Single-packet HTTP/2: **YES** — flagship case study in "Smashing the State Machine"
    - Payload: two concurrent `POST /-/profile` requests changing email to two different addresses; the verification token sent to address A becomes valid for address B because state transitions weren't atomic
    - Root cause: Devise (Rails auth) builds the confirmation token before the new email is persisted; concurrent updates misroute the token
    - Year: 2022 (disclosed 2023), CVSS 6.4, patched 15.7.2 / 15.6.4 / 15.5.7

5. **Worldcoin (Tools for Humanity) — World ID action-verification race** ([Medium writeup](https://medium.com/@gonzo-hacks/the-fast-and-the-curious-finding-a-race-condition-in-worldcoin-621c89bfbd61))
    - Subclass: vote/upvote inflation (one-human-one-action enforcement bypass)
    - Payload: ~20 parallel requests via Burp "Send in Parallel" against the verification endpoint
    - Root cause: `canVerifyForAction` appended to an array without DB-level locking; fix added `nullifiers` table with atomic UPSERT
    - Year: 2023 — **$3,000** (High)

6. **Stripe — Promotion code redeemed past limit** ([H1 #1717650](https://hackerone.com/reports/1717650))
    - Subclass: coupon double-redemption
    - Payload: create promo with redemption limit = 1; open two payment-link tabs of same merchant, apply coupon in both, click Pay simultaneously → both succeed
    - Root cause: redemption counter incremented post-charge, not atomically with charge; no row-level lock on `promotion_code.times_redeemed`
    - Year: 2022 — **$250**

7. **Stripe — Fee discounts redeemed many times** ([H1 #1849626](https://hackerone.com/reports/1849626))
    - Subclass: wallet/balance double-spend (Connect fee discount could be redeemed repeatedly)
    - Payload: parallel POSTs to redemption endpoint of a one-shot promotional credit before the credit-consumed flag flipped
    - Root cause: non-atomic check-then-decrement on the credit balance object
    - Year: 2023 — **$5,000**, ~$600 platform fee loss per redemption

8. **marketplace.example.com — Gift card multi-redemption** ([H1 #759247](https://hackerone.com/reports/759247))
    - Subclass: coupon double-redemption (gift card)
    - Payload: capture `POST /gift_cards/redeem` → duplicate N× → fire parallel → balance credited N× from a single card
    - Root cause: gift-card consumption marker written after balance credit, no `SELECT…FOR UPDATE` around the redemption read
    - Year: 2019 — **$1,500** (foundational/widely cited)

9. **Cosmos / Starport faucet — Double-mint race** ([H1 #1438052](https://hackerone.com/reports/1438052))
    - Subclass: wallet/balance double-spend (crypto faucet token issuance)
    - Payload: simultaneous `/faucet/transfer` requests; the `Transfer` Go function executes two state-mutating actions per request, both non-atomic
    - Root cause: faucet handler did not lock per-recipient; transfer() read-modify-write was not serialized
    - Year: 2022 — **$5,000** (CVSS 9.3)

10. **InnoGames — Email-activation race → unlimited diamonds** ([H1 #509629](https://hackerone.com/reports/509629))
    - Subclass: referral abuse multiplier / account-create race (one activation token → multiple "first activation bonus" payouts)
    - Payload: race the email-activation endpoint with the same one-time token before `token_used` flag committed → reward granted on every winning request
    - Root cause: token-consumption flag set in same transaction as reward grant, but transaction isolation level too low (READ COMMITTED)
    - Year: 2019 — **$2,000**

11. **RyotaK / Flatt Security — "First Sequence Sync" PIN-bruteforce (10,000-req single-packet expansion)** ([Flatt Security Research](https://flatt.tech/research/posts/beyond-the-limit-expanding-single-packet-race-condition-with-first-sequence-sync/))
    - Subclass: rate-limit bypass via race / MFA-OTP-validate race (6-digit PIN with 5-attempt cap)
    - Single-packet HTTP/2: **YES** — extends Kettle's single-packet from ~30 requests to 10,000 requests in 166 ms by splitting across IP fragments with synchronized TCP first-sequence
    - Payload: ~10,000 concurrent `POST /verify-pin` requests in 166 ms, each with a different 4-6 digit guess, all landing inside the rate-limit window
    - Root cause: rate-limit counter incremented per-request asynchronously; "5 attempts" gate read stale counter for the entire batch
    - Year: 2024 — **must-reference modern single-packet example**

12. **nopCommerce — CVE-2024-58248 gift-card double-redemption** ([NVD](https://nvd.nist.gov/vuln/detail/CVE-2024-58248))
    - Subclass: coupon double-redemption (e-commerce checkout TOCTOU)
    - Single-packet HTTP/2: **YES** — single-packet attack reproduces it reliably
    - Payload: two parallel `POST /checkout/PlaceOrder` requests both applying the same gift card → both orders complete, gift card balance debited once
    - Root cause: order-placement code path did not implement locking on gift-card balance row → check-then-debit non-atomic
    - Year: 2024 (versions before 4.80.0)

---

