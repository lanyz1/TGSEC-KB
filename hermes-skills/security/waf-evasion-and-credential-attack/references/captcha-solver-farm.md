# Captcha-gated credential attacks — solver farm + consumer

For login/registration endpoints that flip on a vendor captcha (Aliyun 阿里云 slider class:
sceneId + prefix + region) after the operator notices an attack. The endpoint stops returning the
password verdict and starts returning a "complete the captcha" error instead.

## 1. Detect the gate before designing the run

- Poll the platform's login-settings endpoint at EVERY run start (e.g. `password-login-setting`
  returning `{captchaRequired, captcha:{sceneId,prefix,region,enabled}}`). It flips mid-campaign —
  `false` at the start of a case is not a fact later.
- Error-shape map (same errorCode, different meaning):
  - sent WITHOUT captcha fields → an "upgrade your app to the latest version" style error
    (the 10322 class). It reads like a client-version gate; it is NOT — it means "no captcha
    attached". Do not go download a newer APK for this.
  - sent WITH an invalid/expired solution → "complete the captcha" + `captchaVerifyResult:false`.
  - sent WITH a valid solution → the normal business verdict (e.g. wrong-password).
- Solutions are single-use: one solve authorises exactly ONE attempt. A rejected solution did not
  count as an attempt — retry the SAME candidate with a fresh solve.

## 2. Solve from a LOCALLY-HOSTED captcha page

The vendor page usually depends only on the vendor's public CDN script — not on the target origin:

1. Fetch the target's captcha page once (`/captcha/index.html?region=..&prefix=..&sceneId=..`) and
   read sceneId/prefix/region + element ids + the init call out of the HTML.
2. Save it as a local page. Either stub the app bridge (`window.flutter_inappwebview.callHandler`
   that captures the solved payload + fire any `...PlatformReady` event the page waits on), or
   re-implement the vendor init call directly (`initAliyunCaptcha({SceneId, mode:'popup', element,
   button, slideStyle, ...})`).
3. Serve it from localhost and drive it with Playwright. This keeps working even when the target
   origin is WAF-blocked for your egress — the page never touches the origin.

## 3. Solve mechanics (what passes server-side verification)

- **Real mouse only.** JS-synthesised Pointer/Mouse event chains register inside the widget but fail
  the vendor's server-side verification. `page.mouse.move/down/up` is the only reliable transport.
- Click the start button → wait for the slider element → drag with an S-curve: eased acceleration,
  fast mid-section, deceleration + slight overshoot then correction before `mouse.up`; gaussian
  jitter on both axes; ~40-80 small steps with variable inter-step timing (~5-30ms).
- Poll the page for the solved payload (the bridge / `captchaVerifyCallback` parameter) with a
  timeout — a frictionless-mode solve may complete with no drag at all.
- Typical cost: ~7-10s per solve per headless-browser worker, page load included.

## 4. Farm architecture — decouple solvers from consumers

- **Solver workers**: N separate processes, each with its own browser, each looping solve → write
  token file into a queue directory (timestamped idempotent name). Throttle when the queue is deep.
- **Consumer**: the credential harness claims a token by atomic rename (`.param` → `.taken`),
  enforces a TTL (~120s — stale tokens fail verification), submits through whatever egress tier the
  platform currently accepts, and applies the consumer rules below. Parallel consumers (10+) are
  fine; retry a transport failure through a different egress WITHOUT consuming the token.
- Throughput math: solver count × ~1 solve / 7-10s is the campaign ceiling. Measured: 5 workers ≈
  15-20 solves/min; a 12-way consumer saturates that and no more — adding consumers beyond the
  solver rate just starves.

## 5. Consumer rules (each is a footgun when missed)

- **Never advance the candidate index on `captchaVerifyResult:false`.** Only server-consumed
  attempts advance it; rejected solves are retried (same candidate, fresh token). Advancing on
  rejects silently skips candidates and corrupts the resume point.
- Classify every response as wrong-credential / rate-limited / lockout / captcha-rejected /
  transport-error / unknown. Captcha rejection is its own class — never a hit, never a negative.
- One solve per attempt: do NOT pre-queue hundreds of tokens; they expire and burned tokens are
  solver time lost. Keep the queue shallow (~3-5) and consume the NEWEST token first (LIFO) — FIFO
  hands the consumer the tokens closest to expiry.
- **Verify token transferability per deployment.** Solving on one IP and submitting through another
  (proxy) is ACCEPTED on some deployments of this class (verified: local solve → submit via free
  proxy → `captchaVerifyResult:true`), and rejected on others (browser-session-bound). Before
  scaling, register one known flow: solve → one junk-password attempt through the intended egress →
  inspect `captchaVerifyResult`.

## 6. Volume vs acceptance — the vendor rate-limits solving itself

- Acceptance degrades under volume: ~50% rejects observed after a few hundred solves from one
  IP/fingerprint class. Rejects are retryable, so the run survives — budget for the loss.
- Mitigations in order: pace the solvers; rotate the solver fingerprint class (desktop ↔ mobile
  emulation buckets are counted separately by the vendor); rotate solver egress; for one-shot flows
  (registration) just retry — one good solve is enough.
- Never treat "the browser produced a token" as "the server accepted it" — only
  `captchaVerifyResult:true` on the business response proves it.
- **The solver IP itself accrues risk and can burn to ~0% acceptance.** Measured regression:
  ~100% acceptance early → ~50% after a few hundred solves → near-total rejects after sustained
  volume from one server IP — while solves issued from a clean PROXY were accepted by the same
  submit path. Solve+submit through the SAME clean lane is the strongest configuration (every
  accepted registration solve was same-proxy; local solves were rejected). A/B it in one call:
  solve via proxy → one junk attempt through that same proxy → read `captchaVerifyResult`.
- **Pin the lane in the queue.** Write each token file as `token|proxy`; the consumer submits
  through that same proxy first (other transports only as fallback), so solve IP and verify IP
  match even while consumers parallelize.
- **Lane hunting is its own job.** Most pool proxies fail one of the two halves — mechanics (the
  widget needs seconds of heavy CDN JS; slow proxies never become ready, fast-fail ≈50s) or risk
  (solve rejected server-side). Run a lane tester that loops the pool performing solve+verify as a
  UNIT and records the proxies that pass both; pin solvers to that golden list at low rate and
  re-test as lanes decay. Expect single digits of golden lanes per hundred candidates.
