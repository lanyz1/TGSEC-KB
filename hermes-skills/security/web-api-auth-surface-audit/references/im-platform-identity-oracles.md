# IM-overlay platform: identity oracles & roster pivots

Worked instance for the class in SKILL.md R14/R15/R16: a white-label gambling platform fronting several
Tencent-TIM `SDKAppID` "universes" (each universe = its own IM app id + its own shard of the same business
DB). Condensed to what transfers — request shapes, pivot order, and deadends with reasons. Concrete paths are
kept because the next engagement on this family meets the same names.

## 1. The client bundle is the schema

Flutter-web SPA → one `main.dart.js` (~7 MB). Endpoint list and request keys come straight out of it:

```bash
grep -oE '"<prefix>/[A-Za-z0-9_/]+Api/[A-Za-z0-9_]+"' main.dart.js | sort -u   # the whole surface
grep -o '"<prefix>/<ns>/<path>"' main.dart.js                                  # one endpoint
```

Then read the ~600 chars *before* each hit for the body construction:

- `A.u(["accid",a],...)` → single request key `accid`
- `A.u(["tid",p.w,"memberList",a],...)` → keys `tid` + `memberList`
- `A.u(["type",a,"value",b?"1":"2"],...)` → value is the string `"1"` / `"2"`, not a bool
- `if(J.kS(n.gdu(o),"appid")){n=n.h(o,"appid")}` → the response field the client reads back

Errors that are actually gifts: a key guessed as `appid` answered `请输入APPID或手机号` (required-key error) when
the real key was `number`; and sending a JSON **array** for a key the server types as `String` returns a
Jackson `Cannot deserialize value of type 'java.lang.String' from Array value` — proving both that the handler
is reachable and that the field is scalar.

The extracted surface bounds the **client**: an operator/admin panel fronting the same API can still own routes
the app never calls. "Absent from the bundle" = no app-facing route, not no route.

## 2. Identifier cross-resolution (the oracle)

```
POST /<prefix>/friendsApi/queryFriends      {"number":"<appid>"}  → {"data":{"appid":"...","accid":"..."}}
POST /<prefix>/friendsApi/queryFriends      {"number":"<phone>"}  → {"data":{"appid":"...","accid":"..."}}
POST /<prefix>/friendsApi/queryFriends      {"number":"<accid>"}  → {"data":{}}        ← not a valid key value
POST /<prefix>/friendsApi/queryFriendsAppid {"accid":"<accid>"}   → {"data":{"appid":"..."}}   (friends only)
```

- Empty `data:{}` = unallocated/unknown → clean existence oracle; the differential is what makes it usable at
  scan rates (R13/R16).
- `queryFriends` resolves regardless of friendship despite its name; the sibling `queryFriendsAppid` is
  genuinely friendship-scoped and answers `{}` for non-friends — calibrate each against an account you can
  resolve independently.
- This is the bridge between layers: an IM group roster only ever yields `accid`s, and a business dump is keyed
  on `userId`/`appid`/phone. One request per held identifier re-joins them.
- Spend it on identifiers already in hand, never as a blind id-space sweep. Sub-1M spaces are still days at a
  paced rate; the first confirmed pairs reveal the id format (brand prefix, leading-zero padding) and collapse
  the search.

## 3. Roster + role pivot (member session is enough)

Any account that is a **member** of the target group reads the whole group — no admin rights needed:

```
get_group_public_info  {"GroupIdList":["<gid>",...]}          # ANY group id, member or not; batch ≤50
   → Name / Owner_Account / MemberNum / group_appid  (+ per-id ErrorCode when absent)
get_group_info         {"GroupIdList":["<gid>"], "ResponseFilter":{"GroupBaseInfoFilter":
                        ["Name","Owner_Account","MemberNum","Type","CreateTime","Notification","Introduction"]}}
get_group_member_info  {"GroupId":"<gid>", "MemberInfoFilter":["Role","JoinTime","NameCard"],
                        "Limit":100, "Offset":<n>}            # paginate to MemberNum; Role ∈ Owner|Admin|Member
```

`get_group_public_info` is the cheap probe: it names and attributes group ids you have never joined, in every
universe, 50 ids per call — pair it with a team/appid sweep to turn a bag of ids into a named group map.
`get_group_info` is the **authoritative** owner read; use it instead of any profile/nickname claim (R14).
Member rosters are the pivot into credential work, and they come free from a single cracked member account.

## 4. Platform config rides inside IM group metadata

`get_group_info` with `AppDefinedData` in the filter returns the platform's own team config, readable by any
member: `group_appid`, `expire_date`, `banned_status`, `higher_status`, `private_mode`, `forbid_back`,
`notice_mode`, `good_number`, `icon_url`, `name_colour`. `expire_date` is the platform's own team expiry —
read it early, because a team about to expire changes the cost/benefit of forcing the owner's credentials.

## 5. WAF + egress shape (Cloudflare in front)

- `/<prefix>/teamApi/*` was an **endpoint whitelist**: only the routes the client calls passed; every other
  name — including names avoiding every dangerous-looking keyword — returned CF 403. So "the dismiss route
  exists but is WAF-blocked" was a mirage; discriminate with the known-good + nonsense + suspect triple (R11).
- The SPA host reverse-proxies the API prefix and works even when the API host is picky about `Host`.
- Tor exits were 403'd on the authenticated paths; the direct origin IP was the only viable egress, at a paced
  ~2.5 req/s. A ~25-request burst earned a long 429 window that blocked probes too.
- Login/`getCode` rate-limit hard: pace ~30 s or rotate egress; issued codes have a ~5-minute TTL.

## 6. Deadends recorded (do not re-run)

- **Dismiss/close-group route**: absent from the client surface, and the platform team API is whitelisted. The
  IM **owner's `userSig` is the only lever that destroys a group** — so owner-credential work is the whole
  game, and every step should be scored against "does this get me the owner's session".
- `getUserInfo`-style reads are session-bound (GET only); extra identifier params are ignored. No IDOR.
- `getCode` answers success for existing and non-existing principals alike (anti-enumeration) — not an oracle.
- User-profile reads on other accounts require admin privileges (`Err_Profile_No_Admin_Privileges`).
- `serverId`-style shard params do not validate (`0` / `-1` / `9999` all answered), yet credentials are
  per-shard: replay a failing login on every shard before retiring it (R15).
