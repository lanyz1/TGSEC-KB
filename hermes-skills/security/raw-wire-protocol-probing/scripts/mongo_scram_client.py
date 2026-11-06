#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MongoDB 裸 wire 协议客户端 —— pymongo 4.x 拒连 MongoDB <=4.1 (wire version <=7) 时使用。

用法:
  # 1) 只指纹(完全免认证): 版本 / wire version / 是否要求认证
  python3 mongo_scram_client.py <host> [port]

  # 2) 单组凭据 + 命中后列库
  python3 mongo_scram_client.py <host> [port] <user> <password> [authdb]

  # 3) 批量爆(每行 user:password ; authdb 默认 admin)
  python3 mongo_scram_client.py <host> [port] --file creds.txt [authdb]

关键事实(踩过的坑):
  * OP_MSG messageLength = 16(header) + 4(flagBits) + 1(kind) + len(BSON)
    少算这 5 字节 -> 服务端回 "invalid bson in element with field name 'isMaster'"
  * isMaster 免认证; listDatabases 需要认证
  * 回 "Authentication failed." = SCRAM 实现正确、只是凭据不对(不是代码错)
"""
import socket
import struct
import hashlib
import hmac
import base64
import os
import re
import sys

OP_MSG = 2013


# ---------------------------------------------------------------- BSON

def bson_enc(d):
    out = b""
    for k, v in d.items():
        kb = k.encode() + b"\x00"
        if isinstance(v, bool):
            out += b"\x08" + kb + (b"\x01" if v else b"\x00")
        elif isinstance(v, int):
            out += b"\x10" + kb + struct.pack("<i", v)
        elif isinstance(v, float):
            out += b"\x01" + kb + struct.pack("<d", v)
        elif isinstance(v, str):
            vb = v.encode() + b"\x00"
            out += b"\x02" + kb + struct.pack("<i", len(vb)) + vb
        elif isinstance(v, (bytes, bytearray)):
            out += b"\x05" + kb + struct.pack("<i", len(v)) + b"\x00" + bytes(v)
        elif isinstance(v, dict):
            out += b"\x03" + kb + bson_enc(v)
        elif isinstance(v, list):
            out += b"\x04" + kb + bson_enc({str(i): x for i, x in enumerate(v)})
        elif v is None:
            out += b"\x0a" + kb
        else:
            raise TypeError("unsupported bson type: %r" % type(v))
    body = out + b"\x00"
    return struct.pack("<i", len(body) + 4) + body


def bson_dec(b, off=0):
    end = off + struct.unpack_from("<i", b, off)[0]
    p = off + 4
    out = {}
    while p < end - 1:
        t = b[p]
        p += 1
        z = b.index(b"\x00", p)
        name = b[p:z].decode("utf-8", "replace")
        p = z + 1
        if t == 0x01:      # double
            out[name] = struct.unpack_from("<d", b, p)[0]
            p += 8
        elif t == 0x02:    # string
            sl = struct.unpack_from("<i", b, p)[0]
            p += 4
            out[name] = b[p:p + sl - 1].decode("utf-8", "replace")
            p += sl
        elif t == 0x03:    # embedded doc
            out[name], _ = bson_dec(b, p)
            p += struct.unpack_from("<i", b, p)[0]
        elif t == 0x04:    # array
            out[name], _ = bson_dec(b, p)
            p += struct.unpack_from("<i", b, p)[0]
        elif t == 0x05:    # binary
            sl = struct.unpack_from("<i", b, p)[0]
            p += 5          # length(4) + subtype(1)
            out[name] = b[p:p + sl]
            p += sl
        elif t == 0x07:    # objectid
            p += 12
        elif t == 0x08:    # bool
            out[name] = bool(b[p])
            p += 1
        elif t == 0x09:    # utc datetime
            p += 8
        elif t == 0x0A:    # null
            out[name] = None
        elif t == 0x10:    # int32
            out[name] = struct.unpack_from("<i", b, p)[0]
            p += 4
        elif t in (0x11, 0x12):
            out[name] = struct.unpack_from("<q", b, p)[0]
            p += 8
        else:
            break
    return out, end


# ---------------------------------------------------------------- conn

class Mongo(object):
    def __init__(self, host, port=27017, timeout=15):
        self.host, self.port, self.timeout = host, port, timeout
        self.s = None
        self.rid = 0

    def __enter__(self):
        self.s = socket.socket()
        self.s.settimeout(self.timeout)
        self.s.connect((self.host, self.port))
        return self

    def __exit__(self, *a):
        try:
            self.s.close()
        except Exception:
            pass

    def cmd(self, doc):
        self.rid += 1
        body = b"\x00\x00\x00\x00" + b"\x00" + bson_enc(doc)
        msg = struct.pack("<iiii", 16 + len(body), self.rid, 0, OP_MSG) + body
        self.s.sendall(msg)
        data = b""
        while True:
            chunk = self.s.recv(65536)
            if not chunk:
                break
            data += chunk
            if len(data) >= 4 and len(data) >= struct.unpack_from("<i", data, 0)[0]:
                break
        return bson_dec(data, 21)[0]


# ---------------------------------------------------------------- SCRAM

def scram_auth(m, user, password, mech="SCRAM-SHA-1", authdb="admin"):
    """返回 (ok, info)。ok=False 且 info 含 'Authentication failed' 说明实现正确、凭据不对。"""
    nonce = base64.b64encode(os.urandom(24)).decode()
    cfb = "n=%s,r=%s" % (user.replace("=", "=3D").replace(",", "=2C"), nonce)
    try:
        r1 = m.cmd({"saslStart": 1, "mechanism": mech,
                    "payload": ("n,," + cfb).encode(),
                    "autoAuthorize": 1, "$db": authdb})
    except Exception as e:
        return False, "transport: %s" % str(e)[:80]
    if r1.get("ok") not in (1, 1.0):
        return False, r1.get("errmsg", str(r1)[:120])

    server_first = r1["payload"].decode("utf-8", "replace")
    conv = r1["conversationId"]
    rr = re.search(r"r=([^,]+)", server_first).group(1)
    salt = base64.b64decode(re.search(r"s=([^,]+)", server_first).group(1))
    iters = int(re.search(r"i=(\d+)", server_first).group(1))

    is_sha1 = mech.endswith("SHA-1")
    hfun = hashlib.sha1 if is_sha1 else hashlib.sha256
    dklen = 20 if is_sha1 else 32

    if is_sha1:
        salted = hashlib.pbkdf2_hmac("sha1", password.encode(), salt, iters, dklen)
    else:
        # SCRAM-SHA-256: 口令先做一次 sha256 hex,再进 PBKDF2
        pre = hashlib.sha256(password.encode()).hexdigest().encode()
        salted = hashlib.pbkdf2_hmac("sha256", pre, salt, iters, dklen)

    client_key = hmac.new(salted, b"Client Key", hfun).digest()
    stored_key = hfun(client_key).digest()
    cfp = "c=biws,r=" + rr                              # client final without proof
    auth_msg = cfb + "," + server_first + "," + cfp
    client_sig = hmac.new(stored_key, auth_msg.encode(), hfun).digest()
    proof = bytes(a ^ b for a, b in zip(client_key, client_sig))
    client_final = cfp + ",p=" + base64.b64encode(proof).decode()

    try:
        r2 = m.cmd({"saslContinue": 1, "conversationId": conv,
                    "payload": client_final.encode(), "$db": authdb})
    except Exception as e:
        return False, "transport: %s" % str(e)[:80]
    if r2.get("ok") in (1, 1.0):
        return True, r2
    return False, r2.get("errmsg", str(r2)[:120])


# ---------------------------------------------------------------- main

def fingerprint(m):
    """免认证指纹。"""
    info = m.cmd({"isMaster": 1, "$db": "admin"})
    print("[fingerprint] maxWireVersion    = %s" % info.get("maxWireVersion"))
    print("[fingerprint] minWireVersion    = %s" % info.get("minWireVersion"))
    print("[fingerprint] maxBsonObjectSize = %s" % info.get("maxBsonObjectSize"))
    print("[fingerprint] readOnly          = %s" % info.get("readOnly"))
    if info.get("maxWireVersion") is not None and info["maxWireVersion"] <= 7:
        print("[fingerprint] -> MongoDB <=4.1 : pymongo 4.x 会拒连,必须走本脚本")
    try:
        r = m.cmd({"listDatabases": 1, "$db": "admin"})
        if r.get("ok") in (1, 1.0):
            names = [d.get("name") for d in r.get("databases", [])]
            print("[auth] 未授权可访问! databases = %s" % names)
            return True
        print("[auth] 返回: %s" % r.get("errmsg", str(r)[:120]))
    except Exception as e:
        print("[auth] listDatabases 异常: %s" % str(e)[:80])
    return False


def try_creds(host, port, user, password, authdb):
    for mech in ("SCRAM-SHA-1", "SCRAM-SHA-256"):
        try:
            with Mongo(host, port) as m:
                ok, info = scram_auth(m, user, password, mech, authdb)
                if ok:
                    print("*** MONGO_OK %s %s/%s authdb=%s ***" % (mech, user, password, authdb))
                    r = m.cmd({"listDatabases": 1, "$db": "admin"})
                    print("    databases = %s" % [d.get("name") for d in r.get("databases", [])])
                    return True
                if "Authentication failed" in str(info):
                    print("  fail %s %s/%s@%s (实现正确,凭据不对)" % (mech, user, password, authdb))
                else:
                    print("  odd  %s %s/%s@%s : %s" % (mech, user, password, authdb, str(info)[:80]))
        except Exception as e:
            print("  err  %s %s@%s : %s" % (mech, user, authdb, str(e)[:70]))
    return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    host = sys.argv[1]
    port = 27017
    rest = list(sys.argv[2:])
    if rest and rest[0].isdigit():
        port = int(rest.pop(0))

    if not rest:
        with Mongo(host, port) as m:
            fingerprint(m)
        return 0

    if rest[0] == "--file":
        path = rest[1]
        authdb = rest[2] if len(rest) > 2 else "admin"
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            u, p = line.split(":", 1)
            if try_creds(host, port, u, p, authdb):
                return 0
        print("NO_HIT")
        return 0

    user = rest[0]
    password = rest[1] if len(rest) > 1 else ""
    authdb = rest[2] if len(rest) > 2 else "admin"
    try_creds(host, port, user, password, authdb)
    return 0


if __name__ == "__main__":
    sys.exit(main())
