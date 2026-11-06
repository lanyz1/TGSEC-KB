#!/usr/bin/env python3
"""
WS client template for Cocos 'tw'-style gambling platforms.
Adapt the CONFIG block per target (keys/cmd numbers recovered from the client bundle).

Envelope : {"cmd": int, "jsonStr": b64(iv12 + AESGCM(ct+tag))}
Auth     : HMAC_SHA256(AUTH_SECRET, f"{APP_ID}\n{ts_ms}\n{nonce}")
Login    : RegistClient cmd, sign = md5("machineCode=..&userName=..&wxOpenID=..&sjOpenID=..&password=<REDACTED>")
"""
import asyncio, base64, hashlib, hmac, json, os, time, uuid
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import websockets

# ---------------- CONFIG (edit per target) ----------------
WS_URL      = "wss://tyyl-ws-notcn.net/ws"
KEY         = base64.b64decode("Y29jb3MtZ2F0ZS1rZXkxIQ==")   # AES-GCM key from bundle
AUTH_SECRET = "cocos-gate-dev-auth-secret-2026"
SIGN_KEY    = "dfgrczfr343@*.88"
APP_ID      = "cocos-client"
CMD_AUTH    = 12947457   # AuthClientCmd
CMD_REGIST  = 12779521   # RegistClientCmd (login AND register)
# ----------------------------------------------------------


def md5h(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


class TwClient:
    def __init__(self):
        self.ws = None
        self.aes = AESGCM(KEY)
        self.mc = os.urandom(16).hex()      # machineCode (any hex works in this family)
        self.client_ip = "127.0.0.1"        # put your real egress IP if the server checks it

    def enc(self, obj):
        iv = os.urandom(12)
        ct = self.aes.encrypt(iv, json.dumps(obj, separators=(',', ':')).encode(), None)
        return base64.b64encode(iv + ct).decode()

    def dec(self, b64):
        raw = base64.b64decode(b64)
        return json.loads(self.aes.decrypt(raw[:12], raw[12:], None))

    async def connect(self):
        self.ws = await websockets.connect(WS_URL, max_size=2**22)
        ts = int(time.time() * 1000)
        nonce = str(uuid.uuid4())
        sig = hmac.new(AUTH_SECRET.encode(), f"{APP_ID}\n{ts}\n{nonce}".encode(), hashlib.sha256).hexdigest()
        await self.send(CMD_AUTH, {"appId": APP_ID, "timestamp": ts, "nonce": nonce, "sign": sig})
        for _ in range(5):                  # expect AuthServer reply with sessionId
            _c, b = await self.recv_one()
            if isinstance(b, dict) and "sessionId" in b:
                break
        return self

    async def send(self, cmd, body):
        await self.ws.send(json.dumps({"cmd": cmd, "jsonStr": self.enc(body)}))

    async def recv_one(self, timeout=10):
        raw = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
        m = json.loads(raw)
        return m["cmd"], self.dec(m["jsonStr"])

    async def drain(self, timeout=3, maxn=50):
        out = []
        try:
            while len(out) < maxn:
                out.append(await self.recv_one(timeout))
        except asyncio.TimeoutError:
            pass
        return out

    async def login(self, sj="", password="", wx="", user_name=""):
        """Email/account login: account goes in sjOpenID. TG login: sj="", wx="<openid>xklm1216" (suffix per platform)."""
        pwd = md5h(password) if password else ""
        sign = md5h(
            f"machineCode={self.mc}&userName={user_name}&wxOpenID={wx}&sjOpenID={sj}&password={pwd}&key={SIGN_KEY}"
        )
        body = {
            "isReconnection": 0, "isRegister": False, "sign": sign,
            "clientIP": self.client_ip, "machineCode": self.mc, "sjOpenID": sj,
            "headImageUrl": "", "wxOpenID": wx, "iTargetPlatfrom": 1,
            "verifyCode": "", "password": pwd, "countryCode": "", "userName": user_name,
        }
        await self.send(CMD_REGIST, body)
        _c, b = await self.recv_one()
        return b  # b["ik"][0] == 0 => success

    async def close(self):
        try:
            await self.ws.close()
        except Exception:
            pass


async def kill_switch_scan(cands, good_cmd, good_resp_cmd, login_kwargs):
    """One candidate per FRESH connection; classify kill vs alive via liveness probe.
    kill = command EXISTS but params invalid; silent drop = command absent."""
    kills = []
    for c in cands:
        cli = await TwClient().connect()
        try:
            await cli.login(**login_kwargs)
            await cli.drain(1.5)
            await cli.send(c, {})
            await asyncio.sleep(1.0)
            await cli.send(good_cmd, {})        # liveness probe with a known-good cmd
            alive = False
            try:
                for _ in range(6):
                    rc, _rb = await cli.recv_one(timeout=1.2)
                    if rc == good_resp_cmd:
                        alive = True
                        break
            except Exception:
                pass
            if not alive:
                kills.append(c)
        except Exception:
            kills.append(c)
        finally:
            await cli.close()
    return kills


if __name__ == "__main__":
    async def demo():
        cli = await TwClient().connect()
        resp = await cli.login(sj="<EMAIL-REDACTED>", password="<REDACTED>")
        print("login ik:", resp.get("ik", [None])[0], "player:", resp.get("playerIndex"))
        await cli.close()
    asyncio.run(demo())
