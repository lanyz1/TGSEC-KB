# Credential-pool tree extraction (invite/referral-tree platforms)

Class: MLM / "subsidy" / scam platforms whose entire user base hangs off one invite-code tree, and the ask is
"the full user database". Precondition: ≥1 working login + a candidate phone pool (an IM system's roster, a
data bundle, or the platform's own dumps).

## 1. Measure the tree API before building the engine

- Team endpoints take a generation parameter (`teamLevel=N`): `1` = direct children, `2` = grandchildren,
  `3` = great-grandchildren — each call returns a **complete generation slice**, not a page. Union of levels
  1..N = the account's whole subtree; N beyond the deepest returns `[]` (stop condition).
- **Pagination params are often ignored**: `pageSize=1000` returned ~11.8k rows in one response; `pageNum=2`
  returned the same rows again. A repeated identical page = pagination is dead — take ONE call per level;
  never loop `while len(page) >= size` on it (fixed pages loop forever).
- Sanity-check the union against a recursive count field (`teamNumber`-style): 3-slice union ≈ count ⇒ you
  hold the full subtree.
- Row shape: `inviteCode` (own code), `invitedCode` (parent), `listOfSuperiors` (ancestor chain, root-first),
  plus PII and a `passWord`/`passwordSalt` hash pair. The chain prefix shared by all users = the single
  platform root; frequency-count chain elements to find the spine; a row whose `inviteCode` equals a
  high-frequency ancestor code is that branch's own record (login candidate).
- Register-oracle (SKILL R16): registration accepts an arbitrary invite code (usually no SMS check) and echoes
  the resolved ancestor chain in the new account's record — validates codes and reinforces the spine map for
  free. Account placement is client-controlled: you can register directly under any node you name.

## 2. The engine (multi-process over a file bus — no shared memory)

Workdir files:
- `creds.json` — single credential truth (phone → pw). Every hunter appends hits; consumers re-read it.
- `users_dump.jsonl` — append-only, one full row per user.
- `*_hits.jsonl` — one per hunter (spray / crack / reuse). `*_done.txt` — resume markers.

Processes:
- **Puller**: for each cred — login (session token from the reply, e.g. `data.saToken`), then levels 1..15
  (one call each, stop at empty), append rows. Never exits: when the queue drains it merges `creds.json`
  from disk, sleeps, refills; save state every round.
- **Syncer**: every ~45 s merge all `*_hits.jsonl` into `creds.json` (read-merge-write; a lost race resolves
  next cycle).
- **Cracker**: offline check of dump hashes against a focused wordlist (static weak list + phone-derived:
  full phone, last 8/6/4 digits, digit pairings):
  `hashlib.pbkdf2_hmac('sha1', pw.encode(), base64.b64decode(salt), 10000, dklen=32) == base64.b64decode(hash)`;
  hits → `creds`. Use `multiprocessing.Pool` with **module-level** functions — closures fail to pickle
  (`Can't pickle local object`).
- **Sprayer**: candidates × `123456` first. Measured baseline: 75k same-population phones → 2,117 hits
  (≈2.8%). ~10 req/s per thread is sustainable when the endpoint has no lockout (verify with a throwaway
  account first — SKILL R5 / `pentest-campaign-discipline` §3).

Discipline: append-only everywhere; load the seen-ID set at startup; log checkpoint counts every N items so a
compaction or restart resumes without re-deriving. State lives in files, never only in the conversation.

## 3. Coverage measurement (locate the missing users, don't grind blind)

- **ID bucket histogram** (buckets of 50k): empty buckets = never-covered ranges. Contiguous coverage across
  the live id space is the goal; the gap shape says whether the remainder is mechanical (keep pulling) or
  structural (spine logins needed).
- **Ancestor-code frequency histogram**: count every element of every chain; top codes = spine. For each,
  search the dump for the row whose `inviteCode` == that code — present ⇒ crack/log in and extend downward;
  absent ⇒ structural gap only a node at/above it can fill.
- Report coverage as union-count vs max-id seen.

## 4. Cross-system reuse flow (detail for SKILL R18)

1. Harvest full objects from the sibling system via its account-keyed endpoint (sensitive fields appear only
   on that key form — SKILL R17).
2. Per object: custom plaintext trade password → offline test against the same phone's hash on the target
   system (zero requests); else one online login (`密码错误` = exists/miss; `未注册` = skip; `用户已冻结` = frozen).
3. Hits → `creds` → puller extracts that subtree. Re-run after each harvest batch.

## 5. Pitfalls

- Never fire `pkill -f <pattern>` from a shell whose own command line contains the pattern (self-kill, exit
  -15/-9); kill by PID or run cleanup from a script file — `pentest-campaign-discipline` §4.
- Fake padding batches: platforms mass-generate leaf accounts on vanity number sequences (e.g. `1380000xxxx`)
  with `123456`, sunk under deep nodes to inflate team counts. Probe one sequence to confirm padding; those
  rows are low-value (no children). "测试"/vanity accounts likewise expose spine codes but own no subtree.
- Weak-password rate collapses with the registration wave (SKILL R18) — don't point a dictionary at late
  cohorts.
- New-domain discovery: `grep -oE 'https?://[^"]+'` over any message/chat dump, and hit config endpoints
  (`customerService`-style) — both surface mirrors, download hosts and third-party panels
  (chat/customer-service systems).

## 6. Random-sampled team APIs (no stable ORDER BY)

Some implementations don't ignore pagination — they randomize it. Same page ×3 returns three different
sets; `sort=id&order=asc` is accepted but the order still varies. Treat it as sampling with replacement:
- Totals per level are still authoritative (`data.list.total`); page count is `ceil(total/10)` — page size
  is often hardcoded and `limit`/`page_size` are silently clamped to 10 (confirmed `len=10` for every name).
- Unique after D draws ≈ N(1−e^(−D/N)). One full pass ≈63% (measured ~67%), two ≈86%, three ≈95%. Run
  passes, dedupe by `user_id`, and stop on marginal gain rather than grinding.
- Never loop `while len(page)==size` — it never ends; loop `page=1..ceil(total/10)` per pass.
- Check `type` filters (`type=1/2/3` = all / realname / active) — they are subsets, not partitions.

## 7. Masking tiers and official first-code enumeration

- L1 (direct children) returns full `phone`/`realname`; L2-L4 return masked values. Each new spine login
  only adds its own L1; to grow the unmasked set, crack more direct-upline accounts, not deeper levels.
- **Vanity invite codes are platform officials**: `999999/888888/666666/555555/333333/222222/111111/
  123456` resolve at registration to the upline's realname + phone (register a throwaway under each and read
  `up_user`). Those phones seed the credential pool; official passwords cluster on `123456` / `654321` /
  `aa123456`, and API login has no account lock (R5), so a tiny targeted list per official is high yield.
  The root account is the one whose `up_user_id` is `0`; its own team API may 504 on large trees even when
  every child account answers — record the wall and harvest the child subtree instead.
- Other modules leak full PII for the *authenticated* user even when the team list masks: subsidy
  applications (`subsidy/applyList`) returned realname, ID number, full phone, home address, payee bank
  account and amount. `applyDetail`/`applyProgress` are owner-scoped (another id returns own row or
  `申请记录不存在`) — test IDOR explicitly there, don't assume it from the list shape.
