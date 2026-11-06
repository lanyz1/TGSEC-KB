# BFCP Platform Debugging Notes

## Platform
- Domain: anndgbzg-368bfcom.xyz:6524
- Stack: OpenResty, Java (Tomcat), Vue 3 + Vite + Pinia + Element Plus
- API: POST /tools/_ajax/{Action}
- Encryption: MD5(hostname + "/tools/_ajax/" + action + Si(encryKey))
  - Si(s): s.replace("2","B").replace("7","G")
  - encryKey = Date.now() + '' + Math.floor(Math.random() * 1e15)
  - encryValue = MD5(hostname + "/tools/_ajax/{Action}" + Si(encryKey))
  - Hostname = window.location.hostname (NO port), e.g., "anndgbzg-368bfcom.xyz"
- **WRONG formulas** (do NOT match server): MD5(encryKey + param + ts), MD5(key + action + ts)

## Required Headers & Cookies (OpenResty 402 Protection)
- **Cookies** (ALL required for 200 response):
  - `__uuid=<32-char-device-id>` — device UUID from cookie
  - `JSESSIONID=<session>` — server session
  - `token=<auth-token>` — user auth token from localStorage.token
- **Headers** (ALL required):
  - `user-uuid: <same-as-__uuid>` — must match __uuid cookie
  - `x-build-info: <build-timestamp>` — from window.buildInfo.t
  - `referer: <game-page-url>` — e.g. /lottery/SH/BASH
  - `origin: <base-url>` — e.g. https://anndgbzg-368bfcom.xyz:6524
- Missing any → OpenResty returns **402 Payment Required**
- Source: Verified by comparing curl output with browser Network tab copy-as-cURL
- Token: <REDACTED>
- siteId: 100047
- Live game data: WebSocket (wss://*.ruexjigbgpwl.com/vap/websocket/*), NOT HTTP
- Test account: z147258369 / qwe123456

## API Categories

### No-auth endpoints (accessible without token):
- getSiteInitData, getLotteryOpenNewestGame, getNewestBonusList
- getServerTimeMillisecond, getBetBoardList, getExtGameConfig

### Auth-required:
- User: getUserBanlance, getPersonalLevel, getBetting, cache/PersonalInfoCache
- Wallet: walletTransfer/*, yuebao*, withDraw/*
- Chat: chat/getToken, checkHasChatRoom, loginChatroom
- Betting: getPreNumber, cancelBet, {gameId}/betSingle

## getPreNumber Behavior
- Game types using getPreNumber: SH(梭哈), TH(推筒子), NN(牛牛), DT(龙虎斗), BJL(百家乐)
- Request: POST /tools/_ajax/getPreNumber {gameId, issue}
- Success response contains data.preNumber: comma-separated card numbers
- Error response: {"code":"error","data":null,"msg":"取得浮动赔率失败"}
  - Cause: wrong gameId or issue parameter, or not yet at pre-opening time

## SPA State Extraction
- Page URL pattern: /lottery/{GameType}/{GameId} e.g. /lottery/BJL/OGBJL
- Page calls getPlayerBet?gameId=OGBJL&issue=YYYYMMDDNNN&playId=BJL via XHR
- Token discovered at localStorage.token (not localStorage.user.token)

## Script Version History
- v1.0.0: Initial fetch-only interception (failed on XHR/Axios)
- v1.0.1: Added localStorage.token extraction
- v1.0.2: Added active polling + fetch interceptor for state extraction
- v1.0.3: Fixed polling to extract gameId from getPlayerBet URLs
- v1.0.4: Switched to getLotteryOpenNewestGame for issue extraction, Pinia store for gameId

## BASH (百人梭哈) — 28-Card Deck Game
- GameId: `BASH` (NOT BLSH!)
- Type: SH (梭哈)
- Deck: 28 cards — 8,9,10,J,Q,K,A × ♠♥♣♦
- Card numbering: 1-28 (custom, NOT 52-card standard)
- 5 cards/player, 1st card hidden, 4 revealed
- getPreNumber returns 16 numbers (4 revealed cards × 4 players)
- Hand rank: Straight Flush > 4K > Full House > Flush > Straight > 3K > 2Pair > Pair > High Card
- Suit order: ♠ > ♥ > ♣ > ♦ (tiebreaker)
- Response includes `odds` array with per-player bonus (lower = more likely)
- **Known discrepancy**: API data does NOT match website display for same issue — multiple instances?

## BetSingle Format (VERIFIED via Network tab capture)
- `accountId`: **number** (not string) — from `JSON.parse(localStorage.getItem("user.accountId"))`
- `item`: JSON array of JSON-**stringified** bet objects
- Inside bet object: `times` is a **string** `"1"` (not number), `playId` is array of strings
- OG1K3 (1分快3) 和值 playIds: 大=K3002001010
- Error "参数格式不正确或请求不合法": check accountId type, times type, playId format

## Gzip Body Compression
- Browser sends gzip-compressed body (header 1f 8b) for non-skip endpoints
- Python: use `gzip.compress()` NOT `zlib.compress()` (server rejects zlib format 78 9c)
- Response decompression: `zlib.decompress(data, zlib.MAX_WBITS | 16)` (gzip auto-detect)
