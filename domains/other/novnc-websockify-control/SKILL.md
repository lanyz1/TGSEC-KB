---
name: novnc-websockify-control
description: "Use when noVNC/websockify VNC found. Full desktop control."
---

# noVNC / websockify Remote Control

An unauthenticated VNC-over-WebSocket endpoint (Kasm-style cloud browsers, cloud-phone farms, remote-desktop containers, security type `[1] None`) is FULL desktop control of a live operator workspace: saved logins, session cookies, intranet history. Treat it as a credential store and an internal-network pivot, not a screen.

## Workflow (order matters)

1. **Probe.** Candidate paths on the noVNC port (commonly 5800 / 6080): `/websockify`, `/vnc.html`, `/vnc_lite.html`, `/webdata.json`. A live `/websockify` returns WS binary whose first bytes are the RFB banner `RFB 003.008\n`. The WebSocket upgrade REQUIRES header `Sec-WebSocket-Protocol: binary` (websockify/Kasm rejects or misbehaves without it). Also probe raw RFB on `:5900` — cloud-browser containers (jlesage/firefox and similar) expose plain RFB over TCP next to noVNC `:5800`; same handshake over a plain socket, no websockify, security type `[1] None`.
2. **Handshake, exact order:** banner echo -> security types (pick `1` if offered = no auth) -> SecurityResult -> **send ClientInit (single byte `\x00`)** -> ServerInit -> SetPixelFormat -> SetEncodings -> FBUpdReq. Use `scripts/vnc_ws_client.py` (battle-tested). Byte layouts in `references/rfb-protocol.md`.
   - **Pitfall: skipping the 1-byte ClientInit desyncs the whole stream.** The server consumes your next message's first byte as ClientInit; all parsing shifts and the connection resets a few messages later. Symptom: ServerInit missing/garbled after "blind" sends, then disconnect. Most online python snippets omit ClientInit — do not copy them blindly.
   - **Pitfall: send SetPixelFormat exactly once.** Re-sending it (or replaying handshake messages "just in case") drops the connection on KasmVNC.
3. **Capture.** FBUpdReq, then collect WS frames until quiet; parse rects: enc 0 raw BGRA / 5 hextile / 6 zlib -> PNG. Servers often choose hextile when your SetEncodings offers raw+copyrect+hextile+zlib. Always screenshot first to learn the current screen state.
4. **Read the screen text-first (OCR)** — never guess what is on screen:
   - `tesseract img.png stdout --psm 6 -l chi_sim+eng` (chi_sim needed for Chinese UIs).
   - Preprocess with PIL: upscale x2-4 (LANCZOS), autocontrast, contrast x1.5-1.8, invert for dark themes, optional SHARPEN.
   - Coordinates: `tesseract ... tsv` word boxes; or numpy brightness histograms — per-row bright counts find text bands, near-white rectangles = input boxes, grid-clustered bright pixels = buttons.
   - Zoom the guest UI (`Ctrl+=`, reset `Ctrl+0`) when text is too small to OCR.
   - Screenshot AFTER every state-changing action; diff before/after tells you whether a click or paste landed.
5. **Input.** KeyEvent (type 4; X11 keysyms: Ctrl 0xffe3, Shift 0xffe1, Return 0xff0d, printable ASCII = codepoint) and PointerEvent (type 5, mask bit0 = left; sequence move(0) -> down(1) -> up(0)).
6. **Clipboard is a two-way data channel — the highest-value primitive.**
   - **Write:** ClientCutText (type 6) + `Ctrl+V` enters EXACT strings (URLs, `about:` paths, API keys, passwords). Prefer paste over key-event typing: punctuation can mistranslate under key events (e.g. `:` can land as `;`); paste is byte-exact. Click/focus the target field first, paste, screenshot to confirm, THEN submit.
   - **Read:** ServerCutText (type 3) arrives in the frame stream whenever the guest copies something. Trigger a copy in the guest, then capture the next ServerCutText -> plaintext.
   - Caveat: ServerCutText may arrive down-converted to Latin-1; non-ASCII comes back as literal `?`. ASCII (URLs, usernames, passwords) survives — copy those; OCR the rest.
7. **Harvest (validated recipes).**
   - Firefox saved passwords: paste-navigate to `about:logins`, open the entry, click the small copy icon on the password field row -> read ServerCutText -> plaintext credentials. (Clicking the row's copy buttons beats OCR — OCR misreads credential characters.)
   - Full browsing history: `Ctrl+Shift+H` (Library) -> click the list -> `Ctrl+A`, `Ctrl+C` -> read ServerCutText -> every visited URL, newline-separated. Reveals intranet systems (`http://192.168.x.x` router panels, admin UIs), operator tooling and habits.
   - Bookmarks window / downloads page / any selectable UI: same select-all-copy trick.
8. **Pivot.** `file:///` in the guest browser opens the container filesystem (browser profile, downloads). Internal hosts reachable from the guest but not from you can be probed through the guest browser (SSRF-style via address bar + OCR of the result page).

## Pitfalls

- **Don't guess click coordinates.** A click ~50px off silently no-ops (before/after screenshot diff = 0 is the tell). Locate the element via OCR TSV / pixel analysis first, then click the center of the detected box.
- **The workspace is live and possibly the operator's daily driver.** Read-focused actions only: do not delete, log out, or change settings — visible disruption tips off the target.
- **Check the cloud-browser config** (`webdata.json` served by the front-end): when `fileManager`/`terminal` capability flags are false, auxiliary `/ws-*` channels 404 — only the main VNC channel works, so clipboard is your only in/out.
- **WS framing:** server->client frames unmasked, client->server MUST be masked; answer Ping (op 9) with Pong (op 10); RFB messages can be split across frames — buffer and parse leniently.
- When the framebuffer stream looks empty after connecting, send FBUpdReq with `incremental=0` for a full refresh before concluding the endpoint is dead.
- **Do input and screenshots on SEPARATE connections.** After a KeyEvent burst, update requests on the same connection can keep coming back with zero rects; the reliable pattern is: send input on one connection, then open a fresh connection for the screenshot (validated against jlesage/firefox; the same-connection variant repeatedly returned 0 rects).
- **Browser-only kiosks have no window manager:** in jlesage/firefox-class containers (bare X + Firefox), global shortcuts like `Ctrl+Alt+T` do nothing — drive the browser itself (`Ctrl+L` address bar, type the URL, Return; screenshot on a new connection after it settles).

## Files

- `references/rfb-protocol.md` — byte-level RFB message formats, encodings, Kasm quirks.
- `scripts/vnc_ws_client.py` — tested client: `shot` / `clip` / `paste` / `click` / `key` CLI + importable helpers (WS class, handshake, decode_stream, hextile decoder, input, clipboard).
