# BASH 百人梭哈 — Auto-bet Tampermonkey Script (correct 28-card mapping)

## Correct Card Mapping

```javascript
// 28-card deck: 8,9,10,J,Q,K,A × 4 suits
// Numbers 1-28:
//   1-7:  ♦8→♦A (suit 0)
//   8-14: ♣8→♣A (suit 1)
//  15-21: ♥8→♥A (suit 2)
//  22-28: ♠8→♠A (suit 3)

function toCard(n) {
    n = parseInt(n);
    if (n < 1 || n > 28) return null;
    var rank = (n - 1) % 7;      // 0=8, 1=9, 2=10, 3=J, 4=Q, 5=K, 6=A
    var suit = Math.floor((n - 1) / 7); // 0=♦, 1=♣, 2=♥, 3=♠
    return { rank: rank, suit: suit, name: RANK[rank] + SUIT[suit] };
}
```

## Key Script Elements

### Monitoring roundNo
```javascript
var lis = document.querySelectorAll('.roundNo li');
if (lis.length >= 20) {
    var data = Array.from(lis).slice(0,20).map(function(l){return l.textContent.trim()}).join(',');
    // data is 20 comma-separated numbers = 5 cards × 4 players
    // BUT: this data is from the PREVIOUS round! Not usable for current round.
}
```

### Detecting submit availability
```javascript
var sb = document.querySelector('.submit');
if (sb && !sb.disabled) { /* can bet */ }
```

### Click betting (UI simulation)
```javascript
// 1. Select amount
document.querySelector('.cm10')?.click();  // ¥10
// 2. Click player area (player 1-4 = area00, area01, area10, area11)
document.getElementById('area00')?.click();
// 3. Submit
setTimeout(function() {
    document.querySelector('.submit')?.click();
}, 100);
```

## Verified Conclusions

- **preNumber** (getPreNumber API or `s.shNumber.preNumber`): Returns 16 numbers (4/player) — only visible cards
- **roundNo** (DOM element `.roundNo li`): Returns 20 numbers (5/player) but is from **previous round**
- **5th (face-down) card**: Does NOT exist in any pre-draw data source. Empty `<div class="card back shBack">` in DOM.
- **BASH betSingle API**: Not fully tested (format unknown for SH games)
- **Time window**: roundNo data appears during 派奖中 after submit is 🔒. Data carries over into next 投注中 but is stale.
