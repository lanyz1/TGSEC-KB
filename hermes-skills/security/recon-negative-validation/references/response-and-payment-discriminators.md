# Response and Payment Discriminators

## Redirect-safe API triage

Use two requests for a candidate endpoint:

```bash
curl -skS --max-time 15 -D response.headers -o response.body \
  -w 'initial=%{http_code} final=%{url_effective} bytes=%{size_download}\n' \
  --max-redirs 0 "$URL"

curl -skS --max-time 15 -L -D followed.headers -o followed.body \
  -w 'followed=%{http_code} final=%{url_effective} bytes=%{size_download}\n' \
  "$URL"
```

A `302`/`303` to a login route followed by an HTML `200` is still protected.
The initial status and `Location` header are the authoritative access-control
observation.

## Bounded PHP type differential

For a parameter documented or observed as scalar, compare only:

- parameter absent
- empty scalar
- ordinary scalar
- array-shaped value, for example `address[]=test`

Save headers and body for the smallest reproducible case. A debug page that
includes internal paths, framework/version information, or environment and
database configuration is an information-disclosure finding. Redact secrets
in reports and restrict raw evidence permissions. Do not label the result SQLi
or RCE without an independent sink and impact proof.

## Wallet flow classification

Inspect front-end code without invoking a wallet. Classify the actual ERC-20
method:

- `approve(spender, amount)`: allowance grant
- `transfer(to, amount)`: direct token movement
- `transferFrom(from, to, amount)`: movement using an allowance

Record chain, token contract, destination, amount source, and whether the
server accepts a submitted transaction hash. Use read-only RPC calls for
account/code/balance/transaction metadata. Do not sign, broadcast, or submit a
real registration or payment during recon.
