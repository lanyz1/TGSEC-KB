# Route-Existence Oracle & SPA Bundle Mining

Techniques for mapping an API surface when there is no docs, no Swagger, and
no chunk manifest — verified end-to-end against a CF-fronted Spring Boot SPA
(auth-gated, responses encrypted).

## 1. The 404-vs-wrong-method oracle

Many frameworks distinguish "no such route" from "route exists, wrong verb":

| Probe result | Meaning |
|---|---|
| `404` + app's own not-found JSON | route not registered here |
| `405` / `500` + `Request method 'POST' not supported` | **route EXISTS** |

So a single cheap verb across a large candidate list is enough to enumerate
routes. Bucket by response **shape**, not just status: some stacks answer 500
for the method-mismatch case, so `!= 404` is the usable predicate.

```python
# one probe per candidate, classify by body not just code
r = req(url, method="POST", body={})
if r.code == 404:            hit = False
elif "not supported" in r.text or r.code == 405: hit = True
```

### Context-path revelation

The 404 body often echoes the path **relative to the servlet context**, e.g.
`GET /csapi/index/info` → `{"path":"/info", ...}`. That means the deployed
context is `/csapi/index` — i.e. `/csapi/index` is a *separate module/backend*
behind the same host, not just a prefix. Use this to discover module
boundaries and then enumerate each context independently.

### Pitfall: path-variable routes poison the oracle

A registered `/server/chat/{id}` swallows `/server/chat/<anything>` and returns
200/encrypted data for every candidate — thousands of false "exists" hits.
Mitigations:

- Treat any prefix that sits under a known `{var}` route as unreliable; drop it.
- Compare response **body hashes** across candidates — identical bodies for
different paths means one catch-all, not N routes.
- Correlate with a second verb: real routes usually disagree between verbs.

Observed real-world outcome: ~2600 candidates → a genuinely tiny API surface.
That is a valid, useful answer — report "no SSRF/OOB sink exists here" instead
of assuming the enumeration failed.

## 2. Encrypted bodies as an existence signal

If normal data responses are an opaque base64/AES blob while **errors are plain
JSON**, then "base64 blob" is itself a positive existence signal. Decrypt (the
session key is usually in the bundle or an ECDH handshake endpoint) or at least
record which routes emitted ciphertext.

## 3. Bundle mining when the manifest is missing

Webpack/Vite SPAs ship an entry script only; the other chunks are named in a
manifest/url-mapper inside the runtime bundle. When it can't be extracted:

- The **served index.html** is the source of truth for the *current* build's
  entry hash (`index.web-<hash>.js`) — re-fetch it, old hashes are dead.
- A stale/incorrect chunk hash typically returns the **SPA index HTML with 200**,
  not 404. "200 + HTML instead of JS" = dead hash, not a hidden route.
- Page chunks routinely hold API paths the main bundle lacks (login component
  chunks carry the exact login payload shape). Fetch every chunk you can name.
- Static asset paths may be WAF-challenged while the API and entry HTML pass on
  the same exit — route asset fetches through an exit that returns a real body
  and validate it (a challenge page saved under a `.js` name is common).

## 4. Hardcoded config objects are history, not current state

Bundles commonly carry a product config literal, e.g.

```js
const Us = {name:"<product>", host:"legacy-default-host.example",
            httProtocol:"https", wsProtocol:"wss", encryptMode:"ecdh"}
```

Treat the `host` as the **product's historical default backend**, not the live
one. Verify before believing: resolve it, then test several `Host` headers
(including the real one) and hash the bodies. A legacy default often resolves
to a dead parked/parking-page box. Also mine the bundle for the auth scheme
(header names, ECDH/HKDF details, session header) — that is usually accurate
and current, unlike the host.
