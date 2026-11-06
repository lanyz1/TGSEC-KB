---
name: white-label-platform-recon
description: "Use when reconing a white-label/SaaS platform and its panel."
tags: [白标, 包网, 盘口, 后台入口, 白标后台, 包网后台, 平台侦察, 租户枚举]

---

# White-label platform recon

Applies to white-label fleets: crypto casinos, scam "casinos", storefronts,
TG cloud-control. The pattern is worth memorising because the interesting surface
is never the brand you were handed — it is the **shared back end** and the
**operator panel** that runs the fleet.

## The shape, in order of discovery

```
brand domain  --CF-->  shared origin (one IP, many brands via Host header)
                             |
                       operator / affiliate panel  (separate domain)
                       image CDN, docs site         (separate domains)
```

Expect the brand to be one of dozens. If you identify the platform software, you
have the whole fleet: sibling brands, their origins, and their panel.

## 1. Mine the frontend config object

Modern brand frontends ship a config literal naming every internal API. Grep the
JS bundles for it — it is usually a plain object, not computed:

```js
{ wsLink: "/api/ws", api: "/api",
  localApi: IS_DOCKER ? "http://host.docker.internal:80/api" : "http://localhost:3001",
  paymentsApi: "/payser", slotsApi: "/api/slots",
  picturesApi: e => `https://<shared-cdn>/...` }
```

From that one object you get: the WS path, hidden API prefixes that are *not*
under the obvious `/api/` (e.g. `/payser`), an internal Docker hostname proving
container topology, and the shared CDN that ties the fleet together.

## 2. The vendor's public docs site is the API goldmine

White-label vendors document their panel for their customers. `wiki.<panel-domain>`
(or `/docs`) is frequently **wide open** and enumerates the entire API.

```bash
curl -s https://wiki.<panel>/llms.txt          # full doc index
curl -s https://wiki.<panel>/llms-full.txt     # everything, one file
curl -s https://wiki.<panel>/<any-page>.md     # gitbook-style: append .md
```

Read it for: every endpoint + method + body/response shape, the auth header
format, exact error strings, rate/whitelist notes, and — most valuable — the
**business model itself**. Worked example in this skill's `references/`: the docs
exposed a `newDrain` event whose payload is `{mammothId, domain, network:
"private key"|"phrase", balances:[{token, usd}]}` — i.e. the platform's job is
collecting victims' seed phrases and draining their wallet balances — plus a
`crash`-multiplier prediction endpoint that contradicts the brand's public
"Provably Fair" claim, and a 280-template landing library (celebrity + adult
themes) generated per-domain.

Treat docs as **the highest-value artifact of the engagement** when the panel
itself is unreachable: they are both an API map and proof of purpose.

## 2b. ★ Read the config endpoint unauth — it names the panel and the whole fleet

Before guessing panel hostnames, call the brand's own configuration API with no
auth. The `preInfo` / `site_config` / `getSiteConfig` family routinely answers and
returns the operator's **entire domain map** inside a single JSON object:

```json
{~"agentPcDomainUrl":"https://...", "agentH5DomainUrl":"https://...",
  "pcDomainUrl":"https://...", "siteDomainUrl":"https://...",
  "h5StreamlineDomainUrl":"https://...", "whiteDomain":["... 80+ entries ..."],
  "name":"4号店", "id":1, "title":"..."}
```

Three things fall out of one request: the **affiliate/agent panel address** (the app
you actually want), the **player entrances** on their real hostnames, and the fact
that a `name` like `4号店` ("store #4") with `id=1` means a **multi-tenant**
platform — tenants 1..N exist, each with its own brand, captcha policy and
recruitment funnel. Correlate the CDN/image hostnames across those entries to tie
the fleet together.

## 2c. ★ When the brand's signup is closed, sign up on the *panel*

The brand side is often locked down while the **agent/affiliate panel is a separate
application with its own registration form** — frequently gated by nothing but a
plain 4–6 character image captcha, no GeeTest/Turnstile. This is the highest-value
move on a hardened white-label target, and it is easy to miss because you are
staring at the brand's `/register`.

Signals that you are looking at a *policy* block rather than a payload bug: the
brand returns one generic failure (`注册失败`, `signup unavailable`) across **every**
domain, with the operator's own invite code, *and* through the official recruitment
links you found inside the fleet. Genuine field errors come back as **field-specific**
messages — so a generic failure after all fields validate is policy. Stop iterating
payloads; move to the panel.

Once inside, the panel's own `/promote`-style page leaks **per-agent recruitment
links** (each carrying the agent's sub-code and affiliate id) and each link is
another domain in the fleet. Harvest them before concluding you are out of surface.

**Recruit-loop granularity check (run once inside).** Register a throwaway member through
one of those links carrying *your* code (`/entry/register<subcode>/?i_code=<your
affiliate code>`), then read it back in the panel: `member/list` shows it in your
downline and `member/detail` returns a **full profile** (~19 KB in this family:
deposits, withdrawals, per-venue win-loss, bank/mobile/IP). Two facts, verified in one
loop: the recruitment funnel really binds members to the agent, and the panel's data
granularity is *team-scale full profiles* — everything outside your team stays closed
(refusals / `total:0`). That is what "panel data" honestly means: team full, platform no.

Detail, route inventory and the AES-enveloped variant of this platform family:
`references/agent-panel-and-crypto-envelope.md`.

## 2c2. ★ One IP, many ports = one backend, many tenants — probe the port matrix

白标后端常把每个租户绑在同一台机器的不同高端口（`37xxx`），前端只暴露其中一个。扫全端口后**别挑一个就打**——按下面的矩阵把租户和构建版本分开：

```bash
for p in 37416 37424 37442 37451; do
  curl -sk https://$IP:$p/v1/user -H "Authorization: Bearer $TOK" | jq -r '.data'
done
```

判读：

- 同一 token 在不同端口返回**不同 realname / idcard** ⇒ 独立库、独立 uid 空间，只是共享签名密钥（一个 token 通用）；
- `401 token异常` ⇒ 该实例密钥不同；`500` ⇒ 该库无此 uid；`200` 但只有 99 字节占位 HTML ⇒ 空壳端口；
- **构建版本会差**：同一份代码，有的实例漏写归属校验。用同一个受控端点差分（例：`/v1/user-team?parentId=1` 对零下线账号），一个实例回他人下线、另一个回空 ⇒ 前者可整树爬（真名+余额），并可据此反推主站是否有同版本旧端口。

三北实测：`139.199.15.92` 上 37416（主站）/ 37424 / 37442 / 37451 四套独立库共一对 RS256 密钥，37424 的 `user-team` 完全无归属校验。

## 2c3. ★ 证书日志就是舰队花名册 — 猜子域前先拉 crt.sh

拿不到 §2b 的 config 域名表，或要验证它全不全：拉厂商 apex 的证书透明度日志，一次摊开全部品牌实例与静态分发域。

```bash
curl -s "https://crt.sh/?q=%25.<apex>&output=json" | jq -r '.[].name_value' | tr ',' '\n' | sort -u
```

命名即角色，先分堆再打：

- `*api.<apex>` — 品牌 API 实例，一品牌一套库（本族 47 子域里 20+ 个 `*api`）
- `*tp.` / `*htmlal.` / `*s3kvdz.` / `*apkal.` — 对象存储与静态分发；对每个 `GET https://<sub>/`，按 `ListBucketResult` / `NoSuchKey` / `AccessDenied` 三态定性，打法见 `cloud-storage-bucket-recon` §2c
- `*html.` — 打包/分发控制台（`/api/admin` 家族）

**跨品牌 token 重放只证明共键，不证明同库。** 本族一对 RS256 密钥全省通用，同一 token 在每个 `*api` 实例都回 200，但 uid 空间各自独立：uid 415 在三北是钱红梅、在 chuanboapi 是杨凡、在 xywyapi 是廖方林。想拿数据得逐品牌爬，别把「token 通用」写成「跨品牌直取」。

**归属校验差分定构建。** 同一端点在新旧实例上的错误语义不同：`/v1/goods-order/{id}` 在主站老实例直接 200 回他人订单（`receiverPhone` / `receiverName` / `receiverAddress` 全明文），在品牌新实例回 `UNKNOWN_IDENTITY`。一个端点两种语义 = 两套构建，**老实例才是 IDOR 面**——舰队每个实例都差分一遍再收结论。

**订单 ID 稀疏，max 不等于量。** 上述 IDOR 全量扫 1..106,141 只落 2,182 单；先扫完再报「全量」，别拿最大 ID 当单量估算。

桶四态判读（`ListBucketResult` / `NoSuchKey` / `AccessDenied` / 应用）、翻页游标、并发读半截 key 的坑：`references/subdomain-bucket-fleet.md`；探测脚本 `scripts/bucket_fleet_probe.py`（`--keys` 直接 dump）。

## 2d. ★ The ban is per-DOMAIN — rotate hosts before rotating IPs

On a multi-tenant fleet the WAF blocks **one hostname at a time**, not the
back-end. Check this before reaching for proxies or a real browser:

```
your-IP -> hostA (the one you were hammering)  -> 000 / 416 block page
 your-IP -> hostB (sibling in the SAME config map) -> 200 + normal JSON
your-IP -> the panel host                        -> 200
```

If any sibling answers, you are **not** blocked — just on the wrong hostname.
Three consequences worth writing down:

- **Sessions are cross-domain.** The cookie/token from hostA authenticates on
  hostB for the same tenant (`member/info` returned the same account on three
  different hosts). No re-login, no captcha, no lost foothold.
- **You may be able to drop the browser entirely.** If you were only using a real
  Chromium because the WAF rejected plain HTTP clients, a clean sibling host often
  accepts **plain curl**, which is an order of magnitude faster for enumeration.
- **`chrome-error://chromewebdata/` after `Page.navigate` is an IP-domain block,
  not a dead route.** Confirm by curl-ing a sibling host — if that's healthy, go
  back to §2b and pull the domain map again.

Take the sibling list from the same unauth config endpoint as §2b, or from the
frontend's own cached `customUrl` / domain constants in localStorage.

**Per-instance build ⇒ per-instance constants.** Sibling hosts are not always the same
deployment: `<meta data-commit-info="main_refactor/master_<hash>">` in the served HTML
differs between them (`master_1e203a69e` vs `master_36608c26f`), each with its own
`buildId` and chunk set. So a `6003 非法请求` on a *new* instance usually means **the module
constant harvested from the old build does not apply** — not that the route is gone.
Re-harvest `X-API-XXX` inside that instance's own browser session before concluding
anything about the sibling. A domain that only `301`s to another instance is still an
instance lead: follow the redirect and fingerprint the target (commit hash, chunk count,
buildId) — the fleet's real inventory is in those hashes, not in the brand names.

Relatedly, when a path like `/dpty/api/sport/...` returns the **SPA's HTML** rather than
JSON, it is a frontend route, not an API: grep the chunks for the bare hostname the app
actually calls (that is how `www.jnty.vip` → 301 → the real instance surfaced).

## 2e. ★ Unauthenticated "runner"/marquee endpoints leak real user activity

Front-end tickers (win feeds, invite feeds, red-packet marquees) are decorative and
are routinely shipped **without auth**. They are the most commonly missed real-data
surface on this family:

```
POST /act/api/v1/invite/getMarquee            # no token at all
 -> {"data":{"list":["恭喜会员fp****57,成功邀请cy****21,获得彩金22.00元", ...]}}   # 50 rows
```

Verify properly: **strip the cookie and every `X-API-TOKEN` header and replay.** Still
data = unauthenticated disclosure. Rate it honestly though — this family masks names
server-side (`fp****57`) and flipping `mask/isMask/showAll/pageSize/limit/type` never
unmasks them, so the impact is "real activity feed, masked identifiers", not a user
dump. Say that instead of calling it a user-list leak.

Siblings worth trying: `operationPageBet/getPageBetMarqueeAwards {activityId}`,
`redEnvelope/marquee`, `activityShow/memberApplicationRecords`, `promotion/applyList`,
`bonusService/records`, `realTimeFS/info`, `vipWeek/VipWeekInfo`, `config/ecup/log`.
Most need a **valid `activityId`** — sending `{}` yields `参数错误` or empty `data`,
which is not proof the surface is closed; take ids from the in-app `/activity/list/<id>`
routes or the activity config endpoint.


## 2m. ★ The panel lives on the *vendor's* root domain, not the brand's

When the brand is CF-fronted, every `/admin`-ish path 307s to the player app, and the brand
has **no subdomains at all** (not even `www` — verify with a random-name control), stop
fuzzing paths. Go source-first:

1. **The gateway's own api-docs leak the backend hostname** in `servers`:
   `https://prod-eai.<vendor>.local`. Swap `.local` → `.com` and you often get a real,
   public host that **bypasses the gateway entirely** — the tell is Spring-native error JSON
   (`timestamp`/`requestId`) on this host vs the gateway's generic `999999` fallback on the brand.
2. **Brute the vendor apex, not the brand apex.** It typically yields the operator panel
   (`prod-backoffice.<vendor>`, title often literally "Whitelabel System"), a second
   environment (`uat-backoffice`, `uat-eai`), a sibling tenant (`<other-brand>.<vendor>`),
   and an object-store endpoint (`cdn.<vendor>` → `NoSuchBucket`, echoes the bucket name).
3. **Beware wildcard vendor zones** — fire one random subdomain first; if it resolves to the
   same few IPs, the whole dictionary is noise.
4. **UAT is not a brute-force lab.** It usually shares or clones the production user table
   (same `admin` answers identically on both), so lockouts propagate. Use it for config
   drift only.

Full chain (bundle client extraction, lazy-chunk login sequence, lock policy, dual-origin
upload): `gateway-partition-authz-sweep` → `references/bo-plane-and-panel-client.md`.

Brand frontend is Next.js and you want to reach for React2Shell / middleware bypass?
Read `references/nextjs-front-waf-triage.md` first — it saves you from calling a nginx
403 a "Cloudflare block" and from shipping a payload with no liveness proof.

## 全文导航（已拆分）

主卡保留前 7 节；其余 18 节在 `references/full.md`：

- 2f. ★★ The venue matrix is the credential harvest — one call, nineteen providers
- 2g. ★ The uid auto-increment sequence is the "is this real?" oracle
- 2h. ★ Account-factory chain: register → solve captcha → re-fill → submit
- 2i. File-upload assessment matrix (run it in one pass)
- 2j. ★ The fleet's asset bucket is the tenant roster — and the APK is the platform
- 2k. ★ The shared ingress is the operator's whole cluster — vhost it
- 2l. ★ A wildcard host can be the admin console itself — read the title, not the byte size
- 3. Use error semantics as a route/stack oracle
- 3b. Code-split SPA panels: enumerate the routes, then prove completeness
- 3c. Next.js targets: the build manifest is the whole route map
- 3d. ★ Every oracle needs a negative control — the guard that fakes a finding
- 4. Operator-config fields leak the fraud model
- 5. Expect to be locked out of the panel — and say so precisely
- 6. Separate "vulnerability" from "operator configuration"
- 7. The drainer's ingestion endpoint lives on the brand side, not the panel
- 8. How to work with this operator (standing instructions)
- Pitfalls
- Files

加载：`skill_view(name='white-label-platform-recon', file_path='references/full.md')`

> 全文较大（30767 字符），已分 3 片：`references/parts/index.md`（每片约 12KB）。整包仍可读 `references/full.md`。
