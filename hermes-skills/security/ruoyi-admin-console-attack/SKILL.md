---
name: ruoyi-admin-console-attack
description: "Use when a RuoYi/Spring admin gateway is exposed."
version: 1.0.0
tags: [pentest, ruoyi, spring-boot, admin-console, swagger, jwt, mfa, redteam]
---

# RuoYi / Java admin-console attack

Load this when a target exposes a Spring Boot admin backend, especially the RuoYi family
(RuoYi, RuoYi-Vue-Plus, and forks). Fingerprints: `/swagger-resources` answers, module-scoped
`/v2/api-docs`, `com.<vendor>.system.api.model.LoginUser` class names leaking in cast errors, and
HS512 JWTs shaped `{user_id, user_key, username}`.

The whole point of this skill: an admin gateway usually exposes far more than the customer app,
and the *hard* part is almost never the password — it is (a) knowing which controller you need and
(b) understanding that a valid token is not the same as an authorized token.

## 1. Find and map the gateway

- One host fronting several modules IS the admin gateway. Probe sibling base paths (`/hosting-api`,
`/admin-api`, `/manage-api`, `/api`) — the one that answers with business JSON is it; the others
fall back to the SPA index or an nginx `405`. A `405` from nginx (not the gateway) tells you the
location belongs to a different server block, not that the API is absent.
- `GET <gateway>/swagger-resources` returns the module list; each entry exposes
`/<module>/v2/api-docs`. **Dump every module** (system, the app module, hosting, the agent/team
module, schedule, auth, message). Response is a Springfox/RuoYi `swagger:2.0` doc — read each
doc's `basePath` and `paths`.
- The destructive admin CRUD lives in these docs even when the UI never shows it. Look for
`{ids}` DELETE, `changeStatus`, `destroy*`, `recovery*`, `export`, `importData`. Example of the
class: `iImgroupinfo/destroyTeam` and `iImgroupinfo/{ids}` sit in the same controller as its list.
- Build the endpoint list from the docs, never from a guessed verb wordlist. A 1500-path guess
sweep found 2 routes; the docs name all 477.
- Also read each doc's `definitions` block: it hands you the exact request body, including
server-side-only fields (owner, newOwner, expireTime) the client never sends. Field names are the
difference between a param error and a useful probe.

## 2. Login endpoints and the credential oracle

- Enumerate per-module logins: `/auth/login`, `/<module>/login`, `/<module>/<userTable>/login`,
`/system/login`. Some are real logins, some merely demand a token (respond `令牌不能为空`) — that
distinction tells you which module owns authentication.
- The error strings are a three-way oracle and it is the most useful thing on this surface:
  - unknown user -> "Login user:X doesn't exist." / "用户不存在"
  - known user, wrong password -> "Wrong user name or password"
  - known user, correct password, MFA pending -> "please enter code" / "请输入验证码"
- Use it to enumerate usernames cheaply, and remember the third case is the actual hit: it proves a
credential without needing the second factor. Any account with no MFA bound returns a token
directly on a correct password.
- Case variations of one name usually resolve to the same account — dedupe before declaring a
second admin.
- Registration endpoints (`/auth/register`, `/system/user/register`) are frequently present but
disabled ("registration is not enabled"). Test once, then stop building on them.
- Field names: read them out of the error messages rather than guessing (`请输入值` = the field is
`value`; `请填写appid` = the field is `appid`, lower-case).

## 3. MFA — measure the lockout before brute-forcing

The password is often already known and the second factor is the only gate. Before spending hours:

- Send ~10 wrong second-factor codes and read the responses. Deployments that validate a 6-digit
TOTP with no counter and no lockout are brute-forceable: space 1e6, ~3 codes valid at any instant,
expect a hit near ~333k attempts. Never attempt this on an endpoint that locks.
- **Measure the password lockout separately from the TOTP field.** A full-login body that resends
`username+password+googleCode` on every attempt can still trip `密码错误过多锁定…分钟` even when
the TOTP field itself never locks. Treat any password-lock / account-lock string as an immediate
kill of the scan — cooldown, then one manual unlock probe before resume. Do not keep the range
splitters running "because TOTP had no lock".
- Transport for the scan is a per-IP rate-limit problem, not a target problem — see
`waf-evasion-and-credential-attack` §3 (Tor SOCKS-credential circuit isolation) and §4 (harness
engineering, progress persistence). A four-way range split kept the scan resumable and roughly
tripled aggregate throughput.
- Persist the hit immediately to a file, not to stdout — runner output redacts secrets, so a token
printed to the log is a token you cannot use. Write it to disk and have the next stage read it.
- After a successful admin login, assume single-session and **stop every other login-generating
job** against that account. A later CF/WAF hard-ban on the admin host is common once the IP
reputation is burned; pivot the same token (while live) to any weaker origin that serves the same
module paths, and treat re-login as a separate campaign with a cool egress matrix.

## 4. Read the token model before claiming access

This is where most of the time is lost. Decode the JWT.

- RuoYi-Vue-Plus base claims: `{user_id, user_key, username}`. Forks add their own, commonly
`login_type` and `login_scope` (e.g. `login_scope: "manager"`).
- **A valid, correctly-signed token can still return `access deny` on admin-CRUD controllers while
working perfectly on customer-facing app APIs.** Map real capability empirically: fire one request
at a spread of endpoints across every module and record which answer with business JSON.
- When one token is allowed on some paths and denied on others, the gate is the application's
permission/scope check, not the signature. Path-encoding tricks, dot-segments, case changes,
duplicate slashes, method swaps and scope-ish headers (`scope`, `login_scope`, `X-Scope`) do not
bypass it — confirmed dead end, do not sink time there.
- Fork-specific scope claims are set by the login endpoint. Body params and a `clientid` header
(`clientId`, `clientid`, `clientId`+`tenantId`, `grantType`, `userType`, `deviceType`) all failed to
change it. Verify once, then stop turning those knobs.
- Distinguish "endpoint reachable", "endpoint authorized", and "effect achieved" in the report.

## 5. Session model — single-session is the silent campaign killer

- Assume single-session: **every successful login invalidates previously issued tokens.** A
TOTP-scanning job that logs in on every hit will kill the token you are actively using, mid-run,
and every request starts returning the expired-session string.
- Consequence: never run a login-generating job concurrently with token use. Find the code, log in
**once**, persist the token, then run the whole test battery against that one token with no further
logins.
- Symptom to recognise: an endpoint that worked minutes ago suddenly returns `登录状态已过期` for
the same token, including on paths that were fine. That is the session being replaced, not the
endpoint changing.

## 6. Shared JWT secret between admin gateway and customer app

- RuoYi-Vue-Plus deployments often sign the customer app and the admin gateway with the same HS512
secret. Test cheaply: re-encode the payload with modified claims, keep the ORIGINAL signature, and
send it.
  - signature error (`令牌已过期或验证不正确`) -> the secret IS enforced, and your untouched token
    passing that check means the gateway accepted a customer-app token structurally.
  - authorization/business error (`access deny`) -> the token was accepted; the remaining gate is
    the user/role lookup, not cryptography.
- If the signature is accepted, offline cracking only pays off when the secret is human-chosen.
A full rockyou run against HS512 costs about 80s and is worth doing once; a random secret will not
fall and you should stop.

## 7. Params-before-auth: finding token-less module APIs

Some module controllers skip the token check and validate parameters first. An unauthenticated
request answered with "please enter X" proves a route that needs no token — sweep the whole
documented endpoint list anonymously and collect those. This is how the manager/admin helper APIs
(team, group, friend, official-account operations) surface as reachable without a session.

- Those same APIs are usually gated by a **separate shared secret** (an `apiKey` field) checked
AFTER parameter validation. That is where the remaining effort goes, and it is not guessable from
platform names — treat it as a leaked-credential hunt, not a wordlist target.
- Internal-only paths (`/inner/...`) are typically filtered at the edge and answer with the WAF
page on every ingress; do not spend a cycle on them unless an origin path split says otherwise.
- Before wordlisting the shared secret, hunt for a **public SaaS in the ecosystem that already
holds it**: a partner/agent site on a secondary port of the same origin IP that proxies the same
helper calls with its own developer key. Its docs and portal map the key's capabilities and open
new oracles. See the reference for fingerprints.

## 8. Generic setters and resource scope

- A `{subject, type, value}` setter authorizes per-RESOURCE (owner/admin of that subject), and the
authorization check runs BEFORE the type lookup. Probing a victim resource therefore collapses to
one permission string for every type and teaches you nothing. **Create your own resource of that
class first, then enumerate the type domain against it** — the validation error only appears once
you own the subject.
- Int type domains are SPARSE. Sweep a contiguous range (0..20) instead of assuming 1..N, and
record which values are accepted versus `类型不存在`.
- Platform "shards"/servers are part of app-API authorization scope. A token issued for server A
gets *not-found* errors (`群组不存在！`, `...不属于当前服务`) for server B resources, and a body
`serverId` does not switch context. Confirm the shard before reporting a resource as absent — the
same id resolves once you hold a token for its server, and per-shard actions (including reports)
are impossible until then.

## 9. Reporting discipline

- **An account you registered yourself is not an account takeover.** Verify an account belongs to
the target (age, data, other users' references) before counting it as a win; a self-created test
session is a test fixture.
- **When the objective is to destroy or remove, verify the candidate endpoint actually removes.**
Guard the goal in the wording: a renew/recharge/restore/`openGroup` fee path is the opposite of
the goal even when it is the easiest reachable action, and proposing it reads as not having
understood the task. `余额不足` on those fee paths only proves the resource is billable — it is
not a dismiss lever and must not be offered as one.
- Report three layers separately, never collapse them: **endpoint reachable** (`令牌不能为空` /
cast error) vs **authorized** (business JSON, not `access deny`) vs **effect achieved** (re-read
shows the resource gone/changed). A manager-scope token that lists orders but cannot
`destroyTeam` is a partial map, not a failed destroy claim and not a full admin compromise.
- Report capability boundaries as measured, not aspirational: list what the token actually did,
not what the endpoint name suggests it should do.

## 10. Depth notes

- `references/ruoyi-satoken-druid-chain.md` — Sa-Token random-token mode (non-JWT) detection, front/back auth isolation, Druid console intelligence extraction, password hash leak via getUser (PBKDF2-SHA1/10000), Actuator bypass dead ends against Sa-Token global interceptor, APK source mining for auth flow.
- `references/openim-v3-attack-surface.md` — OpenIM v3 admin token brute-force (operationID header required), user token endpoints, MinIO bucket exploitation for chat media/PII, domain discovery pattern (im./iml./minio. prefixes).
- `references/ruoyi-vue-plus-surface.md` — concrete endpoint/field shapes for module discovery,
login oracles, the `type`/`value` setting pattern (incl. a worked int-enum probe and the
ownership-before-type ordering), `managerApi`-style shared-secret APIs, the public partner-SaaS
fingerprints, shard/server scoping, and the admin-CRUD paths that stay scope-gated.
- `references/destroy-authority-matrix.md` — when the goal is group/team dismiss: which principal
(TIM owner userSig vs platform admin CRUD vs managerApi apiKey vs member recon) can actually
remove the resource, and which nearby fee/report paths must not be substituted for dismiss.
