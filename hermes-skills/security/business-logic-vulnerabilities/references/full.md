# business-logic-vulnerabilities — 全文续篇

> 主卡保留前 3 节；本文件从第 4 节起。原文件：`/root/.hermes/skills/security/business-logic-vulnerabilities/SKILL.md`

## 4. COUPON AND REFERRAL ABUSE

### Coupon Stacking
```
Test: Can you apply multiple coupon codes?
Test: Does "SAVE20" + promo stack to >100%?
Test: Apply coupon, remove item, keep discount applied, add different item
```

### Referral Loop
```
1. Create Account_A
2. Register Account_B with Account_A's referral code → both get credit
3. Create Account_C with Account_B's referral code
4. Ad infinitum with throwaway emails
→ Infinite credit generation
```

### Coupon = Fixed Dollar Amount on Variable-Price Item
```
Coupon: -$5 off any order
Buy item worth $3, use -$5 coupon → net -$2 (credit balance)
```

---

## 5. ACCOUNT / PRIVILEGE LOGIC FLAWS

### Email Verification Bypass
```
1. Register with email A (legitimate, verified)
2. Change email to B (attacker's email, unverified)
3. Use account as verified — does server enforce re-verification?

Or: Change email to victim's email → no verification → account claim
```

### Password Reset Token Binding
```
1. Request password reset for your account → get token
2. Change your email address (account settings)
3. Reuse old password reset token → does it still work for old email?

Or: Request reset for <EMAIL-REDACTED>
    Token sent to victim but check: does URL reveal predictable token pattern?
```

### OAuth Account Linking Abuse
```
1. Have victim's email (but not their password)
2. Register with victim's email → get account with same email
3. Link OAuth (Google/GitHub) to your account
4. Victim logs in with Google → server finds email match → merges with YOUR account
```

### Cookie Replacement — Horizontal/Vertical Privilege Escalation

The textbook IDOR demo from the audit videos:
```
1. Login as super-admin → capture request, copy Cookie (JSESSIONID/Token)
2. Logout, login as plain user → capture another request to the SAME endpoint
3. Replay the plain-user request, but swap the Cookie value with the admin's token
4. If the response returns admin-only data → vertical escalation
   If it returns another-user's data → horizontal escalation
```
A common companion bug: `/oa/emp/list` returns **HTTP 302 to /login when no cookie**, but **200 with full data when any plain-user cookie is sent** — meaning the only check is "logged in?", not "authorized for this endpoint".

### Permission Residue from Database Inconsistency

A subtle case from the second audit class: the admin UI shows that role X has had permission `user:list` revoked, but querying the SQL data:

```sql
SELECT * FROM sys_menu WHERE role_id = 2;
-- two rows for the same menu_id "user:list"
```

The UI's "remove permission" only deleted ONE row; the duplicate row keeps the API accessible. Verify by:
```sql
SELECT menu_id, COUNT(*) FROM sys_menu GROUP BY menu_id, role_id HAVING COUNT(*) > 1;
```

Lesson: when a UI says permission revoked but API still works → check the underlying RBAC table for duplicates / orphaned grants.

### Weak-Random Password Reset Token

PHP / legacy stack on Windows uses `rand()` whose `RAND_MAX = 32768`. If a reset link uses
`/resetpassword.php?id=md5(rand())`, the entire keyspace is precomputable:
```php
$a = 0;
for ($a = 0; $a <= 32768; $a++) {
    $b = md5($a);
    echo $b . "\r\n";
}
```
Iterate the resulting dictionary against `/resetpassword.php?id=<hash>` — when one returns a valid reset page you can change the victim's password. Audit any token generation that ultimately calls `rand()`, `mt_rand()` (without seeding), `Random()` (default seed in C#), etc.

---

## 6. API BUSINESS LOGIC FLAWS

### Object State Manipulation
```
order.status = "pending"
→ PUT /api/orders/1234 {"status": "refunded"}   ← self-trigger refund
→ PUT /api/orders/1234 {"status": "shipped"}    ← mark as shipped without shipping
```

### Transaction Reuse
```
1. Initiate payment → get transaction_id
2. Complete purchase
3. Reuse same transaction_id for second purchase:
   POST /api/checkout {"transaction_id": "USED_TX", "cart": "new_cart"}
```

### Limit Count Manipulation
```
Daily transfer limit = $1000
→ Transfer $999, cancel, transfer $999 (limit not updated on cancel)
→ Parallel transfers (race condition on limit check)
→ Different payment types not sharing limit counter
```

### Java Web "No Filter, No Spring Security" Anti-Pattern

Audit-friendly tell: a Spring Boot project that does **NOT** include `spring-boot-starter-security` and has zero `Filter` classes. This means every controller is wide-open for `guest` unless the developer manually checked the session in each method. Reproduce:
```bash
# Inside the source tree
find . -name "*.java" -exec grep -l "Filter" {} \;     # likely empty
find . -name "*.java" -exec grep -l "@PreAuthorize\|@Secured" {} \;
```
If both are empty, expect almost every API to be unauthorized. From the audit demo:
```java
public Result score(@RequestParam("userId") Integer userId) {
    Score score = scoreService.selectScoreByUserId(userId);
    return Result.success(score);
}
```
No check that `userId` matches the session's logged-in user → horizontal IDOR. Worse: the same endpoint works **without any Cookie**, since nothing forces authentication globally.

### Spring Security `antMatchers` Coverage Gap

The audit videos also showed a partially-secured Spring Security config like:
```java
.antMatchers("/system/user/info").authenticated()
.antMatchers("/system/menu/**").hasRole("admin")
```
A common error is an over-narrow rule — e.g. `/system/user/info` is protected but `/system/user/list` is not, or `/system/menu/**` is admin-only but `/system/dept/treeData` is open. Cross-check the controller annotations (`@PreAuthorize("@ss.hasPermi('system:user:list')")`) against the SecurityConfig — every annotated endpoint must also map to a SecurityConfig rule. Mismatches are common after refactors.

---

## 7. SUBSCRIPTION / TIER CONFUSION

```
Free tier: cannot access feature X
Paid tier: can access feature X

Attack: 
- Sign up for paid trial → enable feature X → downgrade to free
  → Does feature X get disabled on downgrade? 
  → Can you continue using feature X?

Or:
- Inspect premium endpoint list from JS bundle
- Directly call premium endpoints with free account token
→ Server checks subscription for UI but not API?
```

### Direct Media URL Leak — VIP Resource Bypass

Real cases from a fitness/learning app: when the client requests course detail, the JSON response embeds the raw media URL:
```http
GET /gerudo/v2/liveCourse/625020ce8f002700010554c1/detail HTTP/1.1
{
  "previewPullUrl": "http://app-live.../live/app-live_625020ce8f002700010554c2_Preview.flv"
  ...
}
```
Search **all** detail / preview / playback responses for keywords:
```
.flv  .m3u8  .mp4  .mp3  videoUrl  downloadUrl  streamUrl  previewPullUrl
```
For each hit, replay the URL anonymously (curl, VLC, flv.js demo at `https://bilibili.github.io/flv.js/demo/`). If the URL plays without a session, you've broken VIP gating. Defense: use signed, short-TTL URLs bound to user/IP/Referer, not raw resource paths.

### Resource ID Replacement — Free → Paid Course

Companion bug: free course detail returns `{"id": "60caa21e853f5c1651b27c1b", ...}`. Replace the ID in the URL with a known paid course ID. If the response structure remains the same and includes the playable URL → IDOR on premium content. Defense: verify the **owner relation** on each detail call, not just "is logged-in".

---

## 8. FILE UPLOAD BUSINESS LOGIC

For the full upload attack workflow beyond pure logic flaws, also load:

- [upload insecure files](../upload-insecure-files/SKILL.md)

```
Upload size limit: 10MB
→ Upload 10MB → compress client-side → server decompresses → bomb?
(Zip bomb: 1KB zip → 1GB file = denial of service)

Upload type restriction:
→ Upload .csv for "data import" → inject formulas: =SYSTEM("calc")
  (CSV injection in Excel macro context)
→ Upload avatar → server converts → attack converter (ImageMagick, FFmpeg CVEs)

Storage path prediction:
→ /uploads/USER_ID/filename
→ Can you overwrite other user's file by knowing their ID + filename?
```

---

## 9. TESTING APPROACH

```
For each business process:
1. Map the INTENDED flow (happy path)
2. Ask: "What if I skip step N?"
3. Ask: "What if I send negative/zero/MAX values?"
4. Ask: "What if I repeat this step twice?" (idempotency)
5. Ask: "What happens if I do A then B instead of B then A?"
6. Ask: "What if two users do this simultaneously?"
7. Ask: "Can I modify the 'trusted' status fields?"
8. Think from financial/resource impact angle → highest bounty
```

For the formal 5-phase workflow — Business Modeling → State Machine → Attack-Surface Matrix → Checklist-Driven Testing → Human Judgement — load **[METHODOLOGY.md](./METHODOLOGY.md)**. It includes a single-page decision tree (`Q1 ~ Q7`) for "I'm staring at a request and don't know what to try first".

---

## 10. HIGH-IMPACT CHECKLISTS

For the full per-module list (login / register / password recovery / payment / coupon / order / IDOR / privacy / VIP / URL redirect / cookie & token / race / comments) with `why` and `verify` columns — load **[CHECKLIST.md](./CHECKLIST.md)**.

The condensed top-impact items below are the "if you have only 30 minutes, hit these first" set:

### E-commerce / Payment
```
□ Negative quantity / decimal quantity (skuQty=0.02, FoodNum=0.01) in cart
□ Drop required fields (delete prizeIdList) to coerce free tier
□ amount=999999999 integer overflow → final 0
□ Apply multiple conflicting coupons via array params
□ Race condition: double-spend gift card / same coupon
□ Skip payment step directly to order confirmation  
□ Server-trusted client status fields (payment_status=paid, success:true)
□ Refund without return (trigger refund on delivered item via state change)
□ Multi-device concurrent VIP subscription / 补差价升级
□ Currency rounding exploitation (¥0.019 charge → ¥0.02 wallet credit)
```

### Authentication / Account
```
□ 2FA bypass by direct URL access after password step
□ Filter bypass: ../../path traversal truncation, ;path-parameter truncation
□ Password reset token reuse after email change
□ Weak random reset token: md5(rand()) on Windows PHP, predictable seed
□ Email verification bypass (change email after verification)
□ OAuth account takeover via email match
□ Register with existing unverified email
□ Cookie replacement (admin → user / user → another user)
□ Real-name verification "故意填错" replay-to-reset
```

### Subscriptions / Limits / Resources
```
□ Access premium features after downgrade
□ Exceed rate/usage limits via parallel requests (Turbo Intruder)
□ Referral loop for infinite credits
□ Free trial ≠ time-limited (no enforcement after trial)
□ Direct API call to premium endpoint without subscription check
□ Free-course ID swap to paid-course ID (IDOR on resource)
□ Direct media URL exposure in JSON (.flv / .m3u8 / .mp4 in response)
□ Server-side RBAC residue (sys_menu duplicate rows)
□ Java Web no-Filter / Spring Security antMatchers gap
```

---

## 11. CONSOLIDATED CHECKLIST (2-Hour Full Sweep)

The Section 10 list is the "30-minute money grab". This list is the next layer:
when you have a couple of hours and want a defensive-grade sweep across all
nine business surfaces. It's organized by surface, then by attack mechanism
inside the surface, so you can read a column-down for "what classes of bug
might exist on this endpoint" and a row-across for "where else does this
attack apply".

For full `item / why / verify` triplets including reproduction steps and
tooling per item, load **[CHECKLIST.md](./CHECKLIST.md)**. This section
keeps only the item line for fast scanning.

### 11.1 Login / Authentication
```
□ Username enumeration via response diff (msg / status code / timing)
□ Username enumeration via SMS-send response (sent vs not-registered)
□ Brute force without lockout (no rate limit on failed login)
□ Default / weak credentials (admin/admin, root/123456) on backend & infra
□ 2FA bypass via direct URL after password step / replay 2FA token
□ Client-trusted login flag (status=success, is_login=true in response body)
□ Third-party / SSO callback IDOR (modify uid in callback to take over)
□ Biometric liveness bypass (replay static photo / pre-recorded video)
□ Open redirect in login/register (return_url, redirect, callback param)
□ Hardware-key signature replay / forgery (USB-Key, PKI cert)
```

### 11.2 Registration
```
□ Username / phone / email enumeration via "already exists" response
□ Password strength only enforced client-side (set 123456 server-side)
□ Skip multi-step registration (POST final step directly, miss email verify)
□ Verification code not enforced (empty / random / fixed value passes)
□ SMS / email code replay (same code used twice or across users)
□ Re-register same username after logout, inherit old data / privileges
□ Anti-fraud bypass via N similar virtual accounts (same device, diff email)
□ Mass-register replay-protection missing (no nonce on submit step)
```

### 11.3 Password Recovery / Reset
```
□ Reset target tampering (uid / email / phone in submit step)
□ Reset token predictable (timestamp-derived, weak hash, short random)
□ Cross-user token reuse (A's reset_token, change B's password)
□ Old-password check missing on logged-in change-password endpoint
□ Skip code-verify step, hit final reset endpoint directly
□ Reset link / answer / token leaked in HTML or JS source
□ Reset token has no expiry / not invalidated after use
□ Reset code base64-only "obfuscated" in response
□ Inconsistent identity across multi-step flow (reset_token from step 2
  reusable in step 4)
□ Old session not revoked after email/phone re-bind
```

### 11.4 Session / Token
```
□ Session fixation: pre-login session id remains valid after login
□ Token not bound to user/IP/device (steal cookie → use anywhere)
□ Forged token: weak algorithm md5(username + timestamp), no server salt
□ Stale token still accepted after logout / expiry (no blacklist)
□ Cookie tampering (uid / role / is_admin in cookie trusted server-side)
□ State-machine replay (replay "claim red packet" → re-claim)
□ Anti-replay missing on one-time tokens (CSRF token, OTP, nonce)
□ Sensitive credentials (token, answer, key) hardcoded in front-end JS
□ Privileged session created from public Session ID without re-auth
□ Token works cross-environment (different IP, different UA, no validation)
```

### 11.5 Payment / Order
```
□ Amount tampering: amount = 0.01 / 0 / negative / 0.001
□ Quantity tampering: quantity = -1 / 0.01 / 1.5 / 999999999
□ Integer overflow: quantity * price wraps to 0 or negative
□ Floating-point precision exploit (multi-decimal, accumulated rounding)
□ Currency code swap (CNY → JPY/RUB at same numeric value)
□ Coupon / discount field forge (coupon_id, discount=, free_shipping=true)
□ Item ID swap: replace product_id with cheaper SKU at checkout
□ Signature / sign-field bypass (drop sign param, use stale sign)
□ Payment-callback forgery (status=paid posted to internal callback)
□ Replay paid request → multiple shipments / multiple credit
□ Race / concurrency: oversell, double-spend gift card, double redeem coupon
□ Refund without losing the merchandise / virtual rights
□ VIP duration tampering (days=999, months=120, period=-1)
□ Receiver-account redirect (merchant_id / receiver_account swap on withdraw)
□ Negative shipping / fee fields decreasing total (shipping_fee = -500)
□ Concurrent topup-then-refund draining (refund > topup in race window)
□ Pricing rule transition window (price changes at T, replay at T-ε with old rule)
□ Currency rounding micro-arbitrage (charge 0.019 → wallet credit 0.02)
□ Multi-channel inconsistency (online vs cash-on-delivery vs balance pay)
```

### 11.6 IDOR / Authorization
```
□ Horizontal IDOR: uid / order_id / resource_id swap to victim's
□ Vertical IDOR: role / type / level field set to admin in request
□ Hidden field tampering (data-user-id in HTML / JS state)
□ Email / phone re-bind without verifying old binding
□ UID vs session-token consistency missing (token belongs to A, uid sent as B)
□ Predictable / sequential resource IDs (gift IDs, share-link IDs)
□ Resource enumeration on order / coupon / share / trip-detail endpoint
□ Multi-entry inconsistency: web blocks, mobile API doesn't
□ State-machine illegal transition (claim reward without paying / shipping
  before order paid)
□ Hidden / undocumented admin endpoint accessible without admin auth
□ Cross-role function call (user calls merchant API, rider API, etc.)
□ Privilege via concurrent action (request role-elevation race condition)
```

### 11.7 CAPTCHA / Verification Code
```
□ Code returned in plaintext in HTTP response (body / header / JS var)
□ Receiver tampering: change phone / email param to attacker-controlled
□ Empty / fixed code accepted (000000, blank, "test")
□ Drop the code field entirely → request still succeeds
□ Cross-account reuse (A's valid code accepted on B's flow)
□ One-time enforcement missing (same code reusable until expiry)
□ Brute force 4-6 digit code (no attempt limit, no lockout)
□ SMS / email bombing (no rate limit per IP / per phone / no graphical CAPTCHA)
□ Front-end-only "send-success" status (server says fail, FE says success)
□ Code not bound to session (code generated for A, used in B's session)
```

### 11.8 File Upload
```
□ Content-Type bypass (Content-Type: image/jpeg, body is PHP)
□ Extension trick: double ext (.php.jpg), case mix (.Php), null byte, ;path
□ Filename path traversal (filename=../../webshell.php)
□ File-content polyglot (image with embedded PHP / shell)
□ Office XML repack (unzip docx → inject XML → rezip → upload)
□ XXE via .xml / .dtd upload endpoint
□ Backend-only upload (admin login → upload → exec)
□ Upload race: upload + parallel access before AV scan / cleanup
□ ZIP bomb (1KB → 1GB on server, decompress DoS)
□ CSV formula injection (=SYSTEM("calc"), =cmd|'/c calc'!A1)
□ Storage path predictable / overwritable across users (/uploads/UID/file)
□ Image converter / parser CVE (ImageMagick, FFmpeg, pillow)
```

### 11.9 CSRF / SSRF / XXE
```
□ XXE file read (<!ENTITY x SYSTEM "file:///etc/passwd">)
□ XXE blind via OOB (parameter entity → DNSLog / Burp Collaborator)
□ SSRF via image-import / webhook / preview URL (file://, http://127.0.0.1)
□ SSRF via FTP / gopher / jar / php-wrapper / dict protocols
□ XML parser dangerous wrappers enabled (php://expect, expect://)
□ Out-of-band detection for blind injection (DNSLog confirms server hit)
□ CSRF on state-changing endpoint (no token, no SameSite, no origin check)
□ Payment / withdrawal CSRF via auto-submitting hidden form
□ Login CSRF (force victim to log into attacker account)
□ JSONP / JSONP-callback exploitation as CSRF read primitive
```

### How to Use This Section

1. Print or screenshot the relevant 1-2 sub-sections for the target's surface.
2. For each `□` mark: NOT-APPLICABLE / NOT-VULN / VULN / NEEDS-RECHECK.
3. Mark the EXACT endpoint + parameter + payload that proved the bug
   (or proved it absent), so the report is reproducible.
4. Cross-reference with `METHODOLOGY.md` Q1~Q7 decision tree when an item
   triggers something unexpected — the tree tells you which neighboring
   items are likely also vulnerable.
5. For deep payloads / curl-ready commands / Burp screenshots per item,
   load `CHECKLIST.md` (full triplets) and `SCENARIOS.md` (real cases).

