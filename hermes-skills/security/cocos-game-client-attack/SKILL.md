---
name: cocos-game-client-attack
description: "Use when attacking a Cocos Creator game client or backend."
---

# Cocos Creator Game Client Attack (CN gambling white-label families)

Class: white-label gambling platforms whose H5/APK client is a Cocos Creator build (Cocos2d-JS), typically fronted by a redirector shell and served from a rotating line-domain matrix. Siblings of one family share the same bundles and hardcoded secrets. For the specific 天元娱乐 / Playload / twCocos family (tyyl-* domains, 波币 wallet, tyhallkefu) see `references/tianyuan-playload-family.md` — it has the recovered keys, command numbers and infra map. The kefu (客服) side of these ecosystems — visitor APIs, agent consoles, WS/poll channels, XSS-to-agent camps — is its own class: `kefu-system-pentest`.

## Recon order (top to bottom, don't skip 1)

1. **Config buckets first** — these families park their line-domain list in a public-read bucket:
   - `{bucket}/urls-config/download.txt` → all line domains; `weibu-native.txt` → dynamic-address token (values like `asdfg` are REAL defaults, not placeholders).
   - Bucket naming: S3 `{proj}-res-<awsAcct>-<region>-an`; Tencent COS `{proj}-<cosAcct>` (hot-update tree `updir/{ProjName}/{ProjName}.json` + per-bundle `main.manifest` with full md5 asset table). Writes are usually 403 — read-only.
   - Domain formula to expand with `dig`: `{proj}-http-{slot}.net` / `{proj}-ws-{slot}.net` (+ `native-{slot}`, `ws-h5-{slot}` variants). A 502 on the root while `/source/`, `/ws` answer = dead shell, live API.
   - Version probe without pulling bundles: `{base}/updir/{ProjName}/{bundle}/{bundle}-ver.manifest` → `{"version":"x.y.z"}`; a `test/` subtree shows which env runs ahead. Tens-of-MB `*.png` objects in these buckets are disguised binaries (APK payloads) — keep one for lineage, not per-session.
2. **Pull the H5 build.** `GET /game/src/settings.<hash>.js` lists every bundle `{name, hash}`; scripts live at `/game/assets/{bundle}/index.{hash}.js` (+ `config.{hash}.json`). Path guesses 404 — get REAL URLs from the live page: open the game, read `performance.getEntriesByType('resource')` inside the same-origin game iframe, or hook fetch/XHR. Also grab `main.js`, `thirdGameTools/*`.
3. **Recover protocol from bundles.** Usually plain minified (some lazy chunks need `webcrack`). Grep and read around:
   - `X-Signature`/`X-Timestamp` → HTTP signing (e.g. `md5(ts + secret)`, secret client-side). Read the timestamp unit off the code (`Math.floor(Date.now()/1e3)` = SECONDS; sending ms breaks the sig). When an endpoint that used to answer starts returning 403 / `invalid signature`, re-grep and re-implement — the gate is transport-level, not authorization: the parameters behind it still need their own injection tests, and POST/PUT/DELETE answering a generic `internal error` is not a write primitive.
   - XOR'd response bodies: binary-looking answers the client still renders ⇒ grep for `v[n%10]`-style loops, a byte-array/`Int8Array` literal next to `TextDecoder`, then rebuild `bytes([b ^ key[i % len(key)]) for i, b in enumerate(resp)]`. JSON usually starts at offset 0; bytes after the closing `}` are padding.
   - `encryptJsonStr`/`decryptJsonStr`/`twEncipher`/`twPacker` → WS envelope `{"cmd":<int>,"jsonStr":"<b64 iv12||ct||tag16>"}` AES-GCM; key as b64 literal.
   - Auth frame: `{appId, timestamp(ms), nonce, sign: HMAC_SHA256(secret, "appId\nts\nnonce")}`.
   - Login sign: search `getSign` — e.g. `md5("machineCode=..&userName=..&wxOpenID=..&sjOpenID=..&password=..&key=<secret>")`; password is pre-hashed md5 (lowercase hex), never plaintext.
   - Command enums: `grep -oE '(Client|Server)Cmd=([0-9]+)\]="[A-Za-z]+"'`. Client/Server pair adjacently; numbering gaps = undocumented commands.
4. **Build a python WS client** — after this the surface is scriptable without the browser. Skeleton: `templates/cocos-ws-client.py`.
5. **Login-trust tests (biggest hole in this family).** TG/WeChat path sends `wxOpenID=<openid><channel-suffix>` with NO server-side initData validation → a synthetic openId logs in (auto-register); a real openId would be account takeover. Works on prod and test envs. If register is email-code gated and you can't receive mail, the openId path still mints an account.
   - Error codes are an oracle: build the tip-text table (e.g. `loginUserNotFund`=1002 vs `loginWrongPassword`=1001 vs catch-all like 1020) to tell field-placement bugs from real credential failures.
6. **Post-auth cross-player reads.** `SearchPlayerInfo {playerIndex:"6digit"}` returns arbitrary nickname/avatar/online state (user enumeration). Sweep neighbors + random samples across the ID space. Try playerIndex swaps on balance/record/mail commands too.
7. **Hidden-command scan** → section below.
8. **Provider chain.** Club/join commands (e.g. `JoinClubThirdGame {playerIndex, type}`) can return a third-party `gameUrl` carrying `uid` + `token=<REDACTED> Open it (mobile UA), hook fetch/XHR, pull the provider's own JS bundle for its `/api/...` surface and auth format; token/uid are then forgery & IDOR targets. Remember: third-party bypass never counts as completing the main target — keep pushing the main backend.
9. **APK side.** `jadx` the dex + `strings` all `.so`. Custom SDK libs (seen: "AppVest" = local proxy host `{proj}.http:1260`/`{proj}.ws:1260` + device fingerprint) explain webview device gates. `assets/main.js` is plaintext; `*.jsc` are XXTEA — key lives near `jsb_set_xxtea_key` in `libcocos2djs.so` (inspect call sites / Java-side key pass; naive key lists usually fail).

## Kill-switch scan — enumerate hidden server commands

- Send unknown `cmd` with empty params `{}`: silently dropped = command absent; **socket killed = command EXISTS but params invalid** (server exception path).
- Batch scans conflate this with anti-abuse kicks (N unknown messages → disconnect). Method: **one candidate per FRESH connection**, then a liveness probe (send a known-good cmd after ~1s; no reply = that cmd is a killer).
- Param-fuzz the killer list with bodies borrowed from sibling commands' call sites (`{playerIndex, type, terminal…}`). A change from KILL to a real response is the unlock — this recovered a full third-party game-entry flow.
- A full-range sweep that comes back 100% silently-dropped is a TERMINAL result: the reachable command set = the client's own commands, and the kill-range = server-internal commands (admin-gated) that stay kill even under fresh-connection param-borrow fuzzing. Log it; don't re-sweep the same range in later sessions.

## Wallet webview gates

- "设备类型不合法"-style blocks are often just a `navigator.userAgent` regex (`phone|pad|iPhone|Android|Mobile|...`). Bypass: CDP `Page.addScriptToEvaluateOnNewDocument` UA override at document-start BEFORE navigation; re-inject at the start of every browser session (injections don't persist across sessions).
- Entry links carry short-lived cred params (e.g. `p=base64('1;{"app_id":..,"key":..}')`) minted by a game API — fetch a fresh one per session; stale → "身份过期"/"key is null".
- Bodies may be decimal byte arrays (`1,209,194,...`) = binary protocol over HTTP; black-box UI testing works without decoding the format — prefer it when budget is limited.

## Vendor web apps on the same host (2nd/3rd API surfaces)

A vendor deploy/UAT host usually serves several front-ends on separate ports or paths — lobby shell (`:7000`), bet-history app (`/order/index.html`), agent console (`:7030`), bet-detail webview (`:7036`), mock merchant (`:7013`). Each is its own API surface with its own endpoint list and its own validator:
- The lobby manifest (`/lobby/manifest/loadfile*.json`) lists every JS chunk; endpoint literals (`/api/app/*.do`) live in those chunks, not the entry HTML. Pull and grep the whole set per app — the order app carried `record/*` endpoints the lobby shell never calls.
- Session tokens travel as header AND URL params (`?uid=&token=&game=`) and are forwarded into iframes/sub-apps. Test each downstream app separately; a token rejected by one front-end can still be accepted by another's API.
- Decode the token before attacking it: `base64("{uid}_{ts_ms}:{sig}")` = server-signed. Run the forge matrix ONCE (empty sig, zeros, same-length junk, uid swap, ts swap); identical rejections ⇒ stop forging and hunt the MINT — vendor consoles expose an enter-game call answering a full `game_url` with a fresh token, and that URL is the credential to harvest.

## Payment chain (recharge → gateway → callback)

Once the WS/API is scriptable, the deposit flow names every payment provider behind the platform without touching the shop UI:

1. **Dump the channel table from the protocol**, not the shop view: e.g. `GetRechargeInfo` → `{openChannel:[ids], channelsDetail:"<JSON string>"}` (each: channelID, channelName, paymentType, fixedCounts). `paymentType` sorts the fleet: 0 = aggregated Alipay/JD/bank gateways, 1 = bank card, 5 = crypto wallets, 6 = WeChat. Channel names sometimes embed the operator's deposit address (e.g. `数字货币@T...`).
2. **Mint ONE min-amount order per channel** with your own account — take the body shape from the client call site including its typos (server binds `palyerName`, not `playerName`). `strShowUrl` in the response = live checkout URL; `result:1` = channel offline. Each order is real and unpaid: min amount only, never another player's identifiers.
3. **Query each checkout unauthenticated.** Older gateways expose order state with no auth (`GET /getpay?id=<uuid>` → amount, internal `orderid`, payee nickname, QR payload, **`notifyurl`**). The `notifyurl` host is the platform's own payment-callback server — operator-owned, the priority target, not a provider.
4. **Fingerprint each gateway from its API 404/headers, not its UI.** RuoYi: unauth `/prod-api/captchaImage` answers `{"captchaEnabled":false}` (tells you login needs no captcha before you try) plus unauth `/prod-api/v2/api-docs`. Struts2: 404 text `There is no Action mapped for namespace`. Tomcat 404 pages print the exact version — a 9.0.x-era build means the Struts2 POC set is patched.
5. **Callback server** = one action per gateway brand (`/payServer/PayNotify<Brand>`; enumerate brands from channel names). Two response shapes from one action = two code paths (JSON body → lowercase `fail`, form/GET → uppercase `FAIL`); map shape first, then fields, and expect a signature gate. A notify that validates only order existence is self-credit proof, done with your own order id.
6. **Old Java stacks:** run the Struts2 POC set (S2-045/046/057/059) against the action path with the HTTPS tunnel as OOB; no callback = patched, archive and stop.
7. **Stop at the provider boundary.** Aggregators and wallets are third parties: record their stack + order APIs, but the deliverable stays the operator's own callback/backoffice. Order-page tokens are often JWTs — check `alg` first (RS256 kills forging), and an SPA shell that still renders for a swapped order uuid proves nothing until an XHR/JSON endpoint returns data.

## OOB ops

- **Match the callback scheme to the page that renders it.** An operator/admin console served over HTTPS silently blocks `http://` payloads (mixed content) — zero callbacks proves nothing about rendering. Put the listener behind an HTTPS tunnel (cloudflared quick tunnel → local port), re-send the probes, and keep the plain listener alongside.
- Before relying on your own listener for XSS/SSRF callbacks: verify internet reachability via check-host.net (`check-http?host=<url>&max_nodes=2`, then poll `check-result/<id>`) — don't assume the target's vantage can reach you. Behind a tunnel/CDN read the real visitor IP from `CF-Connecting-IP`/`X-Forwarded-For`, not the socket address.

## Pitfalls

- **get-or-create ≠ SQLi.** Repeated payload returns a stored record, but case-varied variants return DIFFERENT records ⇒ exact-string auto-create, not SQL (SQL-equivalent inputs would map to the same row). Check `createTime`: old timestamps mean other testers already hit that payload.
- Numeric-typed params silently drop non-numeric values — the injection candidates are string fields.
- A POST to a GET-only route may return a generic error shape (`code:1500 internal error` / uniform 401s) — stop param-fuzzing it and move on.
- Fastjson triage: `syntax error, expect {` = fastjson; `autoType is not support.` = closed — skip classic chains. Two sharper signals: `@type` anywhere in a WS frame body gets the socket silently killed ⇒ fastjson-family parser behind the gate; and closed autoType ≠ dead for the 1.2.68+ URL-probe class (`jar:http://` @type) — but that only executes when the JVM classloader resolves URLs (fat-jar `LaunchedURLClassLoader`). Verify with a UNIQUE-TAG OOB URL + timing side channel (blackhole host: hang = fetch attempted, instant rejection = no fetch); zero callback + instant rejection = archive it, don't re-spend.
- Vue devtools-hook (`__VUE_DEVTOOLS_GLOBAL_HOOK__.apps`) only receives `app:init` if prod devtools was enabled at build; silence = stripped, don't sink time.
- WS connections may die from malformed messages or rate patterns — always liveness-probe before classifying a test as "no response".
- Same account can exist on prod but not on test (separate DBs) — try both endpoints before ruling the account bad.
- **Server push pollutes command/response matching.** After sending cmd X, the next inbound frame may be an asynchronous broadcast or another command's reply (`msgCMD` different from the expected one). Match by `sessionId` + expected command number and drain several frames; reading the first frame as "the answer" invents results. A silently ignored command (wrong param shape) is not proof the command or params are invalid.
- A signature/WAF page (`invalid signature`, 403, custom 461) is a GATE, not a dead end: compare against real client traffic for a required header, and re-test with the client's full header set before calling a path absent.
- **Probing HTTPS by IP puts the IP in the SNI.** Host-based WAFs then answer SSL error / reset / `400 host_not_found` even with the correct `Host:` header — probe vhosts with `curl -k --resolve <host>:<port>:<ip>` (or `ssl.wrap_socket(server_hostname=<host>)`) and treat an SSL error on a vhost as a probe artefact, not a block. A uniform listener set on every node (80/443/8080/8443 + alt ports) is one WAF, not many services — fingerprint one node and stop.
- **RuoYi-style login throttles can be system-wide.** `操作频繁，稍后再试` from the very first attempt, unchanged across fresh Tor exits and spoofed XFF = a global limiter (or a broken backend), not an IP ban — don't burn circuits. Use the unauth `/prod-api/captchaImage` + `/v2/api-docs` meanwhile and retry once after the window.

## Deliverables

- Case dir `/root/cases/<target>/` with `loot/` + `REPORT.md` (Chinese): 漏洞列表 + 攻击链 + 证据 + 修复建议, plus the recovered protocol constants so the next session doesn't re-derive.
- Support files: `references/tianyuan-playload-family.md` (family dossier), `templates/cocos-ws-client.py` (WS client skeleton).
