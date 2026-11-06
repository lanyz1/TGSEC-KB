# In-browser request forging + page driving (CDP recipe)

Use when a WAF/geo/bot wall blocks scripted clients but the real renderer passes, and
the app's calls are encrypted/session-bound so you cannot just hand-roll them.

## 0. Shape of the solution

Real Chromium = transport + session. Your Python = orchestrator over CDP
(`websocket-client` + `http://127.0.0.1:9222/json/new?<url>` / `/json/list`).
Inject a small toolkit into the page once, then call it repeatedly:

```python
cmd('Runtime.evaluate', expression=JS, returnByValue=True, awaitPromise=True)
```

## 1. The injected toolkit (shape)

```js
(() => { if (window.__T) return 'ready';
  const b64d = s => { const b=atob(s), u=new Uint8Array(b.length);
                      for (let i=0;i<b.length;i++) u[i]=b.charCodeAt(i); return u; };
  const b64e = u => { let s=''; for (let i=0;i<u.length;i++) s+=String.fromCharCode(u[i]); return btoa(s); };
  const tok = () => (document.cookie.match(/TOKEN=([^;]+)/)||[])[1];
  const uid = () => (document.cookie.match(/UUID=([^;]+)/)||[])[1];
  window.__T = {
    key:  async () => (await (await fetch('/<svc>/api/v1/front/Hf6dtBdmHx',
            {method:'POST',headers:{'Content-Type':'application/json'},body:'{}',credentials:'include'})).json()),
    enc:  async (o,k,v) => { /* WebCrypto AES-CBC as in SKILL.md step 6 */ },
    dec:  async (c,k,v) => new TextDecoder().decode(await crypto.subtle.decrypt(
            {name:'AES-CBC', iv: b64d(v)}, await crypto.subtle.importKey('raw', b64d(k),
            {name:'AES-CBC'}, false, ['decrypt']), b64d(c))),
    call: async (path, obj) => { const K=await window.__T.key();
            const r = await fetch(path, {method:'POST',
              headers:{'Content-Type':'application/json;charset=UTF-8', ...requiredHeaders},
              body: JSON.stringify({x: await window.__T.enc(obj, K.k, K.v)}), credentials:'include'});
            let j = JSON.parse(await r.text());
            if (j && j.x) j = JSON.parse(await window.__T.dec(j.x, K.k, K.v));
            return j; } };
  return 'ok token=' + (tok()||'NONE').slice(0,12); })()
```
Always read the token/UUID **from cookies, not localStorage** — apps frequently keep a
stale copy in localStorage while the live pair lives in the cookie.

## 2. Re-auth fully inside the page

Landing pages are often only a shell: the login FORM appears after clicking 「登录」.
Typical H5 login flow: click 登录 → fill → click the captcha input to trigger the blob
image → read it → submit.

## 3. Driving React / mobile-H5 forms (ordered ladder)

Synthetic DOM events are NOT enough on component-library forms — the controlled input
never updates, and the submit silently does nothing (no request at all). Escalate:

| # | Attempt | Works when |
|---|---|---|
| 1 | native setter + `dispatchEvent(new Event('input'))` | plain React controlled input |
| 2 | **`Input.insertText`** after a real click (focus) | always — trusted input, use this first for text |
| 3 | real mouse events `mousePressed`/`mouseReleased` at the button centre | desktop layouts |
| 4 | **`Input.dispatchTouchEvent` (touchStart/touchEnd)** | mobile H5 — tell-tale: `onTouchStart`/`onMouseDown` in the element's `__reactProps`; mouse clicks produce nothing |
| 5 | `form.requestSubmit()` (fires React `onSubmit`) | button type=submit |
| 6 | call the element's own `__reactProps[...].onClick(...)` | last resort, for logging |

Diagnostics before blaming the UI:
- `document.elementFromPoint(cx, cy)` at the button centre — if it is not the button, an
  overlay eats the click (watermark/screenshot-deterrent layers usually set
  `pointer-events:none`, full-screen absolute divs do not).
- `getBoundingClientRect()` on the WRONG element gives a corner, not the centre —
  resolve the real `<button>` by tag/class, then use its rect midpoint.
- Inspect `Object.keys(el).find(k => k.startsWith('__reactProps'))` to see which
  handlers exist (`onClick` vs `onTouchStart`) — this is what tells you to jump to rung 4.
- **No network request at all** = validation or state, not transport. Watch the request
  in-page with an injected `fetch`/`XHR` wrapper rather than guessing.

## 4. Captcha loop that actually passes

- Pull the image from the **API** when one exists (it returns a bare PNG plus a
  session id in a response header, e.g. `x-code`) — the DOM blob may be a stale copy.
- Upscale ×4 nearest-neighbour before OCR/vision. At native 130×50 an OCR engine
  misreads mixed-case strings; at 4× it is reliable.
- Login image captchas are frequently **case-insensitive** — test lowercase before
  assuming the read failed.
- The id header is single-use and short-lived: fetch → read → submit in one go, and on
  failure re-fetch rather than retrying the old id (a stale id returns a generic error
  that looks like a wrong code).
