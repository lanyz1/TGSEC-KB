"""自愈 SOCKS5 over SSH(direct-tcpip)。本地监听常驻,SSH 掉线自动重连,支持并发。
用法: python robust_socks.py <jump_ip> <port> <user> <pass> <local_port>
"""
import socket, struct, threading, select, sys, time, traceback
import paramiko

JUMP_IP, JUMP_PORT, USER, PASS, LOCAL = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5])

_lock = threading.Lock()
_cli = None
_TR = None


def get_transport():
    """返回一个可用的 paramiko Transport,必要时重连。"""
    global _cli, _TR
    with _lock:
        if _TR is not None:
            try:
                if _TR.is_active():
                    return _TR
            except Exception:
                pass
            try:
                _cli.close()
            except Exception:
                pass
            _TR = None
        for attempt in range(50):
            try:
                c = paramiko.SSHClient()
                c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                c.connect(JUMP_IP, port=JUMP_PORT, username=USER, password=PASS,
                          timeout=20, banner_timeout=25, auth_timeout=25,
                          look_for_keys=False, allow_agent=False)
                t = c.get_transport()
                t.set_keepalive(20)
                _cli, _TR = c, t
                log("SSH up")
                return t
            except Exception as e:
                log(f"SSH retry {attempt}: {e}")
                time.sleep(3)
        raise RuntimeError("ssh unavailable")


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def relay(a, b):
    try:
        while True:
            r, _, _ = select.select([a, b], [], [], 60)
            if not r:
                # 双方都无数据;检查是否已断开
                continue
            for s in r:
                try:
                    d = s.recv(65536)
                except Exception:
                    return
                if not d:
                    return
                (b if s is a else a).sendall(d)
    except Exception:
        pass


def handle(conn):
    try:
        conn.settimeout(30)
        hdr = conn.recv(2)
        if len(hdr) < 2 or hdr[0] != 5:
            conn.close(); return
        n = hdr[1]
        conn.recv(n)
        conn.sendall(b"\x05\x00")                      # no-auth
        req = conn.recv(4)
        if len(req) < 4:
            conn.close(); return
        atyp = req[3]
        if atyp == 1:
            host = socket.inet_ntoa(conn.recv(4))
        elif atyp == 3:
            ln = conn.recv(1)[0]
            host = conn.recv(ln).decode()
        elif atyp == 4:
            host = socket.inet_ntop(socket.AF_INET6, conn.recv(16))
        else:
            conn.close(); return
        port = struct.unpack("!H", conn.recv(2))[0]
        conn.settimeout(None)

        tr = get_transport()
        ch = tr.open_channel("direct-tcpip", (host, port), ("127.0.0.1", 0), timeout=30)
        conn.sendall(b"\x05\x00\x00\x01" + socket.inet_aton("0.0.0.0") + struct.pack("!H", 0))
        relay(conn, ch)
        try:
            ch.close()
        except Exception:
            pass
    except Exception:
        try:
            conn.sendall(b"\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00")
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main():
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", LOCAL))
    srv.listen(128)
    log(f"listening 127.0.0.1:{LOCAL} -> {USER}@{JUMP_IP}:{JUMP_PORT}")
    while True:
        try:
            conn, _ = srv.accept()
        except Exception:
            continue
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception:
            log("main crashed: " + traceback.format_exc()[:300])
            time.sleep(2)
