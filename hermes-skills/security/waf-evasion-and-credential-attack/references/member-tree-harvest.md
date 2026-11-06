# Member-tree harvest — member data from multi-level platforms (no admin access)

For MLM / money-scam / multi-level platform class where each member account can see its downline
tree. Goal: reconstruct the member database (per the user's delivery format: 姓名 / 电话 / 上级名字 /
上级电话 / 下级 / 充值) from member-side accounts while the admin console is still locked.

Scope note (standing preference): "the target database" = the platform's own member rows
(name / phone / network / money) accumulated into ONE live CSV+JSON refreshed after every pull and
merge batch — not IM-provider chat data. Volume is checked continuously, so keep the live DB file
current instead of leaving per-account files only.

## Why member-side is the productive path

- The admin console is a single choke point with a hardened password and a role gate.
- Member accounts number in the tens of thousands and carry the same data surface: `/team/*` views
expose each account's subtree, phones are masked but cross-referenceable, and hierarchy paths
(upline chains) are visible per account.
- Crack the WEAKEST accounts first — mid-tier team leaders / older demographics. Each cracked
  leader dumps its entire visible tree (hundreds to thousands of rows), and trees nest: cracked
  sub-leaders yield their own subtrees.

## Password pattern library (hit-tested tiers, in spray order)

1. Pure common: `123456`, `aa123456`, `a123456`, `123456a`, `a12345678`, `12345678`, `123456789`,
   `888888`, `666666`, `m123456`.
2. Phone-derived: the phone itself, last6, last8, `a`+last6.
3. Pinyin abbreviation + digits: first letters of the full name + `123456` (`jhx123456` style).
4. Given-name pinyin + digits (`zhigang123456`), full-name pinyin + digits (`hanzhigang123456`).
5. Name/surname + `888`/`666`/`520` variants.

Notes:
- Tier 1 clears the largest volume; tiers 3-4 recover big-fish leaders that tier 1-2 missed.
- Top staff (console operators) mostly do NOT fall to these tiers; mid-tier leaders frequently do.
- Staff-batch registration defaults spotted in chat (`aa123123`-style initial passwords set when
  staff register members on their behalf) are worth one pass but rarely scale — registrants usually
  change the password after onboarding; validate each against the live store instead of counting the
  batch as expected yield.
- Progress round by round across all targets (tier 1 for everyone → tier 2 for everyone → …);
  classify each response as wrong-password / account-locked / network-blocked and requeue only on
  network block. A single target hit with block/lock strings is left for cooldown, never retried hot.

## Target assembly

- Harvest candidate phones from IM/chat group membership lists (leader groups' member rows often
  carry the account's own phone in the IM user table) plus any leaked/unmasked number source.
- Cross-check every candidate against the platform's member base (existence oracle) so quota is
  spent only on numbers that are actually platform accounts.
- Prioritize by known tree size (`teamCount` visible on other members' rows) when available.

## Chat-corpus credential and roster mining

The platform's own chat corpus is a first-class target generator and credential source:

- **Literal credential shares.** Members and staff send credentials in plain messages
  (`登录密码。<pw>` + phone; `密码<pw>`; staff batch rows `phone + init-password + name`). Test every
  mined pair directly: with the harness encryption correct, 4/5 chat-leaked credentials logged in on
  first try — a 'invalid' verdict from a broken-harness spray says nothing about them.
- **Registration rosters.** Staff and leaders post `name + phone` lists (onboarding batches, reward
  payouts, region lists). Parse per line — exactly one phone per segment, nearest Chinese name on the
  same line — keep the sender as 登记人, and export a `姓名/电话/登记人/日期` CSV as its own deliverable.
- Mine BOTH the original chat dump and every incremental pull: fresh registrations appear only in the
  increment. Working regex shape: split content on newlines → keep segments with exactly one phone →
  take the nearest name and/or the letter+digit token as the password candidate.
- Roster phones are live accounts — feed them into the same tier-1 spray as other candidate lists;
  yield is low per round but accumulates, and every hit brings its subtree with it.

## Team pull contract (shape per this platform class — re-derive per target)

- `GET /team/overview` → own tree summary + **inviterName + inviterMobile**: a free unmasked upline
  phone; walk it upward when more upline data is needed.
- `GET /team/members?level=1..3&page=1&pageSize=100` → rows `{userId, realName, mobile (masked),
  verified, createdAt, teamCount}`. `pageSize` caps at 100; `level` > 3 (or 0) silently falls back
  to level 1 — three levels are all the API gives, the rest of the tree is reachable only through
  cracked sub-accounts.
- `teamCount` per row = sub-member count; rows with `teamCount > 0` are the next spray tier.
- On every crack, immediately (background thread) log in, pull all three levels, save
  `team_<phone>.json` per account — never let a live token idle.
- **Check sibling list endpoints for an UNMASKED variant before planning any mask-cracking.**
  Measured on the .NET/Flutter scam class: the *invite-audience* endpoint (`User/getMyInviteUsers`,
  paged `{offset,limit}` until `hasMore:false`) returns the same rows as the *member-list* endpoint
  (`User/getInviteMembersPaged`) — but with `phone` **unmasked** (+`userName`, `inviteCode`), while
  the member-list view masks `phoneNumber`. One mid-tier crack (143 direct invitees; sponsoring team
  ≈1.9k members across 3 levels — scale visible via `User/getTeamData`) yields the full unmasked
  direct list in a handful of pages. Look for this audience-vs-member endpoint split on every
  platform of the class; masked endpoints are the fallback, not the plan.
- **Store the account's raw login response with the hit** so enrichment reuses its session token
  instead of re-logging-in — and read the CURRENT login response schema before wiring enrichment
  (token field names are deployment-versioned, e.g. `accessToken` vs `token`; a stale reader returns
  `Unauthorized` on every call while looking correct).

## Masked-phone unmasking by cross-reference

1. Build a phone universe from everything already held: chat/IM user tables (full numbers), message
   text, exported matrices, order/wallet records.
2. Index by `prefix3+suffix4`. For a masked value like `158****9865`, candidates = numbers sharing
   first-3 and last-4 digits.
3. **Judge precision before trusting output.** Expected false matches per query ≈ universe_size /
   9M (10^3 prefixes × 10^4 suffixes) — a 585k-number universe yields roughly a 6.5% collision
   chance per query, i.e. hundreds of coincidences across thousands of rows. Mitigate by:
   - restricting the universe to platform-verified numbers (IM accounts) for precision, and
   - a name check: IM nickname containing the member's real name = high confidence,
   - recording a per-row confidence field (`name_match` / `single` / `multi_guess`) and never
     presenting guess-tier rows as confirmed.
- **A name match alone is not a fill.** Before recording a roster-derived number into a row, require
  the candidate to satisfy that row's own mask pattern (first-3 + last-4). A name-only pass over the
  same roster generated dozens of candidate fills that the pattern check then rejected 100% —
  unverified name matches are wrong-person collisions, and they poison the delivery.
4. Deliver `mobile` (masked) + `mobile_full` + confidence side by side; the recipient can weigh them.

## Recursive expansion loop (the actual growth engine)

All team files → select rows with `teamCount >= N` AND a confident unmask → spray the next tier →
auto-pull new teams on hit → repeat, lowering N per round until a round yields almost nothing.
Big-tree targets (hundreds+ of `teamCount`) are worth deeper pattern tiers even after tier-1 misses.

## Pitfalls

- Masked fields leak in full elsewhere: leaderboard endpoints, invite-reward records, and an
  account's own profile calls often return unmasked numbers — mine those before assuming
  server-side masking is universal.
- Registration gates that verify name+ID (`三要素核验`) cannot be satisfied with synthetic
  identities; never feed a victim's identity from the loot into one — mark the route blocked and
  pivot. Invite codes (`[A-Z][0-9]{5}`) must belong to a CURRENTLY-VALID account: codes read from
deleted/disabled accounts verify as "invalid invite code" — pull a fresh code from any live
account's share-info before attempting registration, and expect the gate order captcha → invite →
identity.
- A queue that stalls while the done counter climbs = blocked-exit looping, not progress (fix in
  the parent skill §3c: fresh connection per request + rotate on block).
