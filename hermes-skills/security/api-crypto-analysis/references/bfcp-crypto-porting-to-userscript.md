# BFCP MD5-Based Crypto + Tampermonkey Porting Case Study

**Date**: July 21-22, 2026
**Platform**: 必发彩票 BFCP (anndgbzg-368bfcom.xyz:6524)
**Frontend**: Vue 3 + Vite + Element Plus + Pinia
**Backend**: OpenResty + Tomcat 8.0.36

## Discovery Chain

### 1. Encryption Code Location

The MD5-based encryption was found in `assets/services-k0yFuL9w.js` (373KB), the main API service layer of the Vue 3 SPA. Keys are hardcoded as arrays:

```javascript
const wi = {
  iKey: ["c4d3e13a", "ec499e1b", "c2a3e9d4"],
  key:  ["f47d121e", "c82e389f", "62a341e2"],
  // ...
}
```

The 3 keys are used for login-specific extra encryption (nFrontKey headers + SECRET_KEY body field). Non-login API calls only need the standard encryKey/encryValue.

### 2. Encryption Flow (VERIFIED against browser Network tab)

```python
import hashlib, time, random

HOSTNAME = "anndgbzg-368bfcom.xyz"  # NO port

def gen_encry_key():
    return str(int(time.time() * 1000)) + str(random.randint(0, 10**15-1))

def Si(s):
    return s.replace('2', 'B').replace('7', 'G')

def encry_value(action, ek):
    action_path = f"/tools/_ajax/{action}"
    return hashlib.md5((HOSTNAME + action_path + Si(ek)).encode()).hexdigest()
```

### 3. API Request Format (VERIFIED)

```json
POST /tools/_ajax/<Action>
Content-Type: application/json
Cookie: __uuid=<uuid>; JSESSIONID=<session>; token=<auth-token>
user-uuid: <same-uuid>
x-build-info: 2026-06-23T01:14:29.612Z

{
    "encryKey": "<timestamp><random15>",
    "encryValue": "<32-char MD5 hash>",
    ...action-specific parameters...
}
```

### 4. Critical Findings

| Finding | Detail |
|---------|--------|
| Cookies required | `__uuid`, `JSESSIONID`, `token` — all three or openresty 402 |
| Headers required | `user-uuid` (match __uuid), `x-build-info` (from window.buildInfo.t) |
| No compression | Plain JSON works despite JS showing pako.deflate() |
| Response format | JSON string containing base64(gzip) data |
| Gzip NOT zlib | Decompress with `zlib.decompress(raw, zlib.MAX_WBITS | 16)` |

### 5. Public vs Protected APIs

| Category | Examples | Auth Required |
|----------|----------|--------------|
| Public | getSiteInitData, getNewestBonusList, getLotteryOpenNewestGame, getServerTimeMillisecond | No |
| Login | login, captchaGet, guestRegister | Encryption + extra headers |
| User | getUserBanlance, getBetting | Login session required |
| Game | getPreNumber, getLotteryPlan | Login session required |

### 6. Porting to Tampermonkey JavaScript

```javascript
function md5(s) { /* standard JS MD5 implementation */ }

var HOSTNAME = location.hostname;
var UUID = "1e258a3145014df29489210a09abfc46";  // from __uuid cookie

function encryKey() {
    return Date.now() + '' + Math.floor(Math.random() * 1e15);
}
function Si(s) {
    return s.replace(/2/g, 'B').replace(/7/g, 'G');
}
function encryValue(action, ek) {
    return md5(HOSTNAME + '/tools/_ajax/' + action + Si(ek));
}

function bfcpApi(action, data) {
    var ek = encryKey();
    var ev = encryValue(action, ek);
    return fetch('/tools/_ajax/' + action, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'user-uuid': UUID,
            'x-build-info': '2026-06-23T01:14:29.612Z'
        },
        body: JSON.stringify(Object.assign({
            encryKey: ek, encryValue: ev
        }, data))
    }).then(function(r) { return r.json(); });
}
```

### 7. Card Value Mapping (梭哈)

For pre-dealt card games: preNumber is 16 comma-separated numbers (4 players x 4 cards).

```python
for c in preNumber.split(","):
    n = (int(c)-1) % 13 + 1   # 1=A, 2-13=2-K
    n = 14 if n == 1 else n    # A is HIGH in 梭哈
    s = (int(c)-1) // 13       # 0=♠, 1=♥, 2=♣, 3=♦
    val_names = {14:'A',2:'2',3:'3',4:'4',5:'5',6:'6',7:'7',
                 8:'8',9:'9',10:'10',11:'J',12:'Q',13:'K'}
    suit_names = {0:'♠',1:'♥',2:'♣',3:'♦'}
```

### 8. Game Code Mapping

```python
GAME_CODES = {
    'SH': 'BLSH', 'TH': 'BLTH', 'SLM': 'OGSLM',
    'NN': 'OGNN', 'DT': 'OGDT', 'RB': 'OGRB',
    'BJL': 'OGBJL', 'GF': 'OGGF',
}
```

### 9. Observed Limitations

- **getPreNumber may not match webpage**: Even with matching issue number, the preNumber data from the API may show different cards than the user's browser. Possible causes: multiple game tables/rooms, WebSocket-sourced data overriding API response, or preNumber being for a different game instance.
- **Issue number mismatch**: `getLotteryOpenNewestGame` returns the last completed game's issue, while the webpage shows the current betting issue. These can differ even for sequential 30-second games.
- **SSL in Python**: Direct requests from Python via `requests` fail with SSL errors through SOCKS5 proxy. curl with `-k` works. Workaround: use curl via subprocess.
