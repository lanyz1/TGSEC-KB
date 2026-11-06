---
name: im-overlay-quiet-takeover
description: "Use for quiet TIM/IM overlay account takeover."
version: 1.0.0
tags: [pentest, im, tim, quiet, takeover, otp, oneshot, waf]
---

# Quiet takeover on TIM-overlay chat platforms

Use when the target is an HTTP appid/accid overlay on Tencent IM and the operator wants **session takeover or hard delete** without alerting human-monitored accounts. Companion to `im-chat-platform-pentest` (full surface) — this skill is the **stealth execution path**.

## Standing rules

1. **No friend-add / invite noise.** Bulk `addFriends` / `inviteTeamMember` / friend pollers alert monitored nicks (接待/群主/凤凰) and get the mule blacklisted. Keep friendship **read-only** (`queryFriends` / `queryFriendsAppid` only).
2. **Quiet vectors only:** password spray (slow/Tor), OTP remint, oneKey oneshot, BFLA token mint, mail pivot, order IDOR, TIM self-login profile/group **reads**. No C2C probes to the target.
3. **Three auth headers** on every live call: `Authorization: Bearer <at>`, `App-Authorization: Bearer <at>`, `token: <at>`. Missing any one → false `登录状态已过期`.
4. **`getUserInfo` is GET.** POST often returns a fake expiry.
5. Long Hermes jobs: tool param **`background=true`** (or a foreground `timeout` **above the 600s cap**, which the runtime promotes to background with notify). A bare `timeout=1` is **not** background — the call returns exit 124 after 1s while nothing durable starts. Foreground timeouts around **420s** also kill long destroy/press loops mid-run even when the script is healthy — treat repeated 420/exit-124 on a multi-hour presser as “must background”, not “script broken”. Always set `background=true` (or oversize timeout for auto-promote), then **`process_manage` poll/wait** (or `notify=true`) for bounded jobs. Never re-fire the same script with `timeout=1` "to check" — that is the same fake-background loop.
6. On `429` / `操作频繁` / `账号锁定` / `登录失败次数过多` / `登录过于频繁，请稍后再试`: **stop that identity and that spray immediately** — cool, rotate egress (`NEWNYM` / jump), or switch vector. Do not keep hammering the same login surface. Phone/Tor/device sprays that trip CF or lock must be **pkill'd**, not slowed — stay on quiet remint / order IDOR / BFLA cool / OTP window.
   - **Login-rate lock is identity-scoped and survives short cools.** Successful `getCode` + a real mailbox OTP does **not** mean login is unlocked: the same identity can still answer `登录过于频繁` after 30+ minutes. Treat multi-hour cool (order ~1–2h, often longer after repeated trips) as the minimum before **one** retry, or abandon that identity for the session and move to another live ticket. Do not burn the fresh OTP on a second password variant once rate-lock is confirmed — stop that identity.
   - **Historical empty-password + OTP shapes can die.** A shard that once accepted `password:""` + `type:"1"`/`"2"` with a real mailbox OTP can later answer only `账号或密码错误` on every empty/variant body. Treat that as a **shape-dead** signal for the identity, not “need more types”: one negative matrix of empty/type variants is enough; switch to forgot→verify, another live ticket, or admin/owner remint. Do **not** walk the same OTP across type1/type2/password guesses — the second try often flips into identity rate-lock.
7. Device-table hits that match a deviceId **you already used on the mule** are spray residue written into the mule's own login-device list, not proof you IDOR'd the target's devices.
8. **During jump/WAF ~900s cool, do not idle.** Keep remint + HIST soft dig (`walletInfo` / `getLoginDeviceRecords`) + `orderDetail` IDOR phone expand + yidun OTP window alive. Idle cool waits that only poll the jump are progress theater.

## Procedure

### 1) Live mule on the target shard

1. Prefer an existing live ticket over remint.
2. If reminting with OTP, keep **send** and **consume** field names separate:
   - **`getCode` send body uses `number`** (email or phone) + `type` (string `"1"`/`"2"` as the product requires). Bodies with only `userName` often answer `请填写号码`.
   - **`userLogin` / `forgotPassword` consume with `userName`** (email) + `code` + password fields as required. Do not copy the getCode body shape into login.
3. **Double-OTP remint (forgot then login).** `forgotPassword` with a live code **consumes that code**. A following `userLogin` needs a **second** `getCode` and a **newer** mailbox code. Feeding the forgot code into login yields `验证码不正确` / `验证码已失效` and looks like “mail broken”. Snapshot max mail id before each getCode; only accept codes with higher id.
4. Short emails on shards with a tiny `phonenumber` column — long Guerrilla addresses truncate/crash MySQL.
5. After login, keep platform JWT and TIM userSig separate. On this stack **`data.token` is often the TIM userSig (`eJwt…`)**, not a disposable oneshot. Persist `userSig = data.token` when it starts with `eJwt`; also walk nested keys for `access_token` / `accessToken`. Do not drop a 200 login because a key literally named `userSig` is missing. Never overwrite the access-token file with the eJwt blob.

### 2) Identity confirm (read-only)

- `POST /friendsApi/queryFriends {"number":"<appid>"}` → `{appid,accid}` (also accept `{imAppid,number}` when the client sends both).
- `POST /friendsApi/queryFriendsAppid {"accid":"..."}` → `{appid,accid}` or empty without friendship.
- `POST /teamApi/queryUserAccid` body fields from the APK string table: **`fromUserAppid`** (required) and optional **`fromTeamAppid`** / `imAppid`. Wrong names (`appid`/`userAppid` alone) return field errors; correct shape returns `{"data":{"value":"<accid>"}}` even without friendship.
- TIM Node self-login + `getUserProfile` / group member list for nick/mute state. Polyfill `window`/`WebSocket`/`XMLHttpRequest`/`addEventListener` before `tim-js-sdk`.

### 3) Takeover order

1. **BFLA** `GET/POST /userApi/getUserAccessToken/{userId}` — SafeLine often nails the path substring `accesstoken` on every Host. Soft encodings (`%41`, soft hyphen, split literals) still 403 at the edge. Prefer **jump egress + ultra-slow single-thread** (one request, then long cool on WAF HTML) and rotate origin IPs: **403+SafeLine/CF HTML = WAF cool (often ~900s)**; **504/openresty timeout = bad hop, try next origin without the long cool**. Do not run a parallel local BFLA spray on the same path while the jump job is cooling — same rule family poisons both.
2. **OTP window** — captcha chain when required: yidun `validate` → `captcha/check` → `getCode` (`number`+`type="2"`, optional `captchaId`). If mail is attacker-controlled, read with the correct list/latest params (`accountId` required; mail auth is **bare token**, no `Bearer `). Skip EngageLab noise code `327681`; take the later 6-digit. Blind password+code against a third-party mailbox is last-resort only and must stop on 429. **password+code `账号或密码错误` ≠ code dead** — re-fire captcha→getCode, then try **forgotPassword → password login** in the same window before abandoning OTP.
   - **Product mail (cloud-mail / `mail.<tenant>`):** login path is often **`POST /api/login`** (not `/api/user/login`). Authorization header is the **raw JWT string**. List with `accountId` + `size` + `type` + `full=1` (and/or `/api/email/latest`); **sort by `emailId` descending** — ascending/first-row reads return stale 9/18 codes and burn the window. Prefer `验证码…(\d{4,6})` over bare six-digit noise. Detail: `references/controlled-mail-otp-remint.md`.
   - **Guerrilla / grr.la inboxes:** `getCode` 200 + “no otp” is usually an **extract bug**, not a dead send. Bind with `set_email_user` (`email_user` + `site=grr.la` or equivalent), then `get_email_list` → `fetch_email` and parse `mail_body` for `>(\d{6})<` (fallback word-boundary 6-digit), excluding `327681`. Stamp a pre-getCode timestamp and prefer mails newer than that stamp so stale codes are not fed to login. Detail: `references/guerrilla-otp-read.md`.
   - **Phone getCode on owner-adjacent numbers** can return `发送成功` while the SMS channel is not attacker-controlled. Treat as oracle only — never walk blind 6-digit login against that phone.
3. **forgotPassword** — see pitfalls; success text alone is not proof the password changed. Couple a fresh OTP send tightly to forgot→login; do not burn codes on login-only retries after a failed password+code.
4. **oneKey** — schema and eJwt fix below; burn-copy only; never feed the primary shard ticket into oneKey. Historical success fuel is a **fresh BFLA-minted eyJ access JWT**, not the login response eJwt.
5. **session/init → wsToken only (not userSig)** — body **must** include both **`clientVersion`** and **`deviceId`** (either alone errors). Optional `platform`/`os`. Response is `wsUrl` + `wsToken` (+ often `subscribedGroups`); it does **not** mint a TIM `eJwt` userSig. userSig lives only on login field **`token`** (and rare admin mint paths). Do not grind session/init body knobs (`needUserSig`, platform flips) hoping for eJwt — decode the wsToken JWT if needed, then remint via login when TIM is kicked (`70001`). Response JWT is typically **HS512** with `msg_user_id` / `msg_accid` / `msg_device_id` / `msg_im_appid` — always the **token owner**; swapping `deviceId` does not retarget another uid. wsToken is single-use on the WS query string.

### 4) oneKey / eJwt rules

- Login field `token` is often a **compressed TLS userSig (`eJwt…`)**, not a disposable oneshot JWT. Feeding it to `userLoginByOneKey` after a correct body usually returns **`token过期或者重复使用`** — that is schema-accept + spent/wrong-class blob, not a reason to re-feed the live ticket.
- Corruption: transport may turn `/` into `*`. Fix with **`*` → `+`**, not `*` → `/`, before inflate/use.
- Request body that matches the API: **`token` + `accessToken`** both required (missing either → `请传入Token` / `请传入AccessToken`); `accessCode` is not a substitute for `accessToken`. Also send `deviceId` + `serverId`. Path: **`/userApi/userLoginByOneKey`**.
- Call **immediately** only with a **burn-copy oneshot** (historically BFLA `getUserAccessToken` JWT). Never put the primary live ticket into oneKey retries.

### 5) Stealth ops hygiene

- One aggressive login spray per egress IP; on `429` / `登录失败次数过多` stop that identity and cool or rotate Tor `NEWNYM`.
- Order IDOR (`orderDetail` by `id`) can yield payment PII for side accounts; absence of the core target's orders is common — do not treat empty FH orders as end of chain.
- Mail `forgot`/`genToken` admin oracles and public mail APIs are pivots for OTP read, not proof of app admin.

## Pitfalls

- **Do not addFriends to monitored targets** — they notice, blacklist the mule, and kill invite chains; quiet vectors still work after blacklist.
- **forgotPassword `操作成功` ≠ password reset** — dart is two-step: forgot must return a usable `resetToken` (string/object), then POST reset with `{password,rePassword,userName,resetToken}`. `操作成功` with null/empty `data` is fake and does not change the password; always verify with a password-only login or a fresh password+code login before declaring remint done.
- **`updateAppId` is display rename, not TIM remint** — a successful rename to the target appid can leave `accid`/`imAppid` on the caller shard. Before TIM dismiss, require `accid==target` AND `imAppid==target-tenant` from a fresh login/info response; display appid alone is not ownership.
- **Dismiss success gate** — report dismiss only after `session/init` `subscribedGroups` (or TIM group list) shows the groups gone. Do not claim success from a single REST `ErrorCode:0` or script exit without re-read. Owner TIM userSig and admin-scope platform destroy are different principals; member reads / report submit / openGroup `余额不足` are not dismiss. When the operator says destroy/remove, never substitute renew/recharge plans.
- **eJwt `*` fix is `+`** — using `/` yields garbage inflate and false "bad oneshot" conclusions.
- **Fake IDOR checklist** — logoutMessageUser, privateSetting, updateEmail+userId, many GET+userId only mutate/return self; never use them as "kick phoenix".
- **WAF path substring `accesstoken`** — literal BFLA paths die at the edge; jump IP alone does not fix path rules; encodings that still contain the blocked token usually still match. Free-CN / Fujian / partner hosts that historically served BFLA often graduate to CF 403 / openresty 504 / SafeLine — re-probe once per campaign, then stop dual-spraying every origin.
- **`imApi/getUserSig` / `imuser/changeImToken` are admin-scope** — customer/app JWT gets `access deny` or edge WAF HTML even with correct body shapes (`accid`/`userId`/ImUser). Swagger marks Authorization global on the im-user controller. One negative matrix is enough; switch to owner login remint or a real admin ticket, not payload roulette.
- **Platform ticket live + TIM dead is normal** — `getUserInfo` 200 with kicked userSig (`70001`) means remint login for eJwt, not “JWT expired”. Keep the platform eyJ for HTTP recon while cooling login.
- **Read/mutate path split on the same ticket** — `getUserInfo` / `queryTeam` / `walletInfo` / `queryFriends` can 200 while `destroyTeam` / `session/init` / other mutate paths return edge WAF HTML on the same eyJ and Host. That is a path-family rule, not “token dead”; keep using the ticket for reads and move destroy to owner TIM / admin CRUD / another origin, not endless destroy payload roulette.
- **Same mailbox, many `serverId`s** — one controlled email can mint different `accid`/`imAppid` per server. Cross-tenant TIM destroy against the main phoenix `imAppid` returns `10010`/`10015`; confirm `imAppid` from the fresh login before claiming ownership or dismiss reach.
- **`data.token` missed as userSig** — walkers that only match keys named `userSig` leave a 200 login “without sig” and skip destroy. Prefer `token` when value starts with `eJwt`, then nested names.
- **Forgot then login on one OTP** — after a successful forgot body, force a new getCode before login; one-code remint scripts thrash the mailbox and look like rate-lock.
- **Long destroy pressers must hot-reload ticket files** — a background loop that freezes packs at start keeps firing `70001` after a remint wrote fresh eJwt to disk. Re-read the live pack file each cycle (or on 70001) before TIM calls.
- **Thin group oracles** — `teamApi/queryTeam` with `appid=<tid>` often returns only `{"tid":"…"}` (existence). `get_online_member_num` can return OnlineMemberNum for private groups you are **not** in, while `get_group_info` / roles stay `10007`. Use online counts as liveness intel only; name/owner still need membership, owner sig, or admin.
- **Namecards / bet nicks ≠ TIM tid** — exchange “3群/5群” namecards and robot @nicks with trailing 3/5 are channel labels, not GroupId. Do not promote them to dismiss targets without a real 8–10 digit tid + `queryTeam`/TIM confirm.
- **Controllable `@tenant` mail ∩ target-group members is often empty** — cracked mailbox users on the dump are frequently other-server mules. Cross roles via TIM member lists / `get_role_in_group` before spending OTP budget reminting every cracked address.
- **`timeout=1` is not a background job** — use `background=true` then wait/poll; otherwise you only see exit 124 and zero durable work. Re-launching with `timeout=1` after a failed launch is the same pit, not a fix.
- **429 on login/getCode** — stop that spray and that identity; resume only after cool/egress change. CF/lock on phone·Tor·device → kill that spray; switch to remint / order IDOR / BFLA cool / OTP — never "slow it down and continue".
- **OTP `账号或密码错误` after a real code** — do not discard the window; re-send then forgotPassword→login before declaring OTP dead.
- **WAF cool idle** — a 900s jump cool is work time for remint/HIST soft/order expand/yidun, not a reason to stop the quiet press chain.
- **Owner `getLoginDeviceRecords` showing a known spray deviceId** — usually the mule's own history from your probes, not the target's device inventory.
- **APK stringen field names** — client paths/params are often XOR-obfuscated (`[0xe4e1,0xb55b,0x85cd,0xffff]` cyclic on UTF-16 code units). Decode the **exact** Java string literal (mix of `\ueXXX` escapes and real Unicode) before guessing Retrofit body keys; wrong guesses waste probe budget.

## Related

- Full IM overlay surface / TIM crypto / WAF matrix: skill `im-chat-platform-pentest`
- Dismiss authority / admin scope / fee-vs-destroy: `ruoyi-admin-console-attack` → `references/destroy-authority-matrix.md`; money layer: `tim-overlay-wallet-ops`
- WuQuan dump/BFLA campaign notes: `pentest-execution` → `references/wuquan-57nz-mass-user-dump-chain.md` (user-owned; recommend `hermes curator adopt pentest-execution` if that file should absorb these quiet-path rules)
