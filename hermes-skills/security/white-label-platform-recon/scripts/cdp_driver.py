#!/usr/bin/env python3
"""Minimal CDP driver: drive a system Chromium over websocket when the built-in
browser harness cannot see it. No Playwright/Selenium needed.

Deps: pip install websocket-client      (urllib is stdlib)

Launch once, outside this script:
    /snap/bin/chromium --headless=new --no-sandbox --disable-gpu \
        --remote-debugging-port=9222 --remote-allow-origins=* about:blank

Then use as a library:
    b = Browser("71j8yy")            # substring match on an open tab's URL
    b.navigate("https://target/reg")
    b.fill_react("input[placeholder*=账号]", "user1")
    b.grab_blob_captcha("cap.png")
    b.click(200, 583); b.click_text("确认")
    print(b.text())

Set env: this box may carry a Tor proxy in http(s)_proxy / ALL_PROXY which breaks
Chromium's own fetching. Pop them in-process before launching the browser.
"""
import base64, json, os, time, urllib.request

try:
    import websocket
except ImportError:  # pragma: no cover
    raise SystemExit("pip install websocket-client")

for _k in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy",
           "HTTPS_PROXY", "https_proxy"):
    os.environ.pop(_k, None)

CDP = os.environ.get("CDP_URL", "http://127.0.0.1:9222")
SET_VALUE = (
    "const d = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
)


class Browser:
    def __init__(self, url_match="", timeout=60):
        self._mid = 0
        tabs = [t for t in self._http("/json/list") if url_match in (t.get("url") or "")]
        if not tabs:
            js = self._http("/json/new?about:blank", method="PUT")
            tabs = [js]
        self.tab = tabs[0]
        self.ws = websocket.create_connection(
            self.tab["webSocketDebuggerUrl"], timeout=timeout, suppress_origin=True)
        self.cmd("Page.enable")
        self.cmd("Runtime.enable")

    @staticmethod
    def _http(path, method="GET"):
        req = urllib.request.Request(CDP + path, method=method)
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode() or "{}"
        return json.loads(body)

    def cmd(self, method, **params):
        self._mid += 1
        self.ws.send(json.dumps({"id": self._mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self._mid:
                return msg

    def js(self, expr, await_promise=True):
        r = self.cmd("Runtime.evaluate", expression=expr, returnByValue=True,
                     awaitPromise=await_promise)
        try:
            return r["result"]["result"].get("value")
        except (KeyError, TypeError):
            return None

    def navigate(self, url, settle=8):
        self.cmd("Page.navigate", url=url)
        time.sleep(settle)
        return self.js("location.href")

    def text(self, limit=1500):
        return str(self.js("document.body.innerText.slice(0,%d)" % limit))

    def toasts(self):
        """Validation/error text rendered by most SPAs on submit."""
        return self.js("JSON.stringify(Array.from(document.querySelectorAll("
                       "'[class*=toast],[class*=message],[class*=error],[class*=tip],"
                       "[class*=Modal]')).map(e=>(e.innerText||'').trim())"
                       ".filter(Boolean).slice(0,8))") or "[]"

    def inputs(self):
        return self.js("JSON.stringify(Array.from(document.querySelectorAll('input'))"
                       ".map(i=>({ph:i.placeholder,type:i.type,val:i.value})))")

    @staticmethod
    def _fill_js(sel, value):
        return ("(() => { const el = document.querySelector(%s); if (!el) return 'NOSEL';"
                " %s d.call(el, %s); el.dispatchEvent(new Event('input',{bubbles:true}));"
                " el.dispatchEvent(new Event('change',{bubbles:true})); return el.value; })()"
                % (json.dumps(sel), SET_VALUE, json.dumps(value)))

    def fill(self, selector, value):
        """React/Vue controlled inputs: assigning .value does NOT register.
        Must use the native setter + input/change events."""
        return self.js(self._fill_js(selector, value))

    def fill_by_placeholder(self, needle, value):
        sel = "input[placeholder*=%s]" % json.dumps(needle)
        return self.fill(sel, value)

    def click(self, x, y):
        for ev in ("mousePressed", "mouseReleased"):
            self.cmd("Input.dispatchMouseEvent", type=ev, x=int(x), y=int(y),
                     button="left", clickCount=1)
            time.sleep(0.09)
        time.sleep(0.5)

    def click_rect(self, selector):
        r = self.js("(() => { const e=document.querySelector(%s); if(!e) return null;"
                    " const r=e.getBoundingClientRect();"
                    " return JSON.stringify({x:Math.round(r.x+r.width/2),"
                    " y:Math.round(r.y+r.height/2)}); })()" % json.dumps(selector))
        if r:
            o = json.loads(r)
            self.click(o["x"], o["y"])
        return r

    def click_text(self, label):
        return self.js("(() => { const els=Array.from(document.querySelectorAll("
                       "'button,a,div,span')); const b=els.filter(e=>%s.includes("
                       "(e.innerText||'').trim())); if(!b.length) return 'NOBTN';"
                       " b[b.length-1].click(); return 'CLICKED'; })()"
                       % json.dumps([label]))

    def screenshot(self, path, scale=3):
        """scale=3 (deviceScaleFactor) is what made small captcha glyphs legible."""
        if scale != 1:
            self.cmd("Emulation.setDeviceMetricsOverride", width=500, height=900,
                     deviceScaleFactor=scale, mobile=False)
        r = self.cmd("Page.captureScreenshot", format="png")
        data = r.get("result", {}).get("data")
        if data:
            open(path, "wb").write(base64.b64decode(data))
        return path if data else None

    def grab_blob_captcha(self, path, min_w=60, max_w=400):
        """Captchas are usually a `blob:` <img>; logos are `data:` and larger.
        Pick the blob, rasterise via canvas, write a PNG for vision OCR."""
        d = self.js("""(async () => {
            const imgs = Array.from(document.querySelectorAll('img'))
              .filter(i => (i.src||'').startsWith('blob:') && i.naturalWidth>%d && i.naturalWidth<%d);
            if (!imgs.length) return 'NOBLOB';
            const img = imgs[0], c = document.createElement('canvas');
            c.width = img.naturalWidth; c.height = img.naturalHeight;
            c.getContext('2d').drawImage(img,0,0);
            return JSON.stringify({w:img.naturalWidth,h:img.naturalHeight,b64:c.toDataURL('image/png')});
        })()""" % (min_w, max_w))
        if not d or not str(d).startswith("{"):
            return None
        j = json.loads(d)
        open(path, "wb").write(base64.b64decode(j["b64"].split(",")[-1]))
        return j

    def api_calls(self, n=20):
        """Every XHR/fetch the SPA made — the cheapest route inventory."""
        return self.js("JSON.stringify(performance.getEntriesByType('resource')"
                       ".map(r=>r.name).slice(-%d))" % n)

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


if __name__ == "__main__":
    import sys
    b = Browser(sys.argv[1] if len(sys.argv) > 1 else "")
    print("url   :", b.js("location.href"))
    print("title :", b.js("document.title"))
    print("inputs:", b.inputs())
    print("calls :", b.api_calls())
    b.close()
