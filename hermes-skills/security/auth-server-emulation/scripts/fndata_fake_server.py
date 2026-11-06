#!/usr/bin/env python3
"""
fndata 本地模拟验证服务器 — 配合公钥替换 patch
原理:
  1. main.dll 的 RSA 公钥已被替换为我们的公钥
  2. 客户端请求: {"a": RSA加密(AES密钥), "b": AES-CBC加密(JSON)}
  3. 本服务器用私钥解出 AES 密钥 → 解密请求体
  4. 伪造"登录成功 + VipTime 远期"响应,用 AES 密钥加密返回
用法:
  python fndata_fake_server.py
  (监听 0.0.0.0:18888,配合 Frida 重定向或修改 hosts)
"""
import base64
import hashlib
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad, unpad

PRIV = RSA.import_key(open(r'C:\Users\Administrator\AppData\Local\Temp\my_priv.pem', 'rb').read())

# 远期 VipTime (2099-01-01) 秒
FAR_FUTURE = 4070908800
FAR_FUTURE_STR = "2099-01-01 00:00:00"


def rsa_decrypt(data: bytes) -> bytes:
    cipher = PKCS1_v1_5.new(PRIV)
    return cipher.decrypt(data, None)


def aes_decrypt(enc: bytes, key: bytes) -> bytes:
    iv = key[:16]
    c = AES.new(key, AES.MODE_CBC, iv=iv)
    return unpad(c.decrypt(enc), AES.block_size)


def aes_encrypt(plain: bytes, key: bytes) -> bytes:
    iv = key[:16]
    c = AES.new(key, AES.MODE_CBC, iv=iv)
    return c.encrypt(pad(plain, AES.block_size))


def md5hex(b: bytes) -> str:
    return hashlib.md5(b).hexdigest().upper()


def build_response(req_json: dict) -> dict:
    """根据请求构造伪造的成功响应(明文 JSON,调用方负责加密)"""
    fn = req_json.get('fnobj', req_json.get('func', ''))

    if 'Login' in fn or 'login' in fn:
        return {
            "Status": 1,
            "Msg": "登录成功",
            "User": req_json.get('User', req_json.get('username', 'testuser2026')),
            "Key": "FAKEKEY123456",
            "LoginIp": "127.0.0.1",
            "LoginTime": int(time.time()),
            "OutUser": req_json.get('User', 'testuser2026'),
            "RegisterTime": int(time.time()),
            "UserClassMark": 1,
            "UserClassName": "普通版",
            "VipNumber": 9999.0,
            "VipTime": FAR_FUTURE,
            "NewAppUser": False,
            "Token": "FAKETOKEN1234567890",
        }
    elif 'Heart' in fn or 'heart' in fn:
        return {
            "Status": 1,
            "Msg": "心跳成功",
            "UserClassMark": 1,
            "UserClassName": "普通版",
            "VipTime": FAR_FUTURE,
            "VipNumber": 9999.0,
            "Token": "FAKETOKEN1234567890",
        }
    elif 'GongGao' in fn or 'Notice' in fn:
        return {"Status": 1, "Msg": "成功", "Data": "欢迎使用", "Content": "测试公告"}
    elif 'GetAppUserInfo' in fn or 'UserInfo' in fn:
        return {
            "Status": 1, "Msg": "成功",
            "User": "testuser2026",
            "UserClassMark": 1,
            "UserClassName": "普通版",
            "VipTime": FAR_FUTURE,
            "VipNumber": 9999.0,
        }
    elif 'LogOut' in fn or 'logout' in fn:
        return {"Status": 1, "Msg": "登出成功"}
    else:
        return {"Status": 1, "Msg": "成功"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        self.do_POST()

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length) if length else b'{}'
            req = json.loads(body)

            # 解密请求
            aes_key_b64 = req.get('a', '')
            enc_body_b64 = req.get('b', '')
            aes_key = rsa_decrypt(base64.b64decode(aes_key_b64))
            plain = aes_decrypt(base64.b64decode(enc_body_b64), aes_key)
            req_json = json.loads(plain)

            print(f"[REQ] {self.path} fnobj={req_json.get('fnobj', '?')}")

            # 构造响应
            resp_json = build_response(req_json)
            resp_plain = json.dumps(resp_json, separators=(',', ':')).encode()
            enc_resp = aes_encrypt(resp_plain, aes_key)
            resp = {
                "a": base64.b64encode(enc_resp).decode(),
                "b": md5hex(resp_plain),
            }
            out = json.dumps(resp).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
            self.send_header('Content-Length', str(len(out)))
            self.end_headers()
            self.wfile.write(out)
        except Exception as e:
            print(f"[ERR] {e}")
            err = json.dumps({"Status": 106, "Msg": f"模拟服务器错误: {e}"}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(err)))
            self.end_headers()
            self.wfile.write(err)


if __name__ == '__main__':
    print("=== fndata 模拟验证服务器 ===")
    print(f"私钥: {PRIV.size_in_bits()} bits")
    print(f"伪造 VipTime: {FAR_FUTURE_STR} (2099年)")
    print("监听 0.0.0.0:18888 ...")
    srv = HTTPServer(('0.0.0.0', 18888), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
