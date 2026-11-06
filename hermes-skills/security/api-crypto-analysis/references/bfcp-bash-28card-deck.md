# BASH (百人梭哈) 28-Card Deck Analysis

**Date**: July 23, 2026
**Platform**: BFCP (anndgbzg-368bfcom.xyz:6524)
**Game URL**: `/lottery/SH/BASH`

## Setup

**Cookies required for ALL API calls** (openresty returns 402 without all three):
```
__uuid=1e258a3145014df29489210a09abfc46
JSESSIONID=D7844A8C67094402A561A402EE31B3F2
token=<auth-token>
```

**Required headers:**
```
user-uuid: <same as __uuid>
x-build-info: 2026-06-23T01:14:29.612Z
```

**Referer**: `https://anndgbzg-368bfcom.xyz:6524/lottery/SH/BASH`

## 28-Card Custom Numbering

The game uses only 7 ranks × 4 suits = 28 cards, numbered 1-28:

| Number | Card | r_idx | suit |
|--------|------|-------|------|
| 01 | 8♠ | 0 | 0 |
| 02 | 8♥ | 0 | 1 |
| 03 | 8♣ | 0 | 2 |
| 04 | 8♦ | 0 | 3 |
| 05 | 9♠ | 1 | 0 |
| 06 | 9♥ | 1 | 1 |
| 07 | 9♣ | 1 | 2 |
| 08 | 9♦ | 1 | 3 |
| 09 | 10♠ | 2 | 0 |
| 10 | 10♥ | 2 | 1 |
| 11 | 10♣ | 2 | 2 |
| 12 | 10♦ | 2 | 3 |
| 13 | J♠ | 3 | 0 |
| 14 | J♥ | 3 | 1 |
| 15 | J♣ | 3 | 2 |
| 16 | J♦ | 3 | 3 |
| 17 | Q♠ | 4 | 0 |
| 18 | Q♥ | 4 | 1 |
| 19 | Q♣ | 4 | 2 |
| 20 | Q♦ | 4 | 3 |
| 21 | K♠ | 5 | 0 |
| 22 | K♥ | 5 | 1 |
| 23 | K♣ | 5 | 2 |
| 24 | K♦ | 5 | 3 |
| 25 | A♠ | 6 | 0 |
| 26 | A♥ | 6 | 1 |
| 27 | A♣ | 6 | 2 |
| 28 | A♦ | 6 | 3 |

Python conversion:
```python
RANK = {0:'8', 1:'9', 2:'10', 3:'J', 4:'Q', 5:'K', 6:'A'}
SUIT = {0:'♠', 1:'♥', 2:'♣', 3:'♦'}

def to_card(n):
    r_idx = (int(n)-1)//4  # 0=8, 1=9, 2=10, 3=J, 4=Q, 5=K, 6=A
    suit = (int(n)-1)%4     # 0=♠, 1=♥, 2=♣, 3=♦
    return f"{RANK[r_idx]}{SUIT[suit]}"
```

## PreNumber Structure

`getPreNumber` returns 16 comma-separated numbers: 4 revealed cards × 4 players.

Order: `P1c1,P1c2,P1c3,P1c4, P2c1,P2c2,P2c3,P2c4, P3c1,...`

The 1st card per player (out of 5) is **hidden** (face-down). Only the last 4 cards are visible during betting.

Example response:
```json
{
  "code": "success",
  "data": {
    "issue": "20260722381",
    "preNumber": "20,18,06,12,03,09,07,13,16,05,15,22,17,04,01,14",
    "odds": {
      "odds": [
        {"playCode": "SH001001001", "bonus": "1.54"},
        {"playCode": "SH001001002", "bonus": "13"},
        {"playCode": "SH001001003", "bonus": "3.44"},
        {"playCode": "SH001001004", "bonus": "19.55"}
      ]
    }
  }
}
```

## Hand Ranking (梭哈 rules)

1. 同花顺 (Straight Flush) — 5 cards same suit AND consecutive rank
2. 四条 (Four of a Kind) — 4 same rank
3. 葫芦 (Full House) — 3+2
4. 同花 (Flush) — 5 same suit
5. 顺子 (Straight) — 5 consecutive ranks
6. 三条 (Three of a Kind) — 3 same rank
7. 两对 (Two Pair)
8. 对子 (One Pair)
9. 散牌 (High Card)

Suit tiebreaker: ♠(3) > ♥(2) > ♣(1) > ♦(0)

## Issue Number

The current betting issue is NOT always `getLotteryOpenNewestGame.issueNo`. For BASH, the current betting issue can be calculated as `last_results_issue + 1`, but even with matching issue numbers, the `getPreNumber` data may not match the webpage display (possibly due to multi-table instances).

## Key Lessons Learned

1. **Copy-as-cURL from Network tab is the most reliable debugging tool** — compare byte-by-byte with your Python output
2. **Referer header reveals actual game code** — user was on `/lottery/SH/BASH` not `BLSH`
3. **Custom card numbering ≠ standard 52-card deck** — always verify by matching odds/bonus values to hand strength
4. **Gzip compression varies by endpoint** — test plain JSON first, fall back to gzip
5. **Windows curl needs `--data-raw`** for exact body matching, and `-w \n%{http_code}` for status
6. **UTF-8 decode errors on Windows** — use `subprocess.run(cmd, capture_output=True)` then `.decode('utf-8', errors='replace')` instead of `text=True`
