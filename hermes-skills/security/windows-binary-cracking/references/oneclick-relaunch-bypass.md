# One-Click Relaunch Bypass Pattern (verified 2026-08)

After you have a working bypass (e.g. Frida time-shift), the final deliverable is a relaunch script that re-arms the whole chain after an app restart, because Frida hooks are runtime-only. This pattern was verified on a Nuitka/PyInstaller + pywebview + fndata app (轻云3.8) whose local HTTP port is **random per launch**.

## The chain the script must re-do

1. Launch the EXE (`subprocess.Popen`, cwd = exe dir).
2. Wait for the window token file to regenerate — the app writes `~/.app/.webview2_token` (`secrets.token_urlsafe()`, 43 chars) each launch. Poll until non-empty.
3. Find the local web port: scan 8200–8310, connect, then GET `/?webview2_token=<token>` and check the HTML for the app title / 用户登录 / 控制台 marker. The port is random (`8284` one launch, `8202` next) — never hardcode it.
4. Attach Frida to the **child** (real) process, not the parent launcher:
   - PyInstaller onefile = parent (unpacker, 1 thread, no window) + child (real app, many threads, window title, WebView2 child).
   - Find the child via psutil: `name contains 'TXMyW'` (or exe basename) and `ppid == parent pid`; fall back to newest matching process.
5. Report final URL `http://127.0.0.1:<port>/?webview2_token=<token>` — the user can drive the UI from a browser, and the app's own WebView2 window also works.

## Key details

- The parent process has no TCP listeners; the child listens on 127.0.0.1:<random>.
- Free-registration accounts (username ≥6 chars, QQ, password ≥6) typically log in successfully — the fastest way past the login gate without owning a card key is to register an account through the UI first, then use it. Server-side expiry (VipTime) is then the remaining gate → time-shift hook.
- `C:\Windows\winS` / `winSS` stay 0-byte when 记住我 is unchecked; login_prefs.json only fills when checked. Forging these files is a *candidate* bypass but the time-shift hook is the verified one.
- Verification of a successful bypass = app reaches its main functional screen (dashboard/console tabs), stays alive across a heartbeat cycle, and no "已到期/即将关闭程序" dialog appears.

## File map

- `scripts/frida-vip-expiry-timeshift.js` — the Frida hook the launcher attaches.
- This pattern lives alongside `fndata-verification-platform.md` in the same skill; the launcher script itself is session-specific and was delivered to `Documents\轻云破解\qingyun_launcher.py` — re-derive it from this recipe rather than treating that path as durable.
