# Chinese SPA + IM-overlay platform — contract & oracle notes

Recurring shape: Vue SPA front end + Java/Spring or FastAPI API on a custom port + Tencent TIM
overlay for groups/messaging + a Cloudflare-Worker mail service for the target domain.
Platforms of this class: wuquan/57nz and lookalike gambling/agent panels.

## Login / reset field shapes

- Login body: `userName` (email or phone) + `password` + `type` + `serverId` + `deviceId` +
`loginDeviceType`. `skipVerify` is accepted. The password field is **lowercase** `password` —
a camel-case variant sends an empty credential and every candidate returns the wrong-password
error, so the whole dictionary looks exhausted while nothing was tested.
- Reset body: `userName` + `code` + `password` + `serverId`. Field names are recoverable by
sending `{}` and reading the incrementing "请输入…" errors back.
- `getCode {number, type}`: type=1 = SMS (server prefixes the country code), type=2 = email;
type>=3 answers 验证码类型不正确. Only these two types exist.

## Login oracle strings (fingerprint before designing a run)

| Response | Meaning |
|---|---|
| 账号或密码错误 | wrong credential |
| 当前登录地点异常，请使用验证码登录。 | **password CORRECT**, device untrusted |
| 操作成功 + `access_token` + `token` | success; `token` is the IM provider userSig |
| 登录失败次数过多 | per-account lockout — masks everything else |
| 请求过于频繁 | rate limit |
| 您已开启仅允许验证码登录 | account has code-only login enabled; no password exists to find |

## Setting map that switches the auth mode

`POST .../userApi/privateSetting {type, value}` — type 2=appSearch 3=phoneSearch 4=qrSearch
5=cardSearch **6=codeLogin**. Values are 1/2.

- `codeLogin` 2 = password login allowed; `codeLogin` 1 = code-only login, password disabled.
- The `userName` field is **ignored** — this is self-only, not an IDOR. Confirmed by sending a
foreign `userName` and observing your own record change. Do not report it as an IDOR.
- Read the target's setting first (the profile endpoint returns it). `codeLogin=1` means a
dictionary run cannot succeed regardless of size.

## Trusted-device replay

- `getLoginDeviceRecords` (usually WAF-allowed) returns `deviceId`, `loginIp`, `province`,
first/last login time per device.
- Full user dumps that carry a `devices[]` array per user are the cheapest source of a target's
trusted `deviceId` and `loginDeviceType` values.
- Replaying those two fields suppresses the "location abnormal" code requirement, so a
password-only login returns a full session instead of the code prompt.
- Cross-check: a `deviceId` whose `loginIp` is a CDN range and whose geo is nowhere near the
target is one of YOUR earlier sessions, not the target's own device.

## OTP reset flow

- `forgotPassword {userName, code, password, serverId}` sends the code to the account's registered
address; the reset succeeds on the correct code.
- **No attempt limit**: hundreds of wrong codes then the correct code still works.
- The code is bound to the **account** (the `userName` field), not to a `number` parameter —
requesting a code for your own mailbox does not validate against somebody else's account. The
obvious OTP-binding flaw is absent; verify before reporting it.
- Window is ~240s and the code is 6 digits: an online brute force needs ~1000 attempts/s, which
the per-account limit makes unreachable. Do not plan one.
- If the target's mailbox is on a domain you cannot read, the whole OTP path is closed however
open the reset endpoint is.

## Mail-service panel (Cloudflare Worker mail)

- Login: `POST /api/login {email, password}` -> `data.token`; subsequent calls use a **bare**
`Authorization` header, no `Bearer`.
- Listing: `GET /api/email/list?accountId=&size=&type=&timeSort=&full=1` — the parameter is `size`,
not `limit`; the body (with the 6-digit code) is in the `content` field of each item.
- **Enumeration oracle**: `POST /api/register` checks whether the mailbox already exists BEFORE it
validates the captcha, so 该邮箱已被注册 vs 需要进行人机验证 enumerates registered mailboxes with no
captcha solve.
- Deployment drift is normal: endpoints present in the upstream open-source project (an
all-receive toggle, a detail route) may 404 on the deployed build. Enumerate the deployed JS
chunks and trust only what the deployed front end actually calls.

## Origin-direct ingress: the edge's path rules are NOT the origin's

"The panel blocks X" is only ever true at the edge. The edge and the origin port hold **different
rule sets per path** — verified split on this class:

| Edge blocks, **origin serves** | Edge AND origin block |
|---|---|
| `walletApi/*` (transferCn, exchangeBalance, applyWithdrawUsdt, confirmRecharge, getRechargeInfo, myBill) | `userApi/getUserAccessToken/*` (token minting) |
| `orderApi/*` (orderDetail, orderList, buyCny, addOrder) | `imuser/*`, `imUser/*`, `managerApi/*` |
| `paySetApi/*` (initPwd, resetPwd, forgetPwd) | `system/*`, `monitor/*`, `tool/*`, `common/*` |
| `officialApi/*`, `teamApi/*`, `paymentApi/*`, `reportApi/*`, `versionApi/*` | `messageApi/sendOneMessage`, `redApi/sendRed`, `orderApi/create` |
| `userApi/{realName,getTradeAccountInfo,updateTradeAccountInfo,captcha/check}` | |

Request shape: `Host: <api-domain>` + `Authorization: Bearer <access_token>` + the app's own token
header + the app's routing header when the client sends one (`domain: wallet`). The origin may serve
**plaintext HTTP** — try both schemes before concluding anything. **Always re-send with the token**:
some rules match the anonymous/empty-body shape, so `teamApi/customerSetting` 403'd with `{}` and
passed with a token. Swapping the `Host` to an internal domain / `localhost` / the bare IP changes
nothing — rule is on the URL.

### Contract notes for that surface

- `orderApi/orderDetail {id}` — **IDOR**: no order-ownership check. The body's `paymentWay[]` carries
the counterparty's `realName`, `accountNo` (Alipay id / phone / bank card), `bankName` and the
payment-QR `url`. Sweeping `id` yields a full PII table. `orderApi/orderList` returns the live order
book (userId + nickname).
- `paySetApi/initPwd {password, confirmPassword}` — sets the **money password** with no old password,
no SMS and no captcha, so any session escalates to the fund-transfer credential. `forgetPwd` /
`resetPwd` do demand `smsCode`; `initPwd` is the gap. Do not mistake the gap for free money:
`transferCn` / `exchangeBalance` / `applyWithdrawUsdt` are all server-side balance-checked
(negative, zero and oversized amounts rejected) — report the credential gap, not a balance bug.
- `teamApi/openGroup{tid,levelId}` / `renewGroup{tid,levelId}` accept a **foreign tid** (no ownership
check), gated only by wallet balance; `createTeam{teamName}` is free but its tid is **not persisted**
until `openGroup` pays, so it cannot be used as a probe tid. `customerSetting{tid,type,value}` is an
ownership-unchecked setter whose validation order is type → value → group existence, so a bare
`{tid}` alone already tells you whether the tid is real.
- `friendsApi/addFriends {accid,type,toAccount,appid,msg,remark}` **cross-checks that `appid` belongs
to `toAccount`** — a boolean oracle, useless for *recovering* an appid.
- `friendsApi/queryUserAccid` real params are `{fromUserAppid, fromTeamAppid}`; recover them from the
chat message-view code, not the login code.
- **Identifier entropy decides whether enumeration is even possible.** Sampling ~250 known appids:
241/254 were `<prefix>_` + 9 random chars (62^9) with the rest user-chosen. Do not plan a sweep
against that class — record **physically unreachable** and pivot.
- Before building a "register the missing mailbox, then read the OTP" chain, enumerate the target's
platform-bound addresses against the mail register oracle: if every one already exists as a mailbox,
the chain is unavailable. Check existence first, do not assume a gap.

## Endpoint classes that stay blocked by design

- Token-minting and administrative routes behind an edge URL rule (get-a-user's-token, IM user
admin, super-user password reset, group-destroy wrappers): blocked at the origin too, for every raw
client and every exit IP. Do not grind variants. Note this is the *admin* slice only — do not
generalise it to the business/money surface above, which the edge alone was blocking.
- Provider group destruction requires the **group owner's** signature. A non-owner identity gets
the provider's permission error; platform-side destroy routes sit behind the WAF. An admin or
member identity inside the same group does not escalate.
- Harvested provider userSigs from older loot: check the appid and identifier they were minted for
before use. A mismatch surfaces as an SDKAppID-mismatch error, and "kicked off" means superseded,
not reusable.
