# Mining a hostile code-split SPA behind Cloudflare (Spring backend, case-derived)

Session: 短信系统 SPA (Cloudflare-fronted) + RuoYi-flavored "管理中控" sibling app.
Every technique below was exercised against the live target; outcomes noted honestly.

## 1. Always dump response headers — redirects hand you new domains

`curl -sD -` (or `-i`) on a plain GET. A 301's `location:` header on the
*known* domain surfaced the operator's **second primary domain**, which opened an
entirely fresh recon space (new CT logs, new DNS history, new sibling hostnames)
that was invisible from the original host.

Never fire page requests without headers — the `location`, `x-*-block` and
`server` values are the cheapest intel on the page.

## 2. Custom gateway headers name the control you tripped

The 中控 app returned headers like `x-auth-block`, `x-path-block`,
`x-turnstile-block`. These are the app's *own* edge rules, and they let you tell
"route does not exist" from "route exists, you are blocked" — essential when a
401 is otherwise ambiguous.

## 3. Spring route-existence oracle (unauthenticated)

Differential probing of unknown paths:

| Request | Response | Meaning |
|---|---|---|
| `GET /csapi/<unknown>` | Spring default 404 JSON that **echoes the requested path** | no such route; the echo also reveals the real servlet context path (`/csapi`) |
| `GET /<known-route>` with wrong method | 405 / method-not-supported error | **route exists** |

Cheap oracle for enumerating a Spring/Java route table without auth. Two traps:

- Routes containing `{pathVariable}` (e.g. `/chat/{chatId}`) match *anything* →
  every candidate looks alive. Re-verify hits with a second probe shape (wrong
  method, trailing segment) before believing them.
- The echoed path in the 404 body is what confirms the context path; if you have
  the wrong prefix every route 404s identically.

## 4. Code-split SPA: mine the chunk map, then fetch every chunk

When the main bundle is mostly vendor code, the API calls live in **code-split
chunks**. The inline webpack/Vite runtime in `index.html` holds the chunk-name →
hash table (e.g. `chunk-9da421ec.2434acb2.js`). Extract the table, reconstruct
real filenames, then pull **every** chunk and grep for `/api`, `axios`, `fetch(`,
route names. This recovered the complete endpoint map (proxy/node/phone/carrier
modules) of the 中控 app, plus a second app's `/api/monitor/server`.

Practical notes:

- Pull the inline runtime with a regex over the HTML, or read the runtime chunk
  itself; the map is a plain object of name→hash.
- When the edge 403s bare `curl` on `assets/*.js`, use a foreign/different
  egress or a real browser. Path-obfuscation tricks (`//assets`, `/assets/./`,
  `/assets%2f`, `X-Original-URL`) all failed here — don't burn a cycle on them.
- A fresh build changes hashes; re-extract the map per engagement, don't reuse
  filenames from an older report.

## 5. Sweep the mined surface with the one session you already have

With a single valid session token, iterate the full mined route list and record
per-route status + response shape, then tag IDOR/BOLA candidates. This is where
`/csapi/*` map + CRUD routes turn into findings.

## 6. Fingerprint captcha enforcement before spending cycles on it

POST the protected endpoint twice:

- (a) captcha field empty → `"please complete human verification"`
- (b) syntactically valid random token → `"verification failed"`

Different messages = real server-side siteverify. Identical messages =
client-only check. This tells you whether bypass/forgery is theoretically on the
table at all before you invest in it.

## 7. Historical-DNS multi-IP ≠ origin (shared edge discriminator)

Historical A records for the apex yielded several non-CDN IPs on one date
(Alibaba Cloud HK). Verdict: **not origin**. Discriminator: reverse "domains on
this IP" lookup showed the same IPs hosting dozens of unrelated
gambling/lottery sites → shared high-defense / CDN edge pool. Always run the
same-IP-domain check before claiming an origin; also check outbound reachability
(an origin that only accepts Cloudflare's回源 ranges rejects your direct
connection on all ports — consistent, but not proof by itself).

## 8. Sibling hostnames can enforce *different* controls

`www.<a>` forced server-side Turnstile on `/login` while `single.<a>` served the
same product with a captcha-free login endpoint. Before concluding "the login is
hardened", probe **every** known hostname for the same endpoint — legacy and
secondary entries frequently lag behind the hardened one.

## Pitfalls

- **Account lockout is per-account, not per-IP** (~15 attempts / 2 min observed).
  A short spray against a secondary instance locked the accounts you already
  owned. Prefer using an existing session over re-authenticating elsewhere.
- A brand-new primary domain often has **no DNS history** worth having (registered
  recently, nameservers on Cloudflare from day one) — don't expect historical A
  records to pay off there.
- Space-engine (Shodan etc.) queries against a Cloudflare-only target return zero
  for certificate serial, favicon hash, title and HTML feature strings when the
  origin only accepts回源 traffic — expected, not a syntax error. Sanity-check
  syntax by querying a value you know exists (an edge cert serial).
