import asyncio, re, json, time, requests, sys
from urllib.parse import urlparse, unquote
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestMainWebViewRequest
from telethon.tl.types import InputUser

# 用法: python tg_oauth_confirm.py <session> <api_id> <api_hash> <shop_tg_login_url> <proxy>
# shop_tg_login_url 例: https://acc911.com/tg-login (需返回 302 到 oauth.telegram.org)
SESSION, API_ID, API_HASH, SHOP, PROXY = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]

s = requests.Session()
s.headers.update({"User-Agent":"curl/8.5.0"})
if PROXY != "-":
    s.proxies = {"http":"http://"+PROXY, "https":"http://"+PROXY}

r = s.get(SHOP, verify=False, timeout=15, allow_redirects=False)
oauth_url = r.headers.get("location")
q = urlparse(oauth_url).query
so = requests.Session(); so.headers.update({"User-Agent":"Mozilla/5.0 Chrome/120"})
so.get(oauth_url, verify=False, timeout=20)
pq = so.get("https://oauth.telegram.org/auth/auth?"+q+"&force_qr=1", verify=False, timeout=20)
qtoken = re.search(r"setToken\('([^']+)'\)", pq.text).group(1)
print("qtoken", qtoken, flush=True)

async def wv(qt):
    c = TelegramClient(SESSION, API_ID, API_HASH); await c.connect()
    try:
        e = await c.get_entity("oauth")
        bu = InputUser(user_id=e.id, access_hash=e.access_hash)
        peer = await c.get_input_entity(e)
        res = await c(RequestMainWebViewRequest(peer=peer, bot=bu, platform="android", start_param=qt))
        return res.url
    finally:
        await c.disconnect()

wurl = asyncio.run(wv(qtoken))
initdata = unquote(re.search(r"tgWebAppData=([^&]+)", wurl.split("#",1)[1]).group(1))
t = requests.Session()
t.headers.update({"User-Agent":"Mozilla/5.0 (Linux; Android 13) Chrome/120","X-Requested-With":"XMLHttpRequest",
                  "Origin":"https://webappinternal.telegram.org","Referer":"https://webappinternal.telegram.org/oauth?tgWebAppStartParam="+qtoken})
t.get("https://webappinternal.telegram.org/oauth?tgWebAppStartParam="+qtoken, verify=False, timeout=20)
ra = t.post("https://webappinternal.telegram.org/oauth/api?hash=", data={"method":"auth","_auth":initdata}, verify=False, timeout=15)
api = ra.json().get("api_url")
print("auth", ra.text[:120], flush=True)
rc = t.post("https://webappinternal.telegram.org"+api, data={"method":"confirm","qtoken":qtoken,
            "accept_allow_phone":"false","accept_allow_write":"true"}, verify=False, timeout=15)
print("confirm", rc.status_code, rc.text[:120], flush=True)

for i in range(10):
    time.sleep(1)
    rp = so.post("https://oauth.telegram.org/auth/login?"+q+"&qtoken="+qtoken, data={}, verify=False, timeout=15)
    print("poll", rp.text[:150], flush=True)
    if '"confirmed"' in rp.text:
        r8 = so.get("https://oauth.telegram.org/auth/push?"+q, verify=False, timeout=15, allow_redirects=False)
        print("CALLBACK:", r8.headers.get("location"), flush=True)
        break
    if '"refresh"' in rp.text:
        print("qtoken rotated, retry"); break
