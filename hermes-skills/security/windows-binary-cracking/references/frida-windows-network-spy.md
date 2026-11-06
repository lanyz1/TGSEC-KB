# Frida Windows Network Spy — Hooks, Pitfalls, Proxy Transparency

Working patterns for intercepting a Windows app's verification traffic with Frida, learned cracking a pywebview + FastAPI + NiceGUI app (Nuitka-compiled `main.dll`).

## Attach modes

```bash
frida -p <pid> -l script.js            # interactive REPL; console.log goes to terminal
frida-trace -p <pid> -i "WS2_32.dll!send" -i "WS2_32.dll!recv"   # handler per function
```

- frida-trace handlers are auto-generated at `__handlers__/<DLL>.dll/<func>.js`; **edit them and restart frida-trace** to customize logging (it only loads handlers at startup).
- Handler shape: `defineHandler({ onEnter(log, args, state) {...}, onLeave(log, retval, state) {...} })`.
- `log()` prints with timing prefix; use `send(obj)` from a raw `frida -l` script for structured output.

## CRITICAL pitfall: `Module` global in Frida 17 REPL

`Module.findExportByName('ws2_32.dll', 'send')` threw `TypeError: not a function` when loaded via `frida -p <pid> -l`. **Use the Process API instead:**

```js
var mod = Process.findModuleByName('ws2_32.dll');
var sendPtr = mod.getExportByName('send');
```

Also: avoid fancy API calls in hooks; `parseInt(args[2].toString())` and `readByteArray()` are safe; `args[2].toInt32()` also failed in the REPL.

## CRITICAL pitfall: frida-trace hooks WSOCK32 by default

`-i "send"` generates handlers under `__handlers__/WSOCK32.dll/` — the legacy 16-bit shim, which real Python/Go apps never call. The app used `WS2_32.dll!send/recv`. Fix:
- Qualify the module: `-i "WS2_32.dll!send"`.
- Delete stale `__handlers__/WSOCK32.dll/` between runs (frida-trace regenerates it from `-i` otherwise).
- `-I "WS2_32.dll"` hooks EVERYTHING in the module (noisy — avoid).

## Working hook set

```js
// DNS resolution → reveals verification server domain/IP
hookDns('getaddrinfo', 'ws2_32.dll', false);   // arg0 node.readUtf8String()
hookDns('GetAddrInfoW', 'ws2_32.dll', true);   // arg0 node.readUtf16String()
// Direct connect (only visible when NOT going through a proxy)
// ws2_32!connect / WSAConnect: sockaddr family(2=IPv4) port, ip bytes
// HTTP payload capture
// ws2_32!send: args[1] buffer, args[2] len → print ASCII if starts POST/GET or contains '{'
// ws2_32!recv: capture in onEnter (this.rbuf = args[1]), print in onLeave when contains '{'/'Status'/'Msg'
```

DNS hook result example: `getaddrinfo(HOST: 101.35.246.71)` — app resolved the hardcoded IP, revealing the verification server.

## Proxy transparency (why the app PID shows zero external TCP)

v2rayN/Clash system proxy at `127.0.0.1:10808` means the app's outbound goes through the proxy process — `Get-NetTCPConnection -OwningProcess <apppid>` shows ONLY localhost. The verification traffic is carried by the proxy process (xray/sing-box), and its destination mix is unreadable.

Fix for direct capture:
1. Disable system proxy: `Set-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0`
2. **Restart the app** — proxy settings are cached at startup (requests/aiohttp read them once).
3. Re-attach Frida DNS/connect hooks → now the app PID shows real outbound.

Check proxy state: `(Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings').ProxyEnable` (1=on).

## netsh trace fallback (NDIS packet capture, no Wireshark)

```powershell
netsh trace start capture=yes maxsize=100 filemode=circular overwrite=yes tracefile=C:\Temp\q.etl
# ... trigger traffic ...
netsh trace stop
```

Parse in PowerShell:
```powershell
$events = Get-WinEvent -Path C:\Temp\q.etl -Oldest | Where-Object { $_.ProviderName -eq 'Microsoft-Windows-NDIS-PacketCapture' }
# frame bytes = $e.Properties[3].Value (Byte[])
```
Then parse Ethernet (type 0x0800) → IPv4 (protocol 6/17) → TCP/UDP ports. TLS ClientHello SNI extraction from the payload gives the domain even under TLS (fakainc.shop example). Caveat: this captures ALL processes — correlate by source port/process, and expect proxy-process noise.

## Local web UI access (pywebview token gate)

- App = local FastAPI/NiceGUI server + pywebview (WebView2). Browser gets "不支持的浏览器 / 仅支持通过专用客户端访问".
- Mechanism: app generates `secrets.token_urlsafe()`, writes `~/.jla_app/.webview2_token`, and opens the page as `http://127.0.0.1:<port>/?webview2_token=<tok>`.
- Bypass: read the token file, curl/browser `?webview2_token=<tok>` → full login UI renders. Token file regenerates per launch — re-read after restart.
- Local port is RANDOM per launch (8284, then 8202) — find via `netstat -ano | grep <pid>` / `Get-NetTCPConnection -OwningProcess <pid> -State Listen`.

## Headless-browser quirks with NiceGUI

- WebSocket drops often; page renders empty. Re-navigate with token URL before each interaction.
- browser_console multi-line IIFEs fail with "Unexpected end of input" — keep expressions single-line.
- Direct `input.value = x` doesn't update Quasar v-model; native `browser_type` on the ref is more reliable; setting value + dispatching `input`/`change` events sometimes works.
- After login success the UI switches to the dashboard — snapshot shows 控制台/账号切换/细节设置 tabs.
