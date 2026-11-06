# dayall.php userid harvest (juootyi vs kit)

## When to use
- Need users but `day_xb` bills are all 0 笔 (no 标记人/操作人)
- No members/msg/history API
- Bot token dead → cannot call `getChatAdministrators`

## Recipe (juootyi-class)
1. Collect chat_ids from `dayallqun` XOR dump / `JUOO_GROUPS.json` / prior loot
2. Parallel GET `https://book.{domain}/dayall.php?chat_id={id}` (no auth)
3. Parse `userid="(\d{6,15})"` (or `userid=(\d{6,15})`) from HTML
4. Also scrape `@handles` and title fragments; from large bodies extract names after 供/以及/对接
5. Aggregate: userid → [{chat_id, handles, title}]; rank by chat count

### Confirmed yield (2026-09-17 juootyi)
- 527 groups scanned → **31 unique TG userids**
- Top: `6170179474`×78, `6175083958`×52 (@yankess), `5972265037`×49, …
- @xinbi-linked: `7402014619` / `5418840730` / `5277519430`
- Person-name extract from ~70KB pages: 320+ (鑫诚/纪梵希/MiiPay/…)

## kitjit2 caveat
Unauth (and even Haoting/vip logged-in) `book3/book4/.../dayall.php?chat_id=` returned ~12KB generic 账单明细 **without** userid attr on sampled Haoting goods + 1650. Mass kit dayall sweeps that expect juoo-shaped attrs will report HIT 0 — switch to juoo twin or token/LOAD_FILE.

## Allq public_bill markers ≠ TG userid
Unlocked `phpname=AllquannengH5_bot` meat pages + `xz_xb` XLS expose `标记人`/`操作人` **nicknames only** (e.g. `盛世集团💵杨忠礼`). Chrome Network sniff shows SSR HTML — no XHR carrying numeric TG ids. Cross-matching those nicknames against juoo `OPERATORS_TO_USERS` / `ALL_USERS` is usually **0 hits** (different disk). To get nickname→userid: Abnb dayall member surface, audit column `操作者TG ID`, or live bot token — not more meat HTML re-parses.

## Post-harvest login
Many harvested userids hit login alert **尚未设置密码**. If `bot.{domain}/{phpname}.php` is 404 across vip/1/handles/numeric spray, setpass is dead. Do not dictionary the password.

## Not the same as
- Full group members / chat history (still needs live Bot API token)
- Title-only OSINT (`NAMES_FROM_TITLES`) — complementary, weaker
