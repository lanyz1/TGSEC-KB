#!/usr/bin/env python3
"""noVNC / websockify VNC client - handshake, capture, input, clipboard.

Tested against a Kasm-style cloud-browser (Docker Firefox, security type None).

CLI examples:
    python3 vnc_ws_client.py shot  HOST [PORT] [OUT.png]
    python3 vnc_ws_client.py clip  HOST [PORT]              # read guest clipboard
    python3 vnc_ws_client.py paste HOST [PORT] "TEXT"       # set clipboard + Ctrl+V
    python3 vnc_ws_client.py click HOST [PORT] X Y          # left click
    python3 vnc_ws_client.py key   HOST [PORT] 0xff0d       # press one keysym (hex)

Notes:
- Click/focus the target field BEFORE `paste`; Ctrl+V goes to the focused element.
- Prefer `paste` over key-event typing for exact strings (punctuation is flaky under keys).
- `clip` returns whatever the guest copies NEXT; trigger a copy in-guest first
  (e.g. Firefox about:logins "copy password" button).
"""
import base64
import os
import select
import socket
import struct
import sys
import time
import zlib

try:
    from PIL import Image
except ImportError:  # decode functions need Pillow
    Image = None

KEY_CTRL_L = 0xffe3
KEY_SHIFT_L = 0xffe1
KEY_ALT_L = 0xffe9
KEY_RETURN = 0xff0d
KEY_TAB = 0xff09
KEY_ESC = 0xff1b
KEY_BACKSPACE = 0xff08
KEY_DELETE = 0xffff


class WS:
    """Minimal WebSocket client (binary frames, client-side masking)."""

    def __init__(self, host, port=5800, path="/websockify", timeout=12, protocol="binary"):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n"
            f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n"
        )
        if protocol:
            req += f"Sec-WebSocket-Protocol: {protocol}\r\n"
        req += f"Origin: http://{host}:{port}\r\n\r\n"
        self.sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("closed during WebSocket handshake")
            buf += chunk
        head, _, self.buf = buf.partition(b"\r\n\r\n")
        self.header = head
        if b"101" not in head.split(b"\r\n")[0]:
            raise ConnectionError(f"bad WS upgrade response: {head[:120]!r}")

    def _recv_exact(self, n, timeout=10):
        deadline = time.time() + timeout
        while len(self.buf) < n:
            remain = deadline - time.time()
            if remain <= 0:
                raise socket.timeout(f"recv timeout after {n}B")
            r, _, _ = select.select([self.sock], [], [], remain)
            if not r:
                raise socket.timeout(f"select timeout after {n}B")
            chunk = self.sock.recv(262144)
            if not chunk:
                raise ConnectionError("connection closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv_frame(self, timeout=10):
        b1, b2 = self._recv_exact(2, timeout)
        opcode = b1 & 0x0F
        masked = b2 & 0x80
        length = b2 & 0x7F
        if length == 126:
            length = struct.unpack(">H", self._recv_exact(2, timeout))[0]
        elif length == 127:
            length = struct.unpack(">Q", self._recv_exact(8, timeout))[0]
        mask = self._recv_exact(4, timeout) if masked else b""
        payload = self._recv_exact(length, timeout) if length else b""
        if masked:
            payload = bytes(c ^ mask[i % 4] for i, c in enumerate(payload))
        return opcode, payload

    def send_frame(self, payload, opcode=2):
        mask = os.urandom(4)
        n = len(payload)
        if n < 126:
            hdr = bytes([0x80 | opcode, 0x80 | n])
        elif n < 65536:
            hdr = bytes([0x80 | opcode, 0x80 | 126]) + struct.pack(">H", n)
        else:
            hdr = bytes([0x80 | opcode, 0x80 | 127]) + struct.pack(">Q", n)
        hdr += mask
        self.sock.sendall(hdr + bytes(c ^ mask[i % 4] for i, c in enumerate(payload)))

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def rfb_handshake(ws, shared=0):
    """Full RFB handshake. Returns (width, height, pixel_format, name).

    Order is critical: ClientInit is sent BEFORE anything else after
    SecurityResult, and SetPixelFormat is sent exactly once.
    """
    _, banner = ws.recv_frame(8)          # b"RFB 003.008\n"
    ws.send_frame(banner)                 # echo version
    _, sec = ws.recv_frame(8)
    n = sec[0]
    types = list(sec[1:1 + n])
    if 1 not in types:
        raise RuntimeError(f"security type None not offered: {types}")
    ws.send_frame(bytes([1]))             # choose None
    ws.recv_frame(8)                      # SecurityResult (4B)
    ws.send_frame(bytes([shared]))        # ClientInit - MANDATORY, do not skip

    si = b""
    deadline = time.time() + 8
    while len(si) < 24:
        if time.time() > deadline:
            raise TimeoutError("ServerInit not received")
        op, payload = ws.recv_frame(6)
        if op in (0, 2):
            si += payload
    w, h = struct.unpack(">HH", si[:4])
    pf = si[4:20]
    nlen = struct.unpack(">I", si[20:24])[0]
    while len(si) < 24 + nlen and time.time() <= deadline:
        op, payload = ws.recv_frame(6)
        if op in (0, 2):
            si += payload
    name = si[24:24 + nlen]

    ws.send_frame(bytes(4) + pf)                                   # SetPixelFormat (once)
    ws.send_frame(struct.pack(">BBH", 2, 0, 4)
                  + struct.pack(">iiii", 0, 1, 5, 6))              # SetEncodings
    return w, h, pf, name


def request_screen(ws, w, h, incremental=0, timeout=60, quiet=3.0):
    """Send FBUpdReq and collect binary payloads until quiet / timeout."""
    ws.send_frame(struct.pack(">BBHHHH", 3, incremental, 0, 0, w, h))
    data = b""
    last = time.time()
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            op, payload = ws.recv_frame(1.5)
        except socket.timeout:
            if data and time.time() - last > quiet:
                break
            continue
        if op in (0, 2):
            data += payload
            last = time.time()
        elif op == 9:                      # ping -> pong
            ws.send_frame(payload, opcode=10)
        elif op == 8:                      # close
            break
    return data


def _decode_hextile(stream, off, w, h):
    """Decode one hextile-encoded rect. Returns (raw BGRA bytes, new offset)."""
    dst = bytearray(w * h * 4)
    p = off
    bg = b"\x00\x00\x00\x00"
    fg = None
    for ty in range(0, h, 16):
        for tx in range(0, w, 16):
            tw = min(16, w - tx)
            th = min(16, h - ty)
            sub = stream[p]
            p += 1
            if sub & 1:  # raw tile
                raw = stream[p:p + tw * th * 4]
                p += tw * th * 4
                for yy in range(th):
                    src = raw[yy * tw * 4:(yy + 1) * tw * 4]
                    d = ((ty + yy) * w + tx) * 4
                    dst[d:d + tw * 4] = src
                continue
            if sub & 2:
                bg = stream[p:p + 4]
                p += 4
            if sub & 4:
                fg = stream[p:p + 4]
                p += 4
            row = bg * tw
            for yy in range(th):
                d = ((ty + yy) * w + tx) * 4
                dst[d:d + tw * 4] = row
            if sub & 8:
                count = stream[p]
                p += 1
                for _ in range(count):
                    if sub & 16:
                        color = stream[p:p + 4]
                        p += 4
                    else:
                        color = fg if fg else bg
                    xy = stream[p]
                    whb = stream[p + 1]
                    p += 2
                    sx = xy >> 4
                    sy = xy & 0x0F
                    sw = (whb >> 4) + 1
                    sh = (whb & 0x0F) + 1
                    for yy in range(sy, min(sy + sh, th)):
                        for xx in range(sx, min(sx + sw, tw)):
                            d = ((ty + yy) * w + tx + xx) * 4
                            dst[d:d + 4] = color
    return bytes(dst), p


def decode_stream(stream, w, h, base=None):
    """Parse a FramebufferUpdate stream into a PIL image (raw/hextile/zlib)."""
    if Image is None:
        raise RuntimeError("Pillow required: pip install pillow")
    if base is None:
        base = Image.new("RGB", (w, h), (30, 30, 30))
    if len(stream) < 4 or stream[0] != 0:
        return base
    nrects = struct.unpack(">H", stream[2:4])[0]
    off = 4
    for _ in range(nrects):
        if off + 12 > len(stream):
            break
        rx, ry, rw, rh = struct.unpack(">HHHH", stream[off:off + 8])
        enc = struct.unpack(">i", stream[off + 8:off + 12])[0]
        off += 12
        if enc == 0:
            body = stream[off:off + rw * rh * 4]
            off += rw * rh * 4
            if len(body) < rw * rh * 4:
                break
        elif enc == 5:
            try:
                body, off = _decode_hextile(stream, off, rw, rh)
            except IndexError:
                break
        elif enc == 6:
            if off + 4 > len(stream):
                break
            length = struct.unpack(">I", stream[off:off + 4])[0]
            off += 4
            try:
                body = zlib.decompress(stream[off:off + length])
            except zlib.error:
                break
            off += length
        else:
            break  # unsupported encoding; cannot advance safely
        if rw and rh:
            img = Image.frombytes("RGBA", (rw, rh), body, "raw", "BGRA").convert("RGB")
            base.paste(img, (rx, ry))
    return base


def key_event(ws, keysym, down):
    ws.send_frame(struct.pack(">BBHI", 4, 1 if down else 0, 0, keysym))


def press(ws, keysym, delay=0.06):
    key_event(ws, keysym, True)
    time.sleep(0.03)
    key_event(ws, keysym, False)
    time.sleep(delay)


def combo(ws, mod, keysym):
    key_event(ws, mod, True)
    time.sleep(0.04)
    key_event(ws, keysym, True)
    time.sleep(0.05)
    key_event(ws, keysym, False)
    time.sleep(0.03)
    key_event(ws, mod, False)
    time.sleep(0.10)


def pointer(ws, x, y, mask=0):
    ws.send_frame(struct.pack(">BBHH", 5, mask, x, y))


def click(ws, x, y):
    pointer(ws, x, y, 0)
    time.sleep(0.10)
    pointer(ws, x, y, 1)
    time.sleep(0.08)
    pointer(ws, x, y, 0)
    time.sleep(0.10)


def send_cut_text(ws, text):
    b = text.encode("latin-1", "replace")
    ws.send_frame(struct.pack(">BxxxI", 6, len(b)) + b)


def read_cut_text(ws, timeout=6.0):
    """Wait for the next ServerCutText; returns bytes or None.

    Assumes whole RFB messages per WS frame (true for websockify/Kasm).
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            op, payload = ws.recv_frame(1.5)
        except socket.timeout:
            continue
        if op in (0, 2) and len(payload) >= 8 and payload[0] == 3:
            length = struct.unpack(">I", payload[4:8])[0]
            return payload[8:8 + length]
        if op == 9:
            ws.send_frame(payload, opcode=10)
    return None


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="noVNC/websockify client")
    ap.add_argument("cmd", choices=["shot", "clip", "paste", "click", "key"])
    ap.add_argument("host")
    ap.add_argument("port", nargs="?", type=int, default=5800)
    ap.add_argument("args", nargs="*")
    a = ap.parse_args(argv)

    ws = WS(a.host, a.port)
    w, h, pf, name = rfb_handshake(ws)
    print(f"# connected {w}x{h} name={name!r}", file=sys.stderr)

    if a.cmd == "shot":
        out = a.args[0] if a.args else "screen.png"
        data = request_screen(ws, w, h, incremental=0, timeout=40)
        decode_stream(data, w, h).save(out)
        print(f"# saved {out} ({len(data)}B)")
    elif a.cmd == "clip":
        t = read_cut_text(ws)
        print(t.decode("utf-8", "replace") if t else "# no ServerCutText received")
    elif a.cmd == "paste":
        if not a.args:
            ap.error("paste needs TEXT")
        send_cut_text(ws, a.args[0])
        time.sleep(0.4)
        combo(ws, KEY_CTRL_L, ord("v"))
        print("# pasted via Ctrl+V")
    elif a.cmd == "click":
        if len(a.args) < 2:
            ap.error("click needs X Y")
        click(ws, int(a.args[0]), int(a.args[1]))
        print("# clicked")
    elif a.cmd == "key":
        if not a.args:
            ap.error("key needs KEYSYM (hex)")
        press(ws, int(a.args[0], 16))
        print("# key pressed")
    ws.close()


if __name__ == "__main__":
    main()
