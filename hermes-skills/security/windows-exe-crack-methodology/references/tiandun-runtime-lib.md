# 天盾 (TianDun) runtime verification lib — live RE field notes (后会无期4.15 campaign)

Target: 易语言王者辅助 `后会无期4.15.exe`, TianDun network verification server `123.99.192.92:9001`.
Session outcome: full protocol + runtime-lib map recovered; **response payload forgery achieved** (window title fully controllable via keystream-encrypted text area); status-code 2B field not yet forged (integrity-checked → 非法数据001).

## Recon summary
- E-language: window class `WTWindow` + `_EL_HideOwner`; strings GBK; business strings in `.rdata` 0x2cxxxxx, some plaintext (`您已到期` @ 0x02c21021), others encrypted with interleaved filler.
- Verify IP plaintext at file offset `0x2256f0` (`.rdata`, VA `0x6256f0`), followed by config values + `KBFCB9CC7E56D7A6E8F9870D38888F7D9805` (NOT the file MD5/SHA1 — a key/secret, don't treat as integrity hash).
- No ASLR (`DllCharacteristics=0`). `.text` VA 0x401000, size 0x178000.

## Wire protocol
- Request: `c3 c3 c3 | "999" | 0xd1|0xdf | ":::" | body`. Body has card-dependent prefix + FIXED 24-byte machine-code ciphertext (same across cards → stream cipher property).
- Response: `05 01 04 00 05 02 | len LE u32 | payload(len-10)`. Login-fail 31B, trial-closed 36B. Same card → same response (no per-request salt).
- Server is alive and reachable even under v2rayN TUN (direct-IP TCP passes through); replaying captured request bytes returns the real verdict.

## Runtime lib layout (base changes per launch, offsets fixed)
- Base found via signature scan: bytes `39 65 e8 74 17 68 69 01 00 00` at offset `0x9e9ab` → base = hit − 0x9e9ab. Size 0xb6000.
- Plaintext (dumpable while idle): `0x9e90c` network send/recv wrapper (command code 0x6a; calls recv, checks len>0, then calls response-read fn), `0xa5c00` response-data read, `0xa3f80` status-code dispatch, `0xa5a80` data-type→status reverse map, `0xa5bde` response parse (computes status, stores at `[obj+8]`).
- Encrypted (only during execution): login-command implementation at caller of `0x9e90c` = `TD+0x28bf93`; the block re-encrypts after returning.
- Status dispatch `0xa3f80`: `mov eax,[ebx+8]` (status) → cmp 0x80000101 → ja/je chain → 0x80000301 branch reads dword, returns 0 = success; `0x80000004` → 非法数据.

## Patch attempts & outcomes
- `0xa3f86` → jmp 0xa409a (success-dword branch): crash (shared dispatcher broken).
- `0xa3f89` cmp → jmp 0xa5083 (0x80000301 handler): crash (same reason).
- `0xa5b0a` `mov eax,0x80000003` → `mov eax,0x80000301` (equal length 5B): no crash, verdict unchanged → not the login path.
- String IP patch (`123.99.192.92`→`127.0.0.1` in memory): write succeeds after VirtualProtectEx but app still connects to original IP (parsed at startup into numeric/global form).
- On-disk IP patch: app exits at startup → self-integrity check lives in the runtime lib, not `.text`.

## What actually worked (keep these)
- Find verdict fast: hook SetWindowTextA; auth result appears in window title (`您未充值或您已到期.` + card tail + machine-code hex).
- Find the login command: hook plaintext network wrapper `0x9e90c`, log `returnAddress` → `TD+0x28bf93`; dump `returnAddress-0x100` at that instant to capture the decrypted block.
- Frida-free re-anchor + patch: ReadProcessMemory page scan (start 0x10000) → VirtualProtectEx(PAGE_EXECUTE_READWRITE) → WriteProcessMemory → read-back verify.
- Recover from anti-debug self-destruct (`0xc000041d`, then silent exit every launch): delete `%LOCALAPPDATA%\\CrashDumps\\<target>*.dmp`, `%LOCALAPPDATA%\\frida`, and `AppCrash_<target>*` under `C:\\ProgramData\\Microsoft\\Windows\\WER\\ReportArchive` + `ReportQueue`. No reboot.
- **Response-arrival race dump (Frida-free, beats returnAddress dump when re-injection crashes the app)**: to capture a re-encrypting code block (e.g. login command at `TD+0x28bf93`), don't inject repeatedly — run a pure `ReadProcessMemory` loop in a separate process that waits on a marker file, have the local fakeserver write the marker the instant the real response arrives (BEFORE forwarding it to the client), then loop-read `target±0x400` at high speed looking for a function prologue (`55 8b ec` / `83 ec` / `56 57 53`). This avoids Frida entirely → no 0xc000041d self-destruct. Setup order matters: start the dumper (it scans for TD base first, ~5s), THEN run the connect-redirect + login. Pitfall: the dumper's `OpenProcess` fails with error 87 if the target PID is stale — re-verify PID each run.
- Launch reliably: `Start-Process -FilePath $exe.FullName -PassThru` (PowerShell) or Python `subprocess.Popen`; `cmd //c start` silently no-ops on Chinese exe names.

## Response payload structure (cracked — key finding)
- Payload = `[2B status/command id][keystream-encrypted text area]`. Login-fail payload `54 ae | 9c ce d2 5d ...` (21B total = 2 + 19).
- **Text area has NO integrity check**: flipping any byte of the text area changes the displayed window title to the decrypted result (probe: set to `0x55` → title chars changed per position; title = decrypted text exactly). Status area bytes (pos 0-1) are integrity-checked → any change → 非法数据001.
- **Full 21B keystream recovered (not just text area)**: `55 ae 58 34 1c e9 0b 41 bb e8 4f 07 a4 91 eb 78 ad 01 6b b9 b6`.
  Decrypts the whole payload to `[状态明文 0x0000] + 您未充值或您已到期.` — i.e. status 2B is ALSO keystream-encrypted; the plaintext status for login-fail is `00 00`. (Derivation: keystream[0:2] = `54 ae` (cipher) XOR `00 00` (assumed plaintext), keystream[2:21] = text ciphertext XOR fail-text GBK — verify by decrypting the full payload before trusting it.)
- Keystream is **fixed per card** (same card → same response, verified); differs across cards (login vs trial request). XOR-verify before use: cipher XOR keystream must reproduce the known plaintext.
- **Forge any text**: encrypt custom GBK text with the keystream (repeat keystream for longer text), rebuild payload, update response length field = 6+4+len(payload). Program displays the decrypted text as window title (verified: `AAAAAAAAAAAAAAAAAAA` and `验证成功` both displayed verbatim).
- **Status plaintext 0x0000 is the ONLY legal value** (it IS the fail state — program shows 未充值). Exhaustive plaintext sweep 0x0001–0x00ff (keystream-encrypted, correct ks[0:2]=54ae): ALL → 非法数据001. Empty text (payload = status only) → 连接服务器失败. So the 2B status is a server-computed signed gate; no local value yields success.
- **All invalid cards return byte-identical fail responses** (4 different cards → same `54 ae | 9c ce ...`); server confirms card validity. Conclusion: server-issued model — pure client bypass not viable; valid card / platform-owner route / buy-trial-card-to-observe-success required (see references/cloud-verify-crack-cases.md).

## connect() redirection (the reliable redirect — beats string IP patch)
- String IP patch (memory or disk) does NOT redirect: lib parses IP at startup into numeric form. `netstat -ano` during login shows it still connects to original IP.
- **Frida hook `ws2_32!connect`, rewrite sockaddr**: `sockaddr.add(2).readU16()` reads port in **LE → 9001 appears as 0x2923** (not 0x2329); `sockaddr.add(4).readU32()` reads IP LE (`0x5cc0637b` = 123.99.192.92). Rewrite `sockaddr.add(4).writeU32(0x0100007F)` for 127.0.0.1. Then local fakeserver (forward to real server, modify response, send back) sees the traffic.
- Old fakeserver instances keep LISTENING on the port after kill — check `netstat -ano | grep LISTENING` and kill stale PIDs or the client connects to the wrong server.
- Frida JS quirks hit live: `send()` does NOT support `%`-formatting (use string concat); do NOT name a helper `hexdump` (collides with builtin → `TypeError: cannot define variable`), use `dh`.

## Status codes confirmed
| code | meaning |
|---|---|
| 0x80000002 | ? |
| 0x80000003 | ? (response-parse default) |
| 0x80000004 | 非法数据 (fail) |
| 0x80000005 | error-ish (used as arg in version check) |
| 0x80000101 | success, read 1B |
| 0x80000201 | success, read 2B |
| 0x80000301 | success, read 4B |
| 0x80000401 | success, read 8B |
| 0x80000501 / 0x80000601 | success, read 8B |
