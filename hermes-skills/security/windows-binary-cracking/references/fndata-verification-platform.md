# fndata Network Verification Platform — Protocol Reversal

The verification backend used by the cracked app (module names `fndata` / `fndata_client`, a 飞鸟数据-style commercial network-verification SDK). Reconstructed from Nuitka string mining + Frida traffic capture.

## Endpoint

```
POST http://<host>:18888/Api?AppId=<id>
```

- Observed hosts: `101.35.246.71:18888` (primary, Tencent Cloud), `pubg.795999.xyz:18888` (backup domain).
- `AppId` selects the app edition: 10013 (测试版), 10015 (代理版), 10016 (普通版) — the running app actually used **10015**, not the first URL found.
- Probe: `POST /Api?AppId=10013` with empty body → `404 page not found` on GET; with headers + `{}` body → `{"Time":..., "Status":106, "Msg":"Token无效"}`.

## Headers

```http
Token: <dynamic, from GetToken at runtime>
Content-Type: application/json
Accept: application/json, text/plain, */*
User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64)
```

The hardcoded `Token: <REDACTED> in the binary is a **seed**, not the live token — server rejects it. Real token is fetched by `GetToken` first (captured live: `Token: <REDACTED>

## Request body (hybrid crypto)

```json
{"a": "<RSA-PKCS1v15 encrypted AES key, base64>",
 "b": "<AES-192-CBC encrypted JSON payload, base64>"}
```

- Plaintext payload is `json.dumps(..., separators=(',',':'))` of `{"fnobj": "<Function>", ...params}`.
- AES-192-CBC, PKCS7 padding (Go side: `utils.Aes._cbc192`); RSA PKCS1v15 (Go side: `k.rsa`, `unLeftPad`).
- Look for `new_aes_key` / `get_random_bytes` — AES key may rotate per request (wrapped by RSA in field `a`).
- Response is the same `{"a": AES(payload), "b": MD5-hex}` shape; decrypt with the session key.

## Status / error codes (protocol convergence signal)

| Code | Msg | Meaning |
|---|---|---|
| 103 | 请求签名错误 | Body format/encryption wrong but structure close |
| 106 | Token无效 | Token header wrong / not fetched |

Probing different body shapes moves the error — e.g. plain JSON gives 106, malformed-crypto gives 103. This tells you which part of the protocol is still wrong.

## API function names (from `ufndata.*` symbols)

`GetToken`, `register`, `login`/`UserLogin`, `HeartBeat`, `UseKa`, `SetUserClass`, `LogOut`, `GetKaInfo`, `GetAppUserInfo`, `GetAppGongGao`, `GetAppVersion`, `GetAppUpDataJson`, `SetAppUserKey`, `SetNewUserMsg`, `GetAppPublicData`, `RunJs_Global`, `SetUserConfig`, `GetUserConfig`.

`UserLogin` request fields: `User`, `PassWord`, `UserOrKa` (账号或卡号), `Tab`, `AppVer`, `gddd` (device/machine code from `generate_machine_code` = sha256 of uuid.getnode + motherboard serial + cpu id + mac).

`UserLogin` response fields: `Token`, `Key`, `LoginIp`, `LoginTime`, `OutUser`, `RegisterTime`, `UserClassMark`, `UserClassName`, `VipNumber`, `VipTime`, `NewAppUser`.

## Local persistence (login state files)

- `C:\JLA\login_prefs.json` — `{"remember_me": bool, "username": "", "password": ""}` (only populated when 记住我 checked).
- `C:\JLA\announcement.json`, `C:\JLA\logs.json` — fetched app data.
- `C:\Windows\winS` / `C:\Windows\winSS` — 0-byte when 记住我 is off; candidate token store when on (forging a future `VipTime` here is a bypass vector if the app trusts it).
- App title pattern: `<name>-<4 random chars>` (e.g. 轻云-PZWgN); changes per launch.

## Expiry / heartbeat model

- After login, `AuthSystem.start_heartbeat` runs `_heartbeat_worker` calling `HeartBeat`; server returns `VipTime` (Unix ts). App shows 到期时间 and calls `_shutdown_after_delay` when expired ("已到期 / 即将关闭程序 / 延迟关闭程序").
- Bypass vectors: fake local VipTime file, emulated HeartBeat server returning future VipTime, Frida time-shift, or NOP the `_shutdown_after_delay` call site.

## Time-shift expiry bypass — VERIFIED WORKING (2026-08)

Frida time-shift is the fastest verified bypass: shift the app's perceived wall-clock back ~1 year so `VipTime` (e.g. 1.5h free trial expiry) is always "in the future". The app keeps showing the original 到期时间 string but never fires `_shutdown_after_delay`, because its local comparison `now >= VipTime` never holds.

Critical hook points (hook ALL of these; a single one is not enough):

| Hook | DLL | Why |
|---|---|---|
| `GetSystemTimeAsFileTime` | kernel32 | classic FILETIME source |
| `GetSystemTimePreciseAsFileTime` | **kernelbase** | modern source; `datetime.now()` uses this on Win10+ |
| `time()` | ucrtbase / api-ms-win-crt-time-l1-1-0 | C runtime epoch seconds (may be absent if Python uses FILETIME) |

Shift arithmetic:
- FILETIME = 100ns since 1601; subtract `BigInt(86400) * BigInt(10000000) * BigInt(365)` per year.
- `time_t` = seconds; subtract `86400 * 365`.

Working script: `scripts/frida-vip-expiry-timeshift.js`. Attach with `frida -p <pid> -l scripts/frida-vip-expiry-timeshift.js`. After attaching, verify the app stays healthy (process alive, UI still renders) and no "已到期" shutdown fires across a heartbeat cycle.

Caveat: time-shift can break other time-dependent logic (logs, daily tasks) and it is runtime-only — re-apply after every app restart. Pair it with the one-click relaunch pattern in `references/oneclick-relaunch-bypass.md` so a restart re-arms everything.
