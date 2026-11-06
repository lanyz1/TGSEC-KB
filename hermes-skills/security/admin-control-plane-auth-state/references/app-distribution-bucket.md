# Public app-distribution buckets (WGT / uni-app)

Use when a bucket listing shows `app/*.json`, `app/*.wgt`, or
`app-tool/*.json`. This is a mobile app update/distribution bucket, not a
source repository; do not expect admin-server source code there.

## What the keys mean

- `app/<brand>.json` — app/update manifest for one brand.
- `app/<brand>_<version>.wgt` — a uni-app package (a ZIP archive).
- `app-tool/<tool>.json` — operator/utility app config, not necessarily an
  admin panel.
- A bucket can host several brands. Identify the target brand from its name and
  from the API base in its config; a second brand is a sister app, not
automatically in scope.

## Downloading and parsing a WGT

- Test `GET /<key>` separately from the list operation. A 200 list response
  does not mean the object is public; a 403 object under a listable bucket is
  private, and wildcard retries will not help.
- WGTs can be tens of MB; use a bounded download with a timeout and save to a
  case directory. Do not paste app bundles or tokens into the chat.
- `python3 -c 'import zipfile; ...'` can list entries without `unzip`.
- Look for `app-service.js`, `app-config.js`, `app-config-service.js`, and
  `manifest.json`; grep for API base URLs, `baseURL`, `VITE_`, `ws`, app ids,
  and invitation/registration fields. These often reveal the live API surface
  and the next host to test.

## Scope and expectations

- The bucket is distribution infrastructure, not a root path. Finding it does
  not mean the app backend is weak.
- Apply the same-IP/homepage-JS test to any sister brand; otherwise leave it
  alone and say so in the report.
- If the target app's WGT contains a new API host, treat that host as a new
  target only after the same relation check; do not attack a random third-party
  API found in a bundled SDK.
