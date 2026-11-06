# Agent-panel takeover on an AES-enveloped multi-tenant betting platform

Worked case: an SEO shell ("挖币赚钱软件 2025") funnel led to a **KAIYUN / 开云体育**
white-label sports-betting stack. Player side was hardened correctly; the **agent
(代理) panel was the open door** and yielded a renewable authenticated foothold.
Values below are structural placeholders — never carry live keys/tokens into a skill.

## 1. The funnel shape (spider-gated)

```
SEO landing (static Bootstrap, last-modified months old)
  └─ ad.js:  if UA ~ /spider|bot/  -> return (serve nothing)
              else -> inject fullscreen iframe -> mid-tier "forum" domain
        tj.js:  Baidu tongji id (an operator-cluster fingerprint worth grepping)
  └─ forum domain = Z-BlogPHP ("<sport>-论坛", sibling .co/.com) on its own IP
        home hides  s.src = atob('<base64>')  -> jump.js
  └─ jump.js / g.js -> real platform  +  a white-label app domain (/p/<code>)
```

Two transferable bits: the **UA gate in ad.js** means every tool-based fetch must
send a browser UA or you get an empty page, and the **`atob(...)` in the home
bundle is a hop, not decoration** — decode it before assuming the forum *is* the
target.

## 2. Stack identifiers

- `server: apeiro8` on some vhosts, `server: gocache` + `c-type: df` on the player
  app, `x-kong-upstream-latency` -> **Kong API gateway** in front.
- Next.js player front (SSR `/entry/login`, `/entry/register<code>/`) with
  `data-commit-info="<branch>/<sha>"` in the HTML — leaks the vendor's branch name.
- Route prefix `/page/fd/api/v1/*` — `fd` matched a previously-seen `fd-admin.jar`
  from an unrelated target, i.e. **a shared supplier**. Treat route prefixes as
  vendor fingerprints and cross-reference your own case archive.
- Multi-tenant: `/site/api/v1/configuration/preInfo` returned `id=1 name="4号店"`
  ("store #4") -> tenants 1..N exist, each with its own brand/title/captcha config.

## 3. The crypto envelope — invert it, never brute it

The player API is POST-only, body is a single wrapper field:

```json
{"x": "<base64( AES-256-CBC-Pkcs7( json ) )>"}
```

Responses are encrypted the same way. Recovery path, in order:

1. **Find the unauth key store.** `POST /<svc>/api/v1/sec/<RandomName>` with an empty
   body returned `{"k":"<base64 32B>","v":"<base64 16B>"}` — the AES key+IV, no auth.
   The same endpoint is per-service (`/site/...`, `/act/...`, `/page/fd/...`) and
   returned the **same pair for every `X-API-XXX` prefix** = one global signing key.
2. **Find the crypto core in the bundle.** Grep the chunks for a small module
   exporting two functions (seen as `HI` = encrypt, `pe` = decrypt) with the default
   `var l = "<32-char string>"` used as **both key and iv**. Note the bundle also
   ships separate keys for long-string decode and for token storage — match the key
   to the field you are decrypting before assuming a decode failure means wrong key.
3. **Match the wire shape before blaming the crypto.** A working AES roundtrip still
   returned `6003 非法请求` until the header family was complete.

Required header family (all of them; partial sets return the auth-shaped errors):

```
X-API-CLIENT: h5      X-API-XXX: <first two path segments>
X-API-VERSION: 1.0.0  X-API-SITE: <tenant id>     X-API-TYPE: h5
X-API-UUID  X-API-FINGER  X-API-ORIGIN-SITE   + cookie X-API-TOKEN (user state)
```

Status-code map (each code is a distinct, useful oracle):

| code | meaning |
|---|---|
| 6000 | success |
| 6001 | needs login (also the 30-min idle logout message) |
| 6003 | illegal request (missing/incorrect header family) |
| 6004 | **user/agent does not exist** — enumeration oracle |
| 6005 | request failed (generic) |
| 6008 | parameter error |
| 6020/6021 | image captcha required |
| 6022 | **GeeTest required** — *not* a success code |
| 6023 | captcha disabled |

`6022` is the trap: it reads like a success/pass-through code and will be mistaken
for a login result. It means "solve the captcha."

## 4. Unauthenticated leaks that were the whole engagement

1. **Tenant config** — `POST /site/api/v1/configuration/preInfo` (no auth) returned
   the operator's full domain map: `agentPcDomainUrl`, `agentH5DomainUrl`,
   `pcDomainUrl`, `siteDomainUrl`, `h5StreamlineDomainUrl`, **80+ `whiteDomain`
   entries**, customer-service infrastructure, and the tenant name/id.
   → *This is how you find the panel.* Always call the `preInfo` / `site_config` /
   `getSiteConfig` family unauth before guessing panel hostnames.
2. **Global API signing key/IV** from `sec/<RandomName>` (above).
3. **RSA-2048 keypair, private half included** — `POST /agent/api/v1/security/getRsaPrivateKey`
   returned the PEM with no auth. Siblings in the same namespace: `getQrcodeAndSecret`
   (2FA seed), `bindVerify`, `getSecurityQuestionNoLogin` (security question by
   username). **Always sweep the agent API's `security/*` namespace unauth.**
4. **Enumeration oracle** — the password-reset *step 3* endpoint
   `POST /site/api/v1/user/forgetByPhone/<Random>` was callable standalone with no
   session, no phone, and no prior steps: bare `{"name":"x"}` -> `6008`, then
   `{"name":"x","phone":"y"}` -> `6004 用户不存在` vs `账号和手机不匹配`
   (account exists, wrong phone). Free user enumeration + `admin` confirmed real.
   The generalisable move: **reset flows' later steps are frequently reachable
   without their prerequisites** — enumerate each step as a standalone endpoint.
5. Agent-side oracle: `security/verifyInformationLoginUnverified` -> `代理不存在`,
   `getSecurityQuestionNoLogin` takes `username`.
6. CORS `Access-Control-Allow-Origin: *`, rate limits in response headers
   (player 120/min, agent 60/min) — read them instead of discovering them.

Also open unauth: `operation/queryHotGameDialog`, `advertising/queryBannerList`
(returned thousands of rows with DB audit timestamps), `venue/sort`,
`configuration/vvPretty`; and `video/getAnchorShowSetting` leaked an internal admin
name in an `updateBy` audit field. Audit fields are a cheap insider-name source.

## 5. The winning move: the panel's own signup

The player side was **closed platform-wide**: 14 domains, the operator's own invite
code, and all **five official agent promotion links** returned a generic
`注册失败` (platform policy — genuine field errors return *field* messages, so a
generic failure after the fields pass is policy, not your payload).

But the **agent panel is a separate app with its own registration**
(`agentPcDomainUrl` from the config leak), and it gated on **only a plain
4–6 character image captcha** — no GeeTest. That signup succeeded and landed an
authenticated back-office session.

Sequence: open panel root -> `立即注册` -> fields (username / password / confirm /
captcha) -> solve image captcha -> registered -> `/home?showWelcome=true` with a
`X-API-TOKEN` session and a 合营编码 (affiliate code).

Notes that cost real time:
- Username rule leaked on submit: `<4-11 chars, starts with a letter, >=2 letters + digits>`.
  The 12-char first attempt was rejected. **Read the rule, do not retry blindly.**
- Password rule likewise: `8-12` chars (a 13-char choice was rejected).
- The registration page first calls `POST .../user/member/kaptchcate` with
  `{"kType":4}` and *then* renders the botion challenge — the captcha type is
  server-chosen per tenant, so a payload that hardcodes the captcha type will be
  rejected at policy level even when every field is correct.

## 6. What the agent panel gave up once inside

Player/agent accounts are **separate systems** — the agent account does not work on
the player entrance (and vice versa). Routes reachable:

```
/home                      commission dashboard (rate, net win/loss, active, first-deposit)
/member                    downline member list, bet/status filters
/promote                   ★ the 5 official recruitment links (below)
/commission  /commissionSimulator  /memberBonus  /commission/activeMembers
/subTeam                   下级代理 / 团队佣金 / 返佣方案
/subTeam/newSubAgent       ★ create a sub-agent (username + password + image captcha)
/subTeam/teamCommission/{commissionDetail,settleCommission,settleRecord}
/agentDeposit[/history[/detail]]   agent deposit records
/mine
```

Agent API (authenticated): `member/getAgentInfo`, `member/list` (requires
`startDate`/`endDate`, else "数据量过大请缩小范围"), `finance/draw/initMoney`,
`queryMonthOverview`, `member/getAgentDepositConfig`, `getAllGameVenue`,
`dict/dictTypeQuery`, `sysBasic/setFlag` (returns 成功 — a write endpoint),
`unlimitedAgent/list`, `communicate/getSwitch`.

- `/promote` leaked **five additional domains** plus the agent's own sub-code in
  the path (`/entry/register<subcode>/?i_code=<affiliate code>`) — a per-agent
  recruitment funnel. Harvest these before concluding you are out of surface.
- **Team model config leaked** via `getAgentDepositConfig`: `showTeamModel:1`,
  `teamModelSetting {min,max,stint}` — feature flags you can act on.
- Session expires on **30 min idle** with a `6001 系统检测到您30分钟内无任何操作…`
  message; the credentials + a fresh image captcha log you straight back in
  (verified twice). Report this as a **renewable foothold**, not a one-shot.

## 7. What was closed, and the honest reason

| surface | blocker |
|---|---|
| player signup | platform-level policy (`注册失败` everywhere, incl. official links) |
| player login | GeeTest solvable, but **no valid credential** — agent accounts are not player accounts |
| agent IDOR | endpoints correctly scoped to session; changing `agentId`/`memberId`/`uid` is inert |
| agent privesc | `updateAgentConfig` whitelists; admin fields (`isCaptain`, `agentModel`, `sysType`) return success but do not persist |
| origin DBs | 3306/6379/27017/9200/11211 accept-then-RST = **CDN edge**, not the real origin |
| vendor app backend | Alibaba Cloud WAF hard-blocks datacenter IPs |

Call out the CDN false-positive explicitly in the report: a port scan of a
Cloudflare/edge hostname shows the edge's port list, and edge DB ports accept then
reset the connection. That "all ports open" reading is a manufactured impression.

## 8. Red line on this class of target

Commission settlement, withdrawal, transfer and balance-movement endpoints
(`settleCommission`, `finance/draw/*`, 提现/转账) are **read-only territory**:
read the config, never invoke the movement. State in the report that no funds moved.

## 9. Browser automation recipe

See `scripts/cdp_driver.py` in this skill. Key points: React inputs need the native
value setter + `input`/`change` events; captcha sessions expire in seconds so the
solve must be a single script (or two calls sharing the tab); a `blob:` `<img>` is
the captcha, not the `data:` logos; plain 4–6 char alphanumeric image captchas read
reliably via vision, whereas the "select these in order" sprite type (3 tiny hint
thumbnails + a scene) resisted repeated attempts on coordinate precision — budget
that boundary honestly instead of looping on it.
