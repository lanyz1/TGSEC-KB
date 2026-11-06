# anti-bot-wall-bypass — 全文续篇

> 主卡保留前 6 节；本文件从第 7 节起。原文件：`/root/.hermes/skills/web/anti-bot-wall-bypass/SKILL.md`

## Step 6 — when only a REAL renderer gets through, make the request from inside the page

Signal: `curl` / `python` / even `curl_cffi` with Chrome JA3 all get the wall (e.g.
Aliyun WAF: `您的访问请求可能对网站造成安全威胁，请求已被阻断`), while the same URL
in real Chromium renders fine. The decider is **renderer-grade TLS + JS execution**,
not any header you can add. Do not keep tuning the client TLS profile —
**relocate the request into the page** you already have open:

1. Connect over CDP to the live tab: `Runtime.evaluate` with `awaitPromise: true`.
2. Re-implement the app's own request crypto **in the page** with native WebCrypto
   (no CryptoJS dependency needed):
   ```js
   const key = await crypto.subtle.importKey('raw', b64d(k), {name:'AES-CBC'}, false, ['encrypt']);
   const ct  = await crypto.subtle.encrypt({name:'AES-CBC', iv: b64d(v)}, key,
                new TextEncoder().encode(JSON.stringify(params)));
   body = JSON.stringify({ x: b64e(new Uint8Array(ct)) });
   ```
3. Use the page's own `fetch(..., {credentials:'include'})` plus the app's required
   headers, so cookies/tokens/CSRF come along for free. The response is then
   decryptable by the same key (round-trip self-test first: encrypt `{"a":1}` and
   decrypt it back — do not skip this, a wrong key looks exactly like a rejected
   request).

This converts a blocked datacenter IP into a fully scriptable API client: the
browser is only the transport. It also survives per-IP bans on tools, since the
session cookie stays valid across sibling domains.

### 6b. Three diagnostics that save an hour each

- **`Failed to fetch` / `chrome-error://chromewebdata` is a NETWORK error, not the
  WAF.** Before blaming the target, fetch `/favicon.ico` and an unrelated public
  site from inside the page. Both failing = your own egress is broken, most often a
  proxy var the browser inherited at launch (`ALL_PROXY` / `https_proxy` pointing at
  a dead Tor). Relaunch clean rather than debugging the target:
  `env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u http_proxy -u HTTPS_PROXY -u https_proxy no_proxy='*' NO_PROXY='*' <browser> --headless=new --remote-debugging-port=9222 --user-data-dir=$(mktemp -d)`.
- **Geo-block may cover the HTML routes but not the API.** A US jump-host got
  `302 -> /other/restrictionIp` (“您所在的地区已被禁止访问”) for pages while the same
  host answered API calls `200`. Probe an API path before concluding an exit is useless.
- **A ban is often per-domain, not per-IP.** When one entry point returns `000` but
  sibling hosts of the same backend answer `200`, pivot domains — session tokens in
  this class of app are backend-scoped, so they keep working on the sibling domain.
  Two follow-ons worth knowing: (a) the browser shows the same condition as
  `chrome-error://chromewebdata` and an in-page `fetch` fails with `Failed to fetch`
  even though cookies/localStorage are intact — check a sibling domain before
  declaring the target down; (b) **once you move to an un-banned sibling, plain
  `curl`/python may work again** — the per-IP wall was domain-scoped, so you can drop
  the browser transport entirely and go back to fast scripted requests. Harvest the
  full domain matrix early (from a pre-auth config endpoint or `localStorage`) so the
  pivot is one line, not a recon project.
- **An injected JS hook dies on any full page load.** `Page.navigate` (or any real
  navigation/reload) wipes your hook and every patched prototype — you then capture
  **0** headers/requests and misread it as "this endpoint is never called". Two ways
  out: (a) inject the hook and trigger the request with an **SPA-internal interaction**
  (real mouse click on in-app nav) so no page load happens; or (b) skip JS entirely
  and read CDP `Network.requestWillBeSent` events — `Network.enable`, then drain events
  with a timeout loop (`ws.settimeout(2)` + `recv()` in a try/except, keep looping),
  because a naive CDP reader that returns on the first matching `id` swallows every
  event. Re-inject after any navigation you do perform; never assume it survived.

## Pitfalls

- **Do not report a bypass you did not verify.** A `101`/`200`/handshake is not
  proof of access; read a real application response.
- Do not let "the wall is IP-based" become "this target is unreachable" — the same
  procedure that hits a wall usually hands you the origin.
- A passing exit is often transient. Re-verify with the same exit before
  concluding anything about the target's behaviour vs. your luck.

## Files

- `scripts/deobfuscate-obfuscatorio.js` — Node harness that executes an
  obfuscator.io script and dumps its own decoded strings + DOM side effects.
- `scripts/solve-acw-sc-v2.js` — solves an Aliyun WAF `acw_sc__v2` challenge page in
  a stubbed DOM and prints the cookie to replay (Node 8+ compatible).
- `references/cast-sec-case.md` — full worked example: header/UA/exit matrix,
  decoded challenge, origin identification, forged-header tell.
- `references/in-browser-request-forging.md` — Step 6 recipe in full: CDP-injected
  WebCrypto toolkit, re-auth inside the page, the React/mobile-H5 form-driving ladder
  (`Input.insertText`, `dispatchTouchEvent`, `requestSubmit`), and the captcha loop.

