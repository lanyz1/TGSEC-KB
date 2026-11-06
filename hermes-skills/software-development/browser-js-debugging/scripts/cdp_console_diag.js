// headless Chrome CDP 诊断: 抓 console 错误 + 实测点击行为
// 用法: node cdp_console_diag.js <URL> [CLICK_SELECTOR]
// 示例: node cdp_console_diag.js https://example.com/page "#buyBtn"
// 依赖: Node 22+(自带全局 WebSocket, 无需 npm install)
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');

const URL = process.argv[2];
if (!URL) { console.log('用法: node cdp_console_diag.js <URL> [CLICK_SELECTOR]'); process.exit(1); }
const CLICK_SEL = process.argv[3] || null;

const CHROME = process.env.CHROME_PATH
  || (process.platform === 'win32' ? 'C:/Program Files/Google/Chrome/Application/chrome.exe'
     : process.platform === 'darwin' ? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
     : '/usr/bin/google-chrome');
const PORT = 9333;
const TMP = (process.env.LOCALAPPDATA || process.env.TMPDIR || '/tmp') + '/chrome-cdp-diag';
fs.rmSync(TMP, { recursive: true, force: true });

const chrome = spawn(CHROME, [
  '--headless=new', '--disable-gpu', '--no-sandbox',
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${TMP}`,
  '--window-size=420,900', 'about:blank',
], { stdio: 'ignore' });

function getJson(url) {
  return new Promise((res, rej) => {
    http.get(url, (r) => {
      let d = ''; r.on('data', (c) => d += c);
      r.on('end', () => { try { res(JSON.parse(d)); } catch (e) { rej(e); } });
    }).on('error', rej);
  });
}
let ws;
function cdp(method, params = {}) {
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
  // 等调试端口 + 取 page target(必须 type=page, browser 级没有 Page.enable)
  let targets = [];
  for (let i = 0; i < 30; i++) {
    try { targets = await getJson(`http://127.0.0.1:${PORT}/json`); if (targets.length) break; } catch (e) {}
    await sleep(500);
  }
  const page = targets.find(t => t.type === 'page');
  if (!page) { console.log('CDP 启动失败/无 page target'); chrome.kill(); process.exit(1); }

  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);

  const errs = [];
  ws.addEventListener('message', (raw) => {
    const m = JSON.parse(raw.data);
    if (m.method === 'Runtime.exceptionThrown') {
      errs.push('EXC: ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text).slice(0, 400));
    }
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
      errs.push('CONSOLE: ' + m.params.args.map(a => a.value || a.description || '').join(' ').slice(0, 300));
    }
  });

  await cdp('Page.enable');
  await cdp('Runtime.enable');
  await cdp('Page.navigate', { url: URL });
  await sleep(9000);

  const state = await cdp('Runtime.evaluate', { expression: `({
    title: document.title,
    jq: typeof jQuery !== 'undefined',
    vue: typeof Vue !== 'undefined',
    bodyLen: document.body ? document.body.innerHTML.length : -1,
  })`, returnByValue: true });
  console.log('STATE:', JSON.stringify(state.result.value));

  if (CLICK_SEL) {
    const before = await cdp('Runtime.evaluate', { expression: `({
      href: location.href,
      selExists: !!document.querySelector(${JSON.stringify(CLICK_SEL)}),
      forms: document.querySelectorAll('form').length,
    })`, returnByValue: true });
    await cdp('Runtime.evaluate', { expression: `(() => {
      const b = document.querySelector(${JSON.stringify(CLICK_SEL)});
      if (!b) return 'no element';
      b.click(); return 'clicked';
    })()`, returnByValue: true });
    await sleep(1500);
    const after = await cdp('Runtime.evaluate', { expression: `({
      href: location.href,
      forms: document.querySelectorAll('form').length,
      bodyLen: document.body.innerHTML.length,
      clickTarget: (() => { const b = document.querySelector(${JSON.stringify(CLICK_SEL)}); return b ? {hidden: b.classList.contains('hidden'), display: getComputedStyle(b).display} : null; })(),
    })`, returnByValue: true });
    console.log('BEFORE:', JSON.stringify(before.result.value));
    console.log('CLICK:', JSON.stringify((await cdp('Runtime.evaluate', { expression: '1', returnByValue: true })).result.value) || 'ok');
    console.log('AFTER:', JSON.stringify(after.result.value));
  }

  console.log('ERRORS(' + errs.length + '):');
  errs.slice(0, 20).forEach(e => console.log('  ' + e));

  ws.close(); chrome.kill(); process.exit(0);
})().catch(e => { console.error('FAIL', e.message); chrome.kill(); process.exit(1); });
