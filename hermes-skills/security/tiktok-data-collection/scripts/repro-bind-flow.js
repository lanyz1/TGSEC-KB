/**
 * TikFlow 绑定链路复现探针(2026-08-16 验证,Orca 拦截排查用)
 *
 * 在服务器上复现绑定采集流程:本地认证桥(带认证 SK5 → HTTP CONNECT)+ headless shell
 * + 注入 CK,然后判别三个接口:
 *   A. profile SSR          → 登录态是否有效
 *   B. recommend/item_list  → 签名器/IP 是否正常
 *   C. post/item_list       → 是否被 Orca 拦成 200 空包(响应头 tt_orcas_res:1)
 *
 * 用法(服务器 /srv/tikflow 下,复用项目 node_modules 的 puppeteer-core + socks):
 *   node /tmp/repro-bind-flow.js '<socks5://u:p@h:port>' <ck文件> '@handle' [chrome_exe]
 *
 * 输出解读:
 *   profile.user 有值 + recommend.len>0 + post.len=0 + post.tt_orcas_res='1'
 *   → Cookie 有效、签名器正常、是 Orca 接口级拦截 → 别当"Cookie 失效"处理
 */
const puppeteer = require("puppeteer-core");
const { SocksClient } = require("socks");
const http = require("node:http");
const fs = require("node:fs");

const args = process.argv.slice(2);
const proxyRaw = args[0], ckFile = args[1], handle = args[2];
const CHROME = args[3] || "/opt/chromium/chrome-headless-shell-linux64/chrome-headless-shell";
if (!proxyRaw || !ckFile || !handle) {
  console.error('用法: node repro-bind-flow.js "<socks5://u:p@h:port>" <ck文件> "@handle" [chrome_exe]');
  process.exit(1);
}

function startBridge(proxyHost, proxyPort, user, pass) {
  const server = http.createServer((_req, res) => { res.writeHead(502); res.end("bridge: https only"); });
  server.on("connect", (req, clientSocket, head) => {
    const [host, portStr] = req.url.split(":");
    const port = Number(portStr);
    SocksClient.createConnection({
      proxy: { host: proxyHost, port: proxyPort, type: 5, userId: user || undefined, password: pass || undefined },
      command: "connect", destination: { host, port },
    }).then(({ socket }) => {
      clientSocket.write("HTTP/1.1 200 Connection Established\r\n\r\n");
      if (head && head.length) socket.write(head);
      socket.pipe(clientSocket); clientSocket.pipe(socket);
      socket.on("error", () => clientSocket.destroy());
      clientSocket.on("error", () => socket.destroy());
    }).catch(() => clientSocket.destroy());
  });
  server.on("error", () => {});
  return new Promise((resolve) =>
    server.listen(0, "127.0.0.1", () => resolve({ port: server.address().port, close: () => server.close() })),
  );
}

(async () => {
  const m = proxyRaw.trim().match(/^socks5h?:\/\/(?:([^:@/]+):([^@/]*)@)?([^/\s]+)$/i);
  if (!m) { console.error("代理格式不对(须 socks5://u:p@h:port)"); process.exit(1); }
  const [, user, pass, host] = m;
  const sep = host.lastIndexOf(":");
  const bridge = await startBridge(host.slice(0, sep), Number(host.slice(sep + 1)), user, pass);
  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: true,
    args: ["--no-sandbox", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
           "--disable-dev-shm-usage", "--remote-allow-origins=*",
           `--proxy-server=http://127.0.0.1:${bridge.port}`, "about:blank"],
    defaultViewport: null,
  });
  browser.on("disconnected", () => bridge.close());
  const page = await browser.newPage();
  page.setDefaultTimeout(30000);
  await page.setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36");
  const ck = fs.readFileSync(ckFile, "utf-8");
  const pairs = ck.split(";").map(s => s.trim()).filter(Boolean).map(p => {
    const i = p.indexOf("=");
    return i > 0 ? { name: p.slice(0, i).trim(), value: p.slice(i + 1).trim() } : null;
  }).filter(Boolean);
  await page.setCookie(...pairs.map(c => ({ name: c.name, value: c.value, domain: ".tiktok.com", path: "/", httpOnly: true })));

  const clean = handle.replace(/^@/, "").trim();
  const t0 = Date.now();
  await page.goto(`https://www.tiktok.com/@${encodeURIComponent(clean)}`, { waitUntil: "domcontentloaded", timeout: 40000 });
  await page.reload({ waitUntil: "networkidle2", timeout: 45000 });
  await page.waitForSelector("#__UNIVERSAL_DATA_FOR_REHYDRATION__", { timeout: 20000 });
  await page.waitForFunction(() => {
    const w = window;
    return !!(w.byted_acrawler && typeof w.byted_acrawler.frontierSign === "function");
  }, { timeout: 12000 }).catch(() => {});
  await new Promise(r => setTimeout(r, 4000));

  const res = await page.evaluate(async () => {
    const out = { profile: null, recommend: null, post: null };
    const el = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");
    if (el) {
      try {
        const d = JSON.parse(el.textContent).__DEFAULT_SCOPE__;
        const ud = d["webapp.user-detail"];
        const ctx = d["webapp.app-context"] || {};
        out.loggedInUser = ctx.user ? ctx.user.uniqueId : null;
        if (ud && ud.userInfo && ud.userInfo.user) {
          const u = ud.userInfo.user;
          out.profile = {
            uniqueId: u.uniqueId,
            nickname: u.nickname,
            videoCount: ud.userInfo.stats.videoCount,
            followerCount: ud.userInfo.stats.followerCount,
            statusCode: ud.statusCode,
          };
          const url = "/api/post/item_list/?uniqueId=" + encodeURIComponent(u.uniqueId) +
            "&secUid=" + encodeURIComponent(u.secUid) + "&count=30&cursor=0&aid=1988";
          const r = await fetch(url, { credentials: "include" });
          const t = await r.text();
          out.post = {
            status: r.status, len: t.length,
            tt_orcas_res: r.headers.get("tt-orcas-res"),
            bd_tt_error_code: r.headers.get("bd-tt-error-code"),
            head: t.slice(0, 60),
          };
        }
      } catch (e) { out.profile = { parseError: e.message }; }
    } else {
      out.profile = { error: "no_ssr(页面可能被拦/代理不通)" };
    }
    try {
      const r2 = await fetch("/api/recommend/item_list/?aid=1988&count=30", { credentials: "include" });
      const t2 = await r2.text();
      out.recommend = { status: r2.status, len: t2.length, head: t2.slice(0, 60) };
    } catch (e) { out.recommend = { error: e.message }; }
    return out;
  });

  console.log("ELAPSED_MS:", Date.now() - t0);
  console.log(JSON.stringify(res, null, 1));
  const p = res.profile, rc = res.recommend, po = res.post;
  if (p && p.uniqueId && rc && rc.len > 0 && po && po.len === 0 && String(po.tt_orcas_res) === "1") {
    console.log("=> 判定: Cookie 有效 + 签名器正常 + post/item_list 被 Orca 接口级拦截(非 Cookie 失效)");
  } else if (p && p.uniqueId && rc && rc.len > 0 && po && po.len > 0) {
    console.log("=> 判定: 全链路正常,绑定应能成功");
  } else {
    console.log("=> 判定: 未命中已知模式,按 profile/recommend/post 结果人工分析");
  }
  await browser.close().catch(() => {});
  bridge.close();
  process.exit(0);
})().catch(e => { console.error("FATAL:", e.message); process.exit(1); });
