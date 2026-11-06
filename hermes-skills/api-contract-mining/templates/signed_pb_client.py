#!/usr/bin/env python3
"""签名 + protobuf-over-HTTP 客户端骨架（照抄改三处即可用）。

要点（踩过坑才写的）:
  * sign() 同时返回 ts/nonce/sig —— 禁止「发送端自己生成 nonce、签名却用外部算好的」这种写法，
    那会让「正确签名」用例实际不匹配，误判成「服务端不校验签名」。
  * 超时默认 8s。转发/SSRF 类端点服务端可能挂死，30s 默认值会把批量探针拖到超时。
  * 外层 code=200 只代表传输层成功，业务成败在内层消息自己的字段。

改这三处: HOST / SIGN_SECRET / 各 TCmd_* 的消息编解码。
"""
import hashlib, json, os, random, ssl, string, time, urllib.request

HOST = "https://api.example.com"
SIGN_SECRET = "<从 bundle 里抠出来的 httpSignSecret>"
TIMEOUT = 8
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

# ---------- protobuf 最小实现（不依赖 protobuf 库） ----------
def varint(n):
    if n < 0:
        n += 1 << 64
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        out += bytes([b | (0x80 if n else 0)])
        if not n:
            return out


def pb_tag(field, wt):
    return varint((field << 3) | wt)


def pb_str(field, s):
    b = s.encode() if isinstance(s, str) else s
    return pb_tag(field, 2) + varint(len(b)) + b


def pb_int(field, n):
    return pb_tag(field, 0) + varint(n)


def pb_parse(buf):
    """→ {field: value|bytes}（只做一层，嵌套按需递归调用）"""
    out, i = {}, 0
    while i < len(buf):
        tag, i = _rv(buf, i)
        field, wt = tag >> 3, tag & 7
        if wt == 0:
            v, i = _rv(buf, i)
        elif wt == 2:
            ln, i = _rv(buf, i)
            v, i = buf[i:i + ln], i + ln
        elif wt == 5:
            v, i = buf[i:i + 4], i + 4
        elif wt == 1:
            v, i = buf[i:i + 8], i + 8
        else:
            break
        out[field] = v
    return out


def _rv(buf, i):
    n, shift = 0, 0
    while True:
        b = buf[i]
        i += 1
        n |= (b & 0x7F) << shift
        if not (b & 0x80):
            return n, i
        shift += 7


# ---------- 签名：必须一起产出 ts/nonce/sig ----------
def sign(body: bytes):
    ts = str(int(time.time() * 1000))
    nonce = "".join(random.choices(string.ascii_lowercase + string.digits, k=16))
    raw = (ts + nonce).encode() + body + SIGN_SECRET.encode()
    return {
        "X-Timestamp": ts,
        "X-Nonce": nonce,
        "X-Signature": hashlib.md5(raw).hexdigest(),
    }


def call(uri: str, payload: bytes, token: str | None = None, timeout=TIMEOUT):
    """payload = 已编好的业务消息字节；返回 (http_code, raw_bytes)"""
    headers = {"Content-Type": "application/x-protobuf", **sign(payload)}
    if token:
        <REDACTED>"Authorization"] = token
    req = urllib.request.Request(HOST + uri, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def decode_common(raw: bytes):
    """信封 {code, msg, Any{type_url, value}} → (code, msg, inner_bytes)
    注意: code=200 只是传输层成功，业务成败在内层自己的字段（常见 res/result）。
    """
    env = pb_parse(raw)
    code = env.get(1)
    msg = env.get(2, b"").decode(errors="replace") if isinstance(env.get(2), bytes) else env.get(2)
    inner = b""
    a = env.get(3)
    if isinstance(a, bytes):
        any_ = pb_parse(a)
        inner = any_.get(2, b"")
    return code, msg, inner


if __name__ == "__main__":
    body = pb_int(1, 52)
    print(call("/api/guest/shopItemList", body))
