# The operator's cluster behind the fleet — sibling systems on the shared ingress

Worked case 2026-10 (开云体育 ky 系 / 4号店 white-label family; same engagement as
`agent-panel-and-crypto-envelope.md` and `agent-panel-hardened-gates.md` — this file
covers only what sitting **behind** the fleet revealed). Ports/IPs/keys are case facts,
not the deliverable.

## 1. DNS shape

- The fleet's PC/H5 frontends and member site all proxy to
  `production-microservices.<cluster>` (hostname recovered from the `_app` bundle axios
  baseURL — the front only same-origin reverse-proxies it).
- The cluster zone is **wildcard**: `*.<cluster>` → one ingress IP
  (`16.163.79.238`); crt.sh on the zone returns the wildcard cert and every subdomain
  resolves. Naive HTTPS probing of individual names mostly yields empty/HTML — do not
  read that as "nothing here".
- The microservices hostname also has a **direct IP** (`16.163.250.188`) that answers
  the same API **without the brand front in the path** — no front WAF, no front rate
  limits.

## 2. Host-header enumeration of the zone

- Same one-IP ingress routes per-Host: send candidate `Host` values at its IP
  (`curl --resolve`), and diff bodies rather than status codes (a catch-all/HTML shell
  masks live API vhosts).
- Hit: `api.<cluster>` → a Chinese 「加固控制台」 = the operator's **offline APK
  hardening console** (a Baidu OASES-style build, `OFFLINE_DEPLOY:true` = the vendor
  tool privately deployed on their own cluster). This is the pipeline that processes
  their whole APK fleet — app packages, users, jobs.

## 3. The hardening console (open surface; login not yet broken)

- API prefix `/apkprotect/*` → Go backend; `/v5/`, `/v6/` → legacy nginx routes.
- Login: `POST /apkprotect/v1/login {name,password,captcha?}`; sibling
  `/apkprotect/v1/passport_login`; captcha endpoint separate. Weak-pass sweep
  (admin/admin, admin/123456, baidu/oases …) missed — **pending: captcha solve +
  wider creds, or an unauth route in the map**.
- High-value from the SPA's route map (not yet reachable): `/v6/apk`
  (upload-and-harden = pipeline RCE surface), `/v6/users` (user list), `/v5/jobs`
  (hardening jobs), product/order pages.
- Method: grab the 3.5 MB console bundle once, grep for `apkprotect/` + route names
  (`OFFLINE_DEPLOY`, `passport_login`) — the whole API map is inside; no blind walking.

## 4. Gateway / routing tells (Moleculer + front proxy)

- `production-microservices` root paths 404 — the probe surface is the **frontend's
  mounted proxy prefixes**: `/agent/api` (agent console backend, Go), `/fd/api`,
  `/stream/api`, `/dpty/api` (sports). Hitting the gateway root directly shows nothing;
  the front proxy is what maps path → service.
- Moleculer dialect: `/api/<a>/<b>` maps to action `a.b`; unknown actions answer
  `Service '<name>' is not found` — an addressable action space, **not** proof of a dead
  backend. Response bodies (including 404s) carry the service name you probed.
- A 404 page on the `/dpty/api` channel leaked the build string
  `main_refactor/master-boots-1008-y234569` — cheap per-instance fingerprint for sibling
  deployments.

## 5. Second backend

- `api.tu85ra.com` — a second backend observed while enumerating; not yet assessed.

## 6. Transferable

- Fleet backend in a wildcard zone ⇒ (a) take the direct IP, (b) Host-enumerate the
  zone for the operator's **own tooling** (build/ops/hardening consoles are the payoff,
  not more brand domains), (c) treat front-proxy prefixes as the real route map when the
  gateway root is opaque, (d) collect build strings from every 404 page.
