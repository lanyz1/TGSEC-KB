---
name: im-overlay-multi-group-recon
description: "Use when multi TIM/IM family groups need recon or dismiss."
version: 1.0.0
tags: [pentest, im, tim, multi-group, recon, dismiss, quiet]
---

# Multi-group recon on TIM-overlay IM families

Use when the operator names a **family of parallel money/chat groups** (e.g. lane 3/5/6/9 + exchange) on a Tencent IM overlay, and the goal is **map every live tid/owner then dismiss** — not deep-dive a single famous tid.

Companion to `im-overlay-quiet-takeover` (stealth session) and `ruoyi-admin-console-attack` → `references/destroy-authority-matrix.md` (who can destroy).

## Standing rules

1. **Family board first.** If the operator names N lanes, open/maintain a multi-row board (tid / name evidence / owner / join / online / TIM destroy / platform destroy) **before** grinding one tid. Single-lane tunnel vision after a multi-group brief is a workflow failure.
2. **Channel appid ≠ group tid.** Staff nicks like `AA…3️⃣/5️⃣/9️⃣粉` and appids `FH8888` / `FH5555` / `FH777777` / finance appids are **deposit/finance channels**. `queryTeam` must use **`{"appid":"<numericTid>"}`** (field name is the group id string) — `{"tid":...}` alone returns `请输入APPID`. Channel appids returning `tid:null` is expected — do not treat channel hits as group ids.
3. **Quiet only on monitored staff.** Prefer read-only TIM + offline dumps + member namecards over C2C spam asking for sibling tids. When a **bridge group you own** already holds the staff Admin as member, bridge `send_group_msg` is quieter than cold friend_add (often `38001`) or REST C2C (`90009`). Still do not spray “发群号” into the production money groups themselves.
4. **Destroy principals stay three-way** (owner userSig / admin CRUD / managerApi key). Member JWT `destroyTeam` → `access deny` / edge WAF even on a **self-created** team; TIM non-owner **and TIM Admin role** → `10007`. Low-online windows do not relax owner check. One matrix row per family tid; do not re-fuzz payloads or online-burst forever.
5. **Progress under dismiss pressure:** when the operator asks why groups are not gone yet, what you are doing, or “还办不到吗”, lead with **live work** (long-presser pid/session + last CYC, short-round script name, latest matrix `on`/`d` per family tid, ticket health) then the **missing principal** (owner userSig / admin+TOTP / apiKey). Keep pressing — do not idle, do not claim “done digging”, and do not pad with fee/renew plans. Member/Admin/WS destroy staying `10007` is expected, not a reason to stop the campaign. A status ping is not a stop; answer in-line and continue the same press chain.
6. **Order/payment PII is a sibling-key map, not a destroy key.** `orderDetail` often nests `paymentWay[]` (`realName`/`accountNo`) and dump rows `userId`/`accid`/`phone` that **hint** owner-adjacent identities. Use them for remint/oracle targeting only. Historical JWTs for those uids are usually expired (`401 令牌已过期`); phone `getCode` may send while SMS is not controllable — never blind-login 6-digit space.
7. **Report language:** reachable / authorized / effect achieved. Self-mule groups and probe groups are fixtures, not family takeovers. Member-count dips without destroy `0` / `10010` are churn, not dismiss.

## Procedure

### 1) Seed the family board

1. List every lane the operator named + any “交流/担保” hub group.
2. From live mule TIM: `get_joined_group_list` → seed known tids/names/roles.
3. Offline: prior `subscribedGroups`, session bags, public group dumps, staff nick maps.
4. Write the board to disk early; update online/destroy columns as you probe — do not keep the only copy in chat prose.

### 2) Liveness without membership

| API | Member? | Use |
|---|---|---|
| `get_role_in_group` | Member list not required | Prefer over `get_group_member_info` when the latter errors `10007 you can not get msg flag from this interface` — role oracle still returns Owner/Member/NotMember for named accounts |
| `group_open_http_svc/get_online_member_num` | **No** | Best non-member liveness; online>0 ⇒ group exists even when info is blind |
| `get_group_info` (name/owner/mem) | Often **yes** | `10007 only group member can get group info` = alive+private, **not** deleted |
| `apply_join_group` | — | `DisableApply` / `WaitAdminApproval` / `FreeAccess` join policy; **one** quiet apply max on a candidate — approval pings admins |
| `queryTeam({appid:tid})` on app API | token | `data.tid` present ⇒ row still in platform DB |
| `destroy_group` as mule | — | Expect `10007`; records owner wall, not “wrong gid” |

Never conclude “tid unknown ⇒ lane dead.” Private lanes often show **online only**.

### 3) Prove sibling lanes exist (when tid still unknown)

Run in parallel; stop when tid is nailed or evidence is enough to keep hunting:

1. **Staff announcements** in the hub/exchange group (decrypt AES text if the product wraps TIM text — known product key may already be in campaign loot). Leaderboards that list `…3 / …5 / …9` prove parallel money lanes without publishing tids.
2. **NameCard scan** on hub + known large groups: cards containing `3群`/`5群`/`N群` are membership claims, not tids — record accid+card.
3. **Cross-group role matrix** for those speakers: `get_role_in_group` on famous lane vs hub. **Hub Member + famous-lane NotMember** ⇒ independent lane (not a nickname for the famous group).
4. **Chat quotes** around money ops (“去N群上分/查分/财务”) — evidence of live ops; still not tid.
5. **C2C roam with existing friends only** (`openim/getroammsg` — path is **`getroammsg`**, not `get_roam_msg` / `get_c2c_msg`). Required body fields include **`LastMsgTime`** (and typically `Operator_Account`, `Peer_Account`, `MaxCnt`, `MinTime`, `MaxTime`; empty `MsgKey` on first page). Missing `LastMsgTime` → `10010 not have name "LastMsgTime"`. Paginate with returned `LastMsgTime`/`MsgKey` until `Complete=1`. Channel粉 often re-publish **only the famous TIM tid** plus **WeChat pay-group QR/BMP** (“闲置/团购”) — treat external WeChat groups as payment rails, **not** TIM family tids. OCR payment screenshots for TIM ids only if text clearly shows an 8–12 digit group id; most are WeChat UI chrome.

### 4) Candidate tid validation

When a historical or guessed tid appears (old `subscribedGroups`, public dump, inject logs):

1. `get_online_member_num` → must be ErrorCode 0 (invalid id fails differently).
2. `get_group_info` → name if member; 10007 if private.
3. `queryTeam` / platform destroy one-shot → DB/auth oracle.
4. Label clearly: `confirmed` / `candidate-unverified-name` / `dead-10010|10015`.
5. Do not mark a candidate as “lane 6” solely because a past mule subscribed — require name, staff speech, or owner-view evidence.

### 5) Dismiss path (after board is honest)

1. Per tid: need **that** owner’s TIM userSig on the **same** `imAppid`, **or** admin-scope `destroyTeam`, **or** documented managerApi mutate with real key.
2. Self-rehearse destroy on a throwaway group first (see destroy-authority-matrix).
3. Re-read online/joined/queryTeam before claiming effect.
4. Probe/self groups may be cleaned; never count them as family dismiss.

## Pitfalls

- **Famous tid tunnel vision** — operator named a family; keep N columns live even while one tid is “almost” dismissable.
- **FH* / 粉号 = tid** — channel search and deposit C2C waste cycles; map them as finance contacts only.
- **`10007` on get_group_info = deleted** — wrong; pair with `get_online_member_num`.
- **WeChat “闲置/餐饮” QR from channel粉 = TIM sibling** — payment mule groups; TIM dismiss APIs will not hit them.
- **Asking staff for sibling tids** — noisy, historically unanswered; violates quiet-takeover standing rules.
- **One destroy probe style forever** — member deny / Admin-role 10007 / platform WAF are settled; switch to credential acquisition (owner remint, admin+TOTP, apiKey leak), not payload / online-window roulette.
- **Ticket live ≠ still in the family** — platform `getUserInfo` 200 + TIM `get_online_member_num`/`destroy_group` on family tids can all succeed while `get_joined_group_list` / `session/init.subscribedGroups` show **no phoenix/family tids**. Blind destroy from outside still returns owner-wall `10007`; that is not “wrong gid”. Re-check joined each remint; if empty, treat rejoin (`apply_join_group` → `DisableApply` / `WaitAdminApproval` / forbidden) and owner/admin principal hunt as the levers — do not spend the session only re-bursting destroy from non-members.
- **Background long presser stale packs** — if remint rewrites the live ticket file while `d*_long` still holds start-of-run sigs, TIM flips to `70001` and looks like “all tickets dead”. Hot-reload packs each cycle (or on 70001) and restart the long job after a successful remint write.
- **Finite-cycle long presser exits clean** — many `*_long.py` jobs stop after N cycles with exit 0 (not a crash). Poll the background session; on exit, **immediately** relaunch with `background=true` + notify and keep short keep-rounds in parallel. Waiting for the next operator ping to notice a dead long presser is idle time.
- **Bridge shout ≠ owner handoff** — creating a bridge, inviting Admins, and yelling for 3/6 tids is recon pressure only; destroy still needs that Owner’s userSig or admin CRUD.
- **`get_group_member_info` 10007 msg-flag** — not “not a member”; try `get_role_in_group` with the same account list for Owner/Member/NotMember without needing full member info.
- **Historical owner nick on TIM** — display/history owner can differ from current `Owner_Account`; always re-read live owner before signing dismiss.
- **Historical `subscribedGroups` single-hit** — a past mule/session bag listing only one private tid is strong **candidate** evidence for a closed lane, still not a name proof; pair with online + `queryTeam` + role matrix.
- **Mail OTP wrong `accountId`** — list mail accounts first; `total:0` inbox often means wrong mailbox id, not “code not sent”.
- **Broad gid online sweeps** — timeout-prone; prefer family-context gid sets (joined, dumps, staff-adjacent) over random 9-digit walks.

## Related

- Quiet session/OTP/oneKey: `im-overlay-quiet-takeover`
- Full IM surface: `im-chat-platform-pentest`
- Destroy principals: `ruoyi-admin-console-attack` → `references/destroy-authority-matrix.md`
- Money/binfo layer: `tim-overlay-wallet-ops`
