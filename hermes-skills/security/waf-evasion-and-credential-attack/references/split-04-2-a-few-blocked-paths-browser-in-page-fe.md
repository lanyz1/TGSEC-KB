## 2. A few blocked paths — browser in-page fetch

Load the real SPA, then issue the request from inside the page context. Same-origin absolute URLs
return real business responses because the request carries the browser fingerprint and any CDN
clearance cookies:

```python
new_tab("https://TARGET"); wait_for_load()      # navigate FIRST
js("""(async () => {
  const r = await fetch('https://TARGET/wuquan/userApi/userLogin', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({...})});
  return await r.text();
})()""")
```

Pitfalls:
- Navigate to the origin before reading `localStorage`/`sessionStorage` — on `about:blank` the eval
dies with a `SecurityError` and the whole batch is lost.
- Each eval has a ~5s budget: 5-6 requests per call, drive the loop from the harness. A long
in-page `sleep()` never returns.
- **The bypass is ephemeral.** After a few hundred calls the browser's own IP is flagged and
`fetch` starts returning the WAF HTML too. Use it to READ a handful of otherwise-blocked
endpoints, never as the brute-force transport. A fresh context/cooldown is the only reset.
- Relative URLs break when the tab is not on the origin — use the absolute same-origin URL.
- **Use the page's own stack to capture encrypted payloads and to finish gated form flows.** When a
register/login form works manually in the browser but your API-side reconstruction keeps stalling on
required fields, drive the browser instead of guessing: intercept `window.fetch` and
`XMLHttpRequest.prototype.send`, submit the form once with a KNOWN value, and read the exact request
body — that single submission settles the field names AND the crypto format you must re-implement
(§7). Then read `localStorage` for the session token it issued. One real submission ends a round of
blind field-guessing.
- **In-page fetch defeats a CHALLENGE, never a RULE.** If a path still returns the WAF block page from a
real browser session that is already sitting on the app — on every method — no amount of fingerprint
realism or cookie warm-up clears it, and the browser only adds risk because its IP gets flagged next.
Tell the two apart in one call: a challenge resolves itself after the JS runs, a rule returns the same
static block page immediately. A blocked path also proves nothing about the route's existence — a CF
rule matching a literal like `auth/login` fires whether or not the endpoint was ever configured, so
treating that 403 as "route exists, WAF-protected" aims the whole campaign at nothing.

