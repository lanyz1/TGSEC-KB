---
name: windows-binary-cracking
description: Bypass license/card-key verification in Windows apps.
version: 1.0.0
license: MIT
platforms: [windows]

---

# Windows Binary Cracking Skill

Methodology for defeating license/card-key/activation verification in Windows desktop applications — typically PyInstaller / Nuitka / Electron wrappers gated by a network verification platform (卡密/网络验证). Covers the full killchain from packaging recon to a verified working bypass. Session-specific protocol detail lives in `references/`.

## When to Use
- User hands you an EXE/APK and asks to 绕过卡密验证 / crack the license / make it usable without a card key.
- A desktop app shows login / card-key / activation screens gated by a network verification backend.
- Authorized CTF / pentest targets with a license-gate challenge.

## Prerequisites
- Windows host (or VM) with the target EXE on disk.
- Python 3 with `pycryptodome`, `requests`, `frida` + `frida-tools` (`pip install frida frida-tools pycryptodome requests`).
- Ability to run the target (some require admin / UAC).
- Network observability: PowerShell `Get-NetTCPConnection`, `netsh trace` (NDIS capture), `Get-WinEvent`.

## How to Run
1. Recon the binary (packaging identification) — `references/packaging-recon.md`.
2. Launch it; grab the real extracted program from `%TEMP%\onefile_<pid>_*` / `_MEI*` (often `main.dll` + pyds).
3. Mine strings for verification logic, server URLs, hardcoded credentials.
4. Attach Frida to capture DNS / connect / send / recv — `references/frida-windows-network-spy.md`.
5. Pick the bypass: local state-file forgery, hosts + local API emulator, or Frida return spoofing.

## Quick Reference
| Step | Command / action |
|---|---|
| PE sections + entropy | `python3 scripts/pe_entropy_scan.py <exe>` |
| Find extracted payload | run app → `%TEMP%\onefile_<pid>_*` or `_MEI*` |
| Nuitka detection | strings: "was actively excluded from Nuitka compilation", `u<module ...>` |
| Frida attach | `frida -p <pid> -l script.js` |
| frida-trace one func | `frida-trace -p <pid> -i "WS2_32.dll!send"` |
| Find app's local port | `netstat -ano | grep <pid>` (port may be random per launch) |
| DNS capture | hook `getaddrinfo` + `GetAddrInfoW` → server IP |
| HTTP capture | hook `WS2_32.dll!send/recv`, print ASCII when contains `{` / `POST` |

## Procedure
1. **Recon / packer ID**: parse PE header, section entropies (`.rsrc` ≈ 8.0 = encrypted payload), scan signatures (`MEI`, `onefile_`, `UPX!`, `app.asar`, `NullsoftInst`). Small `.text` + huge `.rsrc` ⇒ onefile wrapper.
2. **Extract real code**: PyInstaller 6.x onefile self-extracts to `%TEMP%\onefile_<pid>_<rand>\` — just launch and copy that dir. Nuitka-compiled `main.dll` has NO `.pyc` — treat as native code but mine its string table (docstrings / function names / module names survive compilation).
3. **Locate verification**: string-mine for 卡密/验证/登录/到期/心跳 and module names (`core.auth`, `fndata`), API paths, IPs, hardcoded keys (Token / KEY / AES string / RSA PEM). CJK runs: regex `(?:[\xe4-\xe9][\x80-\xbf][\x80-\xbf]){2,}`.
4. **Bypass UI/window gates**: pywebview apps validate the client via a token file (e.g. `~/.app/.webview2_token`, `secrets.token_urlsafe`); read it and append `?webview2_token=<tok>` to the local URL to pass "仅支持专用客户端" checks.
5. **Capture live traffic**: attach Frida, hook DNS + send/recv, trigger register/login via the real UI (headless browser against the local port works once the token gate is passed). Note request/response ciphertext shape.
6. **Reverse protocol**: build a Python client replicating the crypto (RSA-PKCS1v15 key wrap + AES-CBC payload). Probe error codes — server error text changes as the format converges (e.g. "Token无效" → "请求签名错误" = progress).
7. **Bypass**: local state-file forgery, hosts + local API emulator, or Frida return spoof (time shift / expiry patch). For VipTime expiry, **Frida time-shift is the verified fastest path** — see `scripts/frida-vip-expiry-timeshift.js` (hook `GetSystemTimeAsFileTime` + `GetSystemTimePreciseAsFileTime`; subtract 1 year so `now >= VipTime` never holds). App still displays the original 到期时间 but never fires shutdown.
8. **Verify**: reach the app's main functional screen (final business state, not just HTTP 200); keep it alive across a heartbeat cycle.
9. **Deliver a relaunch script**: Frida hooks are runtime-only — package the chain (launch EXE → poll token file → scan random port → attach Frida to child PID) so a restart re-arms the bypass. See `references/oneclick-relaunch-bypass.md`.

## Pitfalls
- **Frida 17 `Module` global**: `Module.findExportByName` can throw `TypeError: not a function` in the REPL; use `Process.findModuleByName('x.dll').getExportByName('y')` instead.
- **frida-trace defaults to WSOCK32**: for `connect`/`send`/`recv` it generates handlers under `__handlers__/WSOCK32.dll/` (legacy shim). Qualify with `-i "WS2_32.dll!send"` and delete stale `__handlers__/WSOCK32.dll/`.
- **System proxy hides app traffic**: with v2rayN/Clash system proxy on, the app PID shows ZERO external TCP — the proxy process carries it. Disable proxy (`HKCU\...\Internet Settings` ProxyEnable=0) + restart the app, or hook DNS inside the process.
- **Random local ports**: FastAPI/NiceGUI port can change per launch (`8284`, then `8202`) — re-discover via netstat each time.
- **Nuitka = no decompiler**: no `.pyc`; string mining + dynamic hooking is the way.
- **Token is often dynamic**: hardcoded `Token:` in the binary may be a seed; real token comes from `GetToken` at runtime. "Token无效" vs "请求签名错误" is a protocol-progress signal, not a dead end.
- **AES key may rotate per request**: look for `new_aes_key` / `get_random_bytes`; request body is often `{"a": RSA(AES_key), "b": AES_CBC(payload)}` — field `a` carries the wrapped key.
- **Time-shift needs BOTH FILETIME hooks**: hooking only `GetSystemTimeAsFileTime` is not enough on Win10+ — `datetime.now()` uses `GetSystemTimePreciseAsFileTime` in **kernelbase**. Hook kernel32 + kernelbase FILETIME sources; `ucrtbase!time` is optional (may be absent). See `scripts/frida-vip-expiry-timeshift.js`.
- **PyInstaller onefile = parent+child**: the PID you launch is the unpacker (1 thread, no window, no listener); the real app is its child. Attach Frida / find the port on the **child** PID.
- **Free-registration account is the fastest login bypass**: if the app allows self-registration (username ≥6 + QQ + password), register through the UI first — you get a working account without owning a card key; server-side VipTime expiry is then the only remaining gate.
- **Headless browser + NiceGUI WebSocket**: the page drops connections often; re-navigate with the token URL, and keep browser_console expressions single-line (multi-line IIFE gets "Unexpected end of input").

## Verification
- Final check = app reaches the functional main screen (dashboard/console) with forged/emulated backend, or runs without expiry.
- Record: server IP:port, API shape, credentials found, exact bypass steps, original vs modified behavior.

## Working Style (this user)
- Reply in Chinese for these tasks; keep technical terms in English.
- Present multiple attack options (A/B/C) and **execute them in order autonomously** — the user expects you to keep going until one works.
- Push structured progress updates (已完成/进行中/待测试) on long tasks; user sets hard time budgets (e.g. 60 minutes) and wants pace.

## References
- `references/packaging-recon.md` — PE entropy scan, packer signatures, PyInstaller/Nuitka extraction.
- `references/frida-windows-network-spy.md` — working Frida hook patterns, proxy transparency, netsh ETL parsing.
- `references/fndata-verification-platform.md` — fndata (飞鸟数据-style) network verification protocol: endpoint, hybrid crypto, error codes, API list, **verified time-shift expiry bypass**.
- `references/oneclick-relaunch-bypass.md` — relaunch script recipe: launch EXE → poll token file → scan random port → attach Frida to child PID.
- `scripts/pe_entropy_scan.py` — reusable PE section entropy + packer signature scanner.
- `scripts/frida-vip-expiry-timeshift.js` — verified Frida time-shift hook (bypass VipTime expiry).
