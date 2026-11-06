# Monte Carlo Probability Analysis for Incomplete-Information Card Games

## Problem

In games like 百人梭哈 (BASH), you see 4 of 5 cards per player. The 5th card is face-down and only revealed at draw time. You need to estimate each player's **win probability** with only partial information.

## Approach

### Step 1: Determine remaining deck

28 cards total. 16 are known (4 players × 4 cards). Remaining = 12 cards.

```javascript
var used = {};
known.forEach(function(p){ p.forEach(function(n){ used[n] = true; }); });
var deck = [];
for (var i = 1; i <= 28; i++) {
    if (!used[i]) deck.push(i);
}
// deck = 12 remaining cards
```

### Step 2: Monte Carlo simulation

For each trial:
1. Shuffle the 12 remaining cards
2. Deal top 4 as the 5th cards (one per player)
3. Evaluate all 4 hands (5 cards each)
4. Record which player wins (skip ties)

Repeat N times (2000-20000 trials, takes ~1-3 seconds in browser).

```javascript
var wins = [0,0,0,0];
var N = 20000;
for (var t = 0; t < N; t++) {
    var shuffled = deck.slice();
    for (var i = shuffled.length-1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i+1));
        var tmp = shuffled[i];
        shuffled[i] = shuffled[j];
        shuffled[j] = tmp;
    }
    
    var hands = [];
    for (var p = 0; p < 4; p++) {
        var cards5 = knownCards[p].concat([toCard(shuffled[p])]);
        hands.push(evaluate5(cards5));
    }
    
    var best = 0, tie = false;
    for (var p = 1; p < 4; p++) {
        if (hands[p].cmp > hands[best].cmp) {
            best = p;
            tie = false;
        } else if (hands[p].cmp === hands[best].cmp) {
            tie = true;
        }
    }
    if (!tie) wins[best]++;
}

// Win probabilities
var probs = wins.map(function(w){ return w / N; });
```

### Step 3: Calculate expected value (EV)

```javascript
// EV = probability × odds - 1
var ev = prob * odds - 1;
// If EV > 0, the bet has positive expected value
```

### Step 4: Kelly Criterion for bet sizing

```javascript
// Kelly fraction = (prob × odds - 1) / (odds - 1)
var kelly = ev > 0 ? ((prob * odds - 1) / (odds - 1)) : 0;
```

## Betting Strategies

### 1. Single EV-Max (recommended default)
Bet on the player with highest EV. Bet amount = Kelly fraction × bankroll, rounded to nearest valid chip size (¥5/¥10/¥50/¥100).

```javascript
var bet = Math.max(5, Math.min(50, Math.round(kelly * 100 / 5) * 5));
```

### 2. Hedge (two players)
If two players both have positive EV, bet ¥5 on each. If either wins, you roughly break even or profit. Reduces variance.

```javascript
// Requires: pos.length >= 2
// Bet ¥5 on each of the top 2 positive-EV players
```

### 3. Kelly allocation
Distribute total bet across all positive-EV players proportionally to their Kelly fraction.

```javascript
var totalKelly = pos.reduce(function(a,x){ return a + x.kelly; }, 0);
var alloc = pos.map(function(x){
    return { player: x.i, amount: Math.round(x.kelly / totalKelly * 20 / 5) * 5 };
});
```

### 4. Long-shot (博冷)
If a player has high odds (e.g. > 10x) AND positive EV, a small bet can yield high returns. Only do this when the probability * odds analysis shows value.

```javascript
// Trigger: odds > 10 && prob > 0.05 && ev > 0
```

## Limitations

- **4 cards = incomplete information**: The 5th card often flips results. A 40% favorite can become a 10% dog with one card.
- **Randomness assumption**: MC simulation assumes the 5th card is randomly drawn from remaining deck. If the server uses algorithmic dealing (pseudo-RNG), results may differ.
- **No edge guarantee**: EV > 0 does not guarantee profit — it's a mathematical expectation over many rounds. Short-term variance can be brutal.
- **Kelly requires bankroll input**: The optimal bet size depends on total bankroll. Without it, use fixed small amounts.

## Complete JavaScript Reference (one-liner ready)

The full analysis pipeline fits in a single pasteable console command:

```javascript
var RR=['8','9','10','J','Q','K','A'],SS=['♦','♣','♥','♠'],PP=['一','二','三','四'];
function cc(n){n=parseInt(n);return{rank:(n-1)%7,suit:Math.floor((n-1)/7),name:RR[(n-1)%7]+SS[Math.floor((n-1)/7)]}}
function ee(cs){/* full hand evaluation with同花顺>四条>葫芦>同花>顺子>三条>两对>对子>散牌 */}
// ...simulation + strategy output...
```

Key components:
1. `cc(n)` - 28-card number to card object
2. `ee(cs)` - 5-card hand evaluation (critical: includes 同花/顺子!)
3. Monte Carlo loop (2000-20000 iterations)
4. EV calculation
5. Strategy selection + output

## Pitfalls

- **Missing hand types**: The most common bug is forgetting to include 同花 (flush, type=5) and 顺子 (straight, type=4) in the evaluation function. Without these, hands that make flushes/straights are treated as high card — completely wrong probabilities.
- **Tie handling**: When two players tie, neither is "the winner" and the trial should not count for either. Code `if (!tie) wins[best]++`.
- **Fixed bet amounts**: Kelly fractions often give non-standard amounts (e.g. ¥7). Round to valid chip sizes (¥5, ¥10, ¥50, ¥100, ¥500, etc.).
- **20000 trials ≠ guaranteed accuracy**: Statistical noise still exists. 20000 trials gives ~±0.5% accuracy. For rough estimates, 2000-5000 is enough.
