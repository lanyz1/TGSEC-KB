# BFCP Platform Attack Assessment — Session 2026-07-21

## Platform
- URL: `anndgbzg-368bfcom.xyz:6524`
- Games tested: BASH (百人梭哈), OG1K3 (1分快3)
- Framework: Vue 3 + Pinia + Vite

## Corrected Card Mapping (BASH 28-card deck)

After 3 failed attempts, the correct mapping was verified against actual webpage display:

```
n1-7:  ♦8(1), ♦9(2), ♦10(3), ♦J(4), ♦Q(5), ♦K(6), ♦A(7)
n8-14: ♣8(8), ♣9(9), ♣10(10), ♣J(11), ♣Q(12), ♣K(13), ♣A(14)
n15-21:♥8(15),♥9(16),♥10(17),♥J(18),♥Q(19),♥K(20),♥A(21)
n22-28:♠8(22),♠9(23),♠10(24),♠J(25),♠Q(26),♠K(27),♠A(28)
```

**Formula:** `rank = (n-1) % 7` (0=8,1=9,2=10,3=J,4=Q,5=K,6=A), `suit = Math.floor((n-1) / 7)` (0=♦,1=♣,2=♥,3=♠)

## Data Sources Verified

| Source | Timing | Contains |
|--------|--------|----------|
| `getPreNumber` API | Entire betting phase | 4 cards/player (16 nums) ✅ matches webpage |
| `LotteryResults.BASH.results` | Post-draw only | Full 20 cards + winner + hand types |
| `roundNo` DOM element | Appears at 3s remaining | 20 numbers = PREVIOUS round ❌ |
| `shNumber` Pinia state | Entire betting phase | Same as getPreNumber (16 nums) |
| 5th card (face-down) | Only at draw time | Not in preNumber, not in Vue state, empty `<div>` in DOM |

## Attack Vectors — All Failed

| Attack | Why Failed |
|--------|-----------|
| Read 5th card from preNumber | API only returns 4 cards. 5th card generated server-side at draw time |
| ClientTime manipulation | Server validates issue status (open/closed), not client timestamp |
| CancelBet race condition | Bet locks instantly on draw. `cancelBill: false` after result |
| roundNo DOM pre-read | Data is from previous round, not current |
| Any other A-class game (百家乐/龙虎) | `getPreNumber` returned "取得浮动赔率失败" |

## Timing Timeline (verified)

```
T+0s     → 投注中, submit ✅, counter 39s
T+35s    → 投注中, counter 4s
T+38s    → 停止下注, submit 🔒
T+41s    → 派奖中, roundNo data appears (20 numbers — previous round)
T+43-45s → 洗牌中→发牌中
T+46s    → 新局投注中, counter 39s
```

## K3 (快3) Assessment

- OG1K3: results in `LotteryResults.OG1K3.results` but only post-draw
- No preNumber available (B-class game)
- Same timing limitations: draw happens after close
- Bet API format confirmed: accountId as NUMBER, "times" as STRING, playId is REQUIRED (not empty []), gzip compression required

### BetSingle Format (OG1K3)

```json
{
  "accountId": 1022198162,
  "clientTime": 1784673393892,
  "gameId": "OG1K3",
  "issue": "20260722397",
  "item": ["{\"methodid\":\"K3002001001\",\"nums\":1,\"rebate\":\"0.00\",\"times\":\"1\",\"money\":1,\"mode\":1,\"issueNo\":\"20260722397\",\"codes\":\"大\",\"playId\":[\"K3002001010\"]}"]
}
```

Key format points:
- `accountId` is NUMBER, not string
- `times` is STRING, not number
- `playId` is required array with specific value — NOT empty array
- `money` is NUMBER, not string
- Body must be gzip-compressed (not zlib) for non-skip-list endpoints

## Session 2026-07-21 (Night 2) — Correction of Card Mapping & New Games Tested

### Critical Correction
The card mapping was WRONG for 7+ hours. Correct formula:
- **rank = (n-1) % 7** (0=8, 1=9, 2=10, 3=J, 4=Q, 5=K, 6=A)
- **suit = Math.floor((n-1) / 7)** (0=♦, 1=♣, 2=♥, 3=♠)
- Do NOT use 4-cards-per-suit mapping (rank%4, suit/4). This is wrong for 28-card decks.

### New Games Tested (all failed)

| Game | URL | PreNumber |
|------|-----|-----------|
| OGDT (龙虎斗) | `/lottery/DT/OGDT` | ❌ "取得浮动赔率失败" |
| OGBJL (百家乐) | `/lottery/BJL/OGBJL` | ❌ "取得浮动赔率失败" |
| OGNN (牛牛) | `/lottery/NN/OGNN` | ❌ "取得浮动赔率失败" |

### WebSocket Discovery
Platform has WebSocket at `wss://*.wtljlzfwodiz.com/vap/websocket/{uuid}` — but this is for **chat/meeline only**, not game data. No game result data flows through WebSocket.

### getLotteryOpen API
Returns error for most games: `"开奖号码不支援自主彩种和官彩号码查询"` — cannot pre-fetch current issue results.

### Timing Verification (precise)
- roundNo appears at **派奖中** phase (约T+41s), submit already 🔒
- roundNo data CARRIES OVER to next 投注中 phase — same data, but it's from previous round
- Submit button goes 🔒 at counter 1s→0s, but stays disabled through 停止下注→派奖中→洗牌中→发牌中
- Submit re-enables at next 投注中 counter ~39s

### Confirmed Valid Defenses
1. **5th card**: Generated server-side at draw time — not in API, not in DOM, not in Vue state. DOM has empty `<div class="card back shBack">`
2. **Issue status**: Server validates issue is open for betting, not clientTime
3. **Cancel window**: Cancel locks instantly when draw result is posted
4. **No pre-rolled results**: draw happens at server-side, no pre-determination exposed
