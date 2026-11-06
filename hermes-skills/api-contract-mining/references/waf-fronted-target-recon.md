# Recon Against a WAF-Fronted Target (and a Banned Egress)

When the target sits behind Cloudflare/WAF and your own IP is the thing being
blocked, every probe "fails" for a reason that has nothing to do with the API.
Separate the two failure modes before drawing any conclusion about the surface.

## Classify the block first

- **URL-scoped** — one path/asset challenged, siblings on the same host fetch
  fine. Path variants may help.
- **Egress-scoped** — every route on the host returns the same challenge, and
  so do other CF-fronted services you call. This is your IP, not the target's
  route table.

Tell-tale of an egress-scoped block: a third-party CF-fronted API you rely on
(space-engine query API, verification service, docs site) suddenly starts
returning challenge HTML too. Don't file that as "the service is down" — route
the call through the working exit instead.

Measured non-solutions against a path-scoped WAF rule: `//assets`, `/assets/./`,
`/assets%2f`, `X-Original-URL`, `X-HTTP-Method-Override`. None bypass; don't
spend a batch on them.

## Rotate the exit (cheapest first)

1. A cheap proxy/VPS in a different ASN or jurisdiction. Measured: an HK exit
   returned the SPA + a 656 KB bundle with 200 while the host's own IP was
   1020-banned.
2. A free HTTP proxy pool — maintain a validated file of live `ip:port`
   (`PROXIES_OK.txt` style), probe each with one cheap GET, keep only those
   whose body lacks challenge markers, and note the country/ASN.
3. Tor SOCKS with per-request isolation (`IsolateSOCKSAuth`) for a fresh exit
   per request.

Pin the exit that works for the session, but **re-validate before each batch**
— a good exit rots within minutes. A dead proxy returns its own 502/504, which
is easy to misread as the target refusing you; always record which exit produced
each artifact so a finding is reproducible.

WAF verdicts are also method-scoped: an exit can pass POST while GETs are
probabilistically challenged (or the reverse — a POST-only block returning an
empty 500 while GETs stay 200). Do not conclude "endpoint gone" from one verb.

## Validate the body, not the status

A 200 with a saved file proves nothing:

- CF challenge bodies are a few KB of HTML saved **under the asset's name**
  (`/assets/index.web-<hash>.js` → challenge HTML).
- Reject bodies containing `Just a moment`, `Attention Required`,
  `Enable JavaScript and cookies to continue`, `cf-chl`, `challenge-platform`,
  or a login-redirect `<meta>`/JS stub.
- Size floors and expected-string checks catch the rest.

## Assets vs API tolerance

On one CF-fronted SPA: entry HTML and the hashed main bundle fetched 200 via a
rotated exit while `/assets/*.js` chunks stayed challenged. Enumerate what the
stack will actually give you, then mine that subset — and keep the fetch helper
parameterised by (url, exit, headers) so a new exit can be dropped in without
rewriting the batch.

## Untrusted relays

For anything a user will rely on, don't send cookies/credentials through a
random public proxy — a relay is a man-in-the-middle by construction. Use
rotated exits for unauthenticated recon (banners, bundles, public endpoints),
and keep authenticated traffic on exits you control.
