# Replaying an app's OTP login

Turning a harvested login body into a working session for accounts whose delivery channel
you control. Complements Step 1 of the parent skill (harvest the body from the client).

## Recover the body, do not guess it

Pull the literal request map out of the client build. Field names and enum values are
authoritative. A wrong enum value or a missing boolean surfaces as "account or password
incorrect", which sends you chasing a nonexistent account problem for hours — the account is
fine, the request shape is wrong.

Typical shape recovered from a Flutter web build:

```
getCode   {number: <address>, type: <1|2>, serverId: <shard>}
userLogin {userName: <address>, password: "", code: <6-digit>, skipVerify: true,
           type: <1|2>, serverId: <shard>, deviceId: <id>,
           platform: "android", loginDeviceType: "android"}
```

The two things that are easy to miss and decisive in practice:

- **`skipVerify: true` plus an empty `password`** — without them the same call is treated as a
  password login and fails.
- **The code type enum.** Which value works depends on which column of the account row holds
  the address. An account whose phone column literally contains an email address authenticates
  with the SMS-side type; an account with a real email column needs the email-side type. Test
  both. **A uniform "account or password incorrect" on ONE value across EVERY shard is the switch
  signal, not an account-death verdict** — re-submit the SAME code with the other value, which works
  because a wrong-type attempt does not consume it (re-requesting a fresh code first just burns a
  cooldown window and tells you nothing new). Also read the failure wording: a "bad mobile format"
  style error means the phone column does not hold the address, whereas pointing at the wrong code
  column fails silently.

## Sequence

1. Request the code **for the specific shard/server id** the account lives on.
2. Read the newest message from the delivery channel, then submit the login with the same
   shard id. A code minted without a shard id will not validate against a shard-specific
   login, and codes are short-lived.
3. Immediately perform whatever you needed the session for. Sessions are single-use: a second
   login flow (or a re-login on another shard) kicks the first, and an unspent token can read
   back as "expired or reused" once anything has consumed it.
4. Re-mint before every attempt rather than reusing a stored token.

## Pitfalls

- The code-request endpoint usually does **not** validate that the account exists — a
  "sent successfully" response for a made-up address proves nothing. Only the login call is
  an existence oracle, and only on a given shard.
- The same address is a **different account on each shard**, with its own id, nickname and
  contact fields. A successful login on one shard tells you nothing about another; never infer
  a target's shard from the email domain.
- Accounts the platform has flagged or anonymised fail login on their shard with a generic
  "account or password incorrect" even though the row exists. Treat a single failure as
  inconclusive and test a different shard before concluding the account is gone.
- Rate limits are platform-level and shared across every egress you own, so a burst from one
  path cools down all of them. Space requests widely and back off on the first throttling
  message instead of switching egress to push through.
- After a session is obtained, verify what it can actually do — list the user's own objects on
  the API host — before reporting success. A token that authenticates against the API host may
  still be rejected by the front host and vice versa.
