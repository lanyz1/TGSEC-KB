## Pitfalls
- Don't clear a route from one method — a read-path role check frequently does not cover the write path.
- Don't accept a 200 as success on a Go backend: gin/echo/fiber silently discard JSON fields with the wrong type and
  return 200 with an **empty body**. Verify with Set-Cookie / a known-good error shape, not the status code.
- Don't paste credentials into the summary document — record existence + path, keep values in the loot pack.
- Note **your own** test accounts when you later loot the user table (`sec_research_*`) — they pollute analysis and
  prove you were there.
- **Never name a helper function after a stdlib module you call inside it.** `def http(...)` shadows `http.client`, and
  the failure surfaces late and misleadingly (`'function' object has no attribute 'client'`) long after the probe logic
  looks correct. Name request helpers `req()` / `post_json()`; check your own imports before blaming the target.
