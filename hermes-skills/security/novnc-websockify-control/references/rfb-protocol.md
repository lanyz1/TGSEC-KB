# RFB over websockify — byte-level notes

Verified against a Kasm-style cloud-browser container (Docker Firefox, security type None).

## Transport (WS layer)

- Request: `GET {origin}/websockify` with headers `Upgrade: websocket`, `Connection: Upgrade`, `Sec-WebSocket-Key` (16 random bytes, b64), `Sec-WebSocket-Version: 13`, `Origin: http://host:port`.
- **`Sec-WebSocket-Protocol: binary` is required** by websockify/Kasm — without it the upgrade or the traffic misbehaves.
- Frames: opcode 2 binary (also accept opcode 0 continuation). Server->client unmasked; client->server MUST be masked. Ping (op 9) -> reply Pong (op 10, echo payload).
- Assume one whole RFB message per WS frame as the common case, but buffer across frames defensively.

## Handshake order

1. Server -> `RFB 003.008\n` (12 bytes, first frame payload). Client echoes the same 12 bytes.
2. Server -> security types: `[count][type x count]`. If `1` (None) is present, send choice byte `\x01`. (Type 2 = classic VNC auth: server follows with 16-byte challenge, client replies DES-encrypted password — different path.)
3. Server -> SecurityResult: 4 bytes, `00 00 00 00` = OK. On failure a reason string may follow.
4. Client -> **ClientInit: one byte `\x00`** (shared flag). MANDATORY. Omitting it makes the server consume your next message's first byte as ClientInit -> stream desync -> connection reset.
5. Server -> ServerInit: `width(2) height(2) pixel-format(16) name-len(4) name(n)`. Mirror the pixel format into SetPixelFormat. If it doesn't arrive within a few seconds, nudge with SetPixelFormat and keep reading — but always send ClientInit first.
6. Client -> SetPixelFormat: `00 00 00 00` + pf(16). **Exactly once.**
7. Client -> SetEncodings: `02 00 count(2)` + count x int32. Practical set: 0 raw, 1 copyrect, 5 hextile, 6 zlib. Servers commonly pick hextile.
8. Client -> FramebufferUpdateRequest: `03 incremental(1) x(2) y(2) w(2) h(2)`; `incremental=0` forces a full refresh.

## Client -> server messages

- `0` SetPixelFormat: pad(4) + pf(16)
- `2` SetEncodings: pad(1) + count(2) + encodings int32 x n
- `3` FramebufferUpdateRequest: inc(1) x(2) y(2) w(2) h(2)
- `4` KeyEvent: down(1) pad(2) keysym(4) — down=1 press, 0 release
- `5` PointerEvent: mask(1) x(2) y(2) — bit0 left, bit1 middle, bit2 right; move(mask=0) -> down -> up for a click
- `6` ClientCutText: pad(3) len(4) + text (latin-1)

X11 keysyms: Ctrl_L 0xffe3, Shift_L 0xffe1, Alt_L 0xffe9, Return 0xff0d, Tab 0xff09, Esc 0xff1b, BackSpace 0xff08, Delete 0xffff, printable ASCII keysym == codepoint. Shifted characters under key events are flaky — prefer clipboard paste for exact strings.

## Server -> client messages (inside WS binary frames)

- `0` FramebufferUpdate: pad(1) nrects(2), then per rect `x(2) y(2) w(2) h(2) enc(4)` + payload:
  - enc 0 raw: w*h*4 bytes BGRA
  - enc 5 hextile: per tile (<=16x16, clipped at edges) first byte subencoding:
    - 0x01 Raw: full tile w_t*h_t*4 BGRA bytes
    - 0x02 BackgroundSpecified: 4-byte bg color follows
    - 0x04 ForegroundSpecified: 4-byte fg color follows
    - 0x08 AnySubrects: count(1), then per subrect: color(4B only if 0x10 SubrectsColoured, else use fg); xy(1B as `x<<4|y`); wh(1B as `(w-1)<<4|(h-1)`); subrect dims +1
    - bg/fg state carries over between tiles; raw tiles do not update it
  - enc 6 zlib: len(4) + zlib stream -> decompressed raw BGRA for w*h
- `3` ServerCutText: pad(3) len(4) + text — emitted whenever the guest copies to clipboard. Kasm down-converts to Latin-1: non-ASCII arrives as literal `?`; ASCII content (URLs, credentials) is intact.
- Others: `1` SetColourMapEntries, `2` Bell — skip safely.

Decode to PIL: `Image.frombytes("RGBA", (w, h), body, "raw", "BGRA").convert("RGB")`. For incremental updates, paste rects onto the previous frame image.

## Kasm-style cloud browser notes

- Front-end serves a config JSON (e.g. `/webdata.json`) with `containerInstanceUID`, `applicationName`, and capability flags (`fileManager`, `terminal`, `audioSupport`). Flags false => auxiliary websocket channels (`/ws-filemanager`, `/ws-terminal`) return 404; only `/websockify` works.
- The container session is persistent: saved passwords, cookies, history belong to a real operator.
- `file:///` browsing works in the guest browser: the container filesystem (Firefox profile, downloads) is readable page-by-page.
