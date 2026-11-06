# -*- coding: utf-8 -*-
"""浏览器上下文 fetch 客户端（CDP）— 过 JS 质询 WAF 后打受保护端点的主工具。
请求由「已停在目标域的页面」发出 => 免挑战、带完整指纹、GET/POST 皆可。

用法:
  python cdp_fetch.py METHOD PATH [BODY|-|@file] [CTYPE|-] [HEADERS_JSON|-]
示例:
  python cdp_fetch.py GET "/api/x?p=1"
  python cdp_fetch.py POST /api/x '{"a":1}' application/json '{"x-current-path":"/reg"}'
  python cdp_fetch.py POST /register @body.txt "application/x-www-form-urlencoded" -
  python cdp_fetch.py GET /register - - -          # 大响应存 cdp_last_body.txt

环境: CDP=http://127.0.0.1:9225  OUT=.(二进制/大响应的落盘目录)
前置: chrome --headless=new --remote-debugging-port=9225 --user-data-dir=<英文路径>
      --user-agent="<正常 Chrome UA>" 启动, 并先导航目标域一次(完成挑战)。
要点: PATH 以 / 开头时相对「当前页面 origin」解析 => 先确保页面已停在目标域;
      redirect:'follow' + 回显 final URL (manual 会把 302 显示成 status 0);
      二进制(image/*)走 arrayBuffer->base64 落盘(.bin), 直接 text() 会把图转坏。
"""
import sys, os, json, base64
from playwright.sync_api import sync_playwright

CDP = os.environ.get("CDP", "http://127.0.0.1:9225")
OUT = os.environ.get("OUT", ".")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    method, path = sys.argv[1].upper(), sys.argv[2]
    body = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "-" else None
    if body and body.startswith("@"):
        body = open(body[1:], encoding="utf-8").read()
    ctype = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "-" else "application/json"
    hdrs = json.loads(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5] != "-" else {}

    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP, timeout=15000)
        ctx = b.contexts[0]
        pg = None
        for pg0 in ctx.pages:  # 按目标域选 tab, 多任务共用浏览器时防打错站
            if "http" in (pg0.url or ""):
                pg = pg0
                break
        if pg is None:
            pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        res = pg.evaluate("""async ([m, u, body, ctype, hdrs]) => {
            const opt = {method: m, credentials: 'include', redirect: 'follow',
                         headers: Object.assign({'Accept': '*/*'}, hdrs)};
            if (body) { opt.headers['Content-Type'] = ctype; opt.body = body; }
            const t0 = performance.now();
            try {
                const r = await fetch(u, opt);
                const h = {};
                r.headers.forEach((v, k) => { h[k] = v; });
                const ct = (h['content-type'] || '');
                if (ct.indexOf('image/') === 0 || ct.indexOf('application/octet-stream') === 0) {
                    const buf = new Uint8Array(await r.arrayBuffer());
                    let s = '';
                    for (let i = 0; i < buf.length; i += 8192) { s += String.fromCharCode.apply(null, buf.subarray(i, i + 8192)); }
                    return {status: r.status, url: r.url, ms: Math.round(performance.now() - t0), headers: h, b64: btoa(s), ct: ct, len: buf.length};
                }
                const t = await r.text();
                return {status: r.status, url: r.url, ms: Math.round(performance.now() - t0), headers: h, body: t};
            } catch (e) { return {err: String(e)}; }
        }""", [method, path, body, ctype, hdrs])
        if "err" in res:
            print("ERR:", res["err"])
            return
        keep = {k: v for k, v in (res.get("headers") or {}).items()
                if k.lower() in ("content-type", "location", "set-cookie", "cf-mitigated", "server", "cf-ray")}
        print("=== %s %s ===" % (method, path))
        print("status:", res["status"], "| url:", res.get("url"), "| ms:", res.get("ms"))
        print("headers:", json.dumps(keep, ensure_ascii=False)[:800])
        if res.get("b64"):
            fp = os.path.join(OUT, "cdp_last_body.bin")
            open(fp, "wb").write(base64.b64decode(res["b64"]))
            print("BINARY saved %d bytes -> %s (ct=%s)" % (res.get("len", 0), fp, res.get("ct")))
            return
        bodyt = res.get("body") or ""
        if len(bodyt) > 12000:
            fp = os.path.join(OUT, "cdp_last_body.txt")
            open(fp, "w", encoding="utf-8").write(bodyt)
            print("BODY(saved %d -> %s):" % (len(bodyt), fp))
            print(bodyt[:1500])
        else:
            print("BODY:")
            print(bodyt[:12000])


if __name__ == "__main__":
    main()
