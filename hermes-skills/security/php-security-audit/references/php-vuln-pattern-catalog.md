# PHP Audit — Vulnerability Pattern Catalog

Concrete patterns observed in real audits (evidence from an EMSHOP e-commerce source audit, 2026). Use as a detection checklist: for each pattern, grep/read for the signature, then verify the exploit chain end-to-end before reporting.

## 1. Nested-object bypass of response whitelist → card-key / PII leak (Critical)
- Signature: a sanitize/whitelist function filters the TOP-LEVEL fields of a row, then appends a nested collection wholesale — `$out['order_goods'] = OrderModel::getOrderGoods($id);` — with no per-field filtering inside.
- Evidence: `user/find_order.php` L33-65 — `$orderWhiteList` deliberately excludes `delivery_content`, but `order_goods` rows get `delivery_content` hydrated (card keys) by `OrderModel::hydrateDeliveryContent` (L1173-1209) and are returned unmodified. HTML detail view renders it too: `user/view/guest_order_detail.php` L141-146.
- Check: every endpoint that serializes orders (guest query pages, admin detail, APIs) — does any nested field carry `delivery_content` / `plugin_data` / `card_pwd`?
- Payload sketch: `POST /user/find_order.php` `mode=orderno&order_no=<n>&captcha=<ans>` → JSON `data[].order_goods[].delivery_content` = card keys, unauthenticated.

## 2. Arithmetic captcha with client-visible expression (treat as absent)
- Signature: `Captcha::issue()` returns the display expression ("3 + 5"); HTML renders `<span class="...__expr">3 + 5 = ?</span>`; JSON error payloads re-issue and return the new expr.
- Evidence: `include/lib/Captcha.php` L31-64; `user/find_order.php` L79 (refresh_captcha echoes expr), L108-116 (error path re-issues expr); `user/view/find_order.php` L81/L108.
- Exploit: parse expr from HTML/JSON, eval, submit. One-time-use is irrelevant (unlimited re-issue). Real defense must be rate limiting.

## 3. Rate-limit keyed on spoofable client IP
- Signature: `clientIp()` returns first valid value from `HTTP_CF_CONNECTING_IP` → `HTTP_X_REAL_IP` → `HTTP_X_FORWARDED_FOR` → `REMOTE_ADDR`, with no trusted-proxy validation.
- Evidence: `include/lib/RateLimit.php` L96-113; consumed as `'find_order:' . RateLimit::clientIp()` in `user/find_order.php` L98.
- Bypass: rotate `X-Forwarded-For` per request — works when origin is directly reachable or the proxy passes the header through. Turns "10 queries/min/IP" into unlimited.
- Fix: only trust proxy headers from known proxy IPs; otherwise key on `REMOTE_ADDR`.

## 4. Query-API IDOR: scope check without user_id
- Signature: query-by-identifier endpoints verify `merchant_id` / `owner_id` but never compare the record's `user_id` to the authenticated caller.
- Evidence: `include/controller/ApiController.php` `queryOrder()` L264-299 — any registered user with a self-service API secret (generated in `user/api.php`) can query ANY main-site order's status/amount/payment/time by order_no; API has no rate limit either.
- Check: also scan order-payment, delivery-queue, balance-log query endpoints for the same gap.

## 5. UI-gated feature with ungated POST handler
- Signature: page logic hides a tab/button when a config flag is off, but the POST handler never re-checks the flag.
- Evidence: `user/find_order.php` L253-258 (UI downgrades `orderno` tab when both guest-find modes are off) vs L167-179 (POST `mode=orderno` runs regardless of config).
- Check: compare UI gating conditions with handler-level checks — they must match.

## 6. Credential-design weakness: single-factor guest lookup
- Signature: guest order lookup accepts contact info alone (phone/QQ/email exact match) when the admin enabled only the contact mode; the password fallback is off.
- Evidence: `user/find_order.php` L133-165 (`guest_contact = ?` exact match); `include/model/GuestFindModel.php` L47-66 (`isPasswordEnabled` fallback logic). Plaintext `order_password` stored: `include/controller/OrderController.php` L156-159.
- Verdict: report medium/high — the credential is the buyer's semi-public contact info; the payload is all their orders including card keys.

## 7. Amount check skipped when field absent (low, but note it)
- Signature: `if ($totalAmount !== '' && $totalAmount !== $expected) fail;` — missing field ⇒ check skipped. Low risk when the signature covers all params (alipay RSA2), but flag it.
- Evidence: `content/plugin/alipay/alipay.php` L606/L627/L653.

## 8. Existence oracles via distinct error messages + low-entropy IDs
- Distinct errors ("未找到订单" vs "验证码错误" vs "无权查看") let attackers distinguish exists/not-exists/forbidden.
- Order_no format `date('YmdHis') + 6 random digits` (`include/model/OrderModel.php` L69-77) = 10^6 combos per second; targeted brute-force at recent timestamps is feasible once rate limiting is bypassed.

## Verified-clean patterns (do NOT re-report without new evidence)
- Prepared-statement DB wrapper (mysqli/PDO) with int-cast LIMIT/OFFSET — SQLi bar is high; only concatenated fragments are in scope.
- Server-side pricing in order creation; server-side coupon recompute with server-computed amounts; conditional `UPDATE` for coupon use-count (concurrency-safe, prevents double-use).
- Payment callbacks verifying signature AND amount vs DB record; recharge `markPaid` with `FOR UPDATE` + status guard (idempotent).
- Admin endpoints with `adminRequireLogin()` + CSRF on all non-list actions; card inventory operations scoped by goods ownership assertions.
