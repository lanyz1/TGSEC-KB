# Destroy / dismiss authority matrix (IM-overlay + RuoYi admin)

Use when the operator goal is **remove/dismiss groups or teams**, not renew them. Map the
principal before grinding payloads — most nearby endpoints only prove existence or billability.

## Three independent principals

| Principal | How you hold it | What actually removes a group |
|---|---|---|
| **TIM group owner** | live `userSig` whose `TLS.identifier` == `Owner_Account` on the **same** `imAppid`/SDKAppID as the group | TIM `destroy_group {GroupId}` → `ErrorCode:0` |
| **Platform admin CRUD** | admin gateway JWT with a scope that authorizes the entity controller (not merely `login_scope:manager`) | admin module path e.g. `POST …/iImgroupinfo/destroyTeam` body shaped from Swagger `definitions` |
| **Shared-secret helper** | correct `apiKey` (and required fields) on token-less `managerApi`-style controllers | only if that op's doc actually mutates owner/expire/destroy — parameter-complete wrong keys collapse to one permission string |

A **member** TIM session can read (`get_group_info`, AppDefinedData, expire_date) and is recon only.
Member **or TIM Admin-role** destroy (REST or binfo WS) → `10007 only group owner can destory group`.
Low online windows and dual-head WS tricks do not change that. Do not re-test payload variants.

**Live ticket outside the group still hits the owner wall.** Platform JWT + TIM userSig can stay green
while `get_joined_group_list` / `subscribedGroups` no longer list the family tid — non-members may still
call `get_online_member_num` and `destroy_group`, and destroy remains `10007`. Re-read joined after every
remint before treating continuous destroy bursts as progress; empty joined → fix membership or obtain an
owner/admin principal, do not only raise destroy cadence.

## Platform HTTP vs TIM — do not conflate

- Customer/app JWTs (including the **owner's own** platform token) commonly answer `access deny` on
  admin `destroyTeam` even when that user owns the TIM group. Platform destroy is **admin-scope**,
  not group-owner-scope. Self-created teams still `access deny` / edge WAF on customer tickets —
  that is the admin wall proof, not a wrong tid.
- **Admin-only IM user controllers** (`/imuser/changeImToken`, `/imuser/*`, Swagger `im-user-controller`
  with `Authorization: global`) mint or rotate IM credentials only for admin gateway JWTs.
  Customer tokens get `access deny` or WAF HTML; do not treat these as member BOLA after one matrix.
- **`imApi/getUserSig` / `timApi/getUserSig` / `imuser/getUserSig`** — same admin wall when probed with
  app JWT; body variants (`accid`/`userId`/`identifier`) collapse to one deny. Remint owner login or
  hold admin CRUD instead of grinding mint paths.
- Conversely, a manager-scope admin token that works on order/team **list** APIs still `access deny`
  on destroy CRUD. Decode claims, map a capability matrix, and stop header/scope knobs after one
  negative probe set (see parent skill §4).
- Oracle ladder on the admin path:
  - no/missing token → `令牌不能为空` (route live)
  - wrong principal type → `LoginUser cannot be cast to ImLoginUser` (token accepted, wrong class)
  - signed but under-scoped → `access deny` (including origin IP + Host rewrite that bypasses CF)
  - edge WAF HTML on destroy while read APIs 200 → path rule on mutate/admin routes only
  - authorized → business success; **re-read** membership/list before claiming effect

## Self-rehearsal gate (mandatory before claiming a dismiss path)

1. Create a throwaway group on the same shard (`createTeam` field is often **`teamName`** not `name` —
   `请输入群昵称` means rename the field, not “create disabled”).
2. Destroy it with the candidate principal:
   - owner userSig → TIM `destroy_group` must return `0` then re-read → `10010` / gone
   - admin token → platform `destroyTeam` must succeed **and** TIM/list re-read must show gone
3. Only then aim the same principal at the real target GroupId/tid.
4. Cross-shard: group exists only under its `imAppid`. Wrong SDKAppID → `10010` / `群组不存在` — that
   is tenant miss, not "already deleted". Confirm `imAppid` from login/`session/init` first.
5. Rapid `createTeam` thrash → `操作频繁，休息一下吧`; cool before using create as a destroy probe.

## Paths that are NOT dismiss levers

Do not offer these as substitutes when the goal is destroy/remove:

- `teamApi/openGroup` / `renewGroup` / `renewTeamInfo` — fee/IDOR existence proofs; `余额不足` means
  billable, not dismissable. Operator "dismiss not renew" forbids pitching recharge to finish.
- `reportApi/submitReport` — may insert rows (`code:200`, incremental id) and apply pressure; it does
  **not** remove the group. Useful as side channel only after the authority map is locked.
- Member `customerSetting` / generic `{tid,type,value}` on a victim subject → ownership gate first
  (`权限不足`); type enum only learns on a self-owned subject.
- `userLoginByOneKey` with a correct dual-token body that always returns spent/reuse errors on this
  deploy — disabled door, not a cross-account BOLA (see `tim-overlay-wallet-ops`).

## Priority order when dismiss is the goal

1. **Owner TIM userSig** on the group's `imAppid` (fastest verified remove when ownership is held).
2. **Admin CRUD token** that passes destroy on a self-owned probe, preferably via a non-banned
   origin that serves the same module (edge may hard-ban the pretty admin host after TOTP noise).
3. **managerApi / partner-SaaS apiKey** only after Swagger shows a mutate/destroy/owner-transfer op
   and parameter-complete probes leave a real key oracle — not a platform-name wordlist.
4. Recon-only: member reads, bridge-group social press, report spam, fee-gate IDOR — pressure/intel,
   never as "done". Bridge invites + `friend_add` to owners often hit `38001`; WS group send to a
   self-owned bridge that already has staff Admins is the quieter social channel.

When asked why dismiss has not landed yet: name which of the three principals is still missing and
keep the live matrix (`on`/`d`/`alive`) updating — do not substitute openGroup/renew plans.

## Reporting language

- Say **reachable / authorized / effect achieved** as three checkboxes.
- Self-registered or operator-owned test accounts are fixtures, not takeovers.
- Do not list renew/openGroup success plans under a destroy objective.
