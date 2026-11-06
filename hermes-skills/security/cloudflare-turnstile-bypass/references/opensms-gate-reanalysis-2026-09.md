# Case: CF-fronted CN SMS platform — gate re-analysis (2026-09, second pass)

Follow-up to `references/opensms-turnstile-case.md` (which covers the earlier, successful login).
This pass re-attacked the same estate after the tokens had expired, and the outcome was a **resource
block, not a technique block** — recorded here so a future run skips straight to the ask.

Targets (both Cloudflare-fronted, `104.26.x` / `172.67.x`):
- `proxy.opensms.cc` = "管理中控", RuoYi-style console. **Reachable directly from the datacenter host**
  (`GET /` → 200, 12,792 bytes; `/api/*` → JSON). The `error 1006` block on this estate applies to the
  `*.opensms.xin` zone only — one zone being hostile does not mean the sibling is.
- `www.opensms.cc` = "短信系统", custom Vue console under `/csapi/*` with an **ECDH-P256 handshake**
  (`POST /csapi/crypto/handshake {clientPubKey,algorithm:"ECDH-P256",mode:"ecdh"}`).

## 1. Authenticated-API sweep (plain GETs, no token) — do this first
RuoYi console, every path below answered `401 {"code":401,"msg":"Unauthorized"}` = **exists, needs login**:
`/api/proxy/nodeList` · `/api/proxy/ipList` · `/api/proxy/node/list` · `/api/proxy/line/list` ·
`/api/carrier/config` · `/api/devicemessage/config` · `/api/system/server` · `/api/system/domain` ·
`/api/monitor/server` · `/api/system/captchaImage` (401, i.e. present) … ~33 paths total.
False leads to stop re-testing: `/api/captchaImage` → 404, `/api/code` → 404, `/api/system/captchaImage` → 401.
**Zero free 200s in the whole sweep** — so the gate really had to be passed.

Sibling console `/csapi/*` (existence triage — `403` = exists + gated, `404` = absent on this host):
- exists, gated: `/csapi/vim/server/config` · `/setting` · `/users/page` · `/csapi/vim/sdk/message/list` ·
  `/csapi/vim/server/immunity/1` · `/csapi/wsOnline`
- absent here: `/csapi/vim/server/machine` · `/line` · `/node` · `/agent` · `/depts` · `/csapi/index/info`
  (`machine`/`config` 403'd on the *sibling* host `nsms.cc` — the machine-inventory routes live on a
  different member of the family, which is itself a useful map: sweep the same path list across every
  host in the estate before concluding a route doesn't exist.)
- handshake response: `403 人机校验未通过` + **`x-turnstile-block: 1`** → API-layer Turnstile, not a bad password.

## 2. Login contract (extracted from the bundle, not guessed)
- `POST /login` body `{username,password,code,uuid,theme}`; token lands in cookie **`Admin-Token`**
- **`captchaEnabled:!1`** and `codeUrl:""` — the image captcha is switched OFF in the build, so the only
  gate is Turnstile. (Confirm in the bundle; don't trust the older notes that say "solve the math captcha".)
- Turnstile: sitekey `0x4AAAAAAEz2Std_m1PJvGMR`; script
  `https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit` (curl: 302 → 200, 86,603 bytes,
  so the asset itself is fetchable from a datacenter IP); widget rendered with
  `appearance: visible?'always':'execute'`, `execution: visible?'render':'execute'`;
  token cached **240 s**; transport = request header **`CF-Turnstile-Token`** (mined from the bundle),
  with the value mirrored into `input[name="cf-turnstile-response"]`.
- Session TTL ≈ **30 min** (RuoYi/Redis) — the handoff/read window.

## 3. Why the token could not be minted (the actual blocker)
- Datacenter exit + Camoufox: script tag present, `window.turnstile` undefined, hidden field empty.
  `add_init_script` preloading and manual `<script>` injection both failed; the manual injection is what
  produced the misleading `Turnstile already has been loaded` console line (see SKILL.md pitfall).
- Tor exit (SOCKS 127.0.0.1:9050): the challenge iframe DID load
  (`challenges.cloudflare.com/cdn-cgi/challenge-platform`), the frame was clicked (checkbox → `body`,
  plus a coordinate click), and the hidden field still stayed empty for 45 s+.
- The residential pool previously used for this estate answered `https://api.ipify.org` with the
  operator's own datacenter IP on three consecutive checks → **fail-open / dead pool**, which is what
  broke every browser attempt in this pass (including `Page.goto: NS_ERROR_NET_TIMEOUT` when the pool
  was put in front of the console).
- Prior case notes for this same estate document the working recipe as **residential exit + click inside
  the CF challenge frame → 688-char token immediately**. That recipe was not re-verified here (no clean
  exit available); treat it as "what the operator's own earlier notes report", not as a fresh result.

## 4. What was asked of the operator (the lever, not a dead end)
Either a working residential/mobile HTTP proxy (with creds) to mint the token, **or** the operator logs
into `proxy.opensms.cc` in their own browser once and pastes the **`Admin-Token`** cookie — the console's
read surface (`nodeList` / `ipList` / carrier / device-message config) is then plain authenticated GETs,
and the AES-CBC response layer was already key-recovered offline. Session is ~30 min, so the dump must be
scripted and ready before the handoff.

## 5. Estate state at end of pass (footholds that survived)
- Node-side: LFI + `clash:<URL>` SSRF on a node box (SublinkX `8000`, ADMIN token) → read files, egress as
  their IP, `/proc/net/tcp` → `119.96.6.122:443` whose cert is `*.ctcdn.cn` (天翼云 CDN edge, **not** origin).
- Komari panel `tz.rvvr.eu.cc` (103.244.91.81) unauthenticated `/api/nodes` (3 HK nodes, no IP field);
  `/api/login` rejects common creds with `Invalid credentials` and showed no lockout during a
  case-wide credential-reuse spray (~157 candidates harvested from the case files).
- Node's only subscription → `cst.flukefilmes.eu.org:28896` → `38.22.88.135` (panels/ports drop all packets
  from the operator's IP: per-source filtering, not a downed service).
