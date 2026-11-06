// CDP 页面交互诊断探针: 打开页面 → 抓 console 错误 → 点击目标元素 → 对比 DOM 状态
// 用法: node cdp_page_probe.js <url> [<css-selector-to-click>]
// 依赖: Node >=22(内置 WebSocket); 本机 Chrome
// 注意: 若 --proxy-server 指向 127.0.0.1 必须带 --proxy-bypass-list=<-loopback>(Chrome 默认 bypass 本机)
//       headless 继承系统代理, 代理死时页面报 chrome-error —— 先 curl -x 扫代理可用性
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');

const URL = process.argv[2] || 'https://example.com/';
const CLICK_SEL = process.argv[3] || null;
const PROXY = process.argv[4] || null; // 如 'socks5://127.0.0.1:10899'
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const PORT = 9400 + Math.floor(Math.random() * 100);
const TMP = process.env.LOCALAPPDATA + '/Temp/chrome-cdp-probe-' + Date.now();
fs.rmSync(TMP, { recursive: true, force: true });

const args = ['--headless=new', '--disable-gpu', '--no-sandbox',
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${TMP}`,
  '--window-size=420,900', 'about:blank'];
if (PROXY) args.push('--proxy-server=' + PROXY, '--proxy-bypass-list=<-loopback>');
const chrome = spawn(CHROME, args, { stdio: 'ignore' });

function getJson(url) {
  return new Promise((res, rej) => {
    http.get(url, (r) => {
      let d = '';
      r.on('data', (c) => d += c);
      r.on('end', () => { try { res(JSON.parse(d)); } catch (e) { rej(e); } });
    }).on('error', rej);
  });
}
let ws;
async function cdp(method, params = {}) {
  return new Promise((res, rej) => {
    const id = Math.floor(Math.random() * 1e9);
    ws.send(JSON.stringify({ id, method, params }));
    const onMsg = (raw) => {
      const m = JSON.parse(raw.data);
      if (m.id === id) { ws.removeEventListener('message', onMsg); m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result); }
    };
    ws.addEventListener('message', onMsg);
  });
}
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

(async () => {
  let targets = [];
  for (let i = 0; i < 30; i++) {
    try { targets = await getJson(`http://127.0.0.1:${PORT}/json`); if (targets.length) break; } catch (e) {}
    await sleep(500);
  }
  // 必须连 page target(连 /json/version 的 browser 级会报 'Page.enable' wasn't found)
  const page = targets.find(t => t.type === 'page');
  if (!page) { console.log('无 page target'); chrome.kill(); process.exit(1); }
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);

  const errs = [];
  const netFails = [];
  ws.addEventListener('message', (raw) => {
    const m = JSON.parse(raw.data);
    if (m.method === 'Runtime.exceptionThrown') errs.push('EXC: ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text).slice(0, 400));
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') errs.push('CONSOLE: ' + m.params.args.map(a => a.value || a.description || '').join(' ').slice(0, 300));
    if (m.method === 'Network.loadingFailed') netFails.push(m.params.errorText + ' ' + (m.params.blockedReason || ''));
  });

  await cdp('Page.enable');
  await cdp('Runtime.enable');
  await cdp('Network.enable');
  await cdp('Page.navigate', { url: URL });

  // 页面就绪轮询(head 同步脚本/CDN 慢时会拖很久)
  let ready = false;
  for (let i = 0; i < 40; i++) {
    await sleep(1000);
    const chk = await cdp('Runtime.evaluate', { expression: `document.body && document.body.innerHTML.length > 100`, returnByValue: true });
    if (chk.result && chk.result.value === true) { ready = true; break; }
  }
  console.log('PAGE READY:', ready, '| URL:', (await cdp('Runtime.evaluate', { expression: 'location.href', returnByValue: true })).result.value);

  const st = await cdp('Runtime.evaluate', { expression: `({ title: document.title, ready: document.readyState, bodyLen: document.body ? document.body.innerHTML.length : -1 })`, returnByValue: true });
  console.log('STATE:', JSON.stringify(st.result.value));

  if (CLICK_SEL) {
    const before = await cdp('Runtime.evaluate', { expression: `(() => {
      const el = document.querySelector('${CLICK_SEL}');
      if (!el) return { found: false };
      el.click();
      return { found: true, cls: el.className };
    })()`, returnByValue: true });
    await sleep(2000);
    const after = await cdp('Runtime.evaluate', { expression: `({ href: location.href, text: document.body ? document.body.textContent.slice(0, 80) : '' })`, returnByValue: true });
    console.log('CLICK:', JSON.stringify(before.result.value));
    console.log('AFTER:', JSON.stringify(after.result.value));
  }

  console.log('ERRORS(' + errs.length + '):');
  errs.slice(0, 15).forEach(e => console.log('  ' + e));
  console.log('NETFAILS:', netFails.slice(0, 10));
  ws.close();
  chrome.kill();
  process.exit(0);
})().catch(e => { console.error('FAIL', e.message); chrome.kill(); process.exit(1); });
