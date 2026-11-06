## Pitfalls
- **Single-threaded testing** — race conditions require parallel requests. Curl alone can't demonstrate them reliably. Use Python `asyncio` or Burp Intruder with multiple threads.
- **TOCTOU without state change** — time-of-check-time-of-use is theoretical without demonstrating the state changed between check and use.
- **Race window too small** — if the window between check and use is microseconds, the race may be impractical. Measure the window before reporting.
- **Limit-overrun race** — coupon/credit/withdrawal races are the highest-impact. Test with exact parallel requests, not just rapid sequential.

---

