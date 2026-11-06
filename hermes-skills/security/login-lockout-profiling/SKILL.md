---
name: login-lockout-profiling
description: Use when a login locks — profile scope, key, window first.
---

# Login Lockout Profiling

Measure the lock **before** spending a single dictionary entry. Most "lock bypass" claims are wrong, and one wrong assumption costs days of a campaign or bans your egress.

## Step 0 — prove the login endpoint is real

- **SPA fallback trap**: an unknown path on a Vue/React admin host returns `200 text/html` (the index). That is not an endpoint. Require the app's JSON envelope (`{"code":...,"message":...}`) before believing anything.
- Paths mined from frontend chunks (`url:"/user/page"`) are relative to the axios **baseURL** (often `/admin`). Probing them bare returns the fallback → fake "200s". Always re-probe with the prefix.
- One vhost can run several filter chains: `/admin/*` = token auth + plain JSON, `/api/*` = signature/decrypt filter. A `500` with the app's generic message on POST plus a JSON `400 未登录` on GET means **two different filters**, not a dead path — keep it as a lead.

## Step 1 — build the error-code dictionary

Send deliberate probes and record code+message for each case:

| probe | meaning to extract |
|---|---|
| wrong password, plausible user | bad-credential code |
| nonexistent user | does it differ? (usually not) |
| 6th rapid attempt | lock code + remaining-time text |
| burst from one IP | rate-limit code |
| correct password on a 2FA account | TOTP-required code (this is your **hit** signal) |
| account with IP allowlist | "IP not in whitelist" code |

Codes seen on Chinese operations panels (confirm, never assume): `10002` bad creds, `4001` Google TOTP required, `10014` IP not in whitelist, `430` account locked (message carries remaining minutes), `429` rate limited.

## Step 2 — scope: account vs IP vs (account,IP)

- Retry an already-locked username from **different egress**. Lock persists → account-scoped. Lock clears → IP-scoped.
- The message text is the discriminator: "账号已被临时锁定" vs "当前IP已被临时锁定". **`430` is reused for both** — read the message, never the code alone.

### Step 2a — clear the IP dimension before measuring the account dimension

**Both locks return `430`.** If the IP dimension is active, every probe returns `430 当前IP已被临时锁定` and you learn nothing about the account key — worse, you will mis-read it as "account locked" and chase the wrong dimension for hours.

1. Unspoofed baseline: one request, note the message. `当前IP已被临时锁定` → IP lock is live **now**.
2. Re-send the identical request with a random `X-Forwarded-For` and confirm you now reach the real auth code (`10002` / `4001` / `10014`). That single pair proves the header is the limiter key **and** that your remaining measurements are clean.
3. Only then profile the account dimension. **Every probe from here on carries a fresh XFF**, otherwise the IP timer pollutes the account timer and the counts are garbage.

The two budgets are independent: burning the IP budget does not touch the account budget, and vice-versa. Measured on a Vue+Spring ops panel: unspoofed → `430 当前IP已被临时锁定，请于29分钟后重试`; identical request + `X-Forwarded-For: 8.8.8.8` → `10002`.
- `X-Forwarded-For` / `X-Real-IP` / `X-Client-IP` spoofing usually defeats the IP limiter **only** — confirm, then rely on it to keep your real IP clean.
- **Measure the limiter key directly**: same request, random XFF per attempt vs one fixed XFF, at the same rate. Random-XFF at 4.5 req/s ran thousands of requests with 0×429; the fixed-XFF run went 5×`10002` → `430` → `429`. Header-keyed, not socket-keyed — that means the spoof is the whole bypass and no egress rotation is needed.
- Body fields like `loginType` / `type` / `client` / `platform` usually do **not** join the lock key: one username + wrong password across every value still hit one `430`. Verify with one request per value before counting them as multipliers (and before assuming they route to a different user table — they usually don't; a valid App account tested against `admin|merchant|seller|shop|agent` returned `10002` for all).
- Tor per-request circuit isolation: `curl --socks5-hostname <randname>:x@127.0.0.1:9050` (SOCKS-auth isolation gives a fresh exit per username); in requests use `socks5h://u<rand>:x@127.0.0.1:9050`.

## Step 3 — measure threshold and window

- Use a **throwaway username**, never a real one.
- Fire N spaced attempts, note the code where it flips, and read the remaining-minutes text to derive the window.
- Expect nonexistent usernames to lock too (lock key = normalized string). **Then there is no existence oracle** — say so instead of claiming user enumeration.
- Write the numbers down (`5 per 30 min per account`, `5 per 30 min per IP`, window 30 min). Never estimate.

## Step 4 — lock-key normalization (the multiplier that usually fails)

Goal: strings that are distinct lock keys but resolve to the same DB row.

### The decisive control test — run this BEFORE spending a dictionary

Zero passwords needed. The base account's **current lock** is the oracle:

1. Send the base name once (`admin`) → confirm `430` + **remaining minutes** (the key is now locked).
2. Send each candidate variant once (`ádmin`, `admīn`, `admin\u00A0`, …) **with a fresh random XFF**, and compare the remaining-minutes text, not just the code:
   - variant `430` **with the same countdown** as the base → **same lock key**. The store folded the string onto the locked key → **no multiplier, kill the variant track.**
   - variant `430` **with a different countdown** → **independent lock key** (a separate budget). Only now ask whether the row also resolves — that needs a password, so it stays a hypothesis until a hit.
   - variant returns **bad-credential (`10002`)** → the row lookup is exact/binary → **no fold. Kill the variant track.**
3. Control: the same variant on a junk base (`zzq9x7k2`) must also return bad-credential, otherwise the base itself is dirty.

**The countdown is the real oracle.** `430` alone is ambiguous — same timer means folded, different timer means independent key. Two names sharing one countdown are one row-one key; two names with different countdowns are two keys (possibly two accounts — measured: `admin` 24 min vs `administrator` 13 min → distinct keys, and `administrator` is a real second account). A differing countdown does **not** prove the account exists, because locks are string-keyed (see Step 3) — it only proves the keys are distinct.

Measured on a Spring-Boot + Vue ops panel: 22 accent variants, 7 combining-mark variants and 9 Unicode-space variants **all** returned `10002` while plain `admin` was `430` → store is exact-match. A "unique key per request" campaign on top of that is 100% waste (7,829 requests, 0 real password checks, then had to be retracted to the user).

**Combining marks (U+0301 etc.) as an infinite unique-key generator are the classic trap.** They only help if the control test above proves folding. Under `utf8mb4_bin` / Java-side `.equals` / hashed lookup they never match a row.

- Variants: case flips, 1–3 trailing spaces, `\t`, `\x0b`, fullwidth `\u3000`, accent substitution (`á à ä` for `a`).
- A variant that **inherits** the lock proves the server trims + lowercases → no multiplier. (Observed: `AdMiN`, `admin `, `admin\t`, `admin\x0b` all inherited; only `\u3000` got an independent key and it does not match the row either.)
- An **independent** key only helps if the store collapses the strings:
  - MySQL `utf8mb4_general_ci` / `utf8mb4_0900_ai_ci`: case- and accent-insensitive; `general_ci` PAD SPACE ignores trailing spaces, `0900` (NO PAD) does not.
  - `_bin` / `_as_cs`: nothing collapses.
- You cannot validate the target's collation without a valid password. Validate on a **sibling login from the same vendor stack** where you hold credentials, then state the assumption. (Sibling test on a same-family ThinkPHP mall: `CESHI` logged in, `cèshi` did not → case-insensitive, accent-sensitive. Do not assume `ai_ci`.)
- Report the honest outcome: "variant keys are independent but the row does not match — no bypass" beats dressing it up as a bypass.

## Step 5 — throughput math and go/no-go

```
attempts/day = per_window_per_account × windows_per_day × n_usernames
```

`5 per 30 min` = **240 guesses/day/account**. A 10k dictionary on one account is 41 days — not a plan. Pick 100–200 highest-probability passwords (vendor/brand tokens, operator identity strings, local-language top-N) and **interleave categories** (e.g. 3 targeted : 2 generic) so every window samples each stream; otherwise the generic list only starts after the targeted list exhausts.

If the math says weeks and there is no multiplier, say it plainly and move the effort to structural work.

## Step 6 — windowed campaign engineering

- Persistent state JSON: window index, per-user counters, hits.
- Window sleep = lock window **+ margin** (1860s for a 30-min lock). Shorter → you re-hit 430 and burn a whole window.
- On `430`: `break` out of that username and continue with the next. A `while True: ... continue` on 430 spins forever on one locked account (real bug hit this session).
- Hit handling: `200` → store token and validate immediately; TOTP-required code → **password found**, record it even without the second factor.
- Write the post-auth extractor (list → detail → export endpoints) **before** the campaign starts, so a hit turns into data in minutes.
- Log every ~25 attempts; long runs must be resumable and auditable.

## Step 7 — parallel tracks and objective anchor

- A password campaign is a waiting game. Keep structural work running: object-id matrices, legacy/alternate prefixes on the same vhost, storage keys, sibling hosts.
- Anchor to the stated objective. If the ask is "the platform's user database", do **not** substitute an easier adjacent dataset (support-IM conversations, mall users, one tenant's chat) and call it delivered — the user will call it out.
- The deliverable is the dump/token/DB, not a report listing which doors were tried.

## Pitfalls

- **Stale runners**: earlier brute/runner processes keep hammering and hold the same lock budget; their locks look exactly like "another attacker is on the panel". `pgrep -fa 'brute|runner|spray'` and kill them **before** measuring.
- Interpreting a shared lock as a third-party actor: check your own state files first.
- **Reading `430` as one thing.** Two different messages share the code: `当前IP已被临时锁定` (IP budget) and `账号已被临时锁定` (account budget). Probe unspoofed first, then spoofed; if the message changes you were measuring the wrong dimension.
- **Comparing variants by code instead of countdown.** `430` + same remaining-minutes = same key (folded, no win). `430` + different remaining-minutes = different key. Without the countdown you cannot tell a fold from a fresh budget.
- **Assuming sibling panels give fresh attempts.** Lock a username on panel A, immediately probe panel B with the same name: `430` on B means one shared store → no multiplier. Measured across two vhosts on the same origin (`gtadminops...` ↔ `manager...`): the second panel was already locked, so the two front-ends are one Redis.
- **Expecting more usernames to speed up a given account.** They do not. The window is fixed, so per-name progress stays at `per_window` passwords per window no matter how many names you add; more names only widen coverage, never accelerate one row.
- Believing `430` means the account exists — with string-keyed locks it does not (measured: random `zq_random_nouser_8812` → 5×`10002` then `430`).
- Reading timing as an existence oracle: constant-time dummy hashing kills it (measured: 0.25s for both real and fake usernames).
- Assuming case variants are a bypass without testing inheritance.
- **Declaring a variant bypass without the locked-base control test.** If the base is not locked while you test, every variant looks "independent" and you learn nothing. Lock the base first, then probe variants — that is the whole measurement.
- **Unicode whitespace is not ASCII whitespace**: Java `trim()` strips only ≤U+0020, so `admin\t` inherits the `admin` key while `admin\u00A0` / U+2000 / U+3000 / U+200B / U+180E / U+200A are independent *non-matching* keys. They are not a bypass, just wasted budget.
- Reporting a mechanical win to the user before the control test has run — a retraction costs more trust than the extra 10 minutes of measurement.

## References

- `references/zglw-admin-lockout-2026-10.md` — full measured case: code semantics, threshold table, variant inheritance results, sibling collation test, SPA/baseURL trap, legacy `/api/index/*` lead, campaign configuration.
- `references/collation-fold-control-test.md` — the zero-password control test in probe form, exact variant matrix (accents / combining marks / 9 Unicode spaces), rate-limiter keying experiment, and what the retraction cost looked like.
- `references/lock-key-countdown-discriminator.md` — two-dimension `430` handling: unspoofed-vs-XFF baseline, countdown comparison across case/space variants, sibling-panel shared-store probe, blind-lock check, throughput consequence.
