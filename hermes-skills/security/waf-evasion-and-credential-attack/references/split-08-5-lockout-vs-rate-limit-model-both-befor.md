## 5. Lockout vs rate limit — model both before a big run

- The **per-account** failure lockout threshold is small (order ~10). Once tripped it answers the
lockout string for that account regardless of source IP and **masks the real verdict** — a
wrong-password test that returns the lockout string is not evidence about the password.
- Whether a large run survives depends on the lockout being keyed per account **+ source** rather
than per account alone: spread attempts over many rotating exits and the per-source counter never
reaches the threshold (100k+ attempts completed against one account). Concentrate attempts on a
few reused exits and the same account locks after ~10.
- **Per-endpoint limits differ on the same host — measure each endpoint separately.** On one
platform the admin console login allowed only ~6 failures per exit before a 59-minute network
block, while the member app login on the same infrastructure sustained hundreds of attempts per
minute across rotating exits. The member-side login is often the softest credential oracle; test
both before sizing a run.
- **Shared credential store across surfaces = a free, precise role oracle.** When the admin console
accepts a *member* account's password and answers `insufficient authority` (rather than the
invalid-password string), the store is shared and the account merely lacks a role: classify `400`
wrong / `403` valid-no-role / `200` token. Sweep every cracked (account, password) pair against the
admin endpoint — role membership is the only remaining unknown.
- **Status-check order decides what a login response leaks.** Deployments that check account status
(frozen / banned) *before* verifying the password answer the ban string (`您的账户已禁用：<reason>`)
for ANY password. Consequences: (a) the string is a password-independent **existence oracle** — the
number is a real account; (b) it can never validate a password, so stop spending candidates on such
accounts; (c) forks diverge — a fork that stops normalizing leaks ban reasons the upstream hides
(upstream merges user-not-found / freeze / invalid-password into one invalid string), so test one
known account per class to learn the live fork's semantics.
- **A single pass is not a verdict.** Rate-limit and empty / transport responses are not negative
results: a single-pass sweep bucketed 241/250 pairs as "invalid", and re-testing showed the bucket
was overwhelmingly rate-limit noise (true negatives: single digits). Keep retrying every pair with
fresh exits until it returns a real verdict (hit / valid-no-role / explicit wrong-credentials)
before reporting any count.
- Therefore: **one account per harness run.** Never run a second spray, or a slow manual probe,
against an account already being sprayed — it poisons the first with lockout responses.
- A slow single-candidate probe is WORSE than the bulk harness here: fewer source IPs means the
lockout trips almost immediately and every candidate returns the masking string.
- Confirm the account is unlocked with a single probe after cooldown before resuming.
- **Measure the lockout on the SECOND FACTOR separately from the password step.** A login that
locks after ~10 wrong passwords frequently applies no counter at all to the TOTP/OTP field. Send
~10 wrong 6-digit codes and watch for a lockout string: if none appears, the second factor is
brute-forceable — space 1e6 with roughly 3 codes valid at any instant, so expect a hit near ~333k
attempts. Persist the scan index so a restart resumes; one hit is worth the hours because it
converts an already-known password into a live session. Never start this when the field does lock.
- **Password lock can still fire during a "TOTP-only" scan.** If the client resubmits
`username+password+code` on every attempt, the server may increment the **password** failure
counter (or a combined counter) and answer `密码错误过多锁定…分钟` even while wrong-code responses
stayed unlockable. On any password-lock / account-lock string: **kill the harness immediately**,
cooldown, single unlock probe, then resume from saved index — do not keep range workers up because
"TOTP had no lock". Prefer transports that only vary the MFA field when the API allows it.
- After MFA success, **do not run a second login-generating job** against the same account while
using the fresh token (single-session). Further failed logins plus noisy egress often graduate the
edge from rate-limit into a long CF/WAF hard-ban on the admin host; pivot the live token to weaker
origins first, treat re-auth as a new cool campaign.
- The second-factor scan is a *positive-match-only* run (§4) and MUST treat any non-"wrong code"
response as unknown-and-stop: the response that means success (a token) and the response that means
lockout look nothing like the failure string.

