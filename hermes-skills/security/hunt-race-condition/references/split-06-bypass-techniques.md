## Bypass Techniques

### What Defenders Implement (and How to Bypass)

**Defense: Per-user rate limiting**
- Bypass: Rate limits are checked before the action executes. Send requests simultaneously — all pass the rate-limit check before any is counted.

**Defense: Idempotency keys / unique request tokens**
- Bypass: If the server generates or reuses the token, try sending parallel requests without the token. Or check if the uniqueness check itself has a race window.

**Defense: Database unique constraints**
- Bypass: The constraint catches duplicates *after* the race. The first two may both succeed before DB enforces. Look for partial fulfillment — sometimes one succeeds and one errors but both are honored.

**Defense: Short time windows / expiring tokens**
- Bypass: Pre-stage all requests with valid tokens. Use single-packet HTTP/2 to release all in one TCP frame — server processes them in the same scheduler slot.

**Defense: Queue-based serialization**
- Bypass: Multiple queues (or multiple workers consuming the same queue) can pick up duplicate messages. Test by overwhelming the queue during the window.

**Defense: Application-layer mutex / locks**
- Bypass: Distributed systems running multiple app servers don't share in-process locks. Send requests to the same endpoint via different CDN nodes or load-balanced servers.

**Defense: "Already used" checks in application code**
- Bypass: The check and the update are separate. The check passes for both racing requests before either update completes. Only an atomic `UPDATE ... WHERE used=false RETURNING id` truly prevents this.

---

