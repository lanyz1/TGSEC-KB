---
name: tim-overlay-wallet-ops
description: "Use for TIM binfo, exchangeBalance, openGroup money layer."
version: 1.0.0
tags: [pentest, tim, binfo, wallet, openGroup, exchange, c2c-order, im-overlay]
---

# TIM client + wallet money layer (IM-overlay class)

Companion to user-owned `im-chat-platform-pentest` / `im-overlay-quiet-takeover` (adopt those if they should absorb these rules). This skill is the **client-protocol and money-layer execution path**: binfo WS, AES C2C, exchangeBalance, openGroup fee gate, C2C order stuck-trade diagnosis.

Recognition: platform HTTP (`/userApi`, `/teamApi`, `/walletApi`, `/orderApi`) over a Tencent IM tenant; login returns `access_token` (eyJ) + `token` (eJwt userSig) + `accid` + `imAppid`.

## Standing rules

1. **Three header modes — probe both App-Authorization styles before declaring 401.** Mode A: `App-Authorization: wuquan` (fixed product string) + `Authorization: Bearer <at>`. Mode B: `App-Authorization: <at>` + `token: <at>` + `Authorization: Bearer <at>` (historical free-CN / www host). Same path can 200 under one and CF-HTML under the other.
2. **Never spray pay passwords on a live wallet.** Wrong `password` on `transferCn` / `exchangeBalance` / `buyCny` trips `由于安全原因，您的钱包功能已被暂时锁定` and blocks the entire money path until human unlock. Confirm the paypwd once; stop on first 密码有误.
3. **`余额不足` on openGroup is often USDT-empty, not CNY-empty.** Bill rows of type `OPEN_GROUP` historically debit the large USDT/CNY pool that exchange fills. Read `walletInfo.usdtAmount` before grinding levelId. CNY-only rich accounts still fail openGroup until `exchangeBalance` lands USDT.
4. **userSig dumps: decode offline before batch login.** `base64url(zlib(json))` with `+`↔`*`, `/`↔`-`. Payload has `TLS.identifier` + `TLS.sdkappid` + `TLS.time`. Pair each sig only with its identifier; cross-accid tests waste budget as `70013`. `70001 Kick` means the sig was once valid — stop retrying that blob, remint.
5. **oneKey is a dead door on hardened deploys.** Correct dual-token body still returns `token过期或者重复使用` globally (same shard included). That is schema-accept + spent/wrong-class blob, **not** cross-account BOLA — do not rebuild campaigns around oneKey.
6. **OTP type is asymmetric and product-specific.** Mail **send** uses `getCode type=2`. Code **login** may need `userLogin type=1` with empty/known password on some shards, or `type=2` with password+code on others — probe once from a known-good historical body, then stick to it. `forgetPassword` `操作成功` with empty data is fake until a password/code login re-verifies.
7. **Dismiss goal ≠ fee path.** When the operator wants groups destroyed/removed, do not pitch `openGroup` / `renewGroup` / recharge even if tid has no ownership check and `余额不足` proves the group is in the billing table. Fee-gate IDOR is intel only; the remove levers are owner TIM `destroy_group` or admin-scope platform destroy (see `ruoyi-admin-console-attack` → `references/destroy-authority-matrix.md`).
8. **Platform HTTP destroy ≠ TIM owner rights.** The owner's app JWT still gets `access deny` on admin `destroyTeam` on deploys that separate manager/admin CRUD from customer tokens. Prove remove with TIM owner userSig self-rehearsal (`ErrorCode:0` + re-read) before claiming a platform path works.
9. **`session/init` does not remint userSig.** After TIM `70001 Kick`, keep the platform eyJ for HTTP if still valid and **login-remint** for a new eJwt; session/init only refreshes wsToken/subscribedGroups.

## Procedure A — TIM binfo client (when REST admin is closed)

REST `openim/sendmsg` and admin roam need administrator (`90009`). Client path that works without admin:

1. Endpoint: `wss://wsssgp.im.qcloud.com/binfo?sdkappid=<imAppid>&instanceid=<hex>&random=<r>&platform=7&host=unknown&version=-1&sdkversion=2.27.6&compress=gzip` with Origin `https://web.sdk.qcloud.com`.
2. Outbound frame = **raw UTF-8 JSON bytes** (latin1 pack of the JSON string). No length prefix. Inbound may be plain JSON or `COMP`-prefixed compressed.
3. Login command: `im_open_status.wslogin`, body `{state:"Online", isWebUniapp:0, InstType:0}`.
4. Head before login: `identifier=<accid>`, `usersig=<login token>`, `sdkappid`, `sdkability:192371`, `websdkappid:537048168`, `websdkversion:"1.7.3"`, `contenttype:"json"`, `reqtime`, `seq`, `servcmd`.
5. On login OK: body keys are **PascalCase** — read `A2Key` / `TinyId` / `InstId` (also accept lowercase fallbacks). Missing those fields while `ec=0` usually means you looked at the wrong case, not a failed login. Subsequent heads use `a2` / `tinyid` / `status_instid`; keep `identifier`+`usersig` only as a dual-head probe when a2-only returns protocol errors.
6. **HTTP login `data.token` is often TIM userSig.** When the platform returns `token: eJwt…`, treat it as `usersig` for REST/WS. Walkers that only accept a key named `userSig` drop live sessions after 200 login.
7. **Member C2C goes through WS, not REST.** REST `openim/sendmsg` (and admin roam) returns `90009 Insufficient permissions` even for mutual friends — that path needs TIM admin secret. Client cmd `openim.sendmsg` after wslogin is the member path. Body uses **PascalCase** `From_Account`, `To_Account`, `MsgRandom`, `MsgBody:[{MsgType:"TIMTextElem", MsgContent:{Text:<payload>}}]`. camelCase-only shapes return `90003`.
8. **Chinese / non-ASCII must be AES-128-ECB.** Key string `666888` **NUL-padded to 16 bytes**, PKCS7, base64 into `Text`. Bare Chinese is truncated by the Qr packer. English ASCII may pass plain; still prefer AES when the peer client decrypts.
9. Group send: REST `group_open_http_svc/send_group_msg` and WS `group_open_http_svc.send_group_msg` both work for members of the group (`ErrorCode:0`). Same AES rule. Use bridge/self groups for social press when REST C2C is closed.
10. Owner ops that work client-side when you are owner: `destroy_group {GroupId}` → `ErrorCode:0`; `change_group_owner {GroupId, NewOwner_Account}` when target is already in the group. Non-owner destroy — REST, WS, or TIM **Admin** role — is always `10007 only group owner can destory group` — not a payload / head / online-window problem.
11. **change_group_owner on a bridge group does not transfer rights on the new owner's other groups.** It only moves the group you created.
12. **`sns/friend_add` top-level `ErrorCode:0` is not friendship.** Read `ResultItem[].ResultCode`. Monitored owners/admins often return **`38001` 禁止违规加好友** per item while the envelope is 0 — stop retrying friend_add to those accounts; stay on bridge group send + existing friends (`friend_check` BothWay).
13. Self-rehearsal: `createTeam` (HTTP) or TIM `create_group` → invite → destroy. Prove the chain end-to-end before claiming a dismiss path exists.

Detail: `references/tim-binfo-ws-protocol.md`.

## Procedure B — wallet / openGroup / exchange

1. `GET /walletApi/walletInfo` → `cnyAmount`, `usdtAmount`, `payPwd`, rates, `minExchangeAmount` (often 100).
2. Fee table: `GET|POST /teamApi/getGroupLevelConfig` → VIP1/2/3 monthlyFee (e.g. 458/528/688). openGroup body is `{tid, levelId}` (levelId from config `id`).
3. **openGroup has no ownership check on tid** — any authed caller can target any tid. Failure modes: `请选择要开通的群组配置` (missing/wrong levelId), `余额不足` (fee gate), `群组配置不存在` (levelId 0/invalid).
4. Exchange that works: `POST /walletApi/exchangeBalance` body `{password, balance, from:"CNY", to:"USDT"}` (or reverse). Response `兑换成功` / `操作成功`. **Do not burn time on `/walletApi/cnyToUsdt` or `/walletApi/exchange` when those return CF HTML — path whitelist.**
5. After exchange, re-read walletInfo, then openGroup. If still `余额不足`, the target group may already sit at a higher VIP tier than your USDT covers — try higher levelId only if balance allows.
6. Transfer: `POST /walletApi/transferCn` `{accid, balance, password}` (field name is `balance` not only `amount`). Same paypwd lock risk.

Detail: `references/wallet-openGroup-exchange.md`.

## Procedure C — C2C order free-CN shape (when BFLA seller mint is open)

Historical chain (re-verify live; BFLA path is often edge-blocked now):

1. List open sells: `GET /orderApi/orderList?pageNum=&pageSize=` (POST may answer method-not-supported). Shape is often **`{total, rows:[…]}`** at the top level (not only `data.list`).
2. `POST /orderApi/orderDetail {id}` → `order`, `paymentWay[{id,type,realName,accountNo,url,…}]`, `accountInfo`, optional `tradeOrderList`. **PII is in `paymentWay` / nested account objects** — extractors that only walk `order.*` report zero phones while the same JSON holds `realName`+`accountNo`.
3. Buy: `POST /orderApi/buyCny {id, balance:<minBalance>, password:<paypwd>}` — field for qty is **`balance`**; missing → `请填写购买数量`; wrong pwd field name → `请填写支付密码`.
4. Force settle as seller: `POST /orderApi/confirmLoan {id:<tradeId>}` with **seller** JWT. `该订单已经放款` = already settled; `您无权支付该订单` = wrong actor.
5. Stuck trade blocks cancel: `该订单存在尚未完成的交易，不可取消`. Resolve via confirmLoan / buyer cancelTrade / wait expiry before reusing that sale order.
6. Seller mint (when open): `GET /userApi/getUserAccessToken/{sellerUserId}` under Mode B headers on the host that historically served it. SafeLine/CF on that path = cool, do not dual-spray.

`余额不足` on buy after lock = buyer wallet locked, not order residual.

## Procedure D — userSig triage from dumps

1. Collect `{userID, userSig, SDKAppID}` from login JSON / jump loot / `dc_*.json`.
2. Offline decode every sig; bucket by `TLS.identifier`.
3. Live test only matching pairs on matching `sdkappid`. Codes: `0` live, `70001` kicked (was valid), `70003`/`70009` key wrong, `70013` id mismatch, `70014` appid mismatch.
4. On live: `get_joined_group_list` then owner-only destroy of **self-owned** probes only until ownership of the real target is proven.

## Pitfalls

- **App-Authorization fixed string vs token** — mixing them up produces CF HTML that looks like path WAF; switch mode before concluding blocked.
- **CF path whitelist vs method whitelist** — changing GET/PUT/DELETE on a blocked path still 0-hits when the rule is path-based; find an alternate path name from client bundles or historical loot.
- **session/init BOLA false positive** — swapping uid/deviceId still returns **your** wsToken/msg_user_id. Decode JWT claims before claiming cross-user WS.
- **createTeam thrash** — `操作频繁，休息一下吧` after rapid creates; cool before openGroup tests on new tids.
- **Bridge social ≠ group owner** — C2C friendship + bridge membership + change_group_owner to a target never unlocks their phoenix/owner groups.
- **Cross-shard balance** — a rich wallet on imAppid A cannot openGroup-pay a fee that is settled on shard B's money view; confirm serverId/imAppid of the token matches the group tenant.
- **AES key length** — `createCipheriv('aes-128-ecb', Buffer.from('666888'))` throws invalid key length; always `Buffer.alloc(16,0)` then copy the 6-char key.
- **C2C field case** — `from_Account`/`to_Account` fail; use `From_Account`/`To_Account`.
- **Login body case** — stash `A2Key`/`TinyId`/`InstId` from wslogin; lowercase-only reads look like “login OK but no session”.
- **REST C2C `90009` ≠ friendship missing** — friendship is fine; REST openim needs TIM admin. Switch to WS sendmsg or group bridge send.
- **`38001` on friend_add** — anti-abuse on monitored owners/admins; do not burn wording variants.
- **TIM Admin ≠ Owner for destroy** — Admin role destroy (REST or WS) stays `10007`; only `Owner_Account` userSig removes.

## Deliverable gates

- Dismiss/destroy: only report after the **correct principal** succeeds and re-read shows the group gone — owner TIM `destroy_group ErrorCode:0`, or admin-scope platform destroy that passes a self-owned probe first. Member reads, report submit success, and openGroup/`余额不足` are **not** dismiss proof.
- Money: only report openGroup/exchange after walletInfo before/after deltas and a non-locked paypwd path — and only when money/open is the actual objective.
- Do not pad reports with kicked userSig lists or CF-HTML path probes.
- Self-owned / operator test accounts are fixtures, not takeovers.

## Related

- Full IM overlay surface / quiet takeover: `im-chat-platform-pentest`, `im-overlay-quiet-takeover` (user-owned; adopt to merge).
- Admin destroy scope / TOTP / reporting: `ruoyi-admin-console-attack` (+ `references/destroy-authority-matrix.md`).
- Campaign pacing / codeLogin gates: `pentest-campaign-discipline`.
