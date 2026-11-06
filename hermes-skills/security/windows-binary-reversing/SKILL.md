---
name: windows-binary-reversing
description: "Reverse Windows EXEs to bypass license/card-key checks."
version: 1.0.0
license: MIT
platforms: [windows]

---

# Windows Binary Reversing Skill

Reverse-engineer Windows executables to bypass license / card-key (卡密) verification. Focused on Python-packaged desktop apps (PyInstaller onefile, Nuitka-compiled) and network-verified licensing (RSA+AES hybrid, heartbeat expiry). Covers the full chain: PE recon → packer identification → runtime extraction → local WebUI protection bypass → verification-server discovery → bypass execution.

## When to Use

- User provides an EXE/DLL and asks to bypass license, card-key, registration, trial, or "卡密验证" (the user's recurring task type)
- Need to determine where a desktop app validates credentials (local vs network) and what server it talks to
- Need to make an app reach its post-auth state (main UI / unlocked features)

## Prerequisites

- Windows host with the target EXE (targets are Windows binaries; use PowerShell + python3)
- `python3` (PE parsing, entropy, ETL frame parsing)
- Admin PowerShell for `netsh trace` packet capture
- Optional: Frida (dynamic hooking), DIE/PEiD (packer ID)

## Quick Reference

| Question | Answer |
|---|---|
| What packer? | PE section entropy + signature scan (Procedure 1) |
| PyInstaller? | RCDATA resource id 27 + "MEI" cookie; bootloader strings in .text |
| PyInstaller 6.x runtime dir | `%TEMP%\onefile_<pid>_<random>\` (NOT `_MEI*` — those are stale from older runs) |
| Nuitka? | Strings "gi_code is not writable in Nuitka", "was actively excluded from Nuitka compilation" |
| No .pyc anywhere? | Nuitka — code is native; mine strings (incl. CJK utf-8) + preserved function names |
| WebUI blocked ("不支持的浏览器")? | pywebview token bypass — read token file, append `?webview2_token=` |
| Where's the auth server? | System proxy masks it — disable proxy, capture with netsh trace, extract TLS SNI |
| NiceGUI page JSON | `parseElements(String.raw\`{...}\`)`; children are numeric ID refs — resolve recursively |

## Procedure

### 1. PE recon and packer identification

```bash
md5sum target.exe; sha256sum target.exe   # evidence baseline
```

Python one-liner over the PE headers: dump sections with virtual/raw sizes and entropy.
- `.rsrc` entropy ~8.0 with a small `.text` (~100-200KB) = loader shell; real code is in resources
- Scan signatures: `MEI` (PyInstaller), `UPX!`, `NullsoftInst` (NSIS), `app.asar` (Electron), `PK\x03\x04` (zip)
- PyInstaller onefile: RCDATA resource id 27 (CArchive container); enumerate resource tree to find it

### 2. Runtime extraction (PyInstaller / Nuitka onefile)

PyInstaller 6.x self-extracts to `%TEMP%\onefile_<pid>_<random>\`; older to `_MEIxxxxxx`. Launch via `Start-Process -PassThru`, then poll `%TEMP%` for the new dir. The parent process is often just a launcher — track the **child** process (it owns the window, port, and WebView2).

- Classic PyInstaller: `.pyc` files + `base_library.zip` → decompile with pycdc/decompyle3
- Nuitka: `main.dll` (huge, native) + `*__mypyc.pyd` — no .pyc, decompilation impossible; strategy = string mining + runtime hooking (Frida)

### 3. String mining (Nuitka-compiled)

Extract ASCII strings AND CJK (utf-8) runs — Chinese apps keep business-logic strings in utf-8:
- Module names reveal structure: `core.auth`, `core.services`, `core.user_prefs`
- Function names survive compilation: `create_auth_pages_container.<locals>.show_login`
- CJK strings expose the whole feature map (register/login/heartbeat/recharge/expiry)
- Watch for `webview2_token=`, `验证请求是否来自合法的 WebView2 窗口` → WebUI protection clue

### 4. Local WebUI protection bypass (pywebview token)

Pattern: FastAPI/NiceGUI server + pywebview WebView2 shell. The server blocks non-WebView2 browsers via a per-run token:
- Token generated with `secrets.token_urlsafe`, written to `~/.<appdir>/.webview2_token`
- URL param `?webview2_token=<token>` unlocks the real UI — just read the file and append it
- Then drive the real UI with a normal browser (`browser_navigate` + snapshot/type/click)

### 5. Drive the NiceGUI UI

- Page HTML embeds `parseElements(String.raw\`{json}\`)` — the UI tree
- Children are numeric ID refs into the same JSON object — resolve with `data[str(id)]`, not naive recursion
- Inputs/buttons appear in the accessibility snapshot; events flow over WebSocket
- Wrong-creds login ("用户名或密码错误") confirms the auth API is live and reachable

### 6. Find the verification server (network auth)

Symptom: login "succeeds" but `Get-NetTCPConnection -OwningProcess <pid>` shows NO outbound TCP → **system proxy is masking it** (WinINET proxy like 127.0.0.1:10808). The proxy process (xray/sing-box/Clash) owns the real outbound conns.

Steps:
1. Check/disable system proxy: `Set-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0`
2. Capture: `netsh trace start capture=yes maxsize=50 tracefile=C:\...\cap.etl`, trigger the action, `netsh trace stop`
3. Parse ETL: `Get-WinEvent -Path cap.etl` — NDIS-PacketCapture events (id 1001), frame bytes in `Properties[3]` (Byte[])
4. Extract TLS SNI from ClientHello packets → real target domains. Reusable parser: `scripts/extract_tls_sni.py`

### 7. Bypass options (pick by evidence)

- Local-only check → patch jump / Frida return-value hook
- Network verify → hosts hijack + local Flask simulator, or Frida hook on login/heartbeat functions
- Nuitka binary → Frida (runtime) preferred over patching native code

## Pitfalls

- **Proxy masking**: with v2rayN/Clash system proxy on, the target process shows NO external conns even while online — the proxy process owns them. Always check `ProxyEnable` before concluding "no network".
- **PowerShell `$pid` is read-only** — use `$procId` / `$targetPid` in scripts.
- **MSYS `/tmp` paths fail in Windows PowerShell `-File`** — write .ps1 to a Windows path (`$env:TEMP\script.ps1`).
- **Chinese filenames break MSYS access** — use PowerShell `Get-CimInstance Win32_Process` / `Get-ChildItem` for CJK paths; `ls` on them fails silently.
- **NiceGUI children are ID refs, not nested objects** — a naive JSON walk finds nothing.
- **PyInstaller 6.x**: don't hunt for `_MEI*` — the live dir is `onefile_<pid>_<random>`; old `_MEI*` dirs are stale from other apps.
- **Restarting the app regenerates the token** — re-read the token file after any restart.
- **netsh trace captures ALL system traffic** — don't attribute a connection to the target without process/port evidence.
- **User rule**: never kill/restart running processes without telling the user first.

## Verification

- Prove the bypass: original vs modified behavior (login succeeds, main UI unlocks)
- Keep evidence: file hash, patch offsets, original vs patched bytes
- For network bypass: verify the app reaches the post-auth business state, not just a 200 response

## Support files

- `scripts/extract_tls_sni.py` — parse a netsh ETL into unique connections + TLS SNI domains
- `references/qingyun-case-study.md` — worked example: 轻云3.8 PUBG tool (PyInstaller6+Nuitka, webview2_token bypass, NiceGUI driving, proxy-masked server discovery)
