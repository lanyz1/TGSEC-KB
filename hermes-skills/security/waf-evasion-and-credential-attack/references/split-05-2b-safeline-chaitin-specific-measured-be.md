## 2b. SafeLine (雷池/Chaitin) specific — measured behaviour

- It inspects **headers as well as bodies**: `authorize: ' OR 1=1-- -` gets the same 403 page as a
body payload. Do not assume header-injection is a WAF blind spot.
- It **decodes before matching**: `\u0027` JSON unicode escapes, `/**/` comment obfuscation and
case-mixing (`AnD SlEeP`) are all normalised and still blocked. Duplicate JSON keys are no help —
it parses the whole body, so the "WAF reads first key / app reads last" trick fails.
- **Chunked bodies are decoded too** — `Transfer-Encoding: chunked` does not slip past.
- **Body-size padding is not a bypass here**: it stops the 403, but anything ≥4KB turns into an
nginx `502 Bad Gateway` from the app/proxy body limit. Verify with a *benign* padded payload before
concluding a bypass — if benign 4KB also 502s, the limit is infrastructure, not a hole.
- A bare quote with no SQL keyword passes the WAF but returns the app's ordinary "not found".
**That is not evidence of SQL injection** — it only means no keyword matched. Do not chase it.
- **449/429 after high volume is a long-lived per-IP ban (tens of minutes).** Rotating to a Tor
SOCKS exit restores access immediately (`socks5h://127.0.0.1:9050`); keep the Tor path for the
rest of the session and pace at ≥2s.

