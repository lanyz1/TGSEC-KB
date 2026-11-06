## 0. Identify which layer blocked you — before choosing a bypass

| Response | Layer | Lever |
|---|---|---|
| HTML page branded SafeLine/Chaitin, 403 | edge WAF, **path rule** | **§6 path × ingress matrix first — the origin often serves it**; then §2 browser fetch |
| An edge (not app) block that survives every IP, method and cleared session | edge **path rule**, not a challenge | stop early and re-read the incident: an app-layer answer on the *same* path from another prefix/ingress is the real route |
| Cloudflare 1015 / 1010 / "Attention Required", siblings blocked too | Cloudflare per-IP rate/bot rule | rotate source IP (§3), cooldown |
| Cloudflare "Attention Required" on ONE path while siblings answer normally | Cloudflare **path rule** | do **not** rotate IPs and do **not** reach for the browser (§2) — it fires from every IP, every method and an already-cleared session. Record the path closed, then move to another ingress (§6) |
| Cloudflare **"Sorry, you have been blocked / You are unable to access <domain>"** for EVERY path, including paths that answered JSON minutes earlier | full-site **IP/ASN ban** on your egress | nothing on-host fixes it; switch egress class (§3b-3d). Expect hours, not minutes — a concurrency burst can convert a per-path rate limit into a multi-hour zone ban |
| A pooled egress class answers path A but returns the block page for path B, while another class shows the reverse | **per-(IP, path) burn** from your own traffic | the burn is per IP AND per path — never spend a fresh IP class on latency benchmarks against the path you plan to spray; keep an unbenched reserve per critical path (§3d) |
| JSON `{"code":429,"msg":"请求过于频繁"}` | application rate limit | more source IPs (§3) |
| **HTTP 200 with an EMPTY body / `application/octet-stream`** where the path answered JSON before | route-level **mute** (operator re-pointed/neutered the route mid-campaign) | test route **case variants** (`/api/User/` vs `/api/user/`) and diff against the client binary's endpoint set (§7) — one casing can be muted while the other still serves |
| JSON `登录失败次数过多` | application **account lockout** | §5 — stop, cooldown |
| **504 where sibling paths give 403** | **you are past the WAF**; edge proxied to a dead upstream | probe ops/relay entries (§6) |
| Custom 502/403 page with vendor footer link (`Protected By X`) echoing `client_ip`/`request_id` | branded commercial gateway (e.g. Peekabo), **path-literal rule** | not nginx/CF/SafeLine — bypass variants won't work; switch ingress (§6) and treat the path as UNKNOWN, not present |

- A path-blocked URL answers identically for every `Host:` value, `X-Forwarded-For`,
`X-Real-IP`, URL-encoding, dot-segment, matrix-param and HTTP-method variant. Confirm once, then
stop grinding bypass variants on that path — the rule is on the URL.
- One method sweep (GET/HEAD/OPTIONS/PUT/PATCH/DELETE) is still worth it: a `405 Method Not Allowed`
from the origin proves the route exists and that you reached the application.
- A `422` from a Pydantic/Swagger stack means parameters were validated before auth was checked.
It is NOT evidence about credentials — send `{}` and read the field names out of the errors.

