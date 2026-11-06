# Client-side request signature scheme — reverser's notes

When an API rejects everything with "invalid signature"/"无效签名", the signing code is almost
always **shipped to the browser**. Recover it from the bundle instead of guessing.

## Locating the signer in a bundle

Search the JS (and any sourcemaps) for:

```
interceptors.request   axios.create   sign:   'sign'   apiKey   api_key   appKey
md5(  CryptoJS   JSEncrypt   encrypt(   timestamp   timer   nonce
```

A Vue/Element-UI admin SPA typically exposes it as a one-liner request interceptor:

```js
const r = {};
Object.keys(params).sort().forEach(k => { r[k] = params[k]; });   // ksort by key
let s = Object.values(r).join('') + apiKey;                       // concat values, append secret
config.headers.sign = md5(s).toUpperCase();
config.headers.timer = Date.now();   // or a seconds timestamp
```

So the canonical scheme is:

```
sign = UPPER(md5( concat(values sorted by key) + apiKey ))
```

with `timer`/`lang` merged into the signed parameter set (some builds sort *all* params including
the injected ones — reproduce the exact merge order, it changes the digest).

## Extracting the secret

Multiple SPAs (`admin.*`, `agent.*`, `channel.*`) usually mean multiple bundles and **different
apiKeys**. Grep every bundle and keep a table of bundle → apiKey → the header names it sends.
Also grep for a second-layer secret (`httpSignSecret`, `SIGN_SECRET`, `GATE_SECRET`) — those are
what upstream gateway/`proxy` calls use, and they are worth trying as DB/service credentials too.

## Forging requests

Implement the digest in Python (`hashlib.md5`) or reuse the bundle's own crypto in Node — and
include the same `timer`/`lang` params the client sends, since a stale timestamp or missing
parameter changes the digest. A signed request that returns a normal payload (e.g.
`{"success":true,...}`) *proves* the middleware accepted the forgery.

## Verify which wall rejects you — signature is only the first

Passing the signature is not auth. Read the rejection string and map the layer:

| Response | Meaning |
|---|---|
| `无效签名` / `invalid sign` | signature scheme wrong (or param merge order differs) |
| `无法识别请求来源` / origin error | signature OK, **Origin allowlist** middleware rejects the call site |
| `404` on an unsigned/signed request | route does not exist — do not read this as an auth failure |
| empty body, 200 | route exists, controller returned nothing (auth-scoped data, or dev env) |
| `请登录` / token error | final token gate — you now need a session, not a better signature |

Sketch of a real target: signature middleware reversed and bypassed, but a second Origin
middleware (allow-listing registered client hosts) still returned `无法识别请求来源` for every
data endpoint — so a broken signature alone did **not** open the data plane. Expect layered
middleware and budget for it.

## Route surface harvesting

Regex every bundle for quoted absolute paths (`"/adminapi/..."`, `"/channelapi/..."`) and for
route tables; that yields hundreds of paths including ones absent from the UI. Then **classify by
status**: 404 = no route, 401/`请登录` = auth-walled, 200 = live. Classifying beats spraying and
prevents the classic misread "my signed request 404'd, so the bypass failed".

Pitfalls:

- Candidate origins harvested from bundle URLs (thousands of them) are **not** an Origin
  allowlist — Origin checks usually match registered API hosts, so fuzzing bundle URLs mostly
  produces crashes on a dev deployment.
- Development deployments (`projectName: "...dev"`) may answer `success` with empty data; confirm
  the dataset exists before treating an open endpoint as a finding.
- Client-side encryption of credentials (`encryptionPassword`) can be raw RSA `NoPadding` rather
  than PKCS#1 — a mismatch makes every correct password look wrong.
