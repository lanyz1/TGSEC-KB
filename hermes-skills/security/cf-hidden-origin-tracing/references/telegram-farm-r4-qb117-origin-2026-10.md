# tlgramhq / qb-117 R4 — control-plane origin found, landing still hidden (2026-10-01)

Companion to `telegram-farm-origin-hunt-2026-10.md` (R1–R2) and `farm-domain-pool-expansion.md` (R3).
This round did **not** produce the CF origin IP for `tlgramhq.com` itself. It did produce the
operator's **qb-117 management / TRON API origin**, which is the correct deliverable when the
landing is a dead 500 + CF-cached static shell.

Artifacts: `/root/cases/tlgramhq/REPORT-R4.md`, `health_tron.json`, `fp_logs*.json`,
`/root/qb117_origin/index-*.js`.

---

## 1. What changed vs R1–R3

| Layer | Status after R4 |
|---|---|
| Landing `tlgramhq.com` | Still CF-only; `/` = **500/0B**; statics + robots/sitemap often CF-cache HIT |
| Triple FP on farm CDN pools | 222.167.35 / 94.154.43 / gongyong666 / goDl bare-metal → **no** triple hit |
| **Control plane** | **FOUND** — CF Origin CA + live JSON API |

Do not re-run R3's full Host-spray on deny-unknown-Host netblocks expecting a landing hit. Pivot to
API/admin siblings first (§16b of SKILL).

---

## 2. Confirmed origins (control plane)

### 103.254.110.111 — `api.tron-api.top`

- **Cert**: CloudFlare Origin CA; SAN `*.tron-api.top`, `tron-api.top`
- **ASN**: AS152194 CTG Server Limited (HK Tung Chung)
- **Ports**: 80, 443, 888 (888 = nginx 403 from external)
- **No cf-ray** on direct hits
- **Host routing**:
  - `Host: tron-api.top` / bare / wrong host → SPA HTML ~484 B title `qb-117 管理后台`
  - `Host: api.tron-api.top` + `Accept: application/json` → real Node API

### 192.253.228.147 — `admin.tpwallet.fun` / `api.tpwallet.fun`

- **Cert**: Let's Encrypt CN=`admin.tpwallet.fun`
- Same ASN family; **independent** process from 103.254 (cross-Host does not return sibling JSON)
- SPA bundle points `baseURL` at `https://api.tpwallet.fun`

### Historical / FOFA only

- `103.133.178.250` — prior `admin.tpwallet.fun` cert row; unreachable (000) from this egress in R4
- `goapi.mom` — historical qb-117 on 222.167.35.2/.135; DNS empty at R4 time

---

## 3. Unauth / auth surface on the API origin

Prefix all paths with `/api/v1` unless noted. Auth model = **Telegram ID + OTP** (not password).

### Unauthenticated (verified 200 JSON)

```
GET  /health
GET  /api/v1/fingerprint/logs
GET  /api/v1/fingerprint/stats
GET  /api/v1/fingerprint/config
POST /api/v1/fingerprint/test-match
POST /api/v1/fingerprint/generate-link   # 400 without 9-digit agent UID
```

`/health` sample fields: `database/redis connected`, `telegramMode=webhook`, `blockScanRunning`,
`lastScannedBlock`, `nodeVersion` (v18.20.8), security counters.

Fingerprint logs in this engagement only showed **scanner egress IPs** (historical curl probes),
not end-user fish — still proves the endpoint is live and unauth.

### 401 token required (exist)

```
admins, agents, fish, groups, links, collections,
apk-templates (+ download-links, generation-logs),
tron-api-keys, audit-logs, statistics/*, options
```

### Auth flow

```
POST /api/v1/auth/send-code  {"telegramId":"..."}  → 403 if not admin TG id
POST /api/v1/auth/login      {"telegramId","code"} → 401 bad/expired code
```

JS API map (from SPA): see `/root/qb117_origin/index-CZ9X3iil.js` `ft.get/post/...` extraction in
R4 notes — full fish/agent/collection/APK template CRUD once token is held.

---

## 4. Landing-side findings that are NOT origin

### Triple fingerprint targets (keep using)

| Asset | Value |
|---|---|
| Icon path | `/static/assets/apple-touch-icon.png` |
| Icon md5 | `295ccdb03006b8dfef45090dafbd46ac` |
| Icon FOFA | `icon_hash="-561384241"` |
| robots | ~68 B, body must contain `telegramset.com/sitemap.xml` |
| Brand favicon hash | `-469815234` — **do not use** (Telegram logo, 7k+ noise) |

### goDl catch-all (drop)

`38.76.150.162` and peers matching `body=goDl` + matching icon: **same homepage md5 for every Host**
including `baidu.com`; robots = nginx 404. Template family only.

### APK / OSS chain (supply-chain, not web origin)

From landing `app.js` base64:

```
https://hktuesakk.com/tuesgam.apk
  CNAME → dowinda.cn-hongkong.thepacificgls.com
  A     → 47.79.66.58 / .70  (Aliyun OSS)
  GET   → AccessDenied (private bucket)
```

Sibling shell used `kdhtisekkk.s3.ap-southeast-1.amazonaws.com` → AllAccessDisabled.

### kit-telegramkit.com @ 206.238.197.239

Still the farm bare-metal twin (R2). R4: this egress + multi-node check-host → **443/8888 dead or
filtered**; :80 returns nginx 400 for all Hosts (HTTPS-only vhost). Do not spend another full day
Host-spraying :80 here expecting HTML.

### CDN / 456 / 不死鸟 (R3, still true)

- 222.167.35.0/24: CDNFly-class / `_guard` p456; unknown Host → **000**
- 94.154.43.x: 不死鸟 530; chaojiseo.cloud default page
- Existence-oracle only: non-generic page for `Host: target` = configured node; still needs md5 control

---

## 5. Probe recipes worth keeping

```bash
# A) Prove CF Origin CA
openssl s_client -connect 103.254.110.111:443 -servername api.tron-api.top </dev/null 2>/dev/null \
  | openssl x509 -noout -issuer -ext subjectAltName

# B) JSON vs SPA on same IP
curl -sk -H 'Host: api.tron-api.top' -H 'Accept: application/json' \
  https://103.254.110.111/health
curl -sk -H 'Host: tron-api.top' https://103.254.110.111/ | head -c 200

# C) Triple FP candidate
python3 scripts/triple_fp_verify.py --ip <IP> --host tlgramhq.com \
  --icon-md5 295ccdb03006b8dfef45090dafbd46ac \
  --robots-substr telegramset.com/sitemap.xml

# D) Catch-all control (must differ)
for h in target.example zzz-not-exist-999.com www.baidu.com; do
  curl -sk -H "Host: $h" https://<IP>/ | md5sum
done
```

---

## 6. What to try next (ordered)

1. Token path on qb-117: JWT empty/none, leaked tokens in fingerprint/agent links, 9-digit UID
   `generate-link` abuse, webhook URL leak from misconfig.
2. Same-C / same-ASN neighbours of 103.254.110.111 and 192.253.228.147 with Origin-CA / qb-117 title.
3. Alternate egress for 206.238.197.239:443/8888 only if a new twin domain appears — not blind rescan.
4. Monitor `goapi.mom` / `chaojiseo.cloud` DNS resurrection for panel re-entry.
5. Landing origin: still requires CF-account, Origin-CA for *tlgramhq* SAN (FOFA size 0 so far), or
   operator misbind that fails the deny-unknown-Host posture.

---

## 7. Reporting discipline for this class

When the user demands "the source IP" of a CF landing:

- Lead with **control-plane origin** if found (this R4).
- State explicitly: landing origin **still** externally unobtainable / structural, with the three locks
  (CF + deny-unknown-Host + young domain / no pre-CF PDNS).
- Never promote goDl bare-metal or icon-only FOFA hits as landing origin without the triple gate +
  Host md5 control.
