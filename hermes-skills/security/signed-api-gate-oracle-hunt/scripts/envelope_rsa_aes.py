#!/usr/bin/env python3
"""RSA-wrapped AES request envelope: build + parse (sign/encrypt-gated admin APIs).

Pattern (server-issued rotating key -- no hardcoded secret):
    GET  <base>/webv1/Common/GetRsaPublicKey  -> {"KeyId":"...","PublicKey":"<RSA PEM>"}
    POST <endpoint>   body = {"keyId":.., "encryptKey":.., "encryptData":..}
        key = 32B random, iv = 16B random
        encryptKey  = RSA-PKCS1v15(pub, json{"key":b64(k),"iv":b64(iv)}) -> b64
        encryptData = AES-256-CBC(json(body), k, iv, PKCS7)              -> b64
    response: usually AES-256-CBC with the SAME key/iv (strip padding), else plaintext JSON.

The two local gotchas this encodes (both look like "wrong algorithm", they are not):
    1. Python `cryptography` CBC does NOT auto-pad -> pkcs7_pad() is mandatory,
       otherwise: "The length of the provided data is not a multiple of the block length".
    2. Strip padding BEFORE json.loads() -> otherwise trailing control bytes give
       "JSONDecodeError: Extra data", which reads like "the envelope is wrong".

Verify the whole thing offline first:
    python3 envelope_rsa_aes.py --selftest

Usage:
    pk, kid = get_pubkey("https://admin.example.com/api/webv1/Common/GetRsaPublicKey")
    env     = build_envelope(pk, kid, {"email": "a@b.c", "pwd": "x"})
    # POST json=strip_meta(env) -> then:
    out     = decode_response(resp_text, env["_key"], env["_iv"])
"""
import base64
import json
import os
import sys

BLOCK = 16


# ---------------------------------------------------------------- padding ----
def pkcs7_pad(d: bytes, block: int = BLOCK) -> bytes:
    n = block - len(d) % block
    return d + bytes([n]) * n


def pkcs7_unpad(d: bytes, block: int = BLOCK) -> bytes:
    if not d:
        return d
    n = d[-1]
    if 1 <= n <= block and d[-n:] == bytes([n]) * n:
        return d[:-n]
    return d  # already unpadded / plaintext -> hand back as-is


# ------------------------------------------------------------ aes backends ----
def _aes_cbc(key: bytes, iv: bytes, data: bytes, encrypt: bool) -> bytes:
    try:  # primary: cryptography
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        c = Cipher(algorithms.AES(key), modes.CBC(iv))
        op = c.encryptor() if encrypt else c.decryptor()
        return op.update(data) + op.finalize()
    except ImportError:
        pass
    from Crypto.Cipher import AES  # fallback: pycryptodome
    c = AES.new(key, AES.MODE_CBC, iv)
    return c.encrypt(data) if encrypt else c.decrypt(data)


def rsa_encrypt(pub_pem, data: bytes) -> bytes:
    if isinstance(pub_pem, str):
        pub_pem = pub_pem.encode()
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        pub = serialization.load_pem_public_key(pub_pem)
        return pub.encrypt(data, padding.PKCS1v15())
    except ImportError:
        pass
    from Crypto.Cipher import PKCS1_v1_5  # fallback: pycryptodome
    from Crypto.PublicKey import RSA
    return PKCS1_v1_5.new(RSA.import_key(pub_pem)).encrypt(data)


def b64e(b: bytes) -> str:
    return base64.b64encode(b).decode()


def b64d(s: str) -> bytes:
    return base64.b64decode(s + "=" * (-len(s) % 4))


# ------------------------------------------------------------- envelope -------
def build_envelope(pub_pem, key_id: str, body: dict, key=None, iv=None) -> dict:
    """Returns the wire envelope plus local-private h[_key]/h[_iv] for decoding."""
    key = key or os.urandom(32)
    iv = iv or os.urandom(16)
    env = {
        "keyId": key_id,
        "encryptKey": b64e(rsa_encrypt(pub_pem, json.dumps(
            {"key": b64e(key), "iv": b64e(iv)}).encode())),
        "encryptData": b64e(_aes_cbc(key, iv, pkcs7_pad(
            json.dumps(body, separators=(",", ":")).encode()), True)),
    }
    env["_key"], env["_iv"] = key, iv
    return env


def strip_meta(env: dict) -> dict:
    """Drop the local-private _key/_iv before POSTing."""
    return {k: v for k, v in env.items() if not k.startswith("_")}


def decode_response(resp, key: bytes, iv: bytes):
    """Plaintext JSON pass-through first, then same-key AES-CBC. Returns dict/str."""
    if isinstance(resp, dict):
        return resp
    if isinstance(resp, (bytes, bytearray)):
        resp = resp.decode("utf-8", "replace")
    resp = resp.strip()
    try:
        return json.loads(resp)
    except Exception:
        pass
    try:
        return json.loads(pkcs7_unpad(_aes_cbc(key, iv, b64d(resp), False)))
    except Exception:
        return resp


def get_pubkey(url: str, timeout: int = 20):
    """Unauthenticated key endpoint -> (pem_str, key_id). Adapt the field names."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        j = json.loads(r.read().decode("utf-8", "replace"))
    res = j.get("ResData", j)
    pem = res.get("pubKey") or res.get("publicKey") or res.get("PublicKey")
    kid = res.get("keyId") or res.get("KeyId")
    if pem and "BEGIN" not in pem:
        pem = "-----BEGIN PUBLIC KEY-----\n" + pem + "\n-----END PUBLIC KEY-----"
    return pem, kid


# ------------------------------------------------------------------ selftest ---
def _selftest() -> int:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode()

    body = {"email": "a@b.c", "pwd": "pw", "appID": "1", "language": "en"}
    env = build_envelope(pem, "kid-1", body)
    wire = strip_meta(env)
    assert set(wire) == {"keyId", "encryptKey", "encryptData"}, wire.keys()

    # server side: RSA-unwrap key/iv, AES-decrypt body
    from cryptography.hazmat.primitives.asymmetric import padding as _pad
    kv = json.loads(priv.decrypt(b64d(wire["encryptKey"]), _pad.PKCS1v15()))
    got = json.loads(pkcs7_unpad(_aes_cbc(b64d(kv["key"]), b64d(kv["iv"]),
                                         b64d(wire["encryptData"]), False)))
    assert got == body, got

    # response path: plaintext and encrypted-with-same-key both must parse
    assert decode_response('{"ErrCode":"4009"}', env["_key"], env["_iv"]) == {"ErrCode": "4009"}
    ct = b64e(_aes_cbc(env["_key"], env["_iv"], pkcs7_pad(b'{"a":1}'), True))
    assert decode_response(ct, env["_key"], env["_iv"]) == {"a": 1}
    print("SELFTEST_OK")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else
             (print(__doc__) or 0))
