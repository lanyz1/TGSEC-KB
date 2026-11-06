# Player H5 + panel oracles (multi-tenant betting family)

The brand domain is usually a **download landing page** with zero inputs. The real
player surface is the "streamlined H5" host from the config map (§2b):

```
POST /site/api/v1/configuration/preInfo      # unauth, no signing
POST /site/api/v1/user/member/kaptchcate {"kType":4}   -> 6022  (= sprite captcha)
/entry/register                              # 用户名 / 密码 / 确定密码 + agreement checkbox
```

Registration is *not* closed when the API path you guessed returns `注册失败` — the
form lives on that H5 route, and the API path used by the browser is
`/site/api/v1/user/register` (not the panel's `member/registerFlow`). A same-name test
as an enumeration oracle fails here: the username field name is never what you guess,
and every candidate returns the identical *format* error, which is a "not read" signal,
not "taken".

## Per-module pseudo-signature

```javascript
const t0 = await TC( path.match(/\/\w+\/\w+/)[0] );   // hash of the first two path segments
headers = { "X-API-CLIENT":"h5", "X-API-XXX":t0, "X-API-VERSION":"1.0.0",
            "X-API-SITE":"4002", "X-API-TYPE":"h5",
            "X-API-TOKEN":cookie, "X-API-UUID":cookie }
```

It is a **constant per namespace**, computed from the path prefix — recover it once by
hooking `XMLHttpRequest.setRequestHeader` + `fetch` and calling any endpoint of that
module, then reuse it for every other endpoint of the same module. Only the leading
namespace varies (`/site/api`, `/page/fd`, `/game/api`, `/act/api`, `/sact/api`); the
rest of the path is free. That makes the "signature" a naming convention, not a
control. The **panel** side differs: there `X-API-XXX` is the literal `/agent/api`.

## localStorage credentials, encrypted with a shipped constant

Grep the loaded chunks for `X-API-XXX` and the module next to it does both crypto and
storage. Shape of the leak:

```javascript
var m = "<16 printable bytes, hardcoded in the public bundle>";   // used as BOTH key and IV
localStorage['s_f'] = AES.encrypt(JSON.stringify({name, password, checked}), m, {iv: m})
```

Decrypting `s_f` returns the user's **plaintext login password** (verified end-to-end).
Why it is a finding and not just a client quirk: the platform's own silent re-login
("登录失效，自动登录中...") *depends* on those stored credentials, so the design cannot
drop them; and the key is readable by anyone who loads the bundle, so the encryption
protects nothing. Exploit path is any XSS or local/shared-device read — which is why
sourcing an injection point (nickname, avatar upload, customer-service message) is the
natural follow-up.

## Withdrawal / KYC gate chain

```
GET  /page/fd/api/v1/bankCard/queryMemberBanksInfoList   (X-USER-ENCY header)
POST /page/fd/api/v1/vCurrency/checkSupportUsdt | usdtWithdrawInfo | getUsdtRate
POST /page/fd/api/v1/withdraw/withdrawInfoV2 | baseCfg/listV3 | drawRule/list
POST /page/fd/api/v1/speedDraw/getDrawTypeInfoV4        -> kyc block + hint text
POST /page/fd/api/v1/withdraw/newV2 {amount, bankCardId, version:5, withdrawMethod,
                                     twoPassword, bonusRuleId, category, preVersion}
```

`getDrawTypeInfoV4.kyc = {hasRealName, hasPhone, hasVirtualWithdraw, ...}` plus
`hint.2 = "请绑定真实的姓名与手机号，提交信息后可使用虚拟币取款方式"`. Crypto/USDT
withdrawal therefore needs name + phone; fiat additionally needs a bank card.
Binding routes: `bindFromDepositVe2 {realName, phone, code}` (deposit-based, the
cheapest candidate for an SMS bypass), `bindPhoneVe2`, `bindEmailVe2`, `bindCardId`,
`sendCode/{one,two}Ve2`.

The submit path validates **before** anything else: an empty `bankCardId` returns
`银行卡ID不能为空` regardless of amount. And answer the asset question precisely —
`checkSupportUsdt` returning `true` with a rate of 6.74 and 100–200,000 limits means
USDT **is** supported; the honest blocker is the KYC gate and a zero balance
(`allBalance` across venues, `centerWalletBalance`), not "no USDT".

Beware display-only numbers: the wallet page rendered a five-figure "总金额（元）" that
turned out to be a UI placeholder/animation while `member/info.centerMoney` and
`getBalance` both read `0.00`. Believe the API, not the rendered hero figure, and say
which one you are quoting.

## Panel-side account oracles (plaintext JSON, no auth)

```
POST /agent/api/v1/front/Hf6dtBdmHx                            -> {"k":"<b64>","v":"<b64>"}
POST /agent/api/v1/security/verifyInformationLoginUnverified  {"name":"X"}
      {"data":{"isExists":false,...}}  => **account EXISTS**   (semantics are inverted)
      {"message":"代理不存在"}          => does not exist
POST /agent/api/v1/security/getSecurityQuestionNoLogin       {"userName":"X"}
```

Pitfalls that cost real time:
- These two take **plaintext JSON**. Wrapping them in the platform's AES envelope
  returns `代理不存在` / empty — which reads like "no such account" and is not.
- Field names differ per endpoint: `name` for the existence check, `userName` for the
  security-question read.
- The key endpoint returns base64 — **decode it** (32-byte key, 16-byte IV) before use;
  feeding the string straight to AES raises `Incorrect AES key length`.
- `isExists:false` is the *positive* result. Reading it as "absent" inverts the oracle.
- Enumeration is rate-limited (`API rate limit exceeded`); sleep 3–6 s per hit and
  retry, and expect only a handful of hits from a 150-word list — real names are not
  dictionary-guessable, so do not report "N accounts exist" as coverage of the base.

The unauth RSA private key dumped from the same namespace decrypts those security
questions into real user PII, and the questions are only step *two* of login (the
password check comes first) — so this is a PII read, not an account takeover.

## Properly scoped — do not expect these to leak

Verified across six namespaces and the full chunk-derived route list:
- `X-USER-ENCY` is **md5(username)** and looks like a universal identity header, but
  the server ignores it for account selection; data endpoints stay bound to the token.
- No "list all users" endpoint exists on the player side. Win/invite/leaderboard/
  record endpoints return the caller's own (empty) state or masked server-side strings.
- Multi-tenant selection attempts (`X-API-SITE` variants) do not move the caller
  between tenants; tenancy is bound to the session.
