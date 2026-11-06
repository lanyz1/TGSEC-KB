// CF-internal probe: fetch a candidate origin FROM Cloudflare's network with a Host override.
// Deploy: dash.cloudflare.com -> Compute (Workers) -> Create -> Deploy -> Edit code -> paste -> Deploy.
// Use:    https://<name>.workers.dev/?u=http://47.91.170.222/&h=www.example.com
//         https://<name>.workers.dev/?u=https://47.91.170.222/&h=www.example.com
// WHY the h= matters: fetch("https://<ip>/") sends SNI = the bare IP, which a vhost-based origin
// rejects at TLS -> you get a false "dead". Plain http:// needs no SNI and nginx still routes on Host.
// ALWAYS run a known-alive control IP through the same code path in the same batch.
// If the runtime rejects the Host override the error comes back verbatim in the response.
export default {
  async fetch(req) {
    const p = new URL(req.url).searchParams;
    const u = p.get('u'), h = p.get('h');
    if (!u) return new Response('usage: ?u=<url>&h=<host>', { status: 400 });
    const init = { redirect: 'manual', cf: { cacheTtl: 0 } };
    if (h) init.headers = { Host: h };
    try {
      const t0 = Date.now();
      const r = await fetch(u, init);
      const b = await r.text();
      return Response.json({
        url: u, host: h || null, status: r.status, ms: Date.now() - t0,
        server: r.headers.get('server'), ct: r.headers.get('content-type'),
        len: b.length, body: b.slice(0, 800),
        headers: Object.fromEntries([...r.headers].slice(0, 25)),
      });
    } catch (e) {
      return Response.json({ url: u, host: h || null, status: null, error: String(e) });
    }
  },
};
