# Venue matrix & third-party provider engines (apeiro8-family, "4号店" case)

Session-specific detail behind SKILL.md §2f–§2i. Target: an SEO shell
(`wabizhuanqianruanjian.lol`) funnelling to a multi-tenant betting platform
(`X-API-SITE: 4002`, `SiteBaseConfigVo.name = "4号店"`).

## 1. Module constants (per-route-family, NOT interchangeable)

```
/site/api    047dc7e2a504dc908e2d91faa8a152a23c413390aac299f8a6b7303a26041428
/page/fd     99dc2daa5b3d7361babdcec11750ccfe92b215121024c56be581ce0b6f2f64f6
/game/api    98d2aa91538c60754664d74bb7690fca24897ff409d02e51aa03425ab2efe0ee
/act/api     693b9c351d9a823698f43a00beb98018084cd925f80662204c8b964c2dafe47b
```

Header set that makes plain `curl` work for ~50 player endpoints:

```
X-API-XXX: <module constant>   X-API-CLIENT: h5   X-API-VERSION: 1.0.0
X-API-SITE: 4002               X-API-TYPE: h5     X-API-UUID: <uuid>
X-API-TOKEN: <cookie value>    X-USER-ENCY: md5(username)   # server ignores it
```

Symptom → cause: `6003 非法请求` = wrong/missing **module constant** (not a closed route).
Constants differ **per deployment instance** — instance A's constant gets 6003 on
instance B, so re-grab them when you switch hosts.

## 2. Venue table (`POST /site/api/v1/site/venue/sort {}`)

Categories → venues (44 total; `official=1` marks the operator's own brand):

| Cat | Venues |
|---|---|
| TY 体育 | YBTY 开云体育(official) · DBTY 熊猫体育 · IMTY IM体育 · FBTY FB体育 |
| ZR 真人 | YBZR 开云真人(official) · DBZR · AGZR Choice · BGZR BG · OGZR OG · WMZR 完美 |
| DZ 电子 | PMDZ 开云电子(official) · YBEGDZ DB电子 · PGDZ · PTDZ · PPDZ · DTDZ LGD |
| QP 棋牌 | YBQP 开云棋牌(official) · DBQP · BYQP 博雅 · GDQP 高登 · IMQP 双赢 · YYQP YOO |
| CP 彩票 | YBCP 开云彩票(official) · DBCP · TCGCP |
| BY 捕鱼 | YBBY 开云捕鱼(official) · BYBY · DBGGL 刮刮乐 · OBHX 哈希 · AGBY · YGRBY · SPYL |
| DJ 电竞 | IMDJ 电竞牛 · LHDJ 雷火电竞 |

Site identity: `POST /site/api/v1/configuration/preInfo` →
`SiteBaseConfigVo{id:1, name:"4号店", title:"开云体育官网-皇家马德里足球俱乐部官方区域合作伙伴"}`.

## 3. Launch harvest (19/25 succeeded)

`POST /game/api/v1/venue/launch` body / success shape as in SKILL.md §2f.
Failures returned `6415 场馆已临时维护,维护时间:<window>` (business refusal).

| Venue | Provider entry (tokens redacted) | Provider host |
|---|---|---|
| YBTY | `app-h5.zqt0510.com?token=<REDACTED> | zqt0510.com |
| DBTY | `sports-mobile.satehxv.com?token=<REDACTED> | satehxv.com |
| IMTY | `im.3793343b.com/mobilesitev2/?timestamp=…&token=…` | 3793343b.com (IP-blocked) |
| BGZR | `cdn-ali.sxypedu.com/h5V01/h5.html?sn=ro06&account=p02<user>&uid=1290005345&token=…` | sxypedu.com →302→ cdnnonx-ali.zahanh.com |
| OGZR | `live-api.673ing.com:18088/play?token=<128hex>&player_code=YB_p02<user>&currency=CNY` | 673ing.com |
| WMZR | `wmtc.w1773.net?sid=<19char>&ui=7&lang=cn` | w1773.net |
| YBZR | `ep.rcl4dpz.com:10027/egret/?params=<base64>` | rcl4dpz.com |
| DBZR | `ep.next.tcupoa.com:9001/egret/?params=<base64>` | tcupoa.com |
| AGZR | `gci.qftzhov.com/forwardGame.do?params=<base64>` | qftzhov.com |
| YBQP / DBQP / BYQP | `game.shitucomm.com` / `game.zhongfeijt.com` / `game.jblbouf.com?token=<base64>` | three card providers |
| GDQP | `gc.drutetip.com?game=0&token=<32hex>&grh=https://result.laiplay.win` | drutetip.com (Vite stack) |
| IMQP | `pdx50n.ko93y.cc:8443?p=<base64>` | ko93y.cc |
| TCGCP | `tcgapi.wedhj9.com` | wedhj9.com |

Notes: the three card-provider tokens share the base64 prefix `MkI0ODBBNjk3MEREOENF…`
(one signing scheme). `result.laiplay.win` was a bare Rocky-Linux nginx default page
(unconfigured vhost, several round-robin IPs). Engine locale/currency params are
attacker-visible (`currency=CNY`).

## 4. Engine API auth (sports family, `/yewuNN/*`)

```
POST https://api.<engine>/yewu12/v1/m/matchesPB?t=<ms>
  requestId: <launch-URL token>            # real credential, plaintext in the URL
  checkId:   pc-<md5>-<cuid>-<13-digit-ms> # client-generated, no HMAC, no server secret
  request-code: {"panda-bss-source":"1"}  lang: zh
  body: {"cuid":"<uid>","euid":"…","type":3,…}
```

Response envelope `{"code":"0000000","data":"H4sIAAA…"}` = **gzip+base64**; decode with
`gzip.decompress(base64.b64decode(d))`. The sport feed decoded to **725 KB / 440 fixtures**,
each with a live `betAmount` (real aggregate volume, e.g. `561602.98` on a Spanish
second-division match) — business data, not PII.

Reachable from Python with no CORS/rate friction: `/yewuNN/user/amount`,
`/yewuNN/user/getUserPersonalise` (leaked the engine-internal `merchantCode: 526016` and
`userId`), `/yewuNN/user/getUserParamConfig`, `/yewuNN/v1/art/getAccessConfig`,
`/yewuNN/v3/menu/loadMappingPB`, `/yewuNN/v1/w/eventInfo`,
`/yewuNN/fireworksActivity/getFireworksActivity`.

Not exposed usefully here: `/yewu12/actuator` → only `health`/`info` (env/heapdump 404).

## 5. Identity-swap results (all bound — do not re-report as IDOR)

| Target | Test | Response |
|---|---|---|
| sports `user/amount` | swap `cuid`/`userId` to neighbours (`…411`,`…413`), `1`, `1000` | returns caller's own uid |
| sports `getUserPersonalise` | swap `merchantCode` header (526015, 1, 100) | returns own `526016` |
| live `/play` | `player_code=YB_p02t4pl8bwk` / `p02admin` | `{"error":{"code":400,"message":"player verify fail!"}}` |
| live `/play` | forged token (128×0), missing token | `player verify fail!` / `Required String parameter 'token' is not present` |
| live host | any path but `/play` | `403 Forbidden` (global filter) |
| platform | `venue/launch` on a sibling instance | `6003` (per-instance constants) |

Undecidable: BG live-casino H5 (`account`/`uid` swaps were passed through the 302 to
`zahanh.com`, but the WebGL client rendered blank in a GPU-less Chromium).

## 6. Registration rules & uid arithmetic

```
username : 4–11 chars, ≥2 letters+digits, first char must be a letter
password : 8–12 chars, letters+digits only
success  : localStorage.userEncrypt + cookie X-API-TOKEN + user_ency
login    : POST /site/api/v1/user/login {name,password}   (plain JSON; 6008 = bad creds)
```

uid growth: `521649743` @ 18:56 → `521650814` @ 22:02 (platform tz **UTC+8**)
⇒ Δ1071 / 3.1 h ⇒ **~345/h ⇒ ~8,300 new accounts/day**. A production user table.

## 7. Upload matrix results

`POST /component/front/api/v1/upload/uploadImage` (multipart `file=`) →
`{"contentType":"image/png","fileName":"x.png","fileUri":"/images/new_public/h5/others/<random>.png","fileUrl":"https://pds3img.<cdn>/…"}`

- `.svg/.html/.gif/.txt` → `6010 请上传正确格式的图片`
- SVG bytes renamed `.png` → `6010 上传内容不合法，请稍后重试`
- `x.php.png` / `x.jsp.jpg` / `../../x.png` / `..%2f` / `..\` → WAF block page
- `t;p.png` → `无法识别的文件格式: t` (server splits on `;`)
- rejected: `t.png%00.html`, `t.png\nx`, `t.png.`, `t.png?x=1`, `t%2epng`, `.htaccess`
- accepted: `t..png`, `T.PNG`, `t p.png`, `  t.png`, `t.png `, `.png`, `中文.png`, 300-char
- **`fileUri` is a server-generated random name** ⇒ original filename never reaches the path
  ⇒ no traversal, no overwrite; retrieval Content-Type follows the real type (no sniffing)

## 8. Fleet instances observed

| Host | Note |
|---|---|
| `www.2mxswj.vip:6004` | working instance, build `main_refactor/master_1e203a69e` |
| `www.jnvip406.com:6004` | sibling instance, build `main_refactor/master_36608c26f`, own buildId, own constants |
| `www.jnvip46.com` | third instance (HTTP 200) |
| `www.jnty.vip` | pure redirector → `jnvip406.com:6004` (useful for mining engine hostnames out of chunk paths) |

Bans are per-hostname on this family: one host returning `000` while siblings and the
panel answer normally is the expected state — rotate hosts, not IPs.

## 9. Repro scripts (case dir `/root/cases/t4_wabizhuanqian/`)

- `t4_venues2.py` — 44-venue list + 25-venue launch harvest (correct `/game/api` constant)
- `t4_engines_probe.py` — provider-host reachability + API-path sweep
- `t4_og.py` — live `player_code`/token swap tests
- `t4_uid_up.py` — uid growth arithmetic + upload filename matrix
- `t4_regauto2.py` + `t4_botion_solve2.py` — captcha-gated registration machine
  (see the `botion-captcha-solver` skill for the solver internals)
- `t4_dpty2.py` — mining the provider host out of chunk paths
- Artifacts: `VENUE_ALL.json`, `VENUE_LAUNCHES.json`, `VENUE_SORT.json`,
  `ENGINE_HOSTS_PROBE.json`, `ENGINE_MATCHES.json` (735 KB), `BG_IDOR_RESULT.json`
