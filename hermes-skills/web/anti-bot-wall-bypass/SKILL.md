---
name: anti-bot-wall-bypass
description: "Use when a bot wall or JS challenge blocks a target."
---

# Anti-bot wall / JS challenge bypass

A challenge page is almost never a dead end, and it is almost never a header
problem. Order of likelihood:

1. **Egress-IP reputation** (most common) — the only variable is where you dial from
2. **IP allowlist** — some origins only answer specific ranges
3. A genuinely solvable JS challenge you must actually execute or reverse

Do the diagnosis in that order. Burning hours on header/UA spoofing when the
decision is IP-based is the single most common way to waste a session.

## Step 0 — verify YOUR OWN egress before any recon

Do not assume your requests leave from the machine's own IP. A globally exported
proxy (e.g. `ALL_PROXY=socks5h://127.0.0.1:9050`, or Tor by default) silently
routes every `curl`/scraper request through a shared exit — and shared exits are
precisely what targets score to zero.

```bash
curl -s -m 15 https://api.ipify.org; echo          # what the target actually sees
env | grep -iE 'proxy|socks|tor'                   # why it might not be your IP
ip -4 addr show scope global | grep 'inet '        # your real address
```

Symptom of getting this wrong: a **soft, plausible-looking rejection that never
changes no matter what you vary** — e.g. registration returning a per-IP
"multi account" error on every attempt, including from what you thought was a
fresh direct connection. If a banner is per-IP, first confirm which IP you have.

## Step 1 — fingerprint the vendor from the response itself

| Vendor | Giveaways |
|---|---|
| **cast-sec** | `server: cast-sec`, `cast-mode:`, **status `666`**, cookies `cs-uuid` (32 hex) / `cs-resp`, obfuscator.io body, `via: 1.1 Caddy` |
| Cloudflare | `cf-ray`, `__cf_bm` / `cf_clearance`, `cdn-cgi/challenge`, 1020 |
| Kasada | `429` + `ips.js`, `x-kpsdk-*`, `tkrm_alpekz_*` |
| DataDome | `403` + `var dd={...}`, `datadome` cookie |
| Akamai | `_abck`/`bm_sz`, `428` SEC-CPT, `429` + `{"t":...}` |
| Vercel BotID | `x-is-human`, script often `c.js` |
| **Aliyun WAF (`acw_sc__v2`)** | tiny (≈2.7–4.3 KB) HTML whose only content is one obfuscated `<script>`: opens with `var arg1='<32 hex>'`, sets `document.cookie='acw_sc__v2=<40 hex>'`, reloads. No vendor header — usually on aliyun/huawei CDN nodes behind a file/CDN host |

Non-standard status codes (`666`, `444`) are vendor-specific — treat the code
itself as a fingerprint, not just as "blocked".

## Step 2 — diagnose with egress rotation, never with headers

Verified useless on an IP-reputation wall (do not spend a session on these):
`X-Forwarded-For`, `X-Real-IP`, `X-Client-IP`, `True-Client-IP`, `CF-Connecting-IP`
(behind Cloudflare this one is a hard `1000` error), `Forwarded`; crawler UA
whitelists (`Googlebot`, `bingbot`, `facebookexternalhit`, `Twitterbot`, `curl`,
`python-requests`, `Postman`, `okhttp`); HTTP/1.0 downgrade.

**Use the status code as the measuring instrument — same URL, only the exit changes:**

| Exit | Typical return | Meaning |
|---|---|---|
| datacenter / home ASN | challenge code (`666`) or `403` | scored as a bot / not allowlisted |
| Tor | a *different* code (`403` nginx-style) | you crossed a layer, then hit the next rule |
| clean residential, right region | `200` + real body | through |

Cheap exit rotation without buying proxies — Tor with a random SOCKS user so each
request gets its own circuit:

```bash
curl -s --socks5-hostname 127.0.0.1:9050 --proxy-user "u$RANDOM" https://target/
```

`IsolateSOCKSAuth` gives per-credential circuits. Loop a handful of `--proxy-user`
values; a fraction of exits will pass where others are blocked. Expect Tor exits to
also be the key that opens origins that reject your direct IP outright (see Step 5).

### 2b. The block can be *header-shaped*, and only an A/B on the SAME exit proves it

Before blaming the exit, run a same-exit A/B — same Tor circuit (`--proxy-user`
unchanged), only the header set differs. A Cloudflare zone with a custom rule like
"requests without modern-navigation headers = bot" (2026-09 `telegramasms.com.cn`,
verified `cfOrigin;dur=` > 0 on the 403, i.e. nginx answered, not the edge) behaves
like this:

| Same exit, request shape | Return |
|---|---|
| `curl -A <Chrome UA>` only | `403` CF "Sorry, you have been blocked" |
| + `Sec-Fetch-Mode: navigate`, `Sec-Fetch-Site: none`, `Sec-Fetch-User: ?1`, `Upgrade-Insecure-Requests: 1` | `200` real body |

The four `Sec-Fetch-*`/`Upgrade-Insecure-Requests` headers are how a browser
navigation identifies itself; several anti-scraper CF rules key on exactly that set
and nothing else. Send them on **every** request of a brute-force or you will
collect a wall of 403s and misread it as "the exit got banned". Complementary
rules seen on the same zone: client-supplied `CF-Connecting-IP` -> `403` + 17-byte
plain-text body; `sqlmap` UA -> `403`; `${jndi:` -> `403` (managed rule).

### 2c. Throughput: one circuit + HTTP/2 multiplexing beats per-request circuits

Per-request random circuits cost ~2-7 s each (circuit build) — a 250k-path brute
would take hours. Instead: **find one clean exit once, then pipe a whole batch
through it with `curl -K` + `--parallel`**, which multiplexes many streams over the
one H2 connection:

```bash
# cfg: one socks exit reused, 50 concurrent streams, per-URL output/status
cat > brute.cfg <<'EOF'
socks5-hostname = "127.0.0.1:9050"
proxy-user = "cleanexit1:x"
user-agent = "Mozilla/5.0 … Chrome/131.0.0.0 Safari/537.36"
header = "Accept-Language: zh-CN,zh;q=0.9"
header = "Sec-Fetch-Mode: navigate"
silent
parallel
parallel-max = 50
http2
max-time = 120
write-out = "%{http_code} %{size_download} %{url}\n"
EOF
# then append `url = "https://target/path"` + `output = "/dev/null"` per target
curl -K brute.cfg > results.txt
```

Measured: **~50-70 req/s** with 2000-URL chunks (vs ~5 req/s with per-request
circuits, ~1 req/s sequential), while all responses stay real 404s — no rate-limit
or block. Verify the exit is clean by probing a known-404 path first (404 = pass).
Caveats: paths containing spaces/control chars come back as `000` (curl refuses the
URL — not a finding); a flagged exit turns the whole batch into 403s, so re-probe
and swap `proxy-user` when the hit rate collapses.

### 2d. CF 的 JS 挑战页 = 同一套导航头；且 CDN 缓存会吃掉你的会话
同一手法在 Cloudflare 的 `Just a moment…` 挑战页上复现（2026-09 第二个目标，从客户端 bundle
拿到隐藏路径 `/<随机前缀>/index.html`）：同出口只带 Chrome UA = 挑战页；补
`Sec-Fetch-Mode: navigate` / `Sec-Fetch-Site: none` / `Sec-Fetch-User: ?1` /
`Sec-Fetch-Dest: document` / `Upgrade-Insecure-Requests: 1` → `200` 真页面。
**先把导航头写进你的请求包装器**（后续所有请求共用），否则下一发又掉回挑战页。

**CDN 缓存吃掉 `Set-Cookie` = 隐身杀手**：需要「先取会话 cookie + CSRF token，再做利用」的链
（如未授权上传类 CVE）时，若取到的页面是缓存副本，`Set-Cookie` 已被缓存层剥除 ⇒ 你会
**一直 200 但永远没会话**，然后误判成「这个洞不存在」。对策：每请求加缓存穿透参数
（`?_=<random>`）再取一次，拿到真 `Set-Cookie` 后在同一次会话里完成后续利用。

## Step 3 — deobfuscate by driving the target's OWN decoder

The body is usually obfuscator.io: a base64 array `var a=[...]` plus a string
decoder `b(c,d)` that does `atob -> decodeURIComponent -> RC4(key)`.

**Do not reimplement that in Python/Go.** JS string handling is UTF-16 code units;
a latin-1 reimplementation decodes silently to garbage — you will get plausible
mojibake and conclude the array is encrypted. This is a real, self-inflicted
half-hour.

Instead run their code and call their function:

1. Save the `<script>` body to `challenge.js`.
2. Run `scripts/deobfuscate-obfuscatorio.js challenge.js` (in this skill) — it
   executes the script in a Node `vm` with a mock `document`/`window`, then calls
   the script's own `b(idx,key)` for every call site it finds, and prints recorded
   DOM side effects (`createElement` / `src` / `appendChild` / `set value` /
   `submit`).
3. The plaintext strings name the mechanism, e.g. this class of wall resolves to:
   `window.onload` -> `createElement("script")` -> `src = "/verifyjs"` ->
   `getElementsByTagName("body")[0].appendChild(...)`.

Note what the wall actually gates: `GET /verifyjs` with only the `cs-uuid` cookie
typically just meta-refreshes back to `/` and a loop follows — so the vendor
intends a real browser fingerprint, and rotating exits is the cheaper road anyway.

### 3b. Aliyun WAF (`acw_sc__v2`) — a JS challenge you genuinely *can* solve offline

Unlike the cast-sec reputation wall, this one is **content-bound, not IP-scored**:
the same recipe solved from a datacenter IP and from a US VPS (2026-09, a
client-software share host). So solve it instead of rotating exits.

```bash
# 1. save the challenge with the compression decoded
curl -sS --compressed -A "$UA" -e "$REFERER" -o ch.html "https://<cdn>/file/?<token>"
# 2. run THEIR code in a stubbed DOM, print the cookie it computes
node scripts/solve-acw-sc-v2.js ch.html        # -> COOKIES_JSON:["acw_sc__v2=6ab7…"]
# 3. resend with the cookie -> the page behind the challenge
curl -sS --compressed -A "$UA" -e "$REFERER" -H "Cookie: acw_sc__v2=6ab7…" "https://<cdn>/file/?<token>"
# 4. re-run 2-3: the first cookie often only earns you the *next* page in the chain
```

Pitfalls (all observed):

- **The cookie is bound to the client IP (≈1 h expiry).** Mint it **on the host you
  will keep sending from** — a cookie solved on your workstation is rejected when
  replayed through a jump host and vice versa. If the download has to run on a jump
  host, run the solver there.
- **Old `node` compatibility:** `String.prototype.matchAll` is Node ≥12 — on an older
  box use a `regex.exec` loop instead, or the solver dies before printing anything.
- The challenge script usually **throws immediately after setting the cookie**
  (`Cannot read properties of undefined (reading 'reload')` from a stubbed
  `location`) — that is benign. Capture `document.cookie` independently of the
  exception; treat the throw as success noise, not failure.
- **Tokens are one-shot.** Re-fetch the tokenized URL before every attempt and never
  reuse a `sign`/`file` pair across requests — the server answers `?SignError` or
  `验证码错误` and you will misread it as "the solver failed".
- Passing the challenge is **step one, not the win**: these CDNs commonly sit a
  second *server-side* gate behind it (a `sign` the browser mints after an
  interactive verify). Verify you actually got the payload before reporting a bypass.

## Step 4 — check for the trivial bypass before the clever one

Not every path is walled. On one cast-sec deployment `/favicon.ico` returned
`200` while `/` returned `666`, and `/.well-known/security.txt` returned a third
code — per-path rules exist. Enumerate a few sibling paths before concluding the
whole host is closed.

## Step 5 — once you can reach it, find the ORIGIN

A wall on the edge says nothing about what sits behind it. Test `Host`-header
vhosts against candidate IPs (from OSINT, sibling brands, or historical DNS):

```bash
curl -sk --resolve target.com:443:1.2.3.4 -o /dev/null -w '%{http_code}\n' https://target.com/
# and the plain-HTTP variant, which often reveals the reverse proxy:
curl -sk -H 'Host: target.com' -D - http://1.2.3.4/robots.txt
```

Two tells that you have found the real origin and not another CDN edge:

- **`whois <ip>` does not match the CDN's ASN** while the response still says
  `server: cloudflare` — that header is **forged by the application**. Whois wins.
- Requests from your normal egress fail (connection refused/timeout) while the
  same request over Tor succeeds — an IP allowlist, i.e. the origin.

Confirm scope with a quick burst: N rapid requests that all land in application
logic (recognisable app responses, not edge error pages) prove the edge rate
limiter is out of the path.


## 全文导航（已拆分）

主卡保留前 6 节；其余 3 节在 `references/full.md`：

- Step 6 — when only a REAL renderer gets through, make the request from inside the page
- Pitfalls
- Files

加载：`skill_view(name='anti-bot-wall-bypass', file_path='references/full.md')`
