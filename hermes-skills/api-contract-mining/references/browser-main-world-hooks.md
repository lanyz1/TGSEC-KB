# Mining a live SPA's contract with main-world hooks

Use when the bundle is minified past usefulness and you must know the EXACT bytes the app sends
(field names, header set, plaintext payload) — e.g. to reimplement the protocol in Python, or to
prove your replica is byte-identical before blaming the server.

## The isolated-world trap
Playwright `page.evaluate()` runs in an **isolated world**: monkey-patching `window.fetch`,
`XMLHttpRequest` or `JSON.stringify` there is invisible to the page's own code. Symptom: hook
installs fine, capture array stays empty (`XHRs: []`).

Fix (Firefox/Camoufox): create a script element with the hook source in the page's main world:

```python
src = """
(() => {
  const log = [];  window.__cap = log;
  const of = window.fetch;
  window.fetch = function(...a) { try { if (!(a[1] && a[1].__skip))
      log.push({u: String(a[0]), o: a[1] && {...a[1], body: (a[1].body||'').toString().slice(0,4000)}});
  } catch(e){} return of.apply(this, a); };
  const os = JSON.stringify;
  JSON.stringify = function(v){ try { log.push({json: os(v).slice(0,4000)}); } catch(e){} return os(v); };
  const op = XMLHttpRequest.prototype.open, osd = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(m,u){ this.__u=String(u); this.__m=m; return op.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function(b){ try { log.push({u:this.__u, body:String(b).slice(0,4000), ct:this.getRequestHeader && this.getRequestHeader('content-type')}); } catch(e){} return osd.apply(this, arguments); };
})();
"""
p.evaluate("s => { const e=document.createElement('script'); e.textContent=s; document.documentElement.appendChild(e); }", src)
# read back
cap = p.evaluate("window.__cap || []")
```

Then read `window.__cap` back — plain Python values, no CDP needed.

## Reverse direction: pushing data IN
Synthesise events from the main world by **setting a DOM attribute** and dispatching an event, then
read it from Python (`p.get_attribute(sel, 'data-x')`). Keep an in-memory inbox for the page side so
you can hand it commands batch by batch instead of one `evaluate` round trip per item.

## Pitfall: hooks vs. the captcha widget
Install the hook **after** the challenge widget has produced its token, or after you've grabbed the
token — a hook that re-writes `JSON.stringify` app-wide early can disturb the widget's callback and
yield `token 0`. Grab the token first, then inject.

## What this buys you (real example)
On a Turnstile-protected ECDH/AES SPA the hook gave, verbatim:
- handshake: `POST /csapi/crypto/handshake`, headers `{accept, content-type: application/json, cf-turnstile-token: <tok>}`, body `{"clientPubKey":"<base64 65-byte P-256 point>"}`
- login: `POST /csapi/login`, headers `{accept, content-type: text/plain, x-session-id: <sid>}`, body = base64 AES ciphertext
- and via the `JSON.stringify` hook, the **plaintext** payload: `{"username":"...","password":"...","theme":"default"}`

Reconcile that against your Python replica field by field before concluding the server rejects you.

## When a perfect replica still fails
A confirmed byte-identical replica (same headers, cookie, session id, payload, AND egress IP) that
still returns the app's "session invalid" code means the gate is bound to something you cannot
forge from a script (browser TLS/HTTP2 profile, connection reuse, or an in-page keepalive that
re-handshakes and supersedes your session).
Do NOT burn hours re-deriving the crypto. Switch to driving the real UI in the browser for the
authenticated calls — or, better, find a second panel of the same operator that authenticates with a
plain bearer token instead of a session cookie (those are scriptable from Python directly).
